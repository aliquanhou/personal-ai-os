"""电商运营数字员工 - 审计追踪

记录所有操作的审计日志，确保可追溯性。
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agent import config
from agent.models import AuditEntry

logger = logging.getLogger(__name__)


class AuditLog:
    """审计日志管理器"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        detail TEXT
                    )
                """)
                conn.commit()
            logger.debug("审计日志表初始化完成")
        except Exception as e:
            logger.error("审计日志表初始化失败: %s", e)
            raise

    def log(self, action: str, task_type: str, status: str, detail: str = ""):
        """记录一条审计日志"""
        entry = AuditEntry(
            action=action,
            task_type=task_type,
            status=status,
            detail=detail,
        )
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO audit_log (timestamp, action, task_type, status, detail) VALUES (?, ?, ?, ?, ?)",
                    (entry.timestamp, entry.action, entry.task_type, entry.status, entry.detail),
                )
                conn.commit()
            logger.debug("审计日志已记录: %s/%s/%s", entry.action, entry.task_type, entry.status)
        except Exception as e:
            logger.error("审计日志写入失败: %s", e)

    def get_recent(self, limit: int = 20) -> List[dict]:
        """获取最近的审计日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error("读取审计日志失败: %s", e)
            return []

    def get_summary(self) -> str:
        """获取审计摘要"""
        entries = self.get_recent(10)
        if not entries:
            return "暂无审计记录"
        lines = []
        for e in entries:
            icon = "✅" if e["status"] == "success" else ("❌" if e["status"] == "failed" else "🔄")
            lines.append(f"{icon} [{e['timestamp']}] {e['action']} ({e['task_type']}) - {e['status']}")
        return "\n".join(lines)
