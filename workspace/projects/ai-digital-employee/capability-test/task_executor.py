"""
AI数字员工 — 任务执行器核心逻辑（coding_agent 测试产出）

功能：可重试、带超时、可记录执行日志的简单任务执行器。

设计要点：
- retry：失败自动重试，指数退避
- timeout：单次执行超时保护
- 日志：每次执行留痕（时间戳、状态、错误、耗时）
- 纯标准库实现，无外部依赖
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger("digital_employee")


@dataclass
class TaskResult:
    """单次任务执行结果（留痕用）"""
    task_id: str
    status: str          # success / failed / timeout
    started_at: str
    finished_at: str
    attempts: int = 0
    error: Optional[str] = None
    duration_ms: float = 0.0
    output: Any = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "attempts": self.attempts,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "output": str(self.output)[:500],
        }


class TaskExecutor:
    """可重试、带超时、留痕的任务执行器"""

    def __init__(self, max_retries: int = 3, timeout: float = 30.0,
                 backoff_base: float = 1.0):
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_base = backoff_base
        self.logs: list[dict] = []

    def _now(self) -> str:
        return datetime.now().isoformat()

    def execute(self, task_id: str, fn: Callable[[], Any]) -> TaskResult:
        """执行任务，含重试与超时保护"""
        started = time.time()
        result = TaskResult(
            task_id=task_id,
            status="failed",
            started_at=self._now(),
            finished_at=self._now(),
        )

        for attempt in range(1, self.max_retries + 1):
            result.attempts = attempt
            try:
                # 用信号实现超时（仅 Unix 生效；Windows 下用简单时间窗）
                output = self._run_with_timeout(fn)
                result.status = "success"
                result.output = output
                result.finished_at = self._now()
                result.duration_ms = (time.time() - started) * 1000
                break
            except TimeoutError as e:
                result.error = f"timeout after {self.timeout}s"
                logger.warning(f"[{task_id}] attempt {attempt} timeout")
            except Exception as e:  # noqa: BLE001
                result.error = str(e)
                logger.warning(f"[{task_id}] attempt {attempt} failed: {e}")

            # 退避等待后重试
            if attempt < self.max_retries:
                time.sleep(self.backoff_base * (2 ** (attempt - 1)))

        result.finished_at = self._now()
        result.duration_ms = (time.time() - started) * 1000
        self.logs.append(result.to_dict())
        return result

    def _run_with_timeout(self, fn: Callable[[], Any]) -> Any:
        """简单时间窗超时实现（跨平台）"""
        start = time.time()
        # 这里用线程+join实现真正的超时（Python 标准库）
        import threading

        box: dict = {"output": None, "error": None}

        def worker():
            try:
                box["output"] = fn()
            except Exception as e:  # noqa: BLE001
                box["error"] = e

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(self.timeout)
        if t.is_alive():
            raise TimeoutError("task timeout")
        if box["error"]:
            raise box["error"]
        return box["output"]

    def get_logs(self) -> list[dict]:
        """返回全部执行留痕"""
        return self.logs


# ---------- 自测 ----------
if __name__ == "__main__":
    executor = TaskExecutor(max_retries=3, timeout=2.0)

    # 测试1：正常任务
    r1 = executor.execute("task-ok", lambda: "数据已清洗完成")
    print("正常任务:", r1.status, "| 输出:", r1.output)

    # 测试2：前2次失败第3次成功
    attempts = {"n": 0}
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("临时错误")
        return "成功"

    r2 = executor.execute("task-flaky", flaky)
    print(f"重试任务: {r2.status} | 尝试次数: {r2.attempts} | 输出: {r2.output}")

    # 测试3：超时任务
    r3 = executor.execute("task-timeout", lambda: time.sleep(5))
    print(f"超时任务: {r3.status} | 错误: {r3.error}")

    print("\n--- 执行留痕 ---")
    for log in executor.get_logs():
        print(log)
