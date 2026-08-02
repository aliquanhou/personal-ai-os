"""数据接入层：从 CSV 读取原始数据。

MVP 从本地 CSV 读取。预留 API 数据源接入扩展点。
"""

import csv
import os
from typing import List


def _read_csv(path: str) -> List[dict]:
    """读取 CSV 文件为 dict 列表。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {path}")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def load_orders(data_dir: str) -> List[dict]:
    """加载订单数据。"""
    return _read_csv(os.path.join(data_dir, "orders.csv"))


def load_stocks(data_dir: str) -> List[dict]:
    """加载库存数据。"""
    return _read_csv(os.path.join(data_dir, "stocks.csv"))


def load_products(data_dir: str) -> List[dict]:
    """加载商品数据。"""
    return _read_csv(os.path.join(data_dir, "products.csv"))


# 任务类型 -> 数据加载函数映射
LOADERS = {
    "order_check": load_orders,
    "stock_reconcile": load_stocks,
    "product_clean": load_products,
}
