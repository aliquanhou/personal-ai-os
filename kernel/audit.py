# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Agent Audit Log (Sprint 5)

Enterprise-grade audit trail for every decision, action, and state change.

Three audit streams:
1. DECISION_LOG — why an agent made a choice (rationale, alternatives, basis)
2. ACTION_LOG — what an agent did (tool call, state change, message sent)
3. SYSTEM_LOG — kernel-level events (agent registration, budget change, config)

Each entry is timestamped, attributed, and immutable once written.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditCategory(StrEnum):
    DECISION = "decision"       # Strategic choice
    ACTION = "action"           # Tool execution / state change
    SYSTEM = "system"           # Kernel event
    BUDGET = "budget"           # Cost/spending event
    SECURITY = "security"       # Permission / approval event
    ERROR = "error"             # Failure / exception


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    IMPORTANT = "important"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """A single immutable audit record."""
    id: str = ""
    timestamp: str = ""
    category: AuditCategory = AuditCategory.SYSTEM
    severity: AuditSeverity = AuditSeverity.INFO
    agent: str = ""               # Which agent (or "kernel")
    action: str = ""              # What happened
    detail: str = ""              # Human-readable description
    rationale: str = ""           # Why this was done
    context: dict = field(default_factory=dict)   # Structured data
    related_entries: list[str] = field(default_factory=list)  # Linked audit IDs
    session_id: str = ""
    task_id: str = ""
    project_slug: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "agent": self.agent,
            "action": self.action,
            "detail": self.detail[:500],
            "rationale": self.rationale[:500],
            "context_keys": list(self.context.keys()) if self.context else [],
            "related_entries": self.related_entries,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "project_slug": self.project_slug,
        }


class AuditLog:
    """Central audit trail for the entire AI organization.

    Thread-safe, append-only, persistent. Every important action in the
    system leaves a trace here. This is the "paper trail" that makes
    the AI company auditable and accountable.
    """

    def __init__(self, storage_path: str = ""):
        self._entries: list[AuditEntry] = []
        self._counter: int = 0
        self._storage_path = storage_path or str(
            Path(__file__).parent.parent / "data" / "audit_log.jsonl"
        )
        self._max_memory = 5000
        self._load()

    def record(self, category: AuditCategory, action: str, detail: str = "",
               agent: str = "kernel", severity: AuditSeverity = AuditSeverity.INFO,
               rationale: str = "", context: dict | None = None,
               session_id: str = "", task_id: str = "", project_slug: str = "",
               related: list[str] | None = None) -> str:
        """Record an audit entry. Returns the entry ID."""
        self._counter += 1
        entry = AuditEntry(
            id=f"audit-{self._counter:06d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category,
            severity=severity,
            agent=agent,
            action=action,
            detail=detail,
            rationale=rationale,
            context=context or {},
            related_entries=related or [],
            session_id=session_id,
            task_id=task_id,
            project_slug=project_slug,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_memory:
            self._entries = self._entries[-self._max_memory:]

        # Append to disk immediately for durability
        self._append_to_file(entry)

        logger.debug("Audit [%s] %s: %s", entry.id, category.value, action[:80])
        return entry.id

    # ── Convenience recorders ─────────────────────────

    def record_decision(self, agent: str, decision: str, rationale: str = "",
                        alternatives: list[str] | None = None,
                        context: dict | None = None,
                        session_id: str = "", task_id: str = "") -> str:
        """Record a strategic decision."""
        return self.record(
            category=AuditCategory.DECISION,
            action=decision,
            detail=f"Agent {agent} decided: {decision}",
            rationale=rationale,
            agent=agent,
            severity=AuditSeverity.IMPORTANT,
            context={"alternatives": alternatives or [], **(context or {})},
            session_id=session_id,
            task_id=task_id,
        )

    def record_action(self, agent: str, action: str, result: str = "",
                      tool_name: str = "", session_id: str = "",
                      task_id: str = "") -> str:
        """Record a tool execution or state change."""
        return self.record(
            category=AuditCategory.ACTION,
            action=action,
            detail=result[:500],
            agent=agent,
            context={"tool": tool_name},
            session_id=session_id,
            task_id=task_id,
        )

    def record_budget(self, agent: str, cost_usd: float, context_id: str = "",
                      detail: str = "") -> str:
        """Record a budget/spending event."""
        return self.record(
            category=AuditCategory.BUDGET,
            action=f"Spent ${cost_usd:.6f}",
            detail=detail or f"Budget charge for {context_id}",
            agent=agent,
            context={"cost_usd": cost_usd, "context_id": context_id},
        )

    def record_security(self, agent: str, event: str, detail: str = "",
                        severity: AuditSeverity = AuditSeverity.WARNING) -> str:
        """Record a security/permission event."""
        return self.record(
            category=AuditCategory.SECURITY,
            action=event,
            detail=detail,
            agent=agent,
            severity=severity,
        )

    def record_error(self, agent: str, error: str, detail: str = "",
                     context: dict | None = None) -> str:
        """Record an error/failure."""
        return self.record(
            category=AuditCategory.ERROR,
            action=error[:200],
            detail=detail,
            agent=agent,
            severity=AuditSeverity.CRITICAL,
            context=context,
        )

    # ── Query methods ─────────────────────────────────

    def get_by_agent(self, agent: str, limit: int = 50) -> list[dict]:
        """Get audit entries for a specific agent."""
        return [e.to_dict() for e in self._entries if e.agent == agent][-limit:]

    def get_by_category(self, category: AuditCategory, limit: int = 50) -> list[dict]:
        """Get entries by category."""
        return [e.to_dict() for e in self._entries if e.category == category][-limit:]

    def get_by_task(self, task_id: str, limit: int = 50) -> list[dict]:
        """Get entries for a specific task."""
        return [e.to_dict() for e in self._entries if e.task_id == task_id][-limit:]

    def get_decisions(self, limit: int = 50) -> list[dict]:
        """Get recent decisions."""
        return self.get_by_category(AuditCategory.DECISION, limit)

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Get most recent entries."""
        return [e.to_dict() for e in self._entries[-limit:]]

    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Simple text search across entries."""
        q = query.lower()
        results = []
        for e in reversed(self._entries):
            if q in e.action.lower() or q in e.detail.lower() or q in e.agent.lower():
                results.append(e.to_dict())
                if len(results) >= limit:
                    break
        return results

    def stats(self) -> dict:
        """Get audit statistics."""
        by_cat = {}
        by_agent = {}
        by_severity = {}
        for e in self._entries:
            cat = e.category.value
            by_cat[cat] = by_cat.get(cat, 0) + 1
            by_agent[e.agent] = by_agent.get(e.agent, 0) + 1
            sev = e.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
        return {
            "total_entries": len(self._entries),
            "by_category": by_cat,
            "by_agent": by_agent,
            "by_severity": by_severity,
        }

    # ── Persistence ───────────────────────────────────

    def _append_to_file(self, entry: AuditEntry) -> None:
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            pass  # Non-critical

    def _load(self) -> None:
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        d = json.loads(line)
                        self._counter += 1
                        entry = AuditEntry(
                            id=d.get("id", f"audit-{self._counter:06d}"),
                            timestamp=d.get("timestamp", ""),
                            category=AuditCategory(d.get("category", "system")),
                            severity=AuditSeverity(d.get("severity", "info")),
                            agent=d.get("agent", ""),
                            action=d.get("action", ""),
                            detail=d.get("detail", ""),
                            rationale=d.get("rationale", ""),
                            session_id=d.get("session_id", ""),
                            task_id=d.get("task_id", ""),
                            project_slug=d.get("project_slug", ""),
                        )
                        self._entries.append(entry)
            if self._entries:
                logger.info("Loaded %d audit entries from disk", len(self._entries))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load audit log: %s", e)


# Global singleton
_log: AuditLog | None = None


def get_audit_log() -> AuditLog:
    global _log
    if _log is None:
        _log = AuditLog()
    return _log
