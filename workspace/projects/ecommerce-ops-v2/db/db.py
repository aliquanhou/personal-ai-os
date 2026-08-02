"""SQLite 数据库连接与初始化。"""

import os
import sqlite3
from typing import Optional

from db import models

# 数据库文件路径（相对项目根目录）
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "ecommerce_ops.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """获取数据库连接（自动创建目录）。"""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[str] = None) -> str:
    """初始化数据库表结构，返回数据库路径。"""
    path = db_path or DB_PATH
    conn = get_connection(path)
    try:
        conn.executescript(models.SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
    return path
