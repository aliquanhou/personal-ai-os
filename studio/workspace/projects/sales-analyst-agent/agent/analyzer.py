"""销售数据分析数字员工 - 分析模块（排名 + 异常检测）"""
import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def analyze(df: pd.DataFrame) -> dict:
    """执行销售分析，返回结构化结果"""
    df = _clean_numeric(df)

    result = {
        "total_orders": int(len(df)),
        "total_amount": float(df[config.COL_AMOUNT].sum()),
        "total_qty": float(df[config.COL_QTY].sum()),
        "product_ranking": _product_ranking(df),
        "customer_ranking": _customer_ranking(df),
        "anomalies": _detect_anomalies(df),
    }
    return result


def _clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """清洗数值列：金额、数量转数值，非法值置 NaN"""
    df = df.copy()
    for col in (config.COL_AMOUNT, config.COL_QTY):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _product_ranking(df: pd.DataFrame) -> list[dict]:
    """按商品聚合销售额，返回 Top N 排名"""
    if config.COL_PRODUCT not in df.columns:
        return []
    g = (
        df.groupby(config.COL_PRODUCT)
        .agg(
            total_amount=(config.COL_AMOUNT, "sum"),
            total_qty=(config.COL_QTY, "sum"),
            order_count=(config.COL_ORDER_ID, "count"),
        )
        .sort_values("total_amount", ascending=False)
        .reset_index()
    )
    return g.to_dict("records")


def _customer_ranking(df: pd.DataFrame) -> list[dict]:
    """按客户聚合销售额，返回 Top N 排名"""
    if config.COL_CUSTOMER not in df.columns:
        return []
    g = (
        df.groupby(config.COL_CUSTOMER)
        .agg(
            total_amount=(config.COL_AMOUNT, "sum"),
            order_count=(config.COL_ORDER_ID, "count"),
        )
        .sort_values("total_amount", ascending=False)
        .reset_index()
    )
    return g.to_dict("records")


def _detect_anomalies(df: pd.DataFrame) -> list[dict]:
    """检测异常订单"""
    anomalies = []

    amount_col = config.COL_AMOUNT
    qty_col = config.COL_QTY

    # 1. 金额异常（偏离均值 N 倍标准差）
    if amount_col in df.columns:
        amounts = df[amount_col].dropna()
        if len(amounts) > 1:
            mean = amounts.mean()
            std = amounts.std()
            if std > 0:
                mask = (df[amount_col] - mean).abs() > config.AMOUNT_STD_MULT * std
                for _, row in df[mask].iterrows():
                    anomalies.append({
                        "type": "金额异常",
                        "order_id": _safe(row, config.COL_ORDER_ID),
                        "detail": f"金额 {row[amount_col]:.2f} 元，偏离均值 {mean:.2f} 元超过 {config.AMOUNT_STD_MULT} 倍标准差",
                        "amount": float(row[amount_col]),
                    })

    # 2. 金额越界（绝对值）
    if amount_col in df.columns:
        mask = (df[amount_col] < config.AMOUNT_MIN) | (df[amount_col] > config.AMOUNT_MAX)
        for _, row in df[mask].iterrows():
            anomalies.append({
                "type": "金额越界",
                "order_id": _safe(row, config.COL_ORDER_ID),
                "detail": f"金额 {row[amount_col]:.2f} 元超出合理范围 [{config.AMOUNT_MIN}, {config.AMOUNT_MAX}]",
                "amount": float(row[amount_col]),
            })

    # 3. 数量异常（非正数或超上限）
    if qty_col in df.columns:
        mask = (df[qty_col] <= 0) | (df[qty_col] > config.QTY_MAX)
        for _, row in df[mask].iterrows():
            anomalies.append({
                "type": "数量异常",
                "order_id": _safe(row, config.COL_ORDER_ID),
                "detail": f"数量 {row[qty_col]} 不在合理范围 (0, {config.QTY_MAX}]",
                "amount": float(row[amount_col]) if amount_col in df.columns else 0.0,
            })

    # 4. 重复订单（相同客户+金额+时间窗口内）
    if all(c in df.columns for c in (config.COL_CUSTOMER, config.COL_AMOUNT, config.COL_DATE)):
        try:
            dates = pd.to_datetime(df[config.COL_DATE], errors="coerce")
            tmp = df.copy()
            tmp["_date"] = dates
            tmp = tmp.dropna(subset=["_date"])
            tmp = tmp.sort_values("_date")
            dup_mask = (
                tmp.duplicated(subset=[config.COL_CUSTOMER, config.COL_AMOUNT], keep=False)
            )
            if dup_mask.any():
                # 简单标记：同一客户+金额出现多次即视为疑似重复
                seen = set()
                for _, row in tmp[dup_mask].iterrows():
                    key = (row[config.COL_CUSTOMER], row[config.COL_AMOUNT])
                    if key in seen:
                        anomalies.append({
                            "type": "疑似重复订单",
                            "order_id": _safe(row, config.COL_ORDER_ID),
                            "detail": f"客户 {row[config.COL_CUSTOMER]} 存在重复金额 {row[config.COL_AMOUNT]:.2f} 元",
                            "amount": float(row[config.COL_AMOUNT]),
                        })
                    seen.add(key)
        except Exception as e:  # noqa: BLE001
            logger.warning("重复订单检测跳过: %s", e)

    return anomalies


def _safe(row, col) -> str:
    """安全获取单元格值"""
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    return str(v)
