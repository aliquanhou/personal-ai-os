"""电商运营数字员工 - 数据模型

定义所有数据模型，包括：
- 订单核对模型
- 库存对账模型
- 商品资料模型
- 审计日志模型
- 历史记录模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ============================================================
# 业务数据模型
# ============================================================

@dataclass
class Order:
    """订单数据模型"""
    order_id: str
    platform: str  # taobao / jd / pdd / douyin
    order_date: str
    customer_name: str
    total_amount: float
    status: str  # pending / paid / shipped / completed / cancelled
    items: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "platform": self.platform,
            "order_date": self.order_date,
            "customer_name": self.customer_name,
            "total_amount": self.total_amount,
            "status": self.status,
            "items": self.items,
        }


@dataclass
class InventoryItem:
    """库存数据模型"""
    sku_id: str
    product_name: str
    system_qty: int  # 系统库存
    warehouse_qty: int  # 仓库实际库存
    last_updated: str

    @property
    def diff(self) -> int:
        """库存差异"""
        return self.system_qty - self.warehouse_qty

    @property
    def has_discrepancy(self) -> bool:
        """是否存在差异"""
        return self.system_qty != self.warehouse_qty


@dataclass
class Product:
    """商品资料模型"""
    sku_id: str
    product_name: str
    category: str
    price: float
    cost: float
    status: str  # on_sale / off_sale / pending

    @property
    def profit_margin(self) -> float:
        """毛利率"""
        if self.price <= 0:
            return 0.0
        return round((self.price - self.cost) / self.price * 100, 2)


# ============================================================
# 规则引擎结果模型
# ============================================================

@dataclass
class Anomaly:
    """异常记录"""
    type: str  # order_mismatch / inventory_diff / price_error / missing_field
    level: str  # critical / warning / info
    source: str  # 来源（订单/库存/商品）
    reference_id: str  # 关联ID（订单号/SKU等）
    detail: str  # 异常详情
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "level": self.level,
            "source": self.source,
            "reference_id": self.reference_id,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class TaskResult:
    """单个任务执行结果"""
    task_name: str
    status: str  # success / failed / skipped
    records_processed: int = 0
    anomalies: List[Anomaly] = field(default_factory=list)
    output_path: Optional[str] = None
    error: Optional[str] = None
    duration_sec: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_name": self.task_name,
            "status": self.status,
            "records_processed": self.records_processed,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "output_path": self.output_path,
            "error": self.error,
            "duration_sec": round(self.duration_sec, 2),
        }


# ============================================================
# 审计日志模型
# ============================================================

@dataclass
class AuditEntry:
    """审计日志条目"""
    action: str  # load_data / validate / generate_report / save
    task_type: str  # order_check / inventory_check / product_clean / daily_report
    status: str  # started / success / failed
    detail: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "task_type": self.task_type,
            "status": self.status,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


# ============================================================
# 历史记录模型
# ============================================================

@dataclass
class RunHistory:
    """一次完整执行的记录"""
    data_date: str  # 数据日期
    status: str  # success / failed
    total_orders: int = 0
    total_amount: float = 0.0
    anomaly_count: int = 0
    report_path: Optional[str] = None
    attempts: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        return {
            "data_date": self.data_date,
            "status": self.status,
            "total_orders": self.total_orders,
            "total_amount": self.total_amount,
            "anomaly_count": self.anomaly_count,
            "report_path": self.report_path,
            "attempts": self.attempts,
            "timestamp": self.timestamp,
        }


# ============================================================
# 数据库表结构 (SQLite)
# ============================================================

SCHEMA_SQL = """
-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT
);

-- 历史记录表
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
);

-- 异常记录表
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_date TEXT NOT NULL,
    type TEXT NOT NULL,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    reference_id TEXT,
    detail TEXT,
    timestamp TEXT NOT NULL
);
"""
