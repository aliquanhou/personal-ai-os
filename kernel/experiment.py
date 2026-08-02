"""Personal AI OS Kernel — Experiment Runner (Sprint 6)

A/B testing infrastructure for improvement proposals.

ADR-006 compliance:
  ✅ Experiments run in controlled scope (max 10 tasks)
  ✅ Human Promotion Gate after experiment completes
  ✅ Results compared: baseline vs variant
  ✅ Only promoted experiments become permanent
  ❌ No automatic promotion without human review
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    EXPIRED = "expired"


@dataclass
class ExperimentVariant:
    """One side of an A/B test."""
    name: str = ""                  # "baseline" or "variant_v1.1"
    description: str = ""           # What's different
    agent_name: str = ""            # Which agent
    changes: dict = field(default_factory=dict)  # What changed (e.g. {"system_prompt_add": "..."})
    task_count: int = 0             # How many tasks run on this variant
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    task_results: list[dict] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.task_count == 0:
            return 0.0
        return self.success_count / self.task_count

    @property
    def avg_duration_ms(self) -> float:
        if self.task_count == 0:
            return 0.0
        return self.total_duration_ms / self.task_count


@dataclass
class Experiment:
    """An A/B experiment comparing two agent variants."""
    id: str = field(default_factory=lambda: f"EXP-{str(uuid.uuid4())[:8].upper()}")
    title: str = ""
    proposal_id: str = ""           # Linked improvement proposal
    agent_name: str = ""            # Which agent is being tested
    baseline: ExperimentVariant = field(default_factory=lambda: ExperimentVariant(name="baseline"))
    variant: ExperimentVariant = field(default_factory=ExperimentVariant(name="variant"))
    status: ExperimentStatus = ExperimentStatus.CREATED
    max_tasks: int = 10             # Budget: max tasks per experiment
    created_at: str = ""
    completed_at: str = ""
    winner: str = ""                # "baseline" / "variant" / "tie"
    win_margin: float = 0.0         # How much better the winner was
    promoted: bool = False          # Human promoted gate

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "proposal_id": self.proposal_id,
            "agent_name": self.agent_name,
            "baseline": {
                "name": self.baseline.name,
                "task_count": self.baseline.task_count,
                "success_count": self.baseline.success_count,
                "failure_count": self.baseline.failure_count,
                "success_rate": round(self.baseline.success_rate, 3),
                "avg_duration_ms": round(self.baseline.avg_duration_ms, 0),
            },
            "variant": {
                "name": self.variant.name,
                "description": self.variant.description,
                "task_count": self.variant.task_count,
                "success_count": self.variant.success_count,
                "failure_count": self.variant.failure_count,
                "success_rate": round(self.variant.success_rate, 3),
                "avg_duration_ms": round(self.variant.avg_duration_ms, 0),
            },
            "status": self.status.value,
            "max_tasks": self.max_tasks,
            "winner": self.winner,
            "win_margin": round(self.win_margin, 3),
            "promoted": self.promoted,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    def record_result(self, side: str, success: bool, duration_ms: float,
                      task_info: dict | None = None) -> None:
        """Record a task result on either baseline or variant."""
        variant = self.baseline if side == "baseline" else self.variant
        variant.task_count += 1
        if success:
            variant.success_count += 1
        else:
            variant.failure_count += 1
        variant.total_duration_ms += duration_ms
        if task_info:
            variant.task_results.append(task_info)

    def evaluate(self) -> dict:
        """Compare baseline vs variant. Returns the comparison result."""
        b_sr = self.baseline.success_rate
        v_sr = self.variant.success_rate

        if v_sr > b_sr + 0.05:       # Variant is 5%+ better
            self.winner = "variant"
            self.win_margin = v_sr - b_sr
        elif b_sr > v_sr + 0.05:     # Baseline is 5%+ better
            self.winner = "baseline"
            self.win_margin = b_sr - v_sr
        else:                         # Too close to call
            self.winner = "tie"
            self.win_margin = abs(v_sr - b_sr)

        return {
            "winner": self.winner,
            "baseline_sr": round(b_sr, 3),
            "variant_sr": round(v_sr, 3),
            "margin": round(self.win_margin, 3),
            "baseline_tasks": self.baseline.task_count,
            "variant_tasks": self.variant.task_count,
            "recommendation": self._recommendation(),
        }

    def _recommendation(self) -> str:
        if self.winner == "variant" and self.variant.task_count >= 3:
            return f"建议采用 variant: 成功率提高 {self.win_margin:.0%}"
        elif self.winner == "baseline" and self.baseline.task_count >= 3:
            return "保持 baseline: variant 未显示足够改善"
        else:
            return "需要更多数据才能做出判断"


class ExperimentRunner:
    """Manages A/B experiments for improvement proposals.

    Lifecycle:
      CREATED → RUNNING → COMPLETED → PROMOTED (human gate) / ROLLED_BACK

    Budget: max 10 tasks per experiment.
    """

    def __init__(self, storage_path: str = ""):
        self._experiments: dict[str, Experiment] = {}
        self._storage_path = storage_path or str(
            Path(__file__).parent.parent / "data" / "experiments.json"
        )
        self._load()

    def create(self, title: str, agent_name: str, proposal_id: str = "",
               variant_desc: str = "", changes: dict | None = None) -> Experiment:
        """Create a new A/B experiment."""
        exp = Experiment(
            title=title,
            proposal_id=proposal_id,
            agent_name=agent_name,
            baseline=ExperimentVariant(name="baseline", agent_name=agent_name),
            variant=ExperimentVariant(
                name=f"variant_{agent_name}_v1.1",
                description=variant_desc,
                agent_name=agent_name,
                changes=changes or {},
            ),
            status=ExperimentStatus.CREATED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._experiments[exp.id] = exp
        self._save()

        # Audit
        try:
            from kernel.audit import get_audit_log, AuditCategory
            get_audit_log().record(
                category=AuditCategory.DECISION,
                action=f"Experiment created: {exp.id}",
                detail=f"A/B test for {agent_name}: {title}",
                agent="evolution_advisor",
            )
        except Exception:
            pass

        logger.info("Created experiment %s: %s", exp.id, title)
        return exp

    def start(self, experiment_id: str) -> bool:
        """Start running an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.CREATED:
            return False
        exp.status = ExperimentStatus.RUNNING
        self._save()
        return True

    def record(self, experiment_id: str, side: str, success: bool,
               duration_ms: float, task_info: dict | None = None) -> bool:
        """Record a task result for an experiment side.

        side: "baseline" or "variant"
        max_tasks is per-side (e.g., 10 baseline + 10 variant = 20 total).
        Returns False if both sides are full.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return False

        variant = exp.baseline if side == "baseline" else exp.variant

        # Per-side budget: each side gets max_tasks
        if variant.task_count >= exp.max_tasks:
            # This side is full. Check if both sides are full.
            if exp.baseline.task_count >= exp.max_tasks and exp.variant.task_count >= exp.max_tasks:
                exp.status = ExperimentStatus.COMPLETED
                exp.completed_at = datetime.now(timezone.utc).isoformat()
                evaluation = exp.evaluate()
                self._save()
                logger.info("Experiment %s completed: %s", experiment_id, evaluation["recommendation"])
            return False

        exp.record_result(side, success, duration_ms, task_info)

        # Check if both sides are now full
        if exp.baseline.task_count >= exp.max_tasks and exp.variant.task_count >= exp.max_tasks:
            exp.status = ExperimentStatus.COMPLETED
            exp.completed_at = datetime.now(timezone.utc).isoformat()
            evaluation = exp.evaluate()
            logger.info("Experiment %s completed: %s", experiment_id, evaluation["recommendation"])

        self._save()
        return True

    def evaluate(self, experiment_id: str) -> dict | None:
        """Evaluate experiment results."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        return exp.evaluate()

    def promote(self, experiment_id: str) -> bool:
        """Human promotion gate: make the variant permanent."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.COMPLETED:
            return False
        if exp.winner != "variant":
            logger.info("Experiment %s not promoted: winner is %s", experiment_id, exp.winner)
            return False

        exp.status = ExperimentStatus.PROMOTED
        exp.promoted = True
        self._save()

        try:
            from kernel.audit import get_audit_log, AuditCategory
            get_audit_log().record(
                category=AuditCategory.DECISION,
                action=f"Experiment PROMOTED: {experiment_id}",
                detail=f"Variant promoted: success rate improved by {exp.win_margin:.0%}",
                agent="human",
                context=exp.evaluate(),
            )
        except Exception:
            pass

        logger.info("Experiment %s PROMOTED: variant becomes permanent", experiment_id)
        return True

    def rollback(self, experiment_id: str) -> bool:
        """Rollback/reject an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return False
        exp.status = ExperimentStatus.ROLLED_BACK
        self._save()
        return True

    # ── Query ───────────────────────────────────────────

    def get(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def list_all(self) -> list[dict]:
        return [e.to_dict() for e in self._experiments.values()]

    def list_active(self) -> list[dict]:
        return [e.to_dict() for e in self._experiments.values()
                if e.status in (ExperimentStatus.RUNNING,)]

    def list_completed(self) -> list[dict]:
        return [e.to_dict() for e in self._experiments.values()
                if e.status == ExperimentStatus.COMPLETED]

    def get_stats(self) -> dict:
        return {
            "total": len(self._experiments),
            "running": len(self.list_active()),
            "completed": len(self.list_completed()),
            "promoted": sum(1 for e in self._experiments.values() if e.promoted),
        }

    # ── Persistence ────────────────────────────────────

    def _save(self) -> None:
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            data = {"experiments": {eid: e.to_dict() for eid, e in self._experiments.items()}}
            Path(self._storage_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError:
            pass

    def _load(self) -> None:
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            for eid, ed in data.get("experiments", {}).items():
                exp = Experiment(
                    id=eid,
                    title=ed.get("title", ""),
                    proposal_id=ed.get("proposal_id", ""),
                    agent_name=ed.get("agent_name", ""),
                    status=ExperimentStatus(ed.get("status", "created")),
                    max_tasks=ed.get("max_tasks", 10),
                    created_at=ed.get("created_at", ""),
                    completed_at=ed.get("completed_at", ""),
                    winner=ed.get("winner", ""),
                    win_margin=ed.get("win_margin", 0),
                    promoted=ed.get("promoted", False),
                )
                b = ed.get("baseline", {})
                exp.baseline = ExperimentVariant(
                    name=b.get("name", "baseline"),
                    task_count=b.get("task_count", 0),
                    success_count=b.get("success_count", 0),
                    failure_count=b.get("failure_count", 0),
                )
                v = ed.get("variant", {})
                exp.variant = ExperimentVariant(
                    name=v.get("name", "variant"),
                    description=v.get("description", ""),
                    task_count=v.get("task_count", 0),
                    success_count=v.get("success_count", 0),
                    failure_count=v.get("failure_count", 0),
                )
                self._experiments[eid] = exp
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load experiments: %s", e)


# Global singleton
_runner: ExperimentRunner | None = None


def get_experiment_runner() -> ExperimentRunner:
    global _runner
    if _runner is None:
        _runner = ExperimentRunner()
    return _runner
