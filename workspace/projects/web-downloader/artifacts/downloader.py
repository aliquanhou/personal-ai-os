#!/usr/bin/env python3
"""
Web Downloader - 命令行网页下载工具

功能：
- 输入 URL 下载网页
- 保存为 HTML 或纯文本格式
- 处理 HTTP 错误
- 设置请求超时
- 指定输出文件路径

用法：
    python downloader.py <url> [-o <path>] [-f html|text] [-t <seconds>] [-v]

示例：
    python downloader.py https://example.com
    python downloader.py https://example.com -o out/page.txt -f text -t 15
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# 退出码约定
EXIT_SUCCESS = 0          # 成功
EXIT_HTTP_ERROR = 1       # HTTP 4xx/5xx
EXIT_NETWORK = 2          # 网络异常 / 超时
EXIT_ARGS = 3             # 参数错误 / URL 无效
EXIT_FILE = 4             # 文件写入失败

DEFAULT_TIMEOUT = 10.0
DEFAULT_HEADERS = {
    "User-Agent": "WebDownloader/1.0 (+https://github.com/yourname/web-downloader)"
}


def parse_args(argv=None):
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description="下载网页内容并保存为 HTML 或文本格式"
    )
    parser.add_argument("url", help="要下载的网页 URL（如 https://example.com）")
    parser.add_argument("-o", "--output", help="输出文件路径（默认根据 URL 自动生成）")
    parser.add_argument(
        "-f", "--format",
        choices=["html", "text"],
        default="html",
        help="保存格式：html 或 text（默认 html）"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"请求超时时间（秒，默认 {DEFAULT_TIMEOUT}）"
    )
    parser.add_argument(
        "-H", "--headers",
        help="自定义请求头（JSON 格式），如 '{\"User-Agent\":\"Mozilla/5.0\"}'"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="输出详细调试信息"
    )
    return parser.parse_args(argv)


def normalize_url(url):
    """为 URL 补全协议前缀，并校验格式."""
    url = url.strip()
    if not url:
        raise ValueError("URL 不能为空")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc or not parsed.scheme:
        raise ValueError(f"无效的 URL: {url}")
    return url


def parse_headers(raw):
    """解析 JSON 格式的自定义请求头."""
    if not raw:
        return {}
    try:
        headers = json.loads(raw)
        if not isinstance(headers, dict):
            raise ValueError("请求头必须是 JSON 对象")
        return headers
    except json.JSONDecodeError:
        raise ValueError(f"请求头 JSON 解析失败: {raw}")


def auto_filename(url, fmt):
    """根据 URL 自动生成安全文件名."""
    parsed = urlparse(url)
    host = parsed.netloc.replace("www.", "").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") or "index"
    base = f"{host}_{path}"
    # 替换非法文件名字符
    for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        base = base.replace(ch, "_")
    base = base[:100]  # 限制长度
    ext = ".html" if fmt == "html" else ".txt"
    return f"{base}{ext}"


def fetch(url, timeout, headers, verbose=False):
    """发起 HTTP 请求，返回响应对象."""
    merged_headers = {**DEFAULT_HEADERS, **headers}
    try:
        resp = requests.get(url, headers=merged_headers, timeout=timeout)
    except requests.exceptions.Timeout:
        raise NetworkError(f"请求超时（>{timeout} 秒）: {url}")
    except requests.exceptions.ConnectionError:
        raise NetworkError(f"连接失败: {url}")
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"请求异常: {e}")

    if verbose:
        print(f"[调试] 状态码: {resp.status_code}, 耗时: {resp.elapsed:.2f}s")
        print(f"[调试] Content-Type: {resp.headers.get('Content-Type', '未知')}")

    if resp.status_code >= 400:
        reason = resp.reason or "未知原因"
        raise HttpError(resp.status_code, reason, url)

    return resp


def extract_text(html):
    """从 HTML 提取纯文本."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # 清理多余空行
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


class HttpError(Exception):
    """HTTP 状态码错误."""
    def __init__(self, status, reason, url):
        self.status = status
        super().__init__(f"HTTP {status} {reason}: {url}")


class NetworkError(Exception):
    """网络异常或超时."""
    pass


def main(argv=None):
    args = parse_args(argv)

    # 1. 校验并规范化 URL
    try:
        url = normalize_url(args.url)
    except ValueError as e:
        print(f"❌ 参数错误: {e}", file=sys.stderr)
        return EXIT_ARGS

    # 2. 解析请求头
    try:
        custom_headers = parse_headers(args.headers)
    except ValueError as e:
        print(f"❌ 参数错误: {e}", file=sys.stderr)
        return EXIT_ARGS

    # 3. 发起请求
    try:
        resp = fetch(url, args.timeout, custom_headers, args.verbose)
    except HttpError as e:
        print(f"❌ HTTP 错误: {e}", file=sys.stderr)
        return EXIT_HTTP_ERROR
    except NetworkError as e:
        print(f"❌ 网络错误: {e}", file=sys.stderr)
        return EXIT_NETWORK

    # 4. 处理内容（HTML 或文本）
    if args.format == "text":
        try:
            content = extract_text(resp.text)
        except Exception as e:
            print(f"❌ 文本提取失败: {e}", file=sys.stderr)
            return EXIT_FILE
        encoding = "utf-8"
    else:
        content = resp.content if isinstance(resp.content, bytes) else resp.text
        encoding = None  # HTML 保留原始字节

    # 5. 确定输出路径
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(auto_filename(url, args.format))

    # 6. 写入文件
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if encoding:
            out_path.write_text(content, encoding=encoding)
        else:
            out_path.write_bytes(content)
    except OSError as e:
        print(f"❌ 文件写入失败: {e}", file=sys.stderr)
        return EXIT_FILE

    size = out_path.stat().st_size
    print(f"✅ 已保存到: {out_path} (大小: {size} 字节, 格式: {args.format})")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
