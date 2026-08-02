"""销售数据分析数字员工 - 历史记录模块"""
import json
import logging
from datetime import datetime
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)


def save_history(record: dict) -> str:
    """保存一条执行历史记录到 JSON 文件，返回文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"history_{timestamp}.json"
    path = config.HISTORY_DIR / filename
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("历史记录已保存: %s", path)
    return str(path)


def load_all_history() -> list[dict]:
    """加载全部历史记录（按时间倒序）"""
    records = []
    for path in sorted(config.HISTORY_DIR.glob("history_*.json"), reverse=True):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            logger.warning("读取历史记录失败 %s: %s", path.name, e)
    return records


def get_latest_summary() -> dict | None:
    """获取最近一次执行的关键指标"""
    records = load_all_history()
    if not records:
        return None
    latest = records[0]
    return {
        "date": latest.get("data_date"),
        "total_amount": latest.get("total_amount"),
        "total_orders": latest.get("total_orders"),
        "anomaly_count": latest.get("anomaly_count"),
    }
