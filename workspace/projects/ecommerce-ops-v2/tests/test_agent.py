"""电商运营数字员工 v2 — 测试套件。

覆盖：数据库模型、三个核心任务、执行引擎、人工复核。
"""

import json
import os
import sys
import tempfile

import pytest

# 确保可导入项目模块
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from db import db, models
from agent import registry, rules, runner


# ---------- Fixtures ----------

@pytest.fixture(scope="function")
def tmp_db(tmp_path):
    """使用临时数据库，隔离测试数据。"""
    db_path = str(tmp_path / "test.db")
    db.init_db(db_path)
    # 临时覆盖 DB 连接路径
    old_conn = db.get_connection
    def _conn(db_path_=None):
        return old_conn(db_path_ or db_path)
    db.get_connection = _conn
    yield db_path
    db.get_connection = old_conn


@pytest.fixture(scope="function")
def agent(tmp_db):
    """创建执行引擎实例。"""
    return runner.EcommerceOpsAgent()


# ---------- 数据库模型 ----------

class TestDatabase:
    def test_init_db_creates_tables(self, tmp_db):
        conn = db.get_connection()
        try:
            tables = [r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        finally:
            conn.close()
        for t in ["tasks", "task_runs", "audit_logs", "reviews"]:
            assert t in tables

    def test_task_crud(self, agent):
        tid = agent.create_task("订单核对", models.TASK_TYPE_ORDER_CHECK, {}, "daily:09:00")
        tasks = agent.list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == tid
        assert tasks[0]["task_type"] == models.TASK_TYPE_ORDER_CHECK


# ---------- 规则引擎 ----------

class TestRules:
    def test_order_check_duplicate(self):
        row = {"order_id": "ORD1", "platform": "taobao", "status": "paid",
               "amount": 100, "_duplicate": "1"}
        anomalies = rules.check_order(row, {})
        assert any(a.type == "duplicate_order" for a in anomalies)

    def test_order_check_negative_amount(self):
        row = {"order_id": "ORD2", "platform": "taobao", "status": "paid",
               "amount": -50, "_duplicate": "0"}
        anomalies = rules.check_order(row, {})
        assert any(a.type == "negative_amount" and a.level == "critical"
                   for a in anomalies)

    def test_stock_diff(self):
        anomalies = rules.check_stock(100, 80, "SKU1", tolerance=0)
        assert any(a.type == "stock_diff" and a.meta["diff"] == 20
                   for a in anomalies)

    def test_stock_negative(self):
        anomalies = rules.check_stock(-5, 0, "SKU2")
        assert any(a.type == "negative_stock" and a.level == "critical"
                   for a in anomalies)

    def test_product_clean_rules(self):
        row = {"sku": "PRD1", "name": "", "cost": -10, "price": 100}
        anomalies = rules.check_product(row, {})
        types = {a.type for a in anomalies}
        assert {"missing_name", "negative_cost"} <= types


# ---------- 具体任务 ----------

class TestTasks:
    def test_order_check_task(self):
        orders = [
            {"order_id": "A", "platform": "taobao", "status": "paid", "amount": 100},
            {"order_id": "A", "platform": "taobao", "status": "paid", "amount": 100},  # 重复
            {"order_id": "B", "platform": "unknown", "status": "paid", "amount": 50},  # 无效平台
        ]
        result = registry.get_handler(models.TASK_TYPE_ORDER_CHECK)(orders, {})
        assert result["stats"]["total_orders"] == 3
        assert result["stats"]["duplicates"] == 1
        assert result["stats"]["anomaly_count"] >= 2

    def test_stock_reconcile_task(self):
        stocks = [
            {"sku": "S1", "system_qty": 10, "warehouse_qty": 10},
            {"sku": "S2", "system_qty": 10, "warehouse_qty": 5},   # 差异 5
            {"sku": "S3", "system_qty": -1, "warehouse_qty": 0},   # 负数
        ]
        result = registry.get_handler(models.TASK_TYPE_STOCK_RECONCILE)(stocks, {"tolerance": 0})
        assert result["stats"]["total_skus"] == 3
        assert result["stats"]["diff_count"] == 1
        assert result["stats"]["negative_count"] == 1

    def test_product_clean_task(self):
        products = [
            {"sku": "P1", "name": "  无线  耳机  ", "cost": 50, "price": 100},
            {"sku": "P2", "name": "", "cost": 30, "price": 80},
        ]
        result = registry.get_handler(models.TASK_TYPE_PRODUCT_CLEAN)(products, {})
        # 名称标准化
        assert result["cleaned"][0]["name"] == "无线 耳机"
        # 毛利率计算
        assert result["cleaned"][0]["margin_pct"] == 50.0
        # 检测空名称
        assert result["stats"]["anomaly_count"] == 1


# ---------- 执行引擎 ----------

class TestRunner:
    def test_run_task_success(self, agent, tmp_path):
        # 准备数据文件
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "orders.csv").write_text(
            "order_id,platform,status,amount\n"
            "ORD1,taobao,paid,100\n"
            "ORD2,jd,paid,200\n",
            encoding="utf-8",
        )
        # 指向临时数据目录
        old_data_dir = runner.DATA_DIR
        runner.DATA_DIR = str(data_dir)

        tid = agent.create_task("订单核对", models.TASK_TYPE_ORDER_CHECK, {})
        result = agent.run_task(tid)
        assert result["status"] == "success"
        assert result["stats"]["total_orders"] == 2
        assert result["run_id"] > 0

        runner.DATA_DIR = old_data_dir

    def test_history_records(self, agent, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "orders.csv").write_text(
            "order_id,platform,status,amount\nORD1,taobao,paid,100\n",
            encoding="utf-8",
        )
        old_data_dir = runner.DATA_DIR
        runner.DATA_DIR = str(data_dir)

        tid = agent.create_task("订单核对", models.TASK_TYPE_ORDER_CHECK, {})
        agent.run_task(tid)
        history = agent.history()
        assert len(history) == 1
        assert history[0]["task_id"] == tid

        runner.DATA_DIR = old_data_dir


# ---------- 人工复核 ----------

class TestReview:
    def test_review_flow(self, agent, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "orders.csv").write_text(
            "order_id,platform,status,amount\nORD1,taobao,paid,100\n",
            encoding="utf-8",
        )
        old_data_dir = runner.DATA_DIR
        runner.DATA_DIR = str(data_dir)

        tid = agent.create_task("订单核对", models.TASK_TYPE_ORDER_CHECK, {},
                                review_required=1)
        result = agent.run_task(tid)
        rid = agent.review_run(result["run_id"], tid,
                               models.DECISION_APPROVED, "数据无误")
        assert rid > 0

        # 复核记录已落库
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM reviews WHERE id=?", (rid,)).fetchone()
            assert row["decision"] == models.DECISION_APPROVED
            assert row["comment"] == "数据无误"
        finally:
            conn.close()

        runner.DATA_DIR = old_data_dir

    def test_invalid_review_decision(self, agent):
        with pytest.raises(ValueError):
            agent.review_run(1, 1, "invalid_decision")
