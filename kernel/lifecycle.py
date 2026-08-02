"""Runtime v1.3 — Task Lifecycle Controller & Error Recovery Manager

The core kernel that gives Runtime (not LLM) control over task execution.

Lifecycle State Machine:
  INIT → PLAN → EXECUTE → VERIFY → COMPLETE / ERROR → RECOVER → FAILED

Error Recovery:
  Each tool gets 2 auto-retries. After that, task stops.
  Same-tool-same-args > 2 → force stop (infinite loop detection).

This is the "operating system" part of the AI OS — LLM proposes, Runtime disposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# LIFECYCLE STATE MACHINE
# ═══════════════════════════════════════════════════════════

class LifecycleStage(StrEnum):
    INIT = "INIT"           # Agent spawned, context built
    PLAN = "PLAN"           # Analyzing goal, extracting tasks
    EXECUTE = "EXECUTE"     # Running tools
    VERIFY = "VERIFY"       # Checking tool results
    ERROR = "ERROR"         # Tool failed
    RECOVER = "RECOVER"     # Attempting recovery
    COMPLETE = "COMPLETE"   # All goals fulfilled
    FAILED = "FAILED"       # Unrecoverable


# Legal transitions
TRANSITIONS: dict[LifecycleStage, list[LifecycleStage]] = {
    LifecycleStage.INIT:     [LifecycleStage.PLAN],
    LifecycleStage.PLAN:     [LifecycleStage.EXECUTE],
    LifecycleStage.EXECUTE:  [LifecycleStage.VERIFY, LifecycleStage.ERROR, LifecycleStage.COMPLETE],
    LifecycleStage.VERIFY:   [LifecycleStage.EXECUTE, LifecycleStage.COMPLETE, LifecycleStage.ERROR],
    LifecycleStage.ERROR:    [LifecycleStage.RECOVER, LifecycleStage.FAILED],
    LifecycleStage.RECOVER:  [LifecycleStage.EXECUTE, LifecycleStage.FAILED, LifecycleStage.COMPLETE],
    LifecycleStage.COMPLETE: [],   # terminal
    LifecycleStage.FAILED:   [],   # terminal
}


# ═══════════════════════════════════════════════════════════
# ERROR RECOVERY MANAGER
# ═══════════════════════════════════════════════════════════

class ErrorCategory(StrEnum):
    ENVIRONMENT = "environment"    # Missing deps, wrong python path, encoding
    CODE = "code"                  # Syntax errors, import errors, type errors
    PERMISSION = "permission"      # Access denied, approval required
    NETWORK = "network"            # Timeout, connection refused
    UNKNOWN = "unknown"            # Can't classify


@dataclass
class ErrorRecord:
    tool_name: str = ""
    error_text: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    attempt: int = 0               # How many times this error has been retried
    recovered: bool = False


class ErrorRecoveryManager:
    """Controls error retry per-tool. Hard stops on repeated failures.

    Rules:
      - environment errors: max 2 auto-retries
      - code errors: max 2 auto-retries
      - permission errors: 0 retries (fatal immediately)
      - network errors: max 1 retry
      - unknown errors: max 1 retry
      - Same tool + same args called > 2 times consecutively → force FAILED
    """

    MAX_RETRIES_PER_TOOL = 2
    MAX_SAME_CALLS = 2            # Same tool + same args > this → infinite loop detection

    def __init__(self):
        self.errors: list[ErrorRecord] = []
        self._tool_call_sequence: list[dict] = []  # [(tool, args_hash), ...]

    def classify(self, tool_name: str, error_text: str) -> ErrorCategory:
        """Categorize the error for appropriate recovery strategy."""
        el = error_text.lower()

        # Environment patterns
        env_patterns = [
            "modulenotfounderror", "no module named", "importerror",
            "not found", "no such file", "encoding", "gbk",
            "'python3'", "python3 不是", "python3 is not",
            "permission denied", "access denied",
        ]
        for p in env_patterns:
            if p in el:
                return ErrorCategory.ENVIRONMENT

        # Code patterns
        code_patterns = [
            "syntaxerror", "indentationerror", "typeerror",
            "nameerror", "attributeerror", "keyerror", "indexerror",
            "valueerror", "traceback",
        ]
        for p in code_patterns:
            if p in el:
                return ErrorCategory.CODE

        # Permission patterns
        perm_patterns = ["forbidden", "unauthorized", "blocked", "批准", "approval"]
        for p in perm_patterns:
            if p in el:
                return ErrorCategory.PERMISSION

        # Network patterns
        net_patterns = ["timeout", "connection", "refused", "network", "dns"]
        for p in net_patterns:
            if p in el:
                return ErrorCategory.NETWORK

        return ErrorCategory.UNKNOWN

    def retry_allowed(self, tool_name: str, error_text: str) -> tuple[bool, str]:
        """Returns (allowed_to_retry, reason).

        Considers:
          1. Error category → retry budget
          2. Consecutive same-tool-same-args → infinite loop detection
        """
        category = self.classify(tool_name, error_text)

        # Permission errors → never retry
        if category == ErrorCategory.PERMISSION:
            return False, f"权限错误，不允许重试: {error_text[:100]}"

        # Count retries for this tool (errors from THIS run, not history)
        tool_errors = [e for e in self.errors if e.tool_name == tool_name and not e.recovered]
        retries_used = len(tool_errors)

        budget = self.MAX_RETRIES_PER_TOOL  # default: 2
        if category == ErrorCategory.PERMISSION:
            budget = 0
        elif category == ErrorCategory.NETWORK:
            budget = 1

        if retries_used >= budget:
            return False, (
                f"工具 '{tool_name}' 连续失败 {retries_used} 次（上限 {max(1,budget)}），已停止。"
                f" 错误: {error_text[:150]}"
            )

        # Infinite loop detection: same tool + same error text > 2 consecutive times
        # Only triggers when error_text is non-empty (empty texts are indistinguishable)
        if error_text and len(error_text.strip()) > 0:
            self._tool_call_sequence.append({"tool": tool_name, "text": error_text[:80]})
            if len(self._tool_call_sequence) >= 3:
                last3 = self._tool_call_sequence[-3:]
                all_have_text = all(len(e["text"].strip()) > 0 for e in last3)
                all_same = (
                    all_have_text and
                    last3[0]["tool"] == last3[1]["tool"] == last3[2]["tool"] and
                    last3[0]["text"][:40] == last3[1]["text"][:40] == last3[2]["text"][:40]
                )
                if all_same:
                    return False, (
                        f"检测到死循环：'{tool_name}' 连续 3 次出现相同错误。已强制停止。"
                    )

        self.errors.append(ErrorRecord(
            tool_name=tool_name,
            error_text=error_text[:200],
            category=category,
            attempt=retries_used + 1,
        ))
        return True, f"重试 {retries_used + 1}/{budget}"

    def recovery_message(self) -> str:
        """Build a filtered SYSTEM message for the LLM, hiding raw errors."""
        if not self.errors:
            return ""
        last = self.errors[-1]
        category_guidance = {
            ErrorCategory.ENVIRONMENT: "环境配置问题。请检查依赖安装、路径设置、编码格式。",
            ErrorCategory.CODE: "代码执行错误。请检查语法、导入路径、类型匹配。",
            ErrorCategory.PERMISSION: "权限不足。请确认文件访问权限。",
            ErrorCategory.NETWORK: "网络连接问题。请检查网络和 API 可用性。",
            ErrorCategory.UNKNOWN: "未知错误。请简化操作后重试。",
        }
        return (
            f"⚠️ {last.tool_name} 执行失败（{last.category.value}）\n"
            f"{category_guidance.get(last.category, '')}\n"
            f"重试次数: {last.attempt} | 剩余: {self.MAX_RETRIES_PER_TOOL - last.attempt}"
        )

    def is_fatal(self) -> bool:
        """Returns True if the agent should stop immediately."""
        # Permission errors are always fatal
        if any(e.category == ErrorCategory.PERMISSION for e in self.errors):
            return True
        # Any tool failed more than MAX_RETRIES (2) times
        for tool_name in set(e.tool_name for e in self.errors):
            failures = [e for e in self.errors if e.tool_name == tool_name and not e.recovered]
            if len(failures) > self.MAX_RETRIES_PER_TOOL:
                return True
        # Infinite loop detection check
        if len(self._tool_call_sequence) >= 3:
            last3 = self._tool_call_sequence[-3:]
            if (last3[0]["tool"] == last3[1]["tool"] == last3[2]["tool"] and
                len(last3[0]["text"]) > 0 and
                last3[0]["text"][:40] == last3[1]["text"][:40] == last3[2]["text"][:40]):
                return True
        return False

    def mark_recovered(self) -> None:
        """Mark all errors as recovered after a successful retry."""
        for e in self.errors:
            e.recovered = True
        self._tool_call_sequence.clear()


# ═══════════════════════════════════════════════════════════
# TASK LIFECYCLE CONTROLLER
# ═══════════════════════════════════════════════════════════

class TaskLifecycleController:
    """Owns the lifecycle state machine for a single task execution.

    LLM proposes actions. THIS controller decides if the task continues.

    Usage in AgentRuntime:
        lifecycle = TaskLifecycleController(goal_text, max_iterations=30)
        while lifecycle.can_continue():
            lifecycle.transition(PLAN or EXECUTE)
            ...
            lifecycle.record_tool_result(success, error)
            lifecycle.transition(VERIFY or ERROR or COMPLETE)
    """

    def __init__(self, goal_text: str = "", max_iterations: int = 30):
        from kernel.goal_tracker import GoalTracker

        self.stage = LifecycleStage.INIT
        self.max_iterations = max_iterations
        self.current_iteration = 0
        self.tracker = GoalTracker(goal_text)
        self.error_manager = ErrorRecoveryManager()
        self.stage_history: list[LifecycleStage] = [LifecycleStage.INIT]
        self.forced_stop_reason: str = ""
        self.auto_progress_to(LifecycleStage.INIT)

    # ── State machine ────────────────────────────────────

    def transition(self, target: LifecycleStage) -> bool:
        """Attempt to transition to a new stage. Returns True if allowed."""
        allowed = TRANSITIONS.get(self.stage, [])
        if target not in allowed:
            logger.warning(
                "Invalid transition: %s → %s (allowed: %s)",
                self.stage.value, target.value,
                [s.value for s in allowed],
            )
            return False
        self.stage = target
        self.stage_history.append(target)
        return True

    def auto_progress_to(self, stage: LifecycleStage) -> None:
        """Force-progress to a stage (bypasses transition rules for init/reset)."""
        self.stage = stage
        self.stage_history.append(stage)

    # ── Iteration control ────────────────────────────────

    def advance_iteration(self) -> None:
        """Called at the top of each while loop iteration."""
        self.current_iteration += 1
        # Auto-transition from PLAN to EXECUTE after iteration 3
        if self.current_iteration == 3 and self.stage == LifecycleStage.PLAN:
            self.transition(LifecycleStage.EXECUTE)

    def can_continue(self) -> bool:
        """The single source of truth for whether the agent loop should continue.

        This is where Runtime owns the stop decision — not the LLM.
        """
        # Hard stop: max iterations
        if self.current_iteration >= self.max_iterations:
            self.forced_stop_reason = f"达到最大迭代次数 ({self.max_iterations})"
            self.auto_progress_to(LifecycleStage.FAILED)
            return False

        # Hard stop: terminal stages
        if self.stage in (LifecycleStage.COMPLETE, LifecycleStage.FAILED):
            return False

        # Goal completion: all sub-goals fulfilled → force COMPLETE
        if self.tracker.items and self.tracker.all_fulfilled():
            self.auto_progress_to(LifecycleStage.COMPLETE)
            return False

        # Error recovery: is_fatal → force FAILED
        if self.error_manager.is_fatal():
            self.forced_stop_reason = "错误恢复失败，任务无法继续。"
            self.auto_progress_to(LifecycleStage.FAILED)
            return False

        return True

    # ── Tool result feedback ─────────────────────────────

    def record_tool_result(self, tool_name: str, success: bool,
                           output: str, args: dict | None = None) -> dict:
        """Feed a tool execution result into the lifecycle.

        Returns a dict with guidance on lifecycle state changes.
        """
        # v1.3.1: Sanitize output — never pass None or empty str to error handlers
        if output is None:
            output = ""
        error_text = output if not success else ""

        result: dict[str, Any] = {
            "lifecycle_stage": self.stage.value,
            "should_continue": True,
            "recovery_message": "",
            "verify_result": None,
        }

        if success:
            self.tracker.observe(tool_name, success, output, args)
            self.error_manager.mark_recovered()
            # After successful tool use, enter VERIFY
            self.transition(LifecycleStage.VERIFY)

            # v2.0: Real filesystem verification (not text pattern matching)
            vresult = self.tracker.verify()
            verify_ok = len(vresult.get("newly_fulfilled", [])) > 0
            verify_msg = (f"验证: {vresult['fulfilled']}/{vresult['total']} 目标完成"
                         if vresult.get("total", 0) > 0 else "工具执行成功")
            result["verify_result"] = {"ok": True, "message": verify_msg}

            if verify_ok:
                # VERIFY passed — check if we can go to COMPLETE
                if self.tracker.items and self.tracker.all_fulfilled():
                    self.auto_progress_to(LifecycleStage.COMPLETE)
                    result["lifecycle_stage"] = LifecycleStage.COMPLETE.value
                    result["should_continue"] = False
                    result["goal_progress"] = self.tracker.progress()
                else:
                    # Back to EXECUTE for next task
                    self.auto_progress_to(LifecycleStage.EXECUTE)
            else:
                # VERIFY failed — stay in EXECUTE to retry
                self.auto_progress_to(LifecycleStage.EXECUTE)
        else:
            # Tool failed — ensure we have a meaningful error text
            if not error_text or len(error_text.strip()) == 0:
                error_text = f"{tool_name} returned no output (可能的环境错误)"

            can_retry, reason = self.error_manager.retry_allowed(tool_name, error_text)
            self.tracker.observe(tool_name, False, error_text)

            if can_retry:
                self.auto_progress_to(LifecycleStage.RECOVER)
                result["lifecycle_stage"] = LifecycleStage.RECOVER.value
                result["recovery_message"] = self.error_manager.recovery_message()
            else:
                self.auto_progress_to(LifecycleStage.FAILED)
                result["lifecycle_stage"] = LifecycleStage.FAILED.value
                result["should_continue"] = False
                result["recovery_message"] = reason
                self.forced_stop_reason = reason

        return result

    def _quick_verify(self, tool_name: str, output: str) -> tuple[bool, str]:
        """Quick post-tool verification. Returns (ok, message)."""
        if tool_name == "write_file":
            if "chars" in output.lower() or "written" in output.lower():
                return True, f"文件写入成功"
            return False, f"文件写入验证失败"

        if tool_name == "shell":
            if "stderr" not in output.lower() or "traceback" not in output.lower():
                return True, "命令执行成功"
            return False, f"命令执行有错误输出"

        if tool_name == "list_files":
            if output.strip():
                return True, f"文件列表获取成功"
            return False, "文件列表为空"

        # For all other tools: pass by default
        return True, f"{tool_name} 完成"

    # ── Status ────────────────────────────────────────────

    def get_stage_emoji(self) -> str:
        return {
            LifecycleStage.INIT: "⚡", LifecycleStage.PLAN: "🧠",
            LifecycleStage.EXECUTE: "🔧", LifecycleStage.VERIFY: "🔍",
            LifecycleStage.ERROR: "⚠️", LifecycleStage.RECOVER: "🔨",
            LifecycleStage.COMPLETE: "✅", LifecycleStage.FAILED: "❌",
        }.get(self.stage, "➡️")

    def status_report(self) -> dict:
        return {
            "stage": self.stage.value,
            "iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "goal_progress": self.tracker.progress(),
            "error_count": len(self.error_manager.errors),
            "forced_stop": self.forced_stop_reason or None,
            "stage_history": [s.value for s in self.stage_history[-10:]],
        }
