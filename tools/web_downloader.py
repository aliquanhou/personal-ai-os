#!/usr/bin/env python3
"""
网页下载脚本
============

使用 Python 标准库实现网页下载功能，支持：
  - 处理 HTTP 重定向（301/302/303/307/308）
  - 自定义 User-Agent
  - 异常捕获与友好错误提示
  - 内容写入指定文件
  - 超时控制
  - 命令行调用 & 模块导入两种方式

用法：
    # 命令行方式
    python web_downloader.py <URL> <输出文件> [--timeout 10] [--user-agent "..."]

    # 模块导入方式
    from tools.web_downloader import download_page
    result = download_page("https://example.com", "output.html")
"""

import argparse
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
from typing import Dict, Optional


# 默认 User-Agent，模拟真实浏览器
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 10

# 最大重定向次数，防止无限跳转
MAX_REDIRECTS = 5


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------

class DownloadError(Exception):
    """下载过程中的自定义异常基类。"""


class NetworkError(DownloadError):
    """网络连接相关错误。"""


class HTTPError(DownloadError):
    """HTTP 状态码错误。"""

    def __init__(self, code: int, reason: str, url: str):
        self.code = code
        self.reason = reason
        self.url = url
        super().__init__(f"HTTP {code} {reason} — {url}")


class RedirectLimitError(DownloadError):
    """重定向次数超出限制。"""


# ---------------------------------------------------------------------------
# 自定义重定向处理器（限制重定向次数）
# ---------------------------------------------------------------------------

class _LimitedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """限制重定向次数的 Handler。"""

    def __init__(self, max_redirects: int):
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            raise RedirectLimitError(
                f"重定向次数超过限制 ({self.max_redirects} 次)"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# ---------------------------------------------------------------------------
# 核心下载函数
# ---------------------------------------------------------------------------

def _validate_url(url: str) -> str:
    """验证并规范化 URL。"""
    url = url.strip()
    if not url:
        raise ValueError("URL 不能为空")

    # 自动补全协议
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # 基本格式校验
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"无效的 URL 格式: {url}")

    return url


def download_page(
    url: str,
    output_path: str,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_redirects: int = MAX_REDIRECTS,
    binary: bool = False,
    verbose: bool = False,
) -> Dict:
    """
    下载网页内容并保存到指定文件。

    Args:
        url: 要下载的网页 URL。
        output_path: 输出文件路径。
        timeout: 请求超时时间（秒）。
        user_agent: 自定义 User-Agent。
        max_redirects: 最大重定向次数。
        binary: 是否以二进制模式写入（用于图片/PDF等）。
        verbose: 是否打印详细日志。

    Returns:
        包含下载结果信息的字典：
        {
            "url": 最终 URL（重定向后）,
            "status": HTTP 状态码,
            "size": 内容大小（字节）,
            "headers": 响应头,
            "content_type": 内容类型,
            "output_path": 输出文件路径,
            "redirects": 重定向次数,
        }

    Raises:
        NetworkError: 网络连接错误。
        HTTPError: HTTP 状态码错误（4xx/5xx）。
        RedirectLimitError: 重定向次数超限。
        ValueError: URL 格式无效。
        DownloadError: 其他下载错误。
    """
    url = _validate_url(url)

    # 创建输出目录（如不存在）
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 构建 opener：自定义 User-Agent + 限制重定向
    redirect_handler = _LimitedRedirectHandler(max_redirects)
    opener = urllib.request.build_opener(redirect_handler)
    opener.addheaders = [("User-Agent", user_agent)]

    if verbose:
        print(f"[*] 请求: {url}")
        print(f"[*] User-Agent: {user_agent[:50]}...")
        print(f"[*] 超时: {timeout}s, 最大重定向: {max_redirects}")

    try:
        response = opener.open(url, timeout=timeout)

        # 读取内容
        content = response.read()

        # 写入文件
        if binary:
            with open(output_path, "wb") as f:
                f.write(content)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content.decode("utf-8", errors="replace"))

        result = {
            "url": response.geturl(),
            "status": response.getcode(),
            "size": len(content),
            "headers": dict(response.headers.items()),
            "content_type": response.headers.get("Content-Type", ""),
            "output_path": output_path,
            "redirects": redirect_handler.redirect_count,
        }

        response.close()

        if verbose:
            print(f"[*] 最终 URL: {result['url']}")
            print(f"[*] 状态码: {result['status']}")
            print(f"[*] 内容类型: {result['content_type']}")
            print(f"[*] 重定向: {result['redirects']} 次")
            print(f"[*] 大小: {result['size']:,} 字节")
            print(f"[*] 保存到: {output_path}")

        return result

    except urllib.error.HTTPError as e:
        raise HTTPError(e.code, e.reason, url) from e
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", str(e))
        raise NetworkError(f"网络错误: {reason}") from e
    except TimeoutError as e:
        raise NetworkError(f"请求超时 ({timeout}s)") from e
    except OSError as e:
        raise DownloadError(f"文件操作失败: {e}") from e
    except RedirectLimitError:
        raise


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="下载网页内容到本地文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python web_downloader.py https://example.com output.html\n"
            "  python web_downloader.py https://example.com output.html --timeout 30\n"
            "  python web_downloader.py https://example.com output.html --binary\n"
        ),
    )
    parser.add_argument("url", help="要下载的网页 URL")
    parser.add_argument("output", help="输出文件路径")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"请求超时时间（秒），默认 {DEFAULT_TIMEOUT}")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                        help="自定义 User-Agent")
    parser.add_argument("--binary", action="store_true",
                        help="以二进制模式写入（用于图片/PDF等）")
    parser.add_argument("--max-redirects", type=int, default=MAX_REDIRECTS,
                        help=f"最大重定向次数，默认 {MAX_REDIRECTS}")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细日志")

    args = parser.parse_args()

    try:
        result = download_page(
            args.url,
            args.output,
            timeout=args.timeout,
            user_agent=args.user_agent,
            max_redirects=args.max_redirects,
            binary=args.binary,
            verbose=args.verbose,
        )

        if not args.verbose:
            print(f"\n✅ 下载成功!")
            print(f"   URL:        {result['url']}")
            print(f"   状态码:     {result['status']}")
            print(f"   大小:       {result['size']:,} 字节")
            print(f"   内容类型:   {result['content_type']}")
            print(f"   重定向次数: {result['redirects']}")
            print(f"   保存到:     {result['output_path']}")

    except DownloadError as e:
        print(f"\n❌ 下载失败: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ 参数错误: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
