"""执行引擎：调度任务、执行、结果落库、审计。"""

import json
import logging
import os
import time
from datetime import datetime

from db import db, models
from agent import audit, loader, registry, report, rules

logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "reports")


class EcommerceOpsAgent:
    """电商运营数字员工执行引擎。"""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    # ---------- 任务配置 ----------

    def create_task(self, name: str, task_type: str, params: dict = None,
                    schedule: str = "", review_required: int = 0) -> int:
        """创建一个任务，返回任务ID。"""
        conn = db.get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO tasks (name, task_type, params, schedule, review_required) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, task_type, json.dumps(params or {}), schedule, review_required),
            )
            conn.commit()
            task_id = cur.lastrowid
            audit.log("create_task", "success", task_id=task_id,
                      detail=f"创建任务 {name} ({task_type})")
            return task_id
        finally:
            conn.close()

    def list_tasks(self) -> list:
        """列出所有任务。"""
        conn = db.get_connection()
        try:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------- 任务执行 ----------

    def run_task(self, task_id: int, data_date: str = None) -> dict:
        """执行单个任务，返回执行结果快照。"""
        conn = db.get_connection()
        try:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise ValueError(f"任务不存在: {task_id}")
            task = dict(row)
        finally:
            conn.close()

        task_type = task["task_type"]
        params = json.loads(task["params"] or "{}")
        data_date = data_date or datetime.now().strftime("%Y-%m-%d")

        handler = registry.get_handler(task_type)
        loader_fn = loader.LOADERS.get(task_type)
        if not loader_fn:
            raise ValueError(f"任务类型缺少数据加载器: {task_type}")

        start = time.time()
        status = models.STATUS_SUCCESS
        anomalies = []
        stats = {}
        error_msg = ""

        # 带重试执行
        for attempt in range(1, self.max_retries + 1):
            try:
                records = loader_fn(DATA_DIR)
                result = handler(records, params)
                anomalies = result.get("anomalies", [])
                stats = result.get("stats", {})
                # AI 分析扩展点（MVP 不启用）
                anomalies = rules.ai_analyze(anomalies, task_type)
                status = models.STATUS_SUCCESS
                break
            except Exception as e:  # noqa: BLE001
                logger.warning("任务 %s 执行失败 (尝试 %d/%d): %s",
                               task_type, attempt, self.max_retries, e)
                error_msg = str(e)
                status = models.STATUS_FAILED
                if attempt == self.max_retries:
                    break

        duration = round(time.time() - start, 2)

        # 生成日报
        report_path = ""
        if status == models.STATUS_SUCCESS:
            try:
                report_path = report.generate_report(
                    task["name"], stats, anomalies, data_date, OUTPUT_DIR
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("日报生成失败: %s", e)

        # 落库
        run_id = self._save_run(task_id, status, data_date, stats, anomalies,
                                report_path, duration, error_msg)
        audit.log("run_task", status, task_id=task_id, run_id=run_id,
                  detail=f"执行 {task['name']}，异常 {len(anomalies)} 条")

        return {
            "run_id": run_id,
            "task_id": task_id,
            "task_name": task["name"],
            "task_type": task_type,
            "status": status,
            "data_date": data_date,
            "stats": stats,
            "anomalies": anomalies,
            "report_path": report_path,
            "duration_sec": duration,
            "error": error_msg,
        }

    def _save_run(self, task_id, status, data_date, stats, anomalies,
                  report_path, duration, error_msg) -> int:
        """保存执行快照，返回 run_id。"""
        conn = db.get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO task_runs "
                "(task_id, status, data_date, total_records, anomaly_count, detail, report_path, duration_sec) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, status, data_date,
                 stats.get("total_records", stats.get("total_orders", stats.get("total_products", 0))),
                 len(anomalies),
                 json.dumps({"stats": stats, "error": error_msg}),
                 report_path, duration),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    # ---------- 人工复核 ----------

    def review_run(self, run_id: int, task_id: int, decision: str,
                   comment: str = "") -> int:
        """对一次执行进行人工复核。"""
        if decision not in (models.DECISION_APPROVED, models.DECISION_MODIFIED,
                            models.DECISION_REJECTED):
            raise ValueError(f"无效复核决策: {decision}")
        conn = db.get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO reviews (run_id, task_id, decision, comment) "
                "VALUES (?, ?, ?, ?)",
                (run_id, task_id, decision, comment),
            )
            conn.commit()
            review_id = cur.lastrowid
            audit.log("review_run", "success", task_id=task_id, run_id=run_id,
                      detail=f"复核 {decision}: {comment}")
            return review_id
        finally:
            conn.close()

    # ---------- 历史查询 ----------

    def history(self, limit: int = 20) -> list:
        """查看执行历史。"""
        conn = db.get_connection()
        try:
            rows = conn.execute(
                "SELECT r.*, t.name AS task_name FROM task_runs r "
                "JOIN tasks t ON r.task_id = t.id "
                "ORDER BY r.id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
