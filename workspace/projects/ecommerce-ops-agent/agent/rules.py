"""电商运营数字员工 - 规则引擎

负责执行各类业务规则校验：
- 订单核对规则
- 库存对账规则
- 商品资料清洗规则
"""

import logging
from typing import List

import pandas as pd

from agent import config
from agent.models import Anomaly

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎 - 执行各类业务规则校验"""

    def __init__(self):
        self.anomalies: List[Anomaly] = []

    def check_orders(self, orders_df: pd.DataFrame) -> List[Anomaly]:
        """订单核对规则

        规则：
        1. 订单号不能为空且不能重复
        2. 平台必须在有效列表中
        3. 订单状态必须在有效列表中
        4. 订单金额必须大于0
        5. 订单日期格式必须正确
        """
        self.anomalies = []
        logger.info("开始订单核对，共 %d 条记录", len(orders_df))

        # 规则1：订单号不能为空且不能重复
        if orders_df["order_id"].isna().any():
            for idx in orders_df[orders_df["order_id"].isna()].index:
                self.anomalies.append(Anomaly(
                    type="missing_field",
                    level="critical",
                    source="order",
                    reference_id=f"row_{idx}",
                    detail="订单号为空",
                ))

        dups = orders_df[orders_df.duplicated("order_id", keep=False)]
        if not dups.empty:
            for order_id in dups["order_id"].unique():
                count = len(dups[dups["order_id"] == order_id])
                self.anomalies.append(Anomaly(
                    type="duplicate_order",
                    level="critical",
                    source="order",
                    reference_id=order_id,
                    detail=f"订单号重复，出现 {count} 次",
                ))

        # 规则2：平台必须在有效列表中
        invalid_platforms = orders_df[~orders_df["platform"].isin(config.PLATFORMS)]
        for _, row in invalid_platforms.iterrows():
            self.anomalies.append(Anomaly(
                type="invalid_platform",
                level="warning",
                source="order",
                reference_id=row.get("order_id", "unknown"),
                detail=f"无效平台: {row['platform']}",
            ))

        # 规则3：订单状态必须在有效列表中
        invalid_status = orders_df[~orders_df["status"].isin(config.ORDER_STATUS_VALID)]
        for _, row in invalid_status.iterrows():
            self.anomalies.append(Anomaly(
                type="invalid_status",
                level="warning",
                source="order",
                reference_id=row.get("order_id", "unknown"),
                detail=f"无效订单状态: {row['status']}",
            ))

        # 规则4：订单金额必须大于0
        invalid_amount = orders_df[orders_df["total_amount"] <= 0]
        for _, row in invalid_amount.iterrows():
            self.anomalies.append(Anomaly(
                type="invalid_amount",
                level="warning",
                source="order",
                reference_id=row.get("order_id", "unknown"),
                detail=f"订单金额异常: {row['total_amount']}",
            ))

        # 规则5：订单日期格式检查
        try:
            pd.to_datetime(orders_df["order_date"])
        except Exception:
            self.anomalies.append(Anomaly(
                type="date_format_error",
                level="warning",
                source="order",
                reference_id="N/A",
                detail="订单日期格式存在无法解析的值",
            ))

        logger.info("订单核对完成，发现 %d 条异常", len(self.anomalies))
        return self.anomalies

    def check_inventory(self, inventory_df: pd.DataFrame) -> List[Anomaly]:
        """库存对账规则

        规则：
        1. SKU不能为空且不能重复
        2. 系统库存与仓库库存差异超过容差时预警
        3. 库存数量不能为负数
        """
        self.anomalies = []
        logger.info("开始库存对账，共 %d 条记录", len(inventory_df))

        # 规则1：SKU不能为空且不能重复
        if inventory_df["sku_id"].isna().any():
            for idx in inventory_df[inventory_df["sku_id"].isna()].index:
                self.anomalies.append(Anomaly(
                    type="missing_field",
                    level="critical",
                    source="inventory",
                    reference_id=f"row_{idx}",
                    detail="SKU为空",
                ))

        dups = inventory_df[inventory_df.duplicated("sku_id", keep=False)]
        if not dups.empty:
            for sku in dups["sku_id"].unique():
                count = len(dups[dups["sku_id"] == sku])
                self.anomalies.append(Anomaly(
                    type="duplicate_sku",
                    level="warning",
                    source="inventory",
                    reference_id=sku,
                    detail=f"SKU重复，出现 {count} 次",
                ))

        # 规则2：库存差异检查
        inventory_df["diff"] = inventory_df["system_qty"] - inventory_df["warehouse_qty"]
        tolerance = config.INVENTORY_TOLERANCE
        discrepancies = inventory_df[inventory_df["diff"].abs() > tolerance]
        for _, row in discrepancies.iterrows():
            level = "critical" if abs(row["diff"]) > 10 else "warning"
            self.anomalies.append(Anomaly(
                type="inventory_diff",
                level=level,
                source="inventory",
                reference_id=row["sku_id"],
                detail=f"库存差异: 系统={row['system_qty']}, 仓库={row['warehouse_qty']}, 差={row['diff']}",
            ))

        # 规则3：库存数量不能为负数
        negative_qty = inventory_df[
            (inventory_df["system_qty"] < 0) | (inventory_df["warehouse_qty"] < 0)
        ]
        for _, row in negative_qty.iterrows():
            self.anomalies.append(Anomaly(
                type="negative_qty",
                level="critical",
                source="inventory",
                reference_id=row["sku_id"],
                detail=f"库存为负数: 系统={row['system_qty']}, 仓库={row['warehouse_qty']}",
            ))

        logger.info("库存对账完成，发现 %d 条异常", len(self.anomalies))
        return self.anomalies

    def clean_products(self, products_df: pd.DataFrame) -> pd.DataFrame:
        """商品资料清洗规则

        规则：
        1. 去除空行
        2. 标准化SKU（去除空格、转大写）
        3. 标准化商品名称（去除首尾空格）
        4. 校验价格有效性
        5. 校验状态有效性
        6. 计算毛利率
        """
        self.anomalies = []
        logger.info("开始商品资料清洗，共 %d 条记录", len(products_df))

        df = products_df.copy()

        # 规则1：去除全空行
        before = len(df)
        df = df.dropna(how="all")
        if len(df) < before:
            self.anomalies.append(Anomaly(
                type="empty_rows_removed",
                level="info",
                source="product",
                reference_id="N/A",
                detail=f"移除 {before - len(df)} 行全空数据",
            ))

        # 规则2：标准化SKU
        df["sku_id"] = df["sku_id"].astype(str).str.strip().str.upper()

        # 规则3：标准化商品名称
        df["product_name"] = df["product_name"].astype(str).str.strip()

        # 规则4：校验价格有效性
        invalid_price = df[df["price"] < config.PRICE_MIN]
        for _, row in invalid_price.iterrows():
            self.anomalies.append(Anomaly(
                type="price_error",
                level="warning",
                source="product",
                reference_id=row["sku_id"],
                detail=f"售价异常: {row['price']}",
            ))

        invalid_cost = df[df["cost"] < config.COST_MIN]
        for _, row in invalid_cost.iterrows():
            self.anomalies.append(Anomaly(
                type="cost_error",
                level="warning",
                source="product",
                reference_id=row["sku_id"],
                detail=f"成本异常: {row['cost']}",
            ))

        # 规则5：校验状态有效性
        invalid_status = df[~df["status"].isin(config.PRODUCT_STATUS_VALID)]
        for _, row in invalid_status.iterrows():
            self.anomalies.append(Anomaly(
                type="invalid_status",
                level="warning",
                source="product",
                reference_id=row["sku_id"],
                detail=f"无效商品状态: {row['status']}",
            ))

        # 规则6：计算毛利率
        df["profit_margin"] = df.apply(
            lambda r: round((r["price"] - r["cost"]) / r["price"] * 100, 2)
            if r["price"] > 0 else 0.0,
            axis=1,
        )

        # 规则7：SKU去重（保留第一条）
        before_dedup = len(df)
        df = df.drop_duplicates(subset=["sku_id"], keep="first")
        if len(df) < before_dedup:
            self.anomalies.append(Anomaly(
                type="duplicate_sku",
                level="warning",
                source="product",
                reference_id="N/A",
                detail=f"SKU去重，移除 {before_dedup - len(df)} 条重复记录",
            ))

        logger.info("商品资料清洗完成，发现 %d 条异常", len(self.anomalies))
        return df

    def get_all_anomalies(self) -> List[Anomaly]:
        """获取所有异常"""
        return self.anomalies
