# 网页下载脚本 — 功能规格文档

## 1. 项目概述

使用 Python 标准库（`urllib.request`）实现一个网页下载工具，支持命令行调用和模块导入两种方式。

## 2. 功能需求

### 2.1 核心功能

| 功能 | 描述 |
|------|------|
| URL 下载 | 从指定 URL 下载网页内容 |
| 文件写入 | 将内容保存到指定路径（自动创建目录） |
| 重定向处理 | 自动处理 301/302/303/307/308 重定向 |
| User-Agent | 自定义 User-Agent 头，模拟浏览器访问 |
| 异常处理 | 捕获网络错误、HTTP 错误、超时等异常 |
| 超时控制 | 可配置请求超时时间 |

### 2.2 接口定义

**函数签名：**
```python
def download_page(
    url: str,
    output_path: str,
    timeout: int = 10,
    user_agent: str = DEFAULT_USER_AGENT,
    max_redirects: int = 5,
    binary: bool = False,
    verbose: bool = False,
) -> Dict:
```

**返回值：**
```python
{
    "url": str,           # 最终 URL（重定向后）
    "status": int,        # HTTP 状态码
    "size": int,          # 内容大小（字节）
    "headers": dict,      # 响应头
    "content_type": str,  # 内容类型
    "output_path": str,   # 输出文件路径
    "redirects": int,     # 重定向次数
}
```

**命令行用法：**
```bash
python web_downloader.py <URL> <输出文件> \
    [--timeout 10] \
    [--user-agent "Mozilla/5.0 ..."] \
    [--binary] \
    [--max-redirects 5] \
    [-v]
```

### 2.3 异常类型

| 异常 | 触发条件 |
|------|----------|
| `DownloadError` | 所有下载错误的基类 |
| `NetworkError` | 网络连接失败、DNS 解析失败、超时 |
| `HTTPError` | HTTP 4xx/5xx 状态码 |
| `RedirectLimitError` | 重定向次数超过限制 |
| `ValueError` | URL 格式无效 |

## 3. 错误处理策略

1. **URL 验证**：空 URL、无协议前缀、格式非法均会抛出 `ValueError`
2. **HTTP 错误**：4xx/5xx 状态码转为 `HTTPError`，包含状态码和原因
3. **网络错误**：连接失败、超时转为 `NetworkError`
4. **重定向限制**：超过 `max_redirects` 次抛出 `RedirectLimitError`
5. **文件错误**：写入失败抛出 `DownloadError`

## 4. 安全设计

- 自动补全 `https://` 协议（安全优先）
- 限制最大重定向次数，防止无限跳转
- 默认使用浏览器 UA，避免被服务器拒绝
- 使用 `errors="replace"` 处理非 UTF-8 内容编码

## 5. 测试策略

测试覆盖：
- ✅ URL 验证（合法/非法/空/协议补全）
- ✅ 成功下载并写入文件
- ✅ 二进制模式写入
- ✅ HTTP 错误捕获
- ✅ 网络错误捕获
- ✅ 重定向限制
- ✅ 输出目录自动创建

## 6. 文件结构

```
tools/web_downloader.py       # 主脚本
tests/test_web_downloader.py  # 单元测试
```
