"""生成示例数据：orders.csv / stocks.csv / products.csv。

用于演示电商运营数字员工的三个核心任务。
"""

import csv
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _write_csv(filename: str, fieldnames: list, rows: list) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _gen_orders() -> None:
    """生成订单数据（含重复、无效平台、无效状态、负金额）。"""
    rows = []
    platforms = ["taobao", "jd", "pdd", "unknown", ""]
    statuses = ["paid", "shipped", "completed", "cancelled", ""]

    for i in range(1, 51):
        rows.append({
            "order_id": f"ORD{i:04d}",
            "platform": random.choice(platforms[:3]),  # 正常平台为主
            "status": random.choice(statuses[:3]),     # 正常状态为主
            "amount": round(random.uniform(20, 5000), 2),
        })

    # 注入异常
    rows[3]["platform"] = "unknown"       # 无效平台
    rows[7]["status"] = "cancelled"       # 无效状态
    rows[10]["amount"] = -99.5            # 负金额
    rows.append(dict(rows[0]))            # 重复订单 ORD0001
    rows.append(dict(rows[1]))            # 重复订单 ORD0002

    path = _write_csv("orders.csv",
                      ["order_id", "platform", "status", "amount"], rows)
    print(f"  ✅ 生成 {path} ({len(rows)} 条)")


def _gen_stocks() -> None:
    """生成库存数据（含差异、负数库存）。"""
    rows = []
    for i in range(1, 41):
        sku = f"SKU{i:04d}"
        sys_qty = random.randint(0, 200)
        wh_qty = random.randint(0, 200)
        rows.append({
            "sku": sku,
            "system_qty": sys_qty,
            "warehouse_qty": wh_qty,
        })

    # 注入异常
    rows[5]["system_qty"] = -10           # 负数库存
    rows[12]["warehouse_qty"] = rows[12]["system_qty"] + 50  # 大差异
    rows[20]["system_qty"] = rows[20]["warehouse_qty"] + 30  # 大差异

    path = _write_csv("stocks.csv",
                      ["sku", "system_qty", "warehouse_qty"], rows)
    print(f"  ✅ 生成 {path} ({len(rows)} 条)")


def _gen_products() -> None:
    """生成商品数据（含空名称、负成本、无效售价）。"""
    rows = []
    names = ["无线蓝牙耳机", "智能手环", "便携充电宝", "机械键盘", "显示器支架",
             "USB-C扩展坞", "降噪耳麦", "无线鼠标", "电竞椅", "桌面台灯"]
    for i in range(1, 31):
        rows.append({
            "sku": f"PRD{i:04d}",
            "name": random.choice(names),
            "cost": round(random.uniform(10, 300), 2),
            "price": round(random.uniform(50, 800), 2),
            "category": random.choice(["3C数码", "配件", "外设"]),
        })

    # 注入异常
    rows[4]["name"] = "   "               # 空名称（清洗后为空）
    rows[9]["cost"] = -5.0                # 负成本
    rows[15]["price"] = 0                 # 无效售价

    path = _write_csv("products.csv",
                      ["sku", "name", "cost", "price", "category"], rows)
    print(f"  ✅ 生成 {path} ({len(rows)} 条)")


def main():
    print("生成示例数据...")
    _gen_orders()
    _gen_stocks()
    _gen_products()
    print("完成。")


if __name__ == "__main__":
    main()
