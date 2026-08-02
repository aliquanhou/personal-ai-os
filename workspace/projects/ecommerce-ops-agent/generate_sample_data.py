"""生成电商运营示例数据

生成订单、库存、商品三类示例数据，用于测试数字员工功能。
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from agent import config

# 固定随机种子，保证可复现
random.seed(42)

# 商品基础数据
PRODUCTS = [
    ("SKU001", "iPhone 15 Pro Max 256G", "手机", 8999, 6500),
    ("SKU002", "iPhone 15 Pro 128G", "手机", 7999, 5800),
    ("SKU003", "华为 Mate 60 Pro", "手机", 6999, 5100),
    ("SKU004", "小米 14 Ultra", "手机", 5999, 4300),
    ("SKU005", "MacBook Pro 14寸", "电脑", 14999, 11500),
    ("SKU006", "iPad Pro 12.9寸", "平板", 8999, 6800),
    ("SKU007", "AirPods Pro 2", "耳机", 1899, 1300),
    ("SKU008", "索尼 WH-1000XM5", "耳机", 2499, 1800),
    ("SKU009", "戴森 V12 吸尘器", "家电", 3999, 2800),
    ("SKU010", "飞利浦电动牙刷", "个护", 399, 220),
    ("SKU011", "罗技 MX Master 3S", "外设", 699, 450),
    ("SKU012", "三星 T7 移动硬盘", "存储", 899, 620),
]

PLATFORMS = ["taobao", "jd", "pdd", "douyin", "wechat"]
ORDER_STATUS = ["pending", "paid", "shipped", "completed", "cancelled"]
PRODUCT_STATUS = ["on_sale", "off_sale", "pending"]
CATEGORIES = ["手机", "电脑", "平板", "耳机", "家电", "个护", "外设", "存储"]

NAMES = ["张伟", "王芳", "李娜", "刘洋", "陈静", "杨帆", "赵磊", "黄敏", "周杰", "吴婷"]


def generate_orders(num_orders: int = 200) -> pd.DataFrame:
    """生成订单数据"""
    orders = []
    start_date = datetime.now() - timedelta(days=7)

    for i in range(1, num_orders + 1):
        order_id = f"ORD{i:06d}"
        platform = random.choice(PLATFORMS)
        order_date = start_date + timedelta(
            hours=random.randint(0, 7 * 24),
            minutes=random.randint(0, 59),
        )
        customer = random.choice(NAMES)
        status = random.choice(ORDER_STATUS)
        total_amount = round(random.uniform(100, 15000), 2)

        # 随机注入一些异常数据（约5%）
        if random.random() < 0.05:
            if random.random() < 0.5:
                status = "unknown_status"  # 无效状态
            else:
                total_amount = -random.uniform(100, 500)  # 负数金额

        orders.append({
            "order_id": order_id,
            "platform": platform,
            "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_name": customer,
            "total_amount": total_amount,
            "status": status,
        })

    # 注入一个重复订单
    if len(orders) > 1:
        orders.append(orders[0].copy())

    return pd.DataFrame(orders)


def generate_inventory() -> pd.DataFrame:
    """生成库存数据"""
    inventory = []
    for sku_id, name, cat, price, cost in PRODUCTS:
        system_qty = random.randint(50, 500)
        warehouse_qty = system_qty + random.randint(-20, 20)  # 多数一致，部分有差异

        # 随机注入一些差异较大的数据（约20%）
        if random.random() < 0.2:
            warehouse_qty = system_qty + random.randint(15, 100)

        # 随机注入负数库存（约3%）
        if random.random() < 0.03:
            warehouse_qty = -random.randint(1, 10)

        inventory.append({
            "sku_id": sku_id,
            "product_name": name,
            "system_qty": system_qty,
            "warehouse_qty": warehouse_qty,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    return pd.DataFrame(inventory)


def generate_products() -> pd.DataFrame:
    """生成商品数据"""
    products = []
    for sku_id, name, cat, price, cost in PRODUCTS:
        status = random.choice(PRODUCT_STATUS)

        # 随机注入异常数据（约5%）
        if random.random() < 0.05:
            if random.random() < 0.5:
                price = -random.uniform(100, 500)  # 负数价格
            else:
                status = "unknown"  # 无效状态

        products.append({
            "sku_id": sku_id,
            "product_name": name,
            "category": cat,
            "price": price,
            "cost": cost,
            "status": status,
        })

    # 注入一个重复SKU
    if products:
        products.append(products[0].copy())

    return pd.DataFrame(products)


def main():
    """生成所有示例数据"""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 生成订单数据
    orders = generate_orders(200)
    orders.to_csv(config.ORDERS_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ 订单数据: {config.ORDERS_FILE} ({len(orders)} 条)")

    # 生成库存数据
    inventory = generate_inventory()
    inventory.to_csv(config.INVENTORY_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ 库存数据: {config.INVENTORY_FILE} ({len(inventory)} 条)")

    # 生成商品数据
    products = generate_products()
    products.to_csv(config.PRODUCTS_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ 商品数据: {config.PRODUCTS_FILE} ({len(products)} 条)")

    print("\n示例数据生成完成！")


if __name__ == "__main__":
    main()
