"""销售数据分析数字员工 - 日报生成模块"""
import logging
from datetime import datetime

from . import config

logger = logging.getLogger(__name__)


def generate_report(result: dict, data_date: str) -> str:
    """根据分析结果生成 Markdown 日报文本"""
    lines = []
    lines.append(f"# 销售数据分析日报")
    lines.append("")
    lines.append(f"- **数据日期**: {data_date}")
    lines.append(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 总览
    lines.append("## 📊 总览")
    lines.append("")
    lines.append(f"- 订单总数: **{result['total_orders']}**")
    lines.append(f"- 销售总额: **¥{result['total_amount']:,.2f}**")
    lines.append(f"- 销售总量: **{result['total_qty']:,.0f}** 件")
    lines.append("")

    # 商品排名
    lines.append("## 🏆 商品销售排名 (Top 10)")
    lines.append("")
    lines.append("| 排名 | 商品 | 销售额(元) | 销量 | 订单数 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, item in enumerate(result["product_ranking"][:10], start=1):
        lines.append(
            f"| {i} | {item.get(config.COL_PRODUCT, '-')} | "
            f"{item['total_amount']:,.2f} | {item['total_qty']:,.0f} | {item['order_count']} |"
        )
    lines.append("")

    # 客户排名
    lines.append("## 🏆 客户销售排名 (Top 10)")
    lines.append("")
    lines.append("| 排名 | 客户 | 销售额(元) | 订单数 |")
    lines.append("| --- | --- | --- | --- |")
    for i, item in enumerate(result["customer_ranking"][:10], start=1):
        lines.append(
            f"| {i} | {item.get(config.COL_CUSTOMER, '-')} | "
            f"{item['total_amount']:,.2f} | {item['order_count']} |"
        )
    lines.append("")

    # 异常订单
    anomalies = result["anomalies"]
    lines.append(f"## ⚠️ 异常订单 ({len(anomalies)})")
    lines.append("")
    if anomalies:
        lines.append("| 类型 | 订单号 | 金额(元) | 说明 |")
        lines.append("| --- | --- | --- | --- |")
        for a in anomalies:
            lines.append(
                f"| {a['type']} | {a['order_id']} | {a['amount']:,.2f} | {a['detail']} |"
            )
    else:
        lines.append("未发现异常订单 ✅")
    lines.append("")

    return "\n".join(lines)


def save_report(report_text: str, data_date: str) -> str:
    """保存日报到 reports 目录，返回文件路径"""
    safe_date = data_date.replace("/", "-").replace(":", "-")
    filename = f"日报_{safe_date}.md"
    path = config.REPORTS_DIR / filename
    path.write_text(report_text, encoding="utf-8")
    logger.info("日报已保存: %s", path)
    return str(path)
