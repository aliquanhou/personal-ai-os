"""任务注册表：任务类型可插拔注册。

新增任务只需实现 run(records, params) -> dict 接口并注册。
"""

from typing import Callable, Dict

from db import models
from agent.tasks import order_check, product_clean, stock_reconcile

# 任务类型 -> 执行函数
_TASK_HANDLERS: Dict[str, Callable] = {
    models.TASK_TYPE_ORDER_CHECK: order_check.run,
    models.TASK_TYPE_STOCK_RECONCILE: stock_reconcile.run,
    models.TASK_TYPE_PRODUCT_CLEAN: product_clean.run,
}


def register(task_type: str, handler: Callable) -> None:
    """注册一个新任务类型。"""
    _TASK_HANDLERS[task_type] = handler


def get_handler(task_type: str) -> Callable:
    """获取任务执行函数。"""
    if task_type not in _TASK_HANDLERS:
        raise ValueError(f"未知任务类型: {task_type}")
    return _TASK_HANDLERS[task_type]


def list_task_types() -> list:
    """列出所有已注册任务类型。"""
    return [
        {"type": t, "name": models.TASK_TYPES.get(t, t)}
        for t in _TASK_HANDLERS
    ]
