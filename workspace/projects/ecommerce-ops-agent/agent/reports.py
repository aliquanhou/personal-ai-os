"""电商运营数字员工 - 报表生成

负责生成各类运营报表：
- 每日运营日报（Excel格式）
- 异常报告
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from agent import config
from agent.models import Anomaly

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报表生成器"""

    def generate_daily_report(
        self,
        orders_df: pd.DataFrame,
        inventory_df: pd.DataFrame,
        products_df: pd.DataFrame,
        anomalies: List[Anomaly],
        data_date: str,
    ) -> str:
        """生成每日运营日报（Excel格式）

        Args:
            orders_df: 订单数据
            inventory_df: 库存数据
            products_df: 商品数据（已清洗）
            anomalies: 异常列表
            data_date: 数据日期 YYYY-MM-DD

        Returns:
            报表文件路径
        """
        logger.info("开始生成每日运营日报 %s", data_date)

        # 创建输出目录
        config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = config.REPORT_DIR / f"daily_report_{data_date}.xlsx"

        # 准备数据
        report_date = data_date or datetime.now().strftime("%Y-%m-%d")

        # 1. 销售汇总
        total_orders = len(orders_df)
        total_amount = float(orders_df["total_amount"].sum()) if total_orders > 0 else 0.0
        avg_amount = total_amount / total_orders if total_orders > 0 else 0.0

        # 按平台统计
        platform_stats = orders_df.groupby("platform").agg(
            order_count=("order_id", "count"),
            total_amount=("total_amount", "sum"),
        ).reset_index() if total_orders > 0 else pd.DataFrame()

        # 按状态统计
        status_stats = orders_df.groupby("status").agg(
            order_count=("order_id", "count"),
        ).reset_index() if total_orders > 0 else pd.DataFrame()

        # 2. 库存汇总
        total_skus = len(inventory_df)
        if total_skus > 0 and "diff" not in inventory_df.columns:
            inventory_df = inventory_df.copy()
            inventory_df["diff"] = inventory_df["system_qty"] - inventory_df["warehouse_qty"]
        stock_discrepancy_count = int(
            (inventory_df["diff"].abs() > config.INVENTORY_TOLERANCE).sum()
        ) if total_skus > 0 else 0

        # 3. 商品汇总
        total_products = len(products_df)
        on_sale_count = int((products_df["status"] == "on_sale").sum()) if total_products > 0 else 0
        avg_profit_margin = float(products_df["profit_margin"].mean()) if total_products > 0 else 0.0

        # 4. 异常汇总
        anomaly_counts = {}
        for a in anomalies:
            anomaly_counts[a.type] = anomaly_counts.get(a.type, 0) + 1

        # 创建Excel报表
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Sheet 1: 汇总
            summary_data = {
                "指标": [
                    "数据日期", "订单总数", "销售总额(元)", "平均订单金额(元)",
                    "库存SKU数", "库存差异数", "商品总数", "在售商品数",
                    "平均毛利率(%)", "异常总数",
                ],
                "数值": [
                    report_date, total_orders, round(total_amount, 2), round(avg_amount, 2),
                    total_skus, stock_discrepancy_count, total_products, on_sale_count,
                    round(avg_profit_margin, 2), len(anomalies),
                ],
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="汇总", index=False)

            # Sheet 2: 平台订单统计
            if not platform_stats.empty:
                platform_stats.to_excel(writer, sheet_name="平台统计", index=False)
            else:
                pd.DataFrame({"platform": [], "order_count": [], "total_amount": []}).to_excel(
                    writer, sheet_name="平台统计", index=False
                )

            # Sheet 3: 订单状态统计
            if not status_stats.empty:
                status_stats.to_excel(writer, sheet_name="订单状态", index=False)
            else:
                pd.DataFrame({"status": [], "order_count": []}).to_excel(
                    writer, sheet_name="订单状态", index=False
                )

            # Sheet 4: 库存差异详情
            if total_skus > 0:
                diff_df = inventory_df[inventory_df["diff"].abs() > config.INVENTORY_TOLERANCE]
                if not diff_df.empty:
                    diff_df[["sku_id", "product_name", "system_qty", "warehouse_qty", "diff"]].to_excel(
                        writer, sheet_name="库存差异", index=False
                    )
                else:
                    pd.DataFrame({"sku_id": [], "product_name": [], "system_qty": [], "warehouse_qty": [], "diff": []}).to_excel(
                        writer, sheet_name="库存差异", index=False
                    )

            # Sheet 5: 异常明细
            if anomalies:
                anomaly_df = pd.DataFrame([a.to_dict() for a in anomalies])
                anomaly_df.to_excel(writer, sheet_name="异常明细", index=False)
            else:
                pd.DataFrame({"type": [], "level": [], "source": [], "reference_id": [], "detail": [], "timestamp": []}).to_excel(
                    writer, sheet_name="异常明细", index=False
                )

        logger.info("日报生成成功: %s", output_path)
        return str(output_path)

    def generate_anomaly_report(self, anomalies: List[Anomaly], data_date: str) -> str:
        """生成异常报告（CSV格式）"""
        if not anomalies:
            logger.info("无异常，跳过异常报告生成")
            return ""

        config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = config.REPORT_DIR / f"anomalies_{data_date}.csv"

        anomaly_df = pd.DataFrame([a.to_dict() for a in anomalies])
        anomaly_df.to_csv(output_path, index=False, encoding="utf-8-sig")

        logger.info("异常报告生成成功: %s", output_path)
        return str(output_path)
