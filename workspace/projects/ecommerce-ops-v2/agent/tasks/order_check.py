"""订单核对任务：检测重复订单、无效平台、无效状态、异常金额。"""

from agent import rules


def run(orders: list, params: dict) -> dict:
    """执行订单核对。

    orders: 订单记录列表 (dict)
    params: 规则参数
    返回: {"anomalies": [...], "stats": {...}}
    """
    # 去重检测
    seen = {}
    for row in orders:
        oid = str(row.get("order_id", ""))
        row["_duplicate"] = False
        if oid in seen:
            row["_duplicate"] = True
            seen[oid] = True
        else:
            seen[oid] = False

    anomalies = []
    for row in orders:
        anomalies.extend(rules.check_order(row, params))

    total_amount = sum(float(r.get("amount") or 0) for r in orders)
    stats = {
        "total_orders": len(orders),
        "total_amount": round(total_amount, 2),
        "duplicates": sum(1 for r in orders if r.get("_duplicate")),
        "anomaly_count": len(anomalies),
    }
    return {"anomalies": anomalies, "stats": stats}
