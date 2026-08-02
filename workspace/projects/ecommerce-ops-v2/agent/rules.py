"""规则引擎：强规则定义与校验。

MVP 使用强规则（确定性、可量化）。预留 AI 分析扩展点 ai_analyze()，
后续可接入 DeepSeek 做异常智能分析（复用 Personal AI OS 能力）。
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Anomaly:
    """一条异常记录。"""
    type: str          # 异常类型
    level: str         # info / warning / critical
    reference_id: str  # 关联业务ID（订单号/商品SKU等）
    detail: str        # 异常描述
    meta: dict = field(default_factory=dict)


# ---------- AI 分析扩展点 ----------

def ai_analyze(anomalies: list, task_type: str) -> list:
    """AI 异常智能分析扩展点。

    MVP 阶段返回原样（不启用 AI）。v2.1 可接入：
    - 对 critical 异常做根因分析
    - 生成处理建议
    - 返回增强后的异常列表
    """
    # TODO(v2.1): 接入 DeepSeek 进行异常智能分析
    return anomalies


# ---------- 订单核对规则 ----------

INVALID_PLATFORMS = {"", "unknown", "test"}
INVALID_ORDER_STATUS = {"", "cancelled", "pending_payment"}
AMOUNT_MIN = 0.0


def check_order(row: dict, params: dict) -> list:
    """校验单条订单记录，返回异常列表。"""
    anomalies = []
    order_id = str(row.get("order_id", ""))
    platform = str(row.get("platform", "")).strip().lower()
    status = str(row.get("status", "")).strip().lower()
    amount = float(row.get("amount") or 0)

    # 重复订单（由外层去重检测）
    if str(row.get("_duplicate", "")).lower() in ("1", "true", "yes"):
        anomalies.append(Anomaly(
            type="duplicate_order", level="warning",
            reference_id=order_id, detail=f"重复订单: {order_id}",
        ))

    if platform in INVALID_PLATFORMS:
        anomalies.append(Anomaly(
            type="invalid_platform", level="warning",
            reference_id=order_id, detail=f"无效平台: '{platform}'",
        ))

    if status in INVALID_ORDER_STATUS:
        anomalies.append(Anomaly(
            type="invalid_status", level="warning",
            reference_id=order_id, detail=f"无效状态: '{status}'",
        ))

    if amount < AMOUNT_MIN:
        anomalies.append(Anomaly(
            type="negative_amount", level="critical",
            reference_id=order_id, detail=f"异常金额: {amount}",
        ))

    return anomalies


# ---------- 库存对账规则 ----------

def check_stock(system_qty: float, warehouse_qty: float, sku: str,
                tolerance: float = 0) -> list:
    """校验单条库存记录，返回异常列表。"""
    anomalies = []
    diff = system_qty - warehouse_qty

    if system_qty < 0:
        anomalies.append(Anomaly(
            type="negative_stock", level="critical",
            reference_id=sku, detail=f"系统库存为负: {system_qty}",
        ))

    if abs(diff) > tolerance:
        anomalies.append(Anomaly(
            type="stock_diff", level="warning",
            reference_id=sku,
            detail=f"库存差异 {diff} (系统 {system_qty} vs 仓库 {warehouse_qty})",
            meta={"diff": diff, "system_qty": system_qty, "warehouse_qty": warehouse_qty},
        ))

    return anomalies


# ---------- 商品资料清洗规则 ----------

def check_product(row: dict, params: dict) -> list:
    """校验单条商品记录，返回异常列表。"""
    anomalies = []
    sku = str(row.get("sku", ""))
    name = str(row.get("name", "")).strip()
    cost = float(row.get("cost") or 0)
    price = float(row.get("price") or 0)

    if not name:
        anomalies.append(Anomaly(
            type="missing_name", level="warning",
            reference_id=sku, detail="商品名称为空",
        ))

    if cost < 0:
        anomalies.append(Anomaly(
            type="negative_cost", level="critical",
            reference_id=sku, detail=f"成本为负: {cost}",
        ))

    if price <= 0:
        anomalies.append(Anomaly(
            type="invalid_price", level="critical",
            reference_id=sku, detail=f"售价无效: {price}",
        ))

    return anomalies
