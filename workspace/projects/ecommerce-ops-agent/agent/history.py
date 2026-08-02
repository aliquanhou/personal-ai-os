"""电商运营数字员工 - 历史记录管理"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agent import config
from agent.models import RunHistory

logger = logging.getLogger(__name__)


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_date TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        total_orders INTEGER DEFAULT 0,
                        total_amount REAL DEFAULT 0,
                        anomaly_count INTEGER DEFAULT 0,
                        report_path TEXT,
                        attempts INTEGER DEFAULT 1
                    )
                """)
                conn.commit()
            logger.debug("历史记录表初始化完成")
        except Exception as e:
            logger.error("历史记录表初始化失败: %s", e)
            raise

    def save_run(self, record: RunHistory):
        """保存一次执行记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT INTO history
                       (data_date, timestamp, status, total_orders, total_amount, anomaly_count, report_path, attempts)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.data_date,
                        record.timestamp,
                        record.status,
                        record.total_orders,
                        record.total_amount,
                        record.anomaly_count,
                        record.report_path,
                        record.attempts,
                    ),
                )
                conn.commit()
            logger.debug("历史记录已保存: %s", record.data_date)
        except Exception as e:
            logger.error("保存历史记录失败: %s", e)

    def load_all(self, limit: int = 50) -> List[dict]:
        """加载所有历史记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error("加载历史记录失败: %s", e)
            return []

    def get_latest(self) -> Optional[dict]:
        """获取最近一次执行记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM history ORDER BY id DESC LIMIT 1"
                ).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error("获取最近记录失败: %s", e)
            return None

    def get_latest_summary(self) -> str:
        """获取最近一次执行的摘要"""
        latest = self.get_latest()
        if not latest:
            return "暂无历史记录"
        status_icon = "✅" if latest["status"] == "success" else "❌"
        return (
            f"{status_icon} {latest['data_date']} | "
            f"订单 {latest['total_orders']} | 销售额 ¥{latest['total_amount']:,.2f} | "
            f"异常 {latest['anomaly_count']} | 尝试 {latest['attempts']} 次"
        )
