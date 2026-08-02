# 网页下载脚本使用说明

本文档介绍 `tools/web_downloader.py` 网页下载脚本的安装、运行、参数及使用示例，帮助您快速上手。

---

## 一、脚本简介

`web_downloader.py` 是一个基于 **Python 标准库** 实现的网页下载工具，无需任何第三方依赖。它支持：

- 处理 HTTP 重定向（301/302/303/307/308）
- 自定义 User-Agent，模拟真实浏览器访问
- 异常捕获与友好错误提示
- 内容写入指定文件
- 请求超时控制
- **命令行调用** 与 **模块导入** 两种使用方式

---

## 二、环境要求与安装依赖

### 1. 环境要求

- **Python 3.6 及以上版本**（推荐 3.8+）
- 操作系统：Windows / macOS / Linux 均可

### 2. 确认 Python 版本

```bash
python --version
# 或
python3 --version
```

### 3. 安装依赖

本脚本 **仅使用 Python 标准库**（`argparse`、`urllib`、`os`、`sys` 等），**无需安装任何第三方包**，开箱即用。

如果您希望运行配套的单元测试，请确保已安装 `pytest`（可选，测试本身基于标准库 `unittest`，也可直接运行）：

```bash
# 可选：安装 pytest（用于更友好的测试输出）
pip install pytest
```

---

## 三、运行命令

### 1. 命令行方式（推荐）

在项目根目录下执行：

```bash
python tools/web_downloader.py <URL> <输出文件> [选项]
```

#### 基础用法

```bash
# 下载网页到当前目录
python tools/web_downloader.py https://example.com output.html

# 下载到指定文件夹
python tools/web_downloader.py https://example.com ./downloads/page.html
```

### 2. 模块导入方式（供二次开发）

在 Python 脚本或交互式环境中：

```python
from tools.web_downloader import download_page

result = download_page("https://example.com", "output.html")
print(result)
```

> 注意：使用模块导入时，请确保当前工作目录为项目根目录，或在 `sys.path` 中包含 `tools` 所在路径。

---

## 四、参数详解

### 位置参数（必填）

| 参数 | 说明 |
|------|------|
| `url` | 要下载的网页 URL。可省略协议前缀（如 `example.com` 会自动补全为 `https://example.com`） |
| `output` | 输出文件路径。若目录不存在，脚本会自动创建 |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--timeout` | `10` | 请求超时时间（秒） |
| `--user-agent` | 模拟 Chrome 浏览器的 UA | 自定义 User-Agent 字符串 |
| `--binary` | 关闭 | 以二进制模式写入（用于下载图片、PDF 等非文本文件） |
| `--max-redirects` | `5` | 最大重定向次数，防止无限跳转 |
| `-v, --verbose` | 关闭 | 显示详细请求日志 |

---

## 五、使用示例

### 示例 1：基础下载

```bash
python tools/web_downloader.py https://example.com output.html
```

**输出结果：**

```
✅ 下载成功!
   URL:        https://example.com
   状态码:     200
   大小:       1,256 字节
   内容类型:   text/html; charset=utf-8
   重定向次数: 0
   保存到:     output.html
```

### 示例 2：设置超时时间

```bash
python tools/web_downloader.py https://example.com output.html --timeout 30
```

适合网络较慢或页面较大的场景，等待时间延长至 30 秒。

### 示例 3：下载图片/PDF（二进制模式）

```bash
python tools/web_downloader.py https://example.com/logo.png logo.png --binary
python tools/web_downloader.py https://example.com/report.pdf report.pdf --binary
```

二进制模式确保图片、PDF 等文件内容不被编码转换损坏。

### 示例 4：自定义 User-Agent

```bash
python tools/web_downloader.py https://example.com output.html \
  --user-agent "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"
```

某些网站会针对不同 User-Agent 返回不同内容，可通过此参数模拟移动端访问。

### 示例 5：显示详细日志

```bash
python tools/web_downloader.py https://example.com output.html -v
```

**详细日志输出：**

```
[*] 请求: https://example.com
[*] User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/...
[*] 超时: 10s, 最大重定向: 5
[*] 最终 URL: https://example.com
[*] 状态码: 200
[*] 内容类型: text/html; charset=utf-8
[*] 重定向: 0 次
[*] 大小: 1,256 字节
[*] 保存到: output.html
```

### 示例 6：自动补全协议

```bash
# 等价于 https://example.com
python tools/web_downloader.py example.com output.html
```

### 示例 7：同时使用多个选项

```bash
python tools/web_downloader.py https://example.com/data.json data.json \
  --timeout 20 --max-redirects 10 --binary
```

---

## 六、返回值说明（模块导入模式）

`download_page()` 函数返回一个字典，包含以下字段：

| 字段 | 说明 |
|------|------|
| `url` | 最终 URL（重定向后） |
| `status` | HTTP 状态码 |
| `size` | 内容大小（字节） |
| `headers` | 响应头字典 |
| `content_type` | 内容类型 |
| `output_path` | 输出文件路径 |
| `redirects` | 重定向次数 |

**示例：**

```python
from tools.web_downloader import download_page

result = download_page("https://example.com", "output.html")
print(f"状态码: {result['status']}")
print(f"大小: {result['size']} 字节")
print(f"内容类型: {result['content_type']}")
```

---

## 七、异常处理

脚本定义了以下自定义异常，方便捕获具体错误类型：

| 异常类 | 触发场景 | 退出码 |
|--------|----------|--------|
| `NetworkError` | 网络连接失败、请求超时 | 1 |
| `HTTPError` | 服务器返回 4xx/5xx 错误 | 1 |
| `RedirectLimitError` | 重定向次数超限 | 1 |
| `ValueError` | URL 格式无效 | 2 |
| `DownloadError` | 其他下载错误（如文件写入失败） | 1 |

**命令行模式下**，失败时会在终端输出 `❌ 下载失败: <错误信息>` 并返回相应退出码。

```bash
# 示例：访问不存在的页面（404）
python tools/web_downloader.py https://example.com/404 output.html
# ❌ 下载失败: HTTP 404 Not Found — https://example.com/404
```

---

## 八、运行单元测试

脚本附带完整的单元测试，验证 URL 校验、下载、二进制写入、异常处理等逻辑。

### 方式一：使用 pytest（推荐）

```bash
python -m pytest tests/test_web_downloader.py -v
```

### 方式二：直接运行（基于 unittest）

```bash
python tests/test_web_downloader.py
```

测试全部通过时输出：

```
Ran N tests in 0.0XXs

OK
```

---

## 九、常见问题（FAQ）

**Q1：下载中文网页出现乱码？**
脚本默认以 UTF-8 编码写入文本文件，并对无法解码的字符做替换处理。若网页使用其他编码，建议下载后使用文本编辑器转换编码，或使用二进制模式下载原始字节。

**Q2：提示 `NetworkError: 网络错误`？**
检查网络连接、URL 是否正确，或尝试增大 `--timeout` 参数。

**Q3：提示 `HTTP 403 Forbidden`？**
部分网站会拦截脚本请求，可尝试通过 `--user-agent` 传入真实浏览器的 UA 字符串。

**Q4：可以批量下载多个页面吗？**
命令行方式一次只支持一个 URL。如需批量下载，请在 Python 脚本中循环调用 `download_page()` 函数。

---

## 十、版权与说明

本脚本仅用于学习和合法用途，请遵守目标网站的 robots 协议及相关法律法规，勿用于抓取敏感或受版权保护的内容。
