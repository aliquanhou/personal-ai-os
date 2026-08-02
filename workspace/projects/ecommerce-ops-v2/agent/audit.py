"""审计日志模块：所有操作全程留痕（信任兜底）。"""

from typing import Optional

from db import db


def log(action: str, status: str, task_id: Optional[int] = None,
        run_id: Optional[int] = None, detail: str = "") -> None:
    """写入一条审计记录。"""
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO audit_logs (action, task_id, run_id, status, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (action, task_id, run_id, status, detail),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent(limit: int = 20) -> list:
    """获取最近审计记录。"""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
