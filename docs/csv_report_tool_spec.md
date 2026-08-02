# CSV 报告生成工具 — 功能规格说明

> 版本: v0.1 (草案)
> 归属: Personal AI OS v0.2 / tools 工具链
> 设计原则: 快速验证 · 轻量依赖 · 复用既有模式 · 命令行优先

---

## 1. 背景与定位

Personal AI OS 需要一个通用的 **CSV → 报告** 工具，用于把结构化数据（CSV）快速转化为可读、可分享的总结报告（Markdown / HTML / 纯文本）。

**定位**: 一个轻量、无 GUI 依赖、可在 CLI 和模块导入两种方式下使用的工具，与既有 `web_downloader.py` 保持同一代码范式。

**明确不做**（避免过度工程化 / 重复造轮子）:
- ❌ 不做可视化图表引擎（交给前端/其他工具）
- ❌ 不做数据库连接
- ❌ 不做复杂模板引擎（用 Python f-string / 简单占位符）
- ❌ 不做 GUI / Web UI（本工具只做 CLI + 模块）
- ❌ 不做与 pandas 强绑定（可选支持，但核心走标准库 csv）

---

## 2. 输入数据格式

### 2.1 主要输入：CSV 文件
- **编码**: 自动检测 UTF-8 / UTF-8-BOM / GBK（中文场景常见），默认 UTF-8
- **分隔符**: 支持 `,`（默认）、`\t`、`;`，可显式指定
- **表头**: 默认第一行为表头；支持 `--no-header` 时自动生成 `col_1, col_2, ...`
- **大小**: 建议 ≤ 50MB；超大数据给出提示（不做流式分块，v0.1 限制）

### 2.2 可选输入：报告配置
- 通过命令行参数传入（见 §4）
- 支持一个可选的 JSON 配置文件（`--config`），用于复杂字段映射

### 2.3 输入校验
- 文件不存在 / 无读取权限 → 报错退出
- 空文件 / 只有表头无数据 → 报错退出
- 行字段数不一致 → 警告并跳过异常行（记录数量）
- 非数值字段被用于数值统计 → 跳过并警告

---

## 3. 报告类型

v0.1 支持 **4 种基础报告**，可通过 `--type` 指定：

| type | 说明 | 核心内容 |
|------|------|---------|
| `summary` | 数据概览 | 行数、列数、每列类型、缺失值数、唯一值数 |
| `stats`   | 数值统计 | 每列 min/max/mean/median/std、空值统计 |
| `group`   | 分组聚合 | 按指定列分组，输出每组行数及数值列均值 |
| `top`     | Top-N 排行 | 按指定列排序，输出前 N 行 |

> 后续可扩展: `correlation`（相关性）、`weekly`（时间趋势）等，v0.1 不实现。

---

## 4. 命令行接口（CLI）

### 4.1 用法
```bash
python tools/csv_report.py <input.csv> [options]
```

### 4.2 参数
```
位置参数:
  input                输入 CSV 文件路径

选项:
  -t, --type TYPE       报告类型: summary|stats|group|top (默认 summary)
  -g, --group COLS      分组列(逗号分隔)，用于 group 类型
  -s, --sort COL        排序列，用于 top 类型
  -n, --limit N         top 类型返回行数 (默认 10)
  -c, --columns COLS    仅处理指定列(逗号分隔)
  --sep SEP             分隔符 (默认 ,)
  --encoding ENC        强制编码 (默认自动检测)
  --no-header           首行不作为表头
  -o, --output PATH     输出文件路径 (默认 stdout)
  --format FMT          输出格式: md|html|txt (默认 md)
  --config PATH         可选 JSON 配置
  -q, --quiet           静默模式(仅输出报告内容，无日志)
  -h, --help            帮助
```

### 4.3 示例
```bash
# 概览
python tools/csv_report.py sales.csv

# 数值统计，输出 HTML
python tools/csv_report.py sales.csv -t stats --format html -o report.html

# 按 region 分组
python tools/csv_report.py sales.csv -t group -g region

# 按 revenue 排序取前 5
python tools/csv_report.py sales.csv -t top -s revenue -n 5
```

---

## 5. 模块导入接口（Python API）

```python
from tools.csv_report import generate_report, ReportError

report = generate_report(
    "sales.csv",
    report_type="stats",
    group_cols=["region"],
    columns=["revenue", "units"],
    output_format="md",
)
print(report)  # str
```

### 异常层次（复用 web_downloader 范式）
```
ReportError
├── FileError        — 文件不存在/无权限/空文件
├── ParseError       — 编码/分隔符/字段不一致
└── ConfigError      — 非法参数/列不存在
```

---

## 6. 输出要求

### 6.1 输出格式（`--format`）
- **md (默认)**: Markdown 表格 + 标题
- **html**: 简单 HTML 表格（内联样式，可直接打开）
- **txt**: 纯文本对齐表格

### 6.2 输出目标
- 默认 stdout
- `-o file` 写入文件

### 6.3 退出码
- `0` 成功
- `1` 报告生成失败（含错误信息到 stderr）
- `2` 参数错误（argparse 默认）

### 6.4 报告头部信息
每份报告包含：数据来源、生成时间、行数/列数、报告类型。

---

## 7. 代码结构（遵循 web_downloader 范式）

```
tools/
└── csv_report.py          # 主模块
    ├── generate_report()  # 对外主函数
    ├── _detect_encoding() # 编码检测
    ├── _read_csv()        # 读取+校验
    ├── _render_summary()  # 各报告渲染
    ├── _render_stats()
    ├── _render_group()
    ├── _render_top()
    └── main()             # CLI 入口

tests/
└── test_csv_report.py     # 测试文件
```

---

## 8. 测试计划

| 用例 | 验证点 |
|------|--------|
| 正常 CSV 生成 summary | 行数/列数正确 |
| stats 数值统计 | 均值/中位数计算正确 |
| group 分组 | 分组数量与每组计数正确 |
| top 排序 | 排序与 limit 生效 |
| GBK 编码文件 | 自动检测并正确读取 |
| 字段数不一致 | 跳过并警告，不崩溃 |
| 空文件 | 抛 FileError |
| 文件不存在 | 抛 FileError |
| 非法 type | 抛 ConfigError |
| 模块导入 | 返回正确字符串 |

---

## 9. 验收标准（Definition of Done）

- [ ] 4 种报告类型全部可用
- [ ] CLI 与模块导入双入口可用
- [ ] 3 种输出格式可切换
- [ ] 编码自动检测（UTF-8/GBK）
- [ ] 异常层次清晰、错误信息可读
- [ ] 测试文件覆盖核心场景，`pytest` 通过
- [ ] 无第三方硬依赖（纯标准库）

---

## 10. 开放问题（待老板拍板）

1. 是否需要支持 `correlation`（相关性）报告？→ 建议 v0.2 再加
2. 是否需要支持多个 CSV 合并？→ 建议先不做
3. HTML 输出是否需要内嵌图表？→ 建议不做，交给前端
4. 是否需要 `--whitelist`（允许列白名单）防注入？→ 建议加，成本低

---

*规格 v0.1 草案，待评审后进入开发。*
