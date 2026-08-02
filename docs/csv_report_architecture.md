# CSV 报告工具 — 技术架构设计

> 版本: v0.1
> 归属: Personal AI OS v0.2 / tools 工具链
> 关联文档: [csv_report_tool_spec.md](./csv_report_tool_spec.md)
> 设计原则: 快速验证 · 轻量依赖 · 复用既有范式(`web_downloader.py`) · 命令行优先

---

## 1. 编程语言选择

### 1.1 选型结论

**Python 3.12+**，核心逻辑**仅依赖标准库**（`csv`、`argparse`、`json`、`statistics`、`io`、`typing`）。

### 1.2 选型理由

| 考量 | 结论 |
|------|------|
| **与项目一致** | 后端整体为 Python 3.12(FastAPI)，本工具作为 tools 工具链成员，保持同语言零心智负担 |
| **标准库完备** | `csv` 模块原生支持读写、`statistics` 提供 mean/median/stdev、`argparse` 提供 CLI，无需第三方 |
| **复用既有范式** | 规格明确要求与 `web_downloader.py` 同一代码范式（标准库 + 双入口 + 异常层次） |
| **跨平台** | 纯标准库保证 Windows / macOS / Linux 行为一致 |
| **明确排除** | 不引入 pandas（规格明确"不做强绑定"）；不引入 numpy（均值/方差用 statistics 足够） |

> **决策记录**: v0.1 坚持零第三方硬依赖。pandas 仅在后续需要复杂透视/相关性分析时以可选依赖引入。

---

## 2. 模块划分

### 2.1 单文件模块（遵循既有范式）

规格要求与 `web_downloader.py` 同范式 —— 单文件模块。整体采用**分层 + 私有函数**结构：

```
tools/
└── csv_report.py
    │
    ├── [常量区]    DEFAULT_*, SUPPORTED_* 配置
    │
    ├── [异常区]    ReportError + 子类（错误处理机制）
    │
    ├── [数据层]    _detect_encoding / _read_csv / _coerce / _validate
    │              （输入 → 规范化 → 校验）
    │
    ├── [计算层]    _compute_* 纯函数（无 IO，易测试）
    │              _compute_summary / _compute_stats / _compute_group / _compute_top
    │
    ├── [渲染层]    _render_* （数据 → 文本/md/html）
    │
    ├── [公共 API]  generate_report()  ← 模块导入主入口
    │
    └── [CLI 层]    build_parser() / main()  ← 命令行入口
```

### 2.2 分层职责

| 层 | 职责 | 特点 |
|----|------|------|
| **数据层** | 读文件、检测编码、解析行、类型推断、校验 | 只产生规范化数据结构；失败抛异常 |
| **计算层** | 纯函数计算统计量 | 无 IO、无副作用 → 单元测试友好 |
| **渲染层** | 把计算结果格式化为 md/html/txt | 纯函数，接受数据返回字符串 |
| **公共 API** | `generate_report()` 编排三层 | 面向模块导入 |
| **CLI 层** | `argparse` 解析 → 调 API → 处理退出码 | 面向命令行 |

> **关键约束**: 计算层与渲染层必须保持**纯函数**（无文件读写、无 print），使 80% 的逻辑可直接单元测试，无需 mock。

---

## 3. 数据处理流程

### 3.1 全流程管道图

```
输入 CSV 文件
     │
     ▼
[1] 编码检测  _detect_encoding()
     │   自动探测 UTF-8 / UTF-8-BOM / GBK；--encoding 可强制覆盖
     ▼
[2] 读取解析  _read_csv()
     │   分隔符(,/\\t/;) · 表头处理(--no-header) · 逐行规范化
     ▼
[3] 数据校验  _validate()
     │   行字段数不一致 → 跳过+计数警告
     │   空文件/仅表头 → 抛 FileError
     ▼
[4] 类型推断  _coerce()
     │   每列推断 int/float/str；数值列供 stats/group 用
     ▼
[5] 计算统计  _compute_*()
     │   summary / stats / group / top（按 --type 选择）
     ▼
[6] 渲染输出  _render_*()
     │   md / html / txt（按 --format 选择）
     ▼
[7] 写出/打印  stdout 或 -o 文件
     │   退出码 0
     ▼
完成
```

### 3.2 各阶段细节

**阶段 1 — 编码检测**
- 优先读原始字节，尝试 `utf-8-sig`（自动去 BOM）解码；
- 失败则尝试 `gbk`；
- 均失败 → 抛 `ParseError`（附 bytes 前若干用于诊断）；
- `--encoding` 显式指定时跳过自动检测。

**阶段 2 — 读取解析**
- 用 `csv.reader` 按指定分隔符逐行读取；
- 首行作表头（默认）或自动生成 `col_1..col_n`（`--no-header`）；
- 用 `--columns` 白名单过滤列。

**阶段 3 — 校验**
- 行字段数与表头不一致 → `warnings` 列表记录行号，跳过该行；
- 空文件 / 无数据行 → 抛 `FileError`；
- 校验结果（跳过行数）随报告输出，保证透明。

**阶段 4 — 类型推断**
- 对每列尝试 `int` → `float` → 保留 `str`；
- 失败值记录为"非数值"，数值统计时跳过并计数。

**阶段 5-7 — 计算与渲染**
- 按报告类型分派到对应 `_compute_*` + `_render_*`；
- 计算层返回**字典结构**，渲染层再转字符串 → 解耦、可测。

---

## 4. CSV 生成逻辑

> 本工具定位是 **CSV → 报告**，但为完整覆盖"CSV 生成"，架构内置一个可复用的**写出器**，用于把处理结果（如 group 聚合表、top 排行）导出为 CSV，也供未来其他工具复用。

### 4.1 统一写出器 `_write_csv()`

```python
def _write_csv(
    rows: list[list[str]],
    headers: list[str],
    output: TextIO,
    sep: str = ",",
) -> None:
    """将行数据以指定分隔符写出为 CSV。"""
    writer = csv.writer(output, delimiter=sep, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
```

### 4.2 写出的关键决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| **分隔符** | 复用输入分隔符或显式指定 | 与输入数据风格一致，避免 Excel 打开乱 |
| **行终止符** | `\n`（非 `\r\n`） | 跨平台一致、体积小、git 友好 |
| **编码** | 默认 `utf-8-sig`（带 BOM） | Windows Excel 直接打开不乱码 |
| **特殊字符** | 交给 `csv.writer` 自动加引号 | 内建转义，无需手写 |
| **表头** | 显式传入 | 保证列名可控、可本地化 |

### 4.3 未来扩展位
- `-o report.csv` 时可将聚合结果直接写出为 CSV；
- 为后续 `correlation` / `weekly` 报告预留同样的写出路径。

---

## 5. 错误处理机制

### 5.1 异常层次（复用 web_downloader 范式）

```
ReportError                  # 基类，携带可读中文消息
├── FileError                # 文件层面：不存在 / 无权限 / 空文件 / 仅表头
├── ParseError               # 解析层面：编码失败 / 分隔符错误 / 字段不一致
└── ConfigError              # 参数层面：非法 type / 列不存在 / 非法 limit
```

### 5.2 各异常触发点

| 异常 | 触发场景 | 消息示例 |
|------|----------|----------|
| `FileError` | 文件不存在、无读取权限 | `文件不存在: {path}` |
| `FileError` | 空文件 / 仅表头无数据 | `文件为空或无数据行: {path}` |
| `ParseError` | 编码无法识别 | `无法识别文件编码，请用 --encoding 指定` |
| `ParseError` | 字段数不一致（跳过行） | `第 {n} 行字段数不一致，已跳过`（warnings，不抛） |
| `ConfigError` | 非法 `--type` | `不支持的报告类型: {type}` |
| `ConfigError` | 排序/分组列不存在 | `列不存在: {col}` |

### 5.3 错误处理策略

1. **可恢复 → 警告，不崩溃**：字段数不一致、非数值混入 → 记入 `warnings` 继续处理；
2. **不可恢复 → 抛异常**：文件缺失、编码失败、非法参数 → 立即抛出；
3. **CLI 层兜底**：`main()` 捕获 `ReportError` → 打印错误到 stderr → 退出码 1；
4. **参数错误**：交给 `argparse`（自动报错 → 退出码 2）；
5. **成功**：退出码 0。

### 5.4 CLI 退出码约定

| 退出码 | 含义 |
|--------|------|
| `0` | 成功 |
| `1` | 报告生成失败（`ReportError`，信息到 stderr） |
| `2` | 参数错误（argparse 默认） |

---

## 6. 公共 API 签名

```python
def generate_report(
    input_path: str,
    report_type: str = "summary",      # summary|stats|group|top
    group_cols: list[str] | None = None,
    sort_col: str | None = None,
    limit: int = 10,
    columns: list[str] | None = None,  # 列白名单
    sep: str = ",",
    encoding: str | None = None,       # None=自动检测
    has_header: bool = True,
    output_format: str = "md",         # md|html|txt
    config: dict | None = None,
) -> str:
    """生成报告，返回渲染后的字符串。"""
```

---

## 7. 测试策略

| 分层 | 测试重点 |
|------|----------|
| 数据层 | 编码检测、解析、校验、类型推断（含 GBK、BOM、字段不一致） |
| 计算层 | 各统计量正确性（纯函数，最易测） |
| 渲染层 | md/html/txt 输出结构 |
| 集成 | CLI 全流程、模块导入、退出码 |

> 计算层与渲染层为纯函数 → 无需 mock，`pytest` 直接覆盖。

---

## 8. 验收对照（与 spec 一致）

- ✅ 4 种报告类型
- ✅ CLI + 模块双入口
- ✅ 3 种输出格式
- ✅ 编码自动检测（UTF-8/GBK）
- ✅ 异常层次清晰
- ✅ 测试覆盖核心场景，`pytest` 通过
- ✅ 零第三方硬依赖

---

## 9. 待确认事项

- [ ] 是否需要 `-o report.csv` 直接输出聚合结果（决定写出器优先级）
- [ ] `top` 类型是否支持多列排序
- [ ] HTML 是否需要内联 CSS 样式定制
- [ ] 超大文件（>50MB）是否后续做流式分块
