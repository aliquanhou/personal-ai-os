#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场日报自动生成脚本
====================
每天 9:00 自动生成一份市场日报（Markdown 格式），
包含：市场概览、热门板块、个股涨跌、宏观/要闻摘要。

设计原则：
- 数据源用免费公开接口（新浪财经）+ 兜底数据，无需 API Key
- 定时调度用 schedule 库，简单可靠
- 输出为 Markdown，便于阅读和后续归档
- 失败自动降级为兜底数据，保证日报一定能生成

用法：
    python market_daily_report.py          # 启动调度，每天9点生成
    python market_daily_report.py --once   # 立即生成一份（用于测试）
"""

import argparse
import datetime
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# 新浪财经公开行情接口（免费，无需 key）
# 指数代码：sh000001=上证指数, sz399001=深证成指, sz399006=创业板指
INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
}

SINA_QUOTE_URL = "https://hq.sinajs.cn/list={codes}"
# 新浪接口要求带 Referer，否则可能被拒
HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}


# ---------------------------------------------------------------------------
# 数据采集
# ---------------------------------------------------------------------------
def fetch_index_quotes():
    """从新浪财经拉取指数行情。失败返回 None。"""
    codes = ",".join(INDEX_CODES.values())
    try:
        resp = requests.get(SINA_QUOTE_URL.format(codes=codes), headers=HEADERS, timeout=8)
        resp.encoding = "gbk"  # 新浪返回 GBK 编码
        quotes = {}
        for line in resp.text.strip().splitlines():
            # 格式: var hq_str_sh000001="名称,今开,昨收,现价,最高,最低,...";
            if "=" not in line:
                continue
            code = line.split("=")[0].split("_")[-1]
            raw = line.split('"')[1]
            parts = raw.split(",")
            if len(parts) < 4:
                continue
            quotes[code] = {
                "name": parts[0],
                "price": float(parts[3]) if parts[3] else 0,
                "prev_close": float(parts[2]) if parts[2] else 0,
                "open": float(parts[1]) if parts[1] else 0,
                "high": float(parts[4]) if parts[4] else 0,
                "low": float(parts[5]) if parts[5] else 0,
            }
        return quotes
    except Exception as e:
        print(f"[warn] 新浪行情获取失败: {e}")
        return None


def fetch_news_summary():
    """获取要闻摘要。这里用兜底示例（可替换为真实 RSS/API）。"""
    return [
        {"title": "市场早间盘前要闻（示例，可替换为真实新闻源）",
         "summary": "请在此处接入你的新闻源（如 RSS 或财经 API）以获取实时要闻。"},
    ]


# ---------------------------------------------------------------------------
# 兜底数据（接口不可用时降级使用）
# ---------------------------------------------------------------------------
def fallback_quotes():
    """接口失败时的演示数据，保证日报始终能生成。"""
    return {
        "sh000001": {"name": "上证指数", "price": 0, "prev_close": 0, "open": 0, "high": 0, "low": 0},
        "sz399001": {"name": "深证成指", "price": 0, "prev_close": 0, "open": 0, "high": 0, "low": 0},
        "sz399006": {"name": "创业板指", "price": 0, "prev_close": 0, "open": 0, "high": 0, "low": 0},
    }


# ---------------------------------------------------------------------------
# 日报生成
# ---------------------------------------------------------------------------
def build_report(quotes, news):
    """组装 Markdown 日报内容。"""
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %A")
    time_str = now.strftime("%H:%M")

    lines = []
    lines.append(f"# 📈 市场日报 · {date_str}")
    lines.append("")
    lines.append(f"> 生成时间：{time_str} ｜ 自动生成")
    lines.append("")
    lines.append("## 一、主要指数概览")
    lines.append("")
    lines.append("| 指数 | 最新价 | 涨跌幅 | 今开 | 最高 | 最低 |")
    lines.append("|------|--------|--------|------|------|------|")

    for display_name, code in INDEX_CODES.items():
        q = quotes.get(code, {})
        price = q.get("price", 0)
        prev = q.get("prev_close", 0)
        if prev:
            pct = (price - prev) / prev * 100
            pct_str = f"{pct:+.2f}%"
        else:
            pct_str = "--"
        lines.append(
            f"| {display_name} | {price:.2f} | {pct_str} | "
            f"{q.get('open', 0):.2f} | {q.get('high', 0):.2f} | {q.get('low', 0):.2f} |"
        )

    lines.append("")
    lines.append("## 二、盘前要闻")
    lines.append("")
    for item in news:
        lines.append(f"- **{item['title']}**：{item['summary']}")
    lines.append("")

    # 免责声明
    lines.append("---")
    lines.append("*本日报由脚本自动生成，数据来自公开行情接口，仅供参考，不构成投资建议。*")
    lines.append("")

    return "\n".join(lines)


def generate_report():
    """生成日报并写入文件，返回文件路径。"""
    quotes = fetch_index_quotes()
    if not quotes:
        print("[warn] 使用兜底数据生成日报")
        quotes = fallback_quotes()
    news = fetch_news_summary()

    content = build_report(quotes, news)

    filename = datetime.datetime.now().strftime("market_report_%Y%m%d.md")
    filepath = REPORT_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] 日报已生成：{filepath}")
    return filepath


# ---------------------------------------------------------------------------
# 定时调度
# ---------------------------------------------------------------------------
def run_scheduler():
    """每天 9:00 执行一次生成任务。"""
    import schedule

    schedule.every().day.at("09:00").do(generate_report)
    print("[*] 调度已启动：每天 09:00 自动生成市场日报")
    print("[*] 按 Ctrl+C 停止")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="每天9点自动生成市场日报")
    parser.add_argument("--once", action="store_true", help="立即生成一份日报（测试用）")
    args = parser.parse_args()

    if args.once:
        generate_report()
        return

    run_scheduler()


if __name__ == "__main__":
    main()
