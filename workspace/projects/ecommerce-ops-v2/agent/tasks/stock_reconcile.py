"""库存对账任务：系统库存 vs 仓库库存，检测差异与负数库存。"""

from agent import rules


def run(stocks: list, params: dict) -> dict:
    """执行库存对账。

    stocks: 库存记录列表 (dict, 含 sku/system_qty/warehouse_qty)
    params: 规则参数 (tolerance 差异容忍度)
    """
    tolerance = float(params.get("tolerance", 0))
    anomalies = []
    diffs = 0

    for row in stocks:
        sku = str(row.get("sku", ""))
        sys_qty = float(row.get("system_qty") or 0)
        wh_qty = float(row.get("warehouse_qty") or 0)
        res = rules.check_stock(sys_qty, wh_qty, sku, tolerance)
        anomalies.extend(res)
        if abs(sys_qty - wh_qty) > tolerance:
            diffs += 1

    stats = {
        "total_skus": len(stocks),
        "diff_count": diffs,
        "negative_count": sum(
            1 for a in anomalies if a.type == "negative_stock"
        ),
        "anomaly_count": len(anomalies),
    }
    return {"anomalies": anomalies, "stats": stats}
