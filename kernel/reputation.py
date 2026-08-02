# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Agent Reputation System (Sprint 5)

Tracks every agent's performance history and uses it to influence routing.

Reputation Score = success_rate × speed_score × consistency_score

Router integration:
  match_score = capability_match × reputation_weight
  → Best agent = most capable AND most reliable, not just most capable.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentReputation:
    """Performance history for one agent."""
    agent_name: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    avg_tool_calls: float = 0.0
    max_iterations_hit: int = 0          # Times agent hit iteration limit
    approval_blocks: int = 0             # Times agent was blocked by approval layer
    first_seen: str = ""
    last_active: str = ""
    # Per-capability stats
    capability_stats: dict[str, dict] = field(default_factory=dict)
    # Trend
    recent_results: list[bool] = field(default_factory=list)  # Last 20 results

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # Neutral default for new agents
        return self.successful_tasks / self.total_tasks

    @property
    def reputation_score(self) -> float:
        """Composite reputation score 0.0–1.0."""
        if self.total_tasks == 0:
            return 0.5  # Neutral for new agents

        sr = self.success_rate

        # Speed score: faster than 30s avg = bonus
        if self.avg_duration_ms > 0:
            speed = min(1.0, 30000 / max(self.avg_duration_ms, 1000))
        else:
            speed = 0.5

        # Consistency: recent trend
        if self.recent_results:
            recent_sr = sum(1 for r in self.recent_results[-10:] if r) / max(len(self.recent_results[-10:]), 1)
        else:
            recent_sr = 0.5

        return round(0.5 * sr + 0.3 * speed + 0.2 * recent_sr, 3)

    @property
    def tier(self) -> str:
        """Human-readable tier based on score."""
        s = self.reputation_score
        if s >= 0.90:
            return "S"
        if s >= 0.80:
            return "A"
        if s >= 0.65:
            return "B"
        if s >= 0.50:
            return "C"
        return "D"

    def record_task(self, success: bool, duration_ms: float,
                    tool_calls: int = 0, hit_max_iterations: bool = False,
                    blocked_by_approval: int = 0, capability: str = "") -> None:
        """Record a completed task result."""
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1

        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.total_tasks
        self.avg_tool_calls = ((self.avg_tool_calls * (self.total_tasks - 1)) + tool_calls) / max(self.total_tasks, 1)

        if hit_max_iterations:
            self.max_iterations_hit += 1
        if blocked_by_approval:
            self.approval_blocks += blocked_by_approval

        self.recent_results.append(success)
        if len(self.recent_results) > 20:
            self.recent_results = self.recent_results[-20:]

        now = datetime.now(timezone.utc).isoformat()
        if not self.first_seen:
            self.first_seen = now
        self.last_active = now

        # Per-capability tracking
        if capability:
            if capability not in self.capability_stats:
                self.capability_stats[capability] = {"total": 0, "success": 0}
            self.capability_stats[capability]["total"] += 1
            if success:
                self.capability_stats[capability]["success"] += 1

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": round(self.success_rate, 3),
            "reputation_score": self.reputation_score,
            "tier": self.tier,
            "avg_duration_ms": round(self.avg_duration_ms, 0),
            "avg_tool_calls": round(self.avg_tool_calls, 1),
            "max_iterations_hit": self.max_iterations_hit,
            "approval_blocks": self.approval_blocks,
            "first_seen": self.first_seen,
            "last_active": self.last_active,
            "capability_stats": self.capability_stats,
        }


class ReputationRegistry:
    """Tracks and queries agent reputations.

    Integrated into Router: when matching agents to tasks,
    capability_match_score is multiplied by reputation_weight.
    """

    def __init__(self, storage_path: str = ""):
        self._reputations: dict[str, AgentReputation] = {}
        self._storage_path = storage_path or str(
            Path(__file__).parent.parent / "data" / "reputation.json"
        )
        self._load()

    def get(self, agent_name: str) -> AgentReputation:
        """Get or create reputation for an agent."""
        if agent_name not in self._reputations:
            self._reputations[agent_name] = AgentReputation(agent_name=agent_name)
        return self._reputations[agent_name]

    def record(self, agent_name: str, success: bool, duration_ms: float,
               tool_calls: int = 0, hit_max_iterations: bool = False,
               blocked_by_approval: int = 0, capability: str = "") -> None:
        """Record a task completion for an agent."""
        rep = self.get(agent_name)
        rep.record_task(success, duration_ms, tool_calls,
                        hit_max_iterations, blocked_by_approval, capability)
        logger.info(
            "Reputation: %s score=%.3f tier=%s (%d tasks)",
            agent_name, rep.reputation_score, rep.tier, rep.total_tasks,
        )

    def weighted_match(self, agent_name: str, capability_score: float) -> float:
        """Combine capability match with reputation for final routing score.

        Args:
            agent_name: Agent to score.
            capability_score: 0.0–1.0 from capability matching.

        Returns:
            Weighted score 0.0–1.0.
        """
        rep = self.get(agent_name)
        # Weight: 60% capability, 40% reputation
        return round(0.6 * capability_score + 0.4 * rep.reputation_score, 3)

    def get_team_health(self, agent_names: list[str]) -> dict:
        """Get health overview for a team."""
        agents = {}
        for name in agent_names:
            rep = self.get(name)
            agents[name] = rep.to_dict()

        scores = [r.reputation_score for r in [self.get(n) for n in agent_names]]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "team_size": len(agent_names),
            "avg_reputation": round(avg_score, 3),
            "strongest": max(agent_names, key=lambda n: self.get(n).reputation_score) if agent_names else "",
            "weakest": min(agent_names, key=lambda n: self.get(n).reputation_score) if agent_names else "",
            "agents": agents,
        }

    def get_all(self) -> list[dict]:
        """Get all reputation records."""
        return [rep.to_dict() for rep in self._reputations.values()]

    def save(self) -> None:
        """Persist reputations to disk."""
        data = {name: rep.to_dict() for name, rep in self._reputations.items()}
        Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self._storage_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self) -> None:
        """Load persisted reputations."""
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            for name, d in data.items():
                rep = AgentReputation(agent_name=name)
                rep.total_tasks = d.get("total_tasks", 0)
                rep.successful_tasks = d.get("successful_tasks", 0)
                rep.failed_tasks = d.get("failed_tasks", 0)
                rep.total_duration_ms = d.get("avg_duration_ms", 0) * rep.total_tasks
                rep.avg_duration_ms = d.get("avg_duration_ms", 0)
                rep.max_iterations_hit = d.get("max_iterations_hit", 0)
                rep.approval_blocks = d.get("approval_blocks", 0)
                rep.first_seen = d.get("first_seen", "")
                rep.last_active = d.get("last_active", "")
                rep.capability_stats = d.get("capability_stats", {})
                self._reputations[name] = rep
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load reputation data: %s", e)


# Global singleton
_registry: ReputationRegistry | None = None


def get_reputation_registry() -> ReputationRegistry:
    global _registry
    if _registry is None:
        _registry = ReputationRegistry()
    return _registry
