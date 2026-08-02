"""电商运营数字员工 - 单元测试"""

import sys
import os
from pathlib import Path

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from agent.models import Anomaly, Order, InventoryItem, Product, AuditEntry, RunHistory
from agent.rules import RuleEngine
from agent.loader import DataLoader


# ============================================================
# 数据模型测试
# ============================================================

class TestModels:
    def test_order_model(self):
        order = Order(
            order_id="ORD001",
            platform="taobao",
            order_date="2026-08-03",
            customer_name="张三",
            total_amount=100.5,
            status="paid",
        )
        d = order.to_dict()
        assert d["order_id"] == "ORD001"
        assert d["platform"] == "taobao"
        assert d["total_amount"] == 100.5

    def test_inventory_item_diff(self):
        item = InventoryItem(
            sku_id="SKU001",
            product_name="测试商品",
            system_qty=100,
            warehouse_qty=95,
            last_updated="2026-08-03",
        )
        assert item.diff == 5
        assert item.has_discrepancy

    def test_inventory_item_no_diff(self):
        item = InventoryItem(
            sku_id="SKU002",
            product_name="测试商品2",
            system_qty=80,
            warehouse_qty=80,
            last_updated="2026-08-03",
        )
        assert item.diff == 0
        assert not item.has_discrepancy

    def test_product_profit_margin(self):
        product = Product(
            sku_id="SKU001",
            product_name="测试商品",
            category="手机",
            price=100,
            cost=60,
            status="on_sale",
        )
        assert product.profit_margin == 40.0

    def test_anomaly_model(self):
        anomaly = Anomaly(
            type="order_mismatch",
            level="critical",
            source="order",
            reference_id="ORD001",
            detail="订单金额不一致",
        )
        d = anomaly.to_dict()
        assert d["type"] == "order_mismatch"
        assert d["level"] == "critical"
        assert d["reference_id"] == "ORD001"

    def test_audit_entry_model(self):
        entry = AuditEntry(
            action="validate",
            task_type="order_check",
            status="success",
        )
        d = entry.to_dict()
        assert d["action"] == "validate"
        assert d["status"] == "success"

    def test_run_history_model(self):
        history = RunHistory(
            data_date="2026-08-03",
            status="success",
            total_orders=100,
            total_amount=5000.0,
            anomaly_count=2,
        )
        d = history.to_dict()
        assert d["data_date"] == "2026-08-03"
        assert d["total_orders"] == 100
        assert d["total_amount"] == 5000.0


# ============================================================
# 规则引擎测试
# ============================================================

class TestRuleEngine:
    def setup_method(self):
        self.engine = RuleEngine()

    def test_check_orders_valid(self):
        """测试正常订单数据"""
        df = pd.DataFrame({
            "order_id": ["ORD001", "ORD002"],
            "platform": ["taobao", "jd"],
            "order_date": ["2026-08-03 10:00:00", "2026-08-03 11:00:00"],
            "customer_name": ["张三", "李四"],
            "total_amount": [100.5, 200.0],
            "status": ["paid", "completed"],
        })
        anomalies = self.engine.check_orders(df)
        assert len(anomalies) == 0

    def test_check_orders_duplicate(self):
        """测试重复订单检测"""
        df = pd.DataFrame({
            "order_id": ["ORD001", "ORD001"],
            "platform": ["taobao", "taobao"],
            "order_date": ["2026-08-03", "2026-08-03"],
            "customer_name": ["张三", "张三"],
            "total_amount": [100.0, 100.0],
            "status": ["paid", "paid"],
        })
        anomalies = self.engine.check_orders(df)
        dup_types = [a.type for a in anomalies]
        assert "duplicate_order" in dup_types

    def test_check_orders_invalid_platform(self):
        """测试无效平台检测"""
        df = pd.DataFrame({
            "order_id": ["ORD001"],
            "platform": ["unknown_platform"],
            "order_date": ["2026-08-03"],
            "customer_name": ["张三"],
            "total_amount": [100.0],
            "status": ["paid"],
        })
        anomalies = self.engine.check_orders(df)
        types = [a.type for a in anomalies]
        assert "invalid_platform" in types

    def test_check_orders_invalid_status(self):
        """测试无效状态检测"""
        df = pd.DataFrame({
            "order_id": ["ORD001"],
            "platform": ["taobao"],
            "order_date": ["2026-08-03"],
            "customer_name": ["张三"],
            "total_amount": [100.0],
            "status": ["unknown"],
        })
        anomalies = self.engine.check_orders(df)
        types = [a.type for a in anomalies]
        assert "invalid_status" in types

    def test_check_orders_negative_amount(self):
        """测试负数金额检测"""
        df = pd.DataFrame({
            "order_id": ["ORD001"],
            "platform": ["taobao"],
            "order_date": ["2026-08-03"],
            "customer_name": ["张三"],
            "total_amount": [-100.0],
            "status": ["paid"],
        })
        anomalies = self.engine.check_orders(df)
        types = [a.type for a in anomalies]
        assert "invalid_amount" in types

    def test_check_inventory_discrepancy(self):
        """测试库存差异检测"""
        df = pd.DataFrame({
            "sku_id": ["SKU001"],
            "product_name": ["测试商品"],
            "system_qty": [100],
            "warehouse_qty": [95],
            "last_updated": ["2026-08-03"],
        })
        anomalies = self.engine.check_inventory(df)
        types = [a.type for a in anomalies]
        assert "inventory_diff" in types

    def test_check_inventory_negative(self):
        """测试负数库存检测"""
        df = pd.DataFrame({
            "sku_id": ["SKU001"],
            "product_name": ["测试商品"],
            "system_qty": [-5],
            "warehouse_qty": [10],
            "last_updated": ["2026-08-03"],
        })
        anomalies = self.engine.check_inventory(df)
        types = [a.type for a in anomalies]
        assert "negative_qty" in types

    def test_clean_products(self):
        """测试商品资料清洗"""
        df = pd.DataFrame({
            "sku_id": [" sku001 ", "SKU002"],
            "product_name": ["  测试商品1  ", "测试商品2"],
            "category": ["手机", "电脑"],
            "price": [100.0, 200.0],
            "cost": [60.0, 120.0],
            "status": ["on_sale", "on_sale"],
        })
        cleaned = self.engine.clean_products(df)
        # SKU应被标准化（去空格、转大写）
        assert cleaned.iloc[0]["sku_id"] == "SKU001"
        # 商品名应去除首尾空格
        assert cleaned.iloc[0]["product_name"] == "测试商品1"
        # 毛利率应正确计算
        assert cleaned.iloc[0]["profit_margin"] == 40.0

    def test_clean_products_invalid_price(self):
        """测试无效价格检测"""
        df = pd.DataFrame({
            "sku_id": ["SKU001"],
            "product_name": ["测试商品"],
            "category": ["手机"],
            "price": [-100.0],
            "cost": [60.0],
            "status": ["on_sale"],
        })
        cleaned = self.engine.clean_products(df)
        anomalies = self.engine.get_all_anomalies()
        types = [a.type for a in anomalies]
        assert "price_error" in types


# ============================================================
# 数据加载器测试
# ============================================================

class TestDataLoader:
    def setup_method(self):
        self.loader = DataLoader()

    def test_load_orders_missing_file(self):
        """测试缺失文件时抛出异常"""
        with pytest.raises(FileNotFoundError):
            self.loader.load_orders("nonexistent_file.csv")

    def test_load_orders_invalid_columns(self, tmp_path):
        """测试缺少必需列时抛出异常"""
        import pandas as pd
        df = pd.DataFrame({"wrong_col": [1, 2, 3]})
        file_path = tmp_path / "bad_orders.csv"
        df.to_csv(file_path, index=False)
        with pytest.raises(ValueError):
            self.loader.load_orders(str(file_path))
