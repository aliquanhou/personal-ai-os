"""销售数据分析数字员工 - Excel 读取模块"""
import logging
from pathlib import Path

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


class ExcelReadError(Exception):
    """Excel 读取失败"""


def find_input_files(pattern: str = None) -> list[Path]:
    """查找待分析的 Excel 文件"""
    pattern = pattern or config.INPUT_PATTERN
    files = sorted(config.INPUT_DIR.glob(pattern))
    return files


def read_excel(path: Path) -> pd.DataFrame:
    """读取 Excel 文件，返回标准化 DataFrame"""
    if not path.exists():
        raise ExcelReadError(f"文件不存在: {path}")

    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:  # noqa: BLE001
        raise ExcelReadError(f"读取 Excel 失败 {path.name}: {e}") from e

    if df is None or df.empty:
        raise ExcelReadError(f"Excel 文件为空: {path.name}")

    df = _normalize_columns(df)
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """标准化列名，去掉空白并统一命名"""
    df.columns = [str(c).strip() for c in df.columns]

    # 常见别名映射
    alias_map = {
        "订单编号": config.COL_ORDER_ID,
        "订单id": config.COL_ORDER_ID,
        "下单日期": config.COL_DATE,
        "销售日期": config.COL_DATE,
        "客户名称": config.COL_CUSTOMER,
        "客户名": config.COL_CUSTOMER,
        "商品名称": config.COL_PRODUCT,
        "产品": config.COL_PRODUCT,
        "销量": config.COL_QTY,
        "数量(件)": config.COL_QTY,
        "成交金额": config.COL_AMOUNT,
        "销售额": config.COL_AMOUNT,
        "金额(元)": config.COL_AMOUNT,
        "订单状态": config.COL_STATUS,
        "状态(已支付/已取消)": config.COL_STATUS,
    }
    df = df.rename(columns=alias_map)
    return df


def validate_columns(df: pd.DataFrame) -> list[str]:
    """校验必需列，返回缺失列名列表"""
    required = [config.COL_AMOUNT, config.COL_QTY]
    missing = [c for c in required if c not in df.columns]
    return missing
