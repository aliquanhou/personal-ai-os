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
        """测试重定向次数超限。"""
        from urllib.error import HTTPError as UrllibHTTPError

        mock_response = Mock()
        mock_response.getcode.return_value = 302
        mock_response.geturl.return_value = "https://example.com/redirect"
        mock_response.headers = {"Location": "https://example.com/loop"}
        mock_response.headers.get.return_value = "https://example.com/loop"

        mock_opener = Mock()
        mock_opener.open.return_value = mock_response
        mock_opener.addheaders = []

        with patch("tools.web_downloader.urllib.request.build_opener",
                   return_value=mock_opener):
            with self.assertRaises(RedirectLimitError):
                download_page(
                    "https://example.com",
                    "output.html",
                    max_redirects=0,
                )

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
