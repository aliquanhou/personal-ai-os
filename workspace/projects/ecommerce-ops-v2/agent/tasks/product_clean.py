"""商品资料清洗任务：标准化商品数据，计算毛利率，标记异常。"""

from agent import rules


def _clean_name(name: str) -> str:
    """简单标准化：去除首尾空格、多余连续空格。"""
    return " ".join(str(name).strip().split())


def run(products: list, params: dict) -> dict:
    """执行商品资料清洗。

    products: 商品记录列表 (dict, 含 sku/name/cost/price/category)
    params: 规则参数
    返回: {"anomalies": [...], "cleaned": [...], "stats": {...}}
    """
    anomalies = []
    cleaned = []

    for row in products:
        row = dict(row)
        row["name"] = _clean_name(row.get("name", ""))
        cost = float(row.get("cost") or 0)
        price = float(row.get("price") or 0)
        # 计算毛利率
        margin = round((price - cost) / price * 100, 2) if price > 0 else 0.0
        row["margin_pct"] = margin
        cleaned.append(row)

        res = rules.check_product(row, params)
        anomalies.extend(res)

    stats = {
        "total_products": len(products),
        "cleaned_count": len(cleaned),
        "negative_margin": sum(1 for r in cleaned if r["margin_pct"] < 0),
        "anomaly_count": len(anomalies),
    }
    return {"anomalies": anomalies, "cleaned": cleaned, "stats": stats}
