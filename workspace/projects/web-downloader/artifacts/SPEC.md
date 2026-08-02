# Web Downloader 功能规格文档

## 1. 功能概述

一个命令行网页下载工具，用于从指定 URL 下载网页内容，保存为 **HTML** 或 **纯文本** 格式。核心能力包括：
- 输入 URL
- 指定输出文件路径
- 处理 HTTP 错误
- 设置请求超时
- 选择保存格式（HTML / 文本）

## 2. 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `url` | str | ✅ 必填 | 无 | 要下载的网页 URL（必须带协议，如 `https://`） |
| `-o, --output` | str | 可选 | 自动生成 | 输出文件路径。若省略，根据 URL 自动生成文件名 |
| `-f, --format` | enum | 可选 | `html` | 保存格式：`html` 或 `text` |
| `-t, --timeout` | float | 可选 | `10.0` | 请求超时时间（秒） |
| `-H, --headers` | str | 可选 | 无 | 自定义请求头（JSON 格式），用于设置 User-Agent 等 |
| `-v, --verbose` | bool | 可选 | `False` | 输出详细调试信息 |

### 命令行用法
```bash
python downloader.py <url> [-o <path>] [-f html|text] [-t <seconds>] [-v]
```

### 示例
```bash
# 保存为 HTML（默认），自动命名
python downloader.py https://example.com

# 保存为文本，指定路径和超时
python downloader.py https://example.com -o out/page.txt -f text -t 15

# 带自定义 User-Agent
python downloader.py https://example.com -H '{"User-Agent":"Mozilla/5.0"}'
```

## 3. 输出格式

### 3.1 文件输出
- **HTML 格式** (`-f html`)：保存原始响应内容（`response.text` 或二进制内容），保留完整 HTML 结构。
- **文本格式** (`-f text`)：从 HTML 中提取纯文本，去除标签、脚本、样式，保留可读文本内容。

### 3.2 输出文件命名规则（未指定路径时）
- 从 URL 提取域名 + 路径，生成安全文件名
- 非法字符替换为 `_`
- 自动追加对应扩展名（`.html` / `.txt`）
- 示例：`https://example.com/blog/post` → `example.com_blog_post.html`

### 3.3 控制台输出
成功时输出：
```
✅ 已保存到: <文件路径> (大小: <N> 字节, 格式: <html|text>)
```
详细模式 (`-v`) 额外输出响应状态码、耗时、内容类型等。

## 4. HTTP 错误处理

| 状态码 | 处理方式 |
|--------|----------|
| 200-299 | 成功，正常保存 |
| 300-399 | 跟随重定向（默认），若重定向过多则报错 |
| 400-499 | 报错并退出，输出具体状态码和原因（如 404 Not Found） |
| 500-599 | 报错并退出，提示服务器错误 |
| 网络异常 | 捕获 `ConnectionError`、`Timeout` 等，给出清晰错误信息 |

**错误退出码约定：**
- `0`：成功
- `1`：HTTP 错误（4xx/5xx）
- `2`：网络异常 / 超时
- `3`：参数错误 / URL 无效
- `4`：文件写入失败

## 5. 超时设置

- 通过 `-t/--timeout` 控制，默认 `10` 秒
- 同时设置连接超时和读取超时
- 超时后捕获 `requests.exceptions.Timeout`，报错退出码 `2`

## 6. 技术依赖

- Python 3.8+
- `requests` 库
- `beautifulsoup4`（用于文本提取）
- 标准库：`argparse`, `urllib.parse`, `pathlib`, `json`

## 7. 健壮性要求

- URL 无协议前缀时自动补全 `https://`
- 输出目录不存在时自动创建
- 文件已存在时覆盖（或用 `-i/--no-clobber` 跳过，可选）
- 文本提取时处理编码（优先响应声明的编码）
