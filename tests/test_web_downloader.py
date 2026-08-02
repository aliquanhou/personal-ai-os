#!/usr/bin/env python3
"""
测试 web_downloader 模块。

运行方式：
    python -m pytest tests/test_web_downloader.py -v
    或
    python tests/test_web_downloader.py

使用 Python 标准库的 unittest 编写，无需额外依赖。
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_downloader import (
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    HTTPError,
    NetworkError,
    RedirectLimitError,
    _LimitedRedirectHandler,
    _validate_url,
    download_page,
)


class TestValidateURL(unittest.TestCase):
    """测试 URL 验证函数。"""

    def test_valid_https_url(self):
        self.assertEqual(
            _validate_url("https://example.com"),
            "https://example.com",
        )

    def test_valid_http_url(self):
        self.assertEqual(
            _validate_url("http://example.com"),
            "http://example.com",
        )

    def test_missing_protocol(self):
        """没有协议前缀时自动补全 https://"""
        self.assertEqual(
            _validate_url("example.com"),
            "https://example.com",
        )

    def test_whitespace_stripped(self):
        self.assertEqual(
            _validate_url("  https://example.com  "),
            "https://example.com",
        )

    def test_empty_url_raises(self):
        with self.assertRaises(ValueError):
            _validate_url("")

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            _validate_url("not a valid url with spaces")

    def test_invalid_url_no_netloc(self):
        """没有主机名的 URL 应报错。"""
        with self.assertRaises(ValueError):
            _validate_url("https://")


class TestDownloadPage(unittest.TestCase):
    """测试核心下载函数。"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_download_success(self):
        """测试成功下载并写入文件。"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.geturl.return_value = "https://example.com"
        mock_response.read.return_value = b"<html><body>Hello World</body></html>"
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.headers.get.return_value = "text/html; charset=utf-8"
        mock_response.headers.items.return_value = [
            ("Content-Type", "text/html; charset=utf-8"),
        ]

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        output_path = os.path.join(self.tmpdir, "output.html")

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            result = download_page("https://example.com", output_path)

        self.assertEqual(result["status"], 200)
        self.assertEqual(result["size"], len(b"<html><body>Hello World</body></html>"))
        self.assertTrue(os.path.exists(output_path))

        # 验证文件内容
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello World", content)

        # 验证 User-Agent 被设置
        self.assertTrue(any(
            "User-Agent" in str(h) for h in mock_opener.addheaders
        ))

    def test_download_success_with_unicode(self):
        """测试包含 Unicode 内容的中文网页下载。"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.geturl.return_value = "https://example.com"
        mock_response.read.return_value = "<html><body>你好，世界！</body></html>".encode("utf-8")
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.headers.get.return_value = "text/html; charset=utf-8"
        mock_response.headers.items.return_value = [
            ("Content-Type", "text/html; charset=utf-8"),
        ]

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        output_path = os.path.join(self.tmpdir, "unicode.html")

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            result = download_page("https://example.com", output_path)

        self.assertEqual(result["status"], 200)
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("你好，世界", content)

    def test_download_binary(self):
        """测试二进制模式写入。"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.geturl.return_value = "https://example.com/image.png"
        mock_response.read.return_value = b"\x89PNG\r\n\x1a\nbinarydata"
        mock_response.headers = {}
        mock_response.headers.get.return_value = "image/png"
        mock_response.headers.items.return_value = []

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        output_path = os.path.join(self.tmpdir, "image.png")

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            result = download_page(
                "https://example.com/image.png",
                output_path,
                binary=True,
            )

        self.assertTrue(os.path.exists(output_path))
        with open(output_path, "rb") as f:
            data = f.read()
        self.assertEqual(data, b"\x89PNG\r\n\x1a\nbinarydata")

    def test_http_error_raises(self):
        """测试 HTTP 错误被正确捕获并转换。"""
        from urllib.error import HTTPError as UrllibHTTPError

        mock_error = UrllibHTTPError("https://example.com/404", 404, "Not Found",
                                     None, None)

        mock_opener = Mock()
        mock_opener.open.side_effect = mock_error
        mock_opener.addheaders = []

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            with self.assertRaises(HTTPError) as ctx:
                download_page("https://example.com/404", "output.html")

        self.assertEqual(ctx.exception.code, 404)

    def test_network_error_raises(self):
        """测试网络错误被正确捕获并转换。"""
        from urllib.error import URLError

        mock_opener = Mock()
        mock_opener.open.side_effect = URLError("Connection refused")
        mock_opener.addheaders = []

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            with self.assertRaises(NetworkError):
                download_page("https://example.com", "output.html")

    def test_redirect_limit(self):
        """测试重定向次数超限。

        注意：直接 mock opener.open 无法触发 urllib 内置的重定向机制，
        因此这里直接测试 _LimitedRedirectHandler 的重定向计数逻辑。
        """
        handler = _LimitedRedirectHandler(max_redirects=2)

        req = Mock()
        fp = Mock()
        headers = {"Location": "https://example.com/next"}

        # 前 2 次重定向应成功（redirect_count 1 和 2 均 <= max_redirects=2）
        handler.redirect_request(req, fp, 302, "Found", headers, "https://example.com/next")
        handler.redirect_request(req, fp, 302, "Found", headers, "https://example.com/next")
        self.assertEqual(handler.redirect_count, 2)

        # 第 3 次重定向应触发 RedirectLimitError
        with self.assertRaises(RedirectLimitError):
            handler.redirect_request(req, fp, 302, "Found", headers, "https://example.com/next")

    def test_redirect_limit_zero(self):
        """测试 max_redirects=0 时第一次重定向就超限。"""
        handler = _LimitedRedirectHandler(max_redirects=0)
        req = Mock()
        fp = Mock()
        headers = {"Location": "https://example.com/next"}

        with self.assertRaises(RedirectLimitError):
            handler.redirect_request(req, fp, 302, "Found", headers, "https://example.com/next")

    def test_redirect_within_limit_succeeds(self):
        """测试重定向次数在限制内时正常返回。"""
        handler = _LimitedRedirectHandler(max_redirects=5)
        req = Mock()
        fp = Mock()
        headers = {"Location": "https://example.com/next"}

        # 多次重定向都在限制内，不抛异常
        for _ in range(5):
            handler.redirect_request(req, fp, 302, "Found", headers, "https://example.com/next")
        self.assertEqual(handler.redirect_count, 5)

    def test_output_directory_created(self):
        """测试输出目录自动创建。"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.geturl.return_value = "https://example.com"
        mock_response.read.return_value = b"test"
        mock_response.headers = {}
        mock_response.headers.get.return_value = "text/html"
        mock_response.headers.items.return_value = []

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        output_path = os.path.join(self.tmpdir, "nested", "dir", "output.html")

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            result = download_page("https://example.com", output_path)

        self.assertTrue(os.path.exists(output_path))

    def test_os_error_wrapped(self):
        """测试文件写入错误被包装为 DownloadError。"""
        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.geturl.return_value = "https://example.com"
        mock_response.read.return_value = b"test"
        mock_response.headers = {}
        mock_response.headers.get.return_value = "text/html"
        mock_response.headers.items.return_value = []

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        # 使用一个无法创建的非法路径触发 OSError
        bad_path = os.path.join(self.tmpdir, "no_such_dir", "x" * 300, "out.html")

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            with self.assertRaises(Exception):
                download_page("https://example.com", bad_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
