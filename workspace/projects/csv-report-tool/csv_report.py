#!/usr/bin/env python3
"""
CSV 报告生成工具
================

把结构化数据（CSV）快速转化为可读、可分享的总结报告（Markdown / HTML / 纯文本）。

定位：轻量、无 GUI 依赖、可在 CLI 和模块导入两种方式下使用，与既有
`web_downloader.py` 保持同一代码范式。

支持 4 种基础报告类型：
  - summary  数据概览（行数/列数/每列类型/缺失值/唯一值）
  - stats    数值统计（min/max/mean/median/std）
  - group    分组聚合（按列分组，输出每组行数及数值列均值）
  - top      Top-N 排行（按列排序，输出前 N 行）

用法：
    # 命令行方式
    python tools/csv_report.py sales.csv
    python tools/csv_report.py sales.csv -t stats --format html -o report.html
    python tools/csv_report.py sales.csv -t group -g region
    python tools/csv_report.py sales.csv -t top -s revenue -n 5

    # 模块导入方式
    from tools.csv_report import generate_report, ReportError
    report = generate_report("sales.csv", report_type="stats")
    print(report)
"""

import argparse
import csv
import io
import json
import os
import statistics
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, TextIO


# ---------------------------------------------------------------------------
# 常量区
# ---------------------------------------------------------------------------

# 支持的分隔符
SUPPORTED_SEPS = [",", "\t", ";"]

# 支持的报告类型
SUPPORTED_TYPES = ["summary", "stats", "group", "top"]

# 支持的输出格式
SUPPORTED_FORMATS = ["md", "html", "txt"]

# 编码检测顺序（自动检测时尝试）
ENCODING_CANDIDATES = ["utf-8-sig", "gbk"]

# 默认值
DEFAULT_SEP = ","
DEFAULT_LIMIT = 10
DEFAULT_FORMAT = "md"
DEFAULT_TYPE = "summary"

# 建议最大文件大小（字节），超限给出提示但不强制拦截
SUGGESTED_MAX_SIZE = 50 * 1024 * 1024  # 50MB


# ---------------------------------------------------------------------------
# 异常区
# ---------------------------------------------------------------------------

class ReportError(Exception):
    """CSV 报告生成过程中的自定义异常基类。"""


class FileError(ReportError):
    """文件层面错误：不存在 / 无权限 / 空文件 / 仅表头。"""


class ParseError(ReportError):
    """解析层面错误：编码失败 / 分隔符错误 / 字段不一致。"""


class ConfigError(ReportError):
    """参数层面错误：非法 type / 列不存在 / 非法 limit。"""


# ---------------------------------------------------------------------------
# 数据层
# ---------------------------------------------------------------------------

def _detect_encoding(raw: bytes) -> str:
    """
    自动检测文件编码。

    优先尝试 utf-8-sig（自动去 BOM），失败则尝试 gbk。
    均失败则抛出 ParseError。
    """
    for enc in ENCODING_CANDIDATES:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    # 诊断信息：展示前若干字节
    head = repr(raw[:40])
    raise ParseError(f"无法识别文件编码（前 40 字节: {head}），请用 --encoding 指定")


def _read_csv(
    input_path: str,
    sep: str = DEFAULT_SEP,
    encoding: Optional[str] = None,
    has_header: bool = True,
    columns: Optional[List[str]] = None,
):
    """
    读取并解析 CSV 文件。

    Returns:
        (headers, rows, warnings)
        headers: 表头列表
        rows: 数据行（每行为字符串列表）
        warnings: 解析过程中的警告信息列表

    Raises:
        FileError: 文件不存在 / 无读取权限 / 空文件 / 仅表头无数据
        ParseError: 编码无法识别 / 分隔符无效
        ConfigError: 指定的列不存在
    """
    if not os.path.exists(input_path):
        raise FileError(f"文件不存在: {input_path}")

    if not os.access(input_path, os.R_OK):
        raise FileError(f"文件无读取权限: {input_path}")

    warnings: List[str] = []

    # 读取原始字节
    try:
        with open(input_path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise FileError(f"读取文件失败: {input_path} ({e})") from e

    # 校验文件大小
    if len(raw) > SUGGESTED_MAX_SIZE:
        warnings.append(
            f"文件超过建议大小 ({SUGGESTED_MAX_SIZE // (1024 * 1024)}MB)，"
            f"实际 {len(raw) / (1024 * 1024):.1f}MB，处理可能较慢"
        )

    # 编码检测
    enc = encoding or _detect_encoding(raw)

    # 解码
    try:
        text = raw.decode(enc)
    except (UnicodeDecodeError, LookupError) as e:
        raise ParseError(f"使用编码 {enc} 解码失败: {e}") from e

    # 分隔符校验
    if sep not in SUPPORTED_SEPS:
        raise ConfigError(f"不支持的分隔符: {sep!r}，可选: {', '.join(SUPPORTED_SEPS)}")

    # 解析
    reader = csv.reader(io.StringIO(text), delimiter=sep)
    all_rows = [row for row in reader if any(cell.strip() for cell in row)]

    if not all_rows:
        raise FileError(f"文件为空或无数据行: {input_path}")

    # 处理表头
    if has_header:
        headers = all_rows[0]
        rows = all_rows[1:]
    else:
        width = max(len(r) for r in all_rows)
        headers = [f"col_{i + 1}" for i in range(width)]
        rows = all_rows

    if not rows:
        raise FileError(f"文件仅含表头无数据行: {input_path}")

    # 校验字段数一致性，跳过异常行
    n_cols = len(headers)
    valid_rows: List[List[str]] = []
    for idx, row in enumerate(rows, start=2 if has_header else 1):
        if len(row) != n_cols:
            warnings.append(f"第 {idx} 行字段数不一致（{len(row)} != {n_cols}），已跳过")
            continue
        valid_rows.append(row)

    if not valid_rows:
        raise FileError(f"文件无有效数据行（全部字段数不一致）: {input_path}")

    # 列白名单过滤
    if columns:
        try:
            col_indices = [headers.index(col) for col in columns]
        except ValueError as e:
            raise ConfigError(f"列不存在: {e}") from e
        headers = [headers[i] for i in col_indices]
        valid_rows = [[row[i] for i in col_indices] for row in valid_rows]

    return headers, valid_rows, warnings


def _coerce(headers: List[str], rows: List[List[str]]):
    """
    对每列做类型推断并转换。

    Returns:
        (col_types, col_data, warnings)
        col_types: 列名 -> 推断类型名（int/float/str）
        col_data: 列名 -> 该列所有值列表（已转换，非数值保留为 str）
        warnings: 非数值混入的警告列表

    推断规则：尝试 int → float → 保留 str。
    """
    col_types: Dict[str, str] = {}
    col_data: Dict[str, List[Any]] = {h: [] for h in headers}
    warnings: List[str] = []

    for col_idx, header in enumerate(headers):
        values = [row[col_idx] for row in rows]
        # 判断列类型：空值跳过
        non_empty = [v for v in values if v.strip() != ""]

        col_type = "str"
        if non_empty:
            # 尝试全部转 int
            try:
                [int(v) for v in non_empty]
                col_type = "int"
            except ValueError:
                # 尝试全部转 float
                try:
                    [float(v) for v in non_empty]
                    col_type = "float"
                except ValueError:
                    # 保留字符串，但记录非数值混入
                    col_type = "str"
                    warnings.append(f"列 {header!r} 含非数值数据，数值统计时将被跳过")

        col_data[header] = values
        col_types[header] = col_type

    return col_types, col_data, warnings


# ---------------------------------------------------------------------------
# 计算层（纯函数，无 IO）
# ---------------------------------------------------------------------------

def _compute_summary(headers, rows, col_types, col_data):
    """计算数据概览。"""
    n_rows = len(rows)
    n_cols = len(headers)

    columns_detail = []
    for header in headers:
        values = col_data[header]
        missing = sum(1 for v in values if v.strip() == "")
        unique = len(set(v for v in values if v.strip() != ""))
        columns_detail.append({
            "name": header,
            "type": col_types[header],
            "missing": missing,
            "unique": unique,
        })

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "columns": columns_detail,
    }


def _compute_stats(headers, col_types, col_data):
    """计算数值统计。"""
    stats_detail = []
    for header in headers:
        col_type = col_types[header]
        entry = {"name": header, "type": col_type}

        if col_type in ("int", "float"):
            numeric = []
            for v in col_data[header]:
                if v.strip() == "":
                    continue
                try:
                    numeric.append(float(v))
                except ValueError:
                    continue  # 非数值跳过

            if numeric:
                entry["count"] = len(numeric)
                entry["missing"] = len(col_data[header]) - len(numeric)
                entry["min"] = min(numeric)
                entry["max"] = max(numeric)
                entry["mean"] = statistics.mean(numeric)
                entry["median"] = statistics.median(numeric)
                entry["std"] = statistics.stdev(numeric) if len(numeric) > 1 else None
            else:
                entry["count"] = 0
                entry["missing"] = len(col_data[header])
                entry["min"] = entry["max"] = entry["mean"] = entry["median"] = None
                entry["std"] = None
        else:
            # 非数值列：仅统计非空数量
            non_empty = [v for v in col_data[header] if v.strip() != ""]
            entry["count"] = len(non_empty)
            entry["missing"] = len(col_data[header]) - len(non_empty)
            entry["note"] = "非数值列，仅统计非空数量"

        stats_detail.append(entry)

    return {"columns": stats_detail}


def _compute_group(headers, rows, col_types, group_cols):
    """按指定列分组聚合。"""
    # 校验分组列存在
    for col in group_cols:
        if col not in headers:
            raise ConfigError(f"分组列不存在: {col}")

    # 数值列（用于计算均值）
    numeric_cols = [
        h for h in headers
        if col_types[h] in ("int", "float") and h not in group_cols
    ]

    group_indices = [headers.index(col) for col in group_cols]
    numeric_indices = [headers.index(col) for col in numeric_cols]

    groups: Dict[tuple, List[List[str]]] = {}
    for row in rows:
        key = tuple(row[i] for i in group_indices)
        groups.setdefault(key, []).append(row)

    group_result = []
    for key, group_rows in groups.items():
        entry = {"group": list(key), "count": len(group_rows)}
        # 计算数值列均值
        entry["means"] = {}
        for col, idx in zip(numeric_cols, numeric_indices):
            numeric = []
            for r in group_rows:
                if r[idx].strip() == "":
                    continue
                try:
                    numeric.append(float(r[idx]))
                except ValueError:
                    continue
            entry["means"][col] = statistics.mean(numeric) if numeric else None
        group_result.append(entry)

    # 按组大小降序排序
    group_result.sort(key=lambda e: e["count"], reverse=True)

    return {
        "group_cols": group_cols,
        "numeric_cols": numeric_cols,
        "groups": group_result,
        "n_groups": len(group_result),
    }


def _compute_top(headers, rows, sort_col, limit):
    """按指定列排序，取前 N 行。"""
    if sort_col not in headers:
        raise ConfigError(f"排序列不存在: {sort_col}")

    sort_idx = headers.index(sort_col)

    def _sort_key(row):
        val = row[sort_idx]
        # 尝试数值排序，失败则用字符串（小写）排序
        try:
            return (0, float(val))
        except (ValueError, TypeError):
            return (1, val.lower())

    sorted_rows = sorted(rows, key=_sort_key, reverse=True)
    top_rows = sorted_rows[:limit]

    return {
        "sort_col": sort_col,
        "limit": limit,
        "rows": top_rows,
        "headers": headers,
    }


# ---------------------------------------------------------------------------
# 渲染层辅助函数
# ---------------------------------------------------------------------------

def _fmt(v):
    """格式化数值，None 显示为 '-'。"""
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _render_md_table(headers, rows):
    """渲染 Markdown 表格。"""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        cells = [str(c) for c in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _render_header_meta(input_path, report_type, n_rows, n_cols, warnings=None):
    """生成报告头部元信息行（用于 md/txt）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# CSV 报告",
        "",
        f"- **数据来源**: `{input_path}`",
        f"- **生成时间**: {now}",
        f"- **行数/列数**: {n_rows} / {n_cols}",
        f"- **报告类型**: {report_type}",
        "",
    ]
    if warnings:
        lines.append("**警告**:")
        for w in warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
    return lines


def _render_html_table(headers, rows):
    """渲染 HTML 表格。"""
    thead = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for row in rows:
        tds = "".join(f"<td>{c}</td>" for c in row)
        body.append(f"<tr>{tds}</tr>")
    return (
        f"<table><thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _render_txt_table(headers, rows):
    """渲染纯文本对齐表格。"""
    all_rows = [headers] + [[str(c) for c in r] for r in rows]
    widths = []
    for i in range(len(headers)):
        widths.append(max(len(r[i]) for r in all_rows))

    def _line(r):
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(r))

    lines = [_line(all_rows[0])]
    lines.append("-+-".join("-" * w for w in widths))
    for r in all_rows[1:]:
        lines.append(_line(r))
    return "\n".join(lines)


def _html_wrap(title, content):
    """包裹为完整 HTML 文档（内联样式）。"""
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif;
       margin: 2rem auto; max-width: 900px; padding: 0 1rem; color: #333; }}
h1 {{ border-bottom: 2px solid #eee; padding-bottom: .3rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f5f5; font-weight: 600; }}
tr:nth-child(even) {{ background: #fafafa; }}
.meta {{ color: #666; font-size: .9rem; }}
.warn {{ color: #b58900; }}
</style>
</head>
<body>
{content}
</body>
</html>
"""
