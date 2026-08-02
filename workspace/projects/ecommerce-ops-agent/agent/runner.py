"""电商运营数字员工 - 执行引擎

负责编排所有任务，管理执行流程：
1. 加载数据
2. 执行规则校验
3. 生成报表
4. 记录审计日志
5. 保存历史记录
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from agent import config
from agent.audit import AuditLog
from agent.history import HistoryManager
from agent.loader import DataLoader
from agent.models import Anomaly, RunHistory
from agent.reports import ReportGenerator
from agent.rules import RuleEngine

logger = logging.getLogger(__name__)


class EcommerceOpsAgent:
    """电商运营数字员工 - 主执行引擎"""

    def __init__(self, max_retries: Optional[int] = None):
        self.max_retries = max_retries or config.MAX_RETRIES
        self.loader = DataLoader()
        self.rules = RuleEngine()
        self.reports = ReportGenerator()
        self.audit = AuditLog()
        self.history = HistoryManager()

    def run(self, data_date: Optional[str] = None) -> dict:
        """执行全部电商运营任务

        Args:
            data_date: 数据日期 YYYY-MM-DD，默认今天

        Returns:
            执行结果摘要
        """
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            attempts += 1
            try:
                return self._execute(data_date=data_date, attempts=attempts)
            except Exception as e:
                last_error = e
                logger.error("第 %d 次执行失败: %s", attempts, e)
                self.audit.log(
                    action="run",
                    task_type="full_pipeline",
                    status="failed",
                    detail=f"第{attempts}次执行失败: {str(e)}",
                )
                if attempts >= self.max_retries:
                    break
                time.sleep(1)  # 等待1秒后重试

        raise RuntimeError(f"执行失败（已重试{attempts}次）: {last_error}")

    def _execute(self, data_date: Optional[str], attempts: int) -> dict:
        """实际执行流程"""
        start_time = time.time()
        report_date = data_date or datetime.now().strftime("%Y-%m-%d")
        all_anomalies: List[Anomaly] = []

        logger.info("=" * 60)
        logger.info("电商运营数字员工开始执行 | 数据日期: %s | 第%d次尝试", report_date, attempts)
        logger.info("=" * 60)

        # ========== 步骤1: 加载数据 ==========
        self.audit.log(action="load_data", task_type="full_pipeline", status="started", detail=f"数据日期: {report_date}")

        try:
            orders_df = self.loader.load_orders()
            inventory_df = self.loader.load_inventory()
            products_df = self.loader.load_products()
            logger.info("✅ 数据加载完成: 订单%d条, 库存%d条, 商品%d条",
                        len(orders_df), len(inventory_df), len(products_df))
            self.audit.log(
                action="load_data", task_type="full_pipeline", status="success",
                detail=f"订单{len(orders_df)}条, 库存{len(inventory_df)}条, 商品{len(products_df)}条",
            )
        except Exception as e:
            self.audit.log(action="load_data", task_type="full_pipeline", status="failed", detail=str(e))
            raise

        # ========== 步骤2: 规则校验 ==========
        self.audit.log(action="validate", task_type="full_pipeline", status="started")

        # 2a. 订单核对
        order_anomalies = self.rules.check_orders(orders_df)
        all_anomalies.extend(order_anomalies)
        logger.info("✅ 订单核对完成: %d 条异常", len(order_anomalies))

        # 2b. 库存对账
        inventory_anomalies = self.rules.check_inventory(inventory_df)
        all_anomalies.extend(inventory_anomalies)
        logger.info("✅ 库存对账完成: %d 条异常", len(inventory_anomalies))

        # 2c. 商品资料清洗
        cleaned_products = self.rules.clean_products(products_df)
        product_anomalies = self.rules.get_all_anomalies()
        all_anomalies.extend(product_anomalies)
        logger.info("✅ 商品资料清洗完成: %d 条异常", len(product_anomalies))

        self.audit.log(
            action="validate", task_type="full_pipeline", status="success",
            detail=f"订单异常{len(order_anomalies)}条, 库存异常{len(inventory_anomalies)}条, 商品异常{len(product_anomalies)}条",
        )

        # ========== 步骤3: 生成报表 ==========
        self.audit.log(action="generate_report", task_type="full_pipeline", status="started")

        try:
            report_path = self.reports.generate_daily_report(
                orders_df=orders_df,
                inventory_df=inventory_df,
                products_df=cleaned_products,
                anomalies=all_anomalies,
                data_date=report_date,
            )
            anomaly_report_path = self.reports.generate_anomaly_report(all_anomalies, report_date)
            logger.info("✅ 报表生成完成: %s", report_path)
            self.audit.log(
                action="generate_report", task_type="full_pipeline", status="success",
                detail=f"日报: {report_path}",
            )
        except Exception as e:
            self.audit.log(action="generate_report", task_type="full_pipeline", status="failed", detail=str(e))
            raise

        # ========== 步骤4: 保存历史记录 ==========
        total_orders = len(orders_df)
        total_amount = float(orders_df["total_amount"].sum()) if total_orders > 0 else 0.0

        record = RunHistory(
            data_date=report_date,
            status="success",
            total_orders=total_orders,
            total_amount=total_amount,
            anomaly_count=len(all_anomalies),
            report_path=report_path,
            attempts=attempts,
        )
        self.history.save_run(record)

        # ========== 汇总结果 ==========
        duration = time.time() - start_time
        result = {
            "data_date": report_date,
            "status": "success",
            "total_orders": total_orders,
            "total_amount": total_amount,
            "anomalies": all_anomalies,
            "report_path": report_path,
            "anomaly_report_path": anomaly_report_path,
            "attempts": attempts,
            "duration_sec": round(duration, 2),
            "cleaned_products": cleaned_products,
        }

        logger.info("=" * 60)
        logger.info("执行完成 ✅ | 耗时 %.2f秒 | 订单%d笔 | 销售额¥%.2f | 异常%d条",
                    duration, total_orders, total_amount, len(all_anomalies))
        logger.info("=" * 60)

        return result

    def get_history(self, limit: int = 50) -> list:
        """获取历史记录"""
        return self.history.load_all(limit)

    def get_latest_summary(self) -> str:
        """获取最近一次执行摘要"""
        return self.history.get_latest_summary()
