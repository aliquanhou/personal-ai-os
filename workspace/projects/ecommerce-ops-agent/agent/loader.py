"""电商运营数字员工 - 数据接入层

负责加载和清洗各类数据源（CSV、Excel等）。
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from agent import config

logger = logging.getLogger(__name__)


class DataLoader:
    """数据接入层 - 负责加载和清洗各类数据"""

    REQUIRED_ORDER_COLS = ["order_id", "platform", "order_date", "customer_name", "total_amount", "status"]
    REQUIRED_INVENTORY_COLS = ["sku_id", "product_name", "system_qty", "warehouse_qty", "last_updated"]
    REQUIRED_PRODUCT_COLS = ["sku_id", "product_name", "category", "price", "cost", "status"]

    def __init__(self):
        self._validate_directories()

    def _validate_directories(self):
        """确保数据目录存在"""
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def load_orders(self, path: Optional[str] = None) -> pd.DataFrame:
        """加载订单数据"""
        file_path = Path(path) if path else config.ORDERS_FILE
        if not file_path.exists():
            raise FileNotFoundError(f"订单数据文件不存在: {file_path}")

        df = self._read_csv(file_path)
        self._validate_columns(df, self.REQUIRED_ORDER_COLS, "订单")
        return df

    def load_inventory(self, path: Optional[str] = None) -> pd.DataFrame:
        """加载库存数据"""
        file_path = Path(path) if path else config.INVENTORY_FILE
        if not file_path.exists():
            raise FileNotFoundError(f"库存数据文件不存在: {file_path}")

        df = self._read_csv(file_path)
        self._validate_columns(df, self.REQUIRED_INVENTORY_COLS, "库存")
        return df

    def load_products(self, path: Optional[str] = None) -> pd.DataFrame:
        """加载商品数据"""
        file_path = Path(path) if path else config.PRODUCTS_FILE
        if not file_path.exists():
            raise FileNotFoundError(f"商品数据文件不存在: {file_path}")

        df = self._read_csv(file_path)
        self._validate_columns(df, self.REQUIRED_PRODUCT_COLS, "商品")
        return df

    def _read_csv(self, path: Path) -> pd.DataFrame:
        """读取CSV文件"""
        try:
            df = pd.read_csv(path)
            logger.info("成功读取 %s: %d 行", path.name, len(df))
            return df
        except Exception as e:
            logger.error("读取文件失败 %s: %s", path, e)
            raise ValueError(f"无法读取CSV文件 {path}: {e}")

    def _validate_columns(self, df: pd.DataFrame, required: list, data_type: str):
        """校验必需列"""
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{data_type}数据缺少必需列: {missing}")
