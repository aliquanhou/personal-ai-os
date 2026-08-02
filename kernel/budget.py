"""Personal AI OS Kernel — Cost Budget Manager (Sprint 5)

Controls execution costs so the AI company doesn't overspend.

Tracks:
  - Token usage (per-agent, per-task, total)
  - Estimated API cost (based on model pricing)
  - Time budget
  - Budget limits with hard stops

Integration point: Router.execute() checks budget before each node.
If budget exceeded → node skipped with BUDGET_EXCEEDED state.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

logger = logging.getLogger(__name__)


# ── Model Pricing (USD per 1M tokens) ───────────────────

MODEL_PRICING = {
    "deepseek-chat":      {"input": 0.14, "output": 0.28},
    "deepseek-reasoner":  {"input": 0.55, "output": 2.19},
    "gpt-4o":             {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":        {"input": 0.15, "output": 0.60},
    "claude-sonnet-5":    {"input": 3.00, "output": 15.00},
    "claude-haiku-4.5":   {"input": 0.80, "output": 4.00},
    "qwen-plus":          {"input": 0.80, "output": 2.00},
    "llama3-70b":         {"input": 0.59, "output": 0.79},
    "default":            {"input": 1.00, "output": 3.00},
}


class BudgetStatus(StrEnum):
    ACTIVE = "active"
    WARNING = "warning"     # 80% used
    CRITICAL = "critical"   # 95% used
    EXCEEDED = "exceeded"   # Budget exhausted


@dataclass
class TokenUsage:
    """Token consumption record."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


class BudgetManager:
    """Manages spending limits for the AI organization.

    Usage:
        budget = BudgetManager(daily_limit_usd=5.00, task_limit_usd=1.00)

        # Before each agent run:
        budget.check(f"task_{task_id}", estimated_tokens=2000)

        # After each agent run:
        budget.record(task_id, model, input_tokens, output_tokens)
    """

    def __init__(self, daily_limit_usd: float = 5.00,
                 task_limit_usd: float = 2.00,
                 monthly_limit_usd: float = 100.00,
                 model: str = "deepseek-chat"):
        self.daily_limit = daily_limit_usd
        self.task_limit = task_limit_usd
        self.monthly_limit = monthly_limit_usd
        self.model = model

        # Running totals
        self.daily_spent: float = 0.0
        self.monthly_spent: float = 0.0
        self.total_spent: float = 0.0

        # Per-task tracking
        self._task_budgets: dict[str, TokenUsage] = {}
        self._agent_usage: dict[str, TokenUsage] = {}

        # History
        self._transactions: list[dict] = []

        # Date tracking
        self._current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._current_month = datetime.now(timezone.utc).strftime("%Y-%m")

        self._reset_daily_if_needed()

    def _reset_daily_if_needed(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if today != self._current_day:
            self.daily_spent = 0.0
            self._current_day = today
        if this_month != self._current_month:
            self.monthly_spent = 0.0
            self._current_month = this_month

    def estimate_cost(self, model: str = "", input_tokens: int = 0,
                      output_tokens: int = 0) -> float:
        """Estimate cost for a token count."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]
        return cost

    def check(self, context_id: str = "", estimated_input: int = 1000,
              estimated_output: int = 500) -> dict:
        """Check if there's budget remaining for an operation.

        Returns:
            {"allowed": bool, "status": BudgetStatus, "remaining_usd": float, "estimated_cost": float}
        """
        self._reset_daily_if_needed()
        est_cost = self.estimate_cost(self.model, estimated_input, estimated_output)

        status = BudgetStatus.ACTIVE
        allowed = True

        daily_after = self.daily_spent + est_cost
        monthly_after = self.monthly_spent + est_cost

        if daily_after >= self.daily_limit:
            status = BudgetStatus.EXCEEDED
            allowed = False
        elif monthly_after >= self.monthly_limit:
            status = BudgetStatus.EXCEEDED
            allowed = False
        elif daily_after >= self.daily_limit * 0.95:
            status = BudgetStatus.CRITICAL
        elif daily_after >= self.daily_limit * 0.80:
            status = BudgetStatus.WARNING

        # Task-specific limit
        if context_id in self._task_budgets:
            task_cost = self._task_budgets[context_id].estimated_cost_usd
            if task_cost + est_cost >= self.task_limit:
                status = BudgetStatus.EXCEEDED
                allowed = False

        return {
            "allowed": allowed,
            "status": status.value,
            "remaining_daily_usd": round(max(0, self.daily_limit - self.daily_spent), 4),
            "remaining_monthly_usd": round(max(0, self.monthly_limit - self.monthly_spent), 4),
            "estimated_cost_usd": round(est_cost, 6),
            "daily_spent_usd": round(self.daily_spent, 4),
        }

    def record(self, context_id: str, agent_name: str, model: str = "",
               input_tokens: int = 0, output_tokens: int = 0) -> TokenUsage:
        """Record actual token usage after an agent run.

        Returns the TokenUsage record.
        """
        self._reset_daily_if_needed()
        model = model or self.model
        cost = self.estimate_cost(model, input_tokens, output_tokens)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=cost,
        )

        # Accumulate
        self.daily_spent += cost
        self.monthly_spent += cost
        self.total_spent += cost

        # Per-task
        if context_id not in self._task_budgets:
            self._task_budgets[context_id] = TokenUsage()
        task = self._task_budgets[context_id]
        task.input_tokens += input_tokens
        task.output_tokens += output_tokens
        task.total_tokens += usage.total_tokens
        task.estimated_cost_usd += cost

        # Per-agent
        if agent_name not in self._agent_usage:
            self._agent_usage[agent_name] = TokenUsage()
        ag = self._agent_usage[agent_name]
        ag.input_tokens += input_tokens
        ag.output_tokens += output_tokens
        ag.total_tokens += usage.total_tokens
        ag.estimated_cost_usd += cost

        # Transaction log
        self._transactions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_id": context_id,
            "agent": agent_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        })
        if len(self._transactions) > 1000:
            self._transactions = self._transactions[-1000:]

        logger.debug(
            "Budget: %s spent $%.6f (daily: $%.4f/$%.2f)",
            context_id, cost, self.daily_spent, self.daily_limit,
        )
        return usage

    def get_status(self) -> dict:
        """Get current budget status."""
        self._reset_daily_if_needed()
        return {
            "daily_limit_usd": self.daily_limit,
            "daily_spent_usd": round(self.daily_spent, 4),
            "daily_remaining_usd": round(max(0, self.daily_limit - self.daily_spent), 4),
            "daily_pct": round(self.daily_spent / self.daily_limit * 100, 1) if self.daily_limit else 0,
            "monthly_limit_usd": self.monthly_limit,
            "monthly_spent_usd": round(self.monthly_spent, 4),
            "task_limit_usd": self.task_limit,
            "total_spent_usd": round(self.total_spent, 4),
            "model": self.model,
            "status": self._compute_status().value,
        }

    def _compute_status(self) -> BudgetStatus:
        pct = self.daily_spent / self.daily_limit if self.daily_limit else 0
        if pct >= 1.0:
            return BudgetStatus.EXCEEDED
        if pct >= 0.95:
            return BudgetStatus.CRITICAL
        if pct >= 0.80:
            return BudgetStatus.WARNING
        return BudgetStatus.ACTIVE

    def get_agent_costs(self) -> dict:
        """Get per-agent cost breakdown."""
        return {
            name: usage.to_dict()
            for name, usage in self._agent_usage.items()
        }

    def get_task_cost(self, context_id: str) -> dict:
        """Get cost for a specific task context."""
        usage = self._task_budgets.get(context_id, TokenUsage())
        return usage.to_dict()

    def get_transactions(self, limit: int = 50) -> list[dict]:
        """Get recent budget transactions."""
        return self._transactions[-limit:]

    def reset_daily(self) -> None:
        """Force reset daily budget."""
        self.daily_spent = 0.0
        self._current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# Global singleton
_manager: BudgetManager | None = None


def get_budget_manager(**kwargs) -> BudgetManager:
    global _manager
    if _manager is None:
        _manager = BudgetManager(**kwargs)
    return _manager
