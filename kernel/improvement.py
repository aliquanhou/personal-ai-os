# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Improvement Proposal System (Sprint 6)

Generates concrete improvement proposals from PatternReport analysis.

ADR-006 compliance:
  ✅ AI ANALYZES data and GENERATES proposals
  ❌ AI does NOT apply proposals without Human Approval
  ✅ All proposals tracked in Audit Log
  ✅ Proposals auto-expire after 30 days if not reviewed
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPERIMENTING = "experimenting"
    PROMOTED = "promoted"     # Promoted from experiment → permanent
    STALE = "stale"           # Auto-expired (30 days no review)
    WITHDRAWN = "withdrawn"


class ProposalType(StrEnum):
    ADD_CHECKLIST = "add_checklist"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    AGENT_GUIDANCE = "agent_guidance"
    ROUTER_ADJUSTMENT = "router_adjustment"
    BUDGET_ADJUSTMENT = "budget_adjustment"
    SKILL_SUGGESTION = "skill_suggestion"
    TEST_SCENARIO = "test_scenario"
    OTHER = "other"


@dataclass
class ImprovementProposal:
    """A concrete proposal for system improvement.

    Generated from PatternReport data. Must pass Human Approval before
    any application. Tracked in Audit Log.
    """
    id: str = field(default_factory=lambda: f"IMP-{str(uuid.uuid4())[:8].upper()}")
    title: str = ""
    description: str = ""
    proposal_type: ProposalType = ProposalType.OTHER
    target_agent: str = ""           # Which agent to improve (or "all")
    target_module: str = ""          # Which module (or "")
    rationale: str = ""              # Why this improvement (from pattern analysis)
    expected_impact: str = ""        # What should improve
    confidence: float = 0.5          # 0.0–1.0 — how confident the analysis was
    priority: str = "medium"         # low / medium / high / critical
    suggested_changes: dict = field(default_factory=dict)  # What to change
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: str = ""            # "human" or "auto"
    review_notes: str = ""
    experiment_id: str = ""          # Linked experiment (if approved for testing)
    expires_at: str = ""             # Auto-stale after 30 days

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.proposal_type.value,
            "target_agent": self.target_agent,
            "rationale": self.rationale,
            "expected_impact": self.expected_impact,
            "confidence": self.confidence,
            "priority": self.priority,
            "suggested_changes": self.suggested_changes,
            "status": self.status.value,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "experiment_id": self.experiment_id,
            "expires_at": self.expires_at,
        }


class ImprovementRegistry:
    """Manages the lifecycle of ImprovementProposals.

    Flow: DRAFT → PENDING_REVIEW → APPROVED/REJECTED
               → EXPERIMENTING → PROMOTED
               → (or STALE after 30 days)

    All state changes are audited.
    """

    def __init__(self, storage_path: str = ""):
        self._proposals: dict[str, ImprovementProposal] = {}
        self._storage_path = storage_path or str(
            Path(__file__).parent.parent / "data" / "improvements.json"
        )
        # Stats
        self._counters = {
            "total_generated": 0,
            "approved": 0,
            "rejected": 0,
            "promoted": 0,
            "stale": 0,
        }
        self._load()

    # ── Create ──────────────────────────────────────────

    def create(self, title: str, description: str = "",
               proposal_type: ProposalType = ProposalType.OTHER,
               target_agent: str = "", rationale: str = "",
               expected_impact: str = "", confidence: float = 0.5,
               priority: str = "medium",
               suggested_changes: dict | None = None) -> ImprovementProposal:
        """Create a new improvement proposal."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)

        proposal = ImprovementProposal(
            title=title,
            description=description,
            proposal_type=proposal_type,
            target_agent=target_agent,
            rationale=rationale,
            expected_impact=expected_impact,
            confidence=confidence,
            priority=priority,
            suggested_changes=suggested_changes or {},
            status=ProposalStatus.DRAFT,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )

        self._proposals[proposal.id] = proposal
        self._counters["total_generated"] += 1
        self._save()

        # Audit
        try:
            from kernel.audit import get_audit_log, AuditCategory
            get_audit_log().record(
                category=AuditCategory.DECISION,
                action=f"Improvement proposal created: {proposal.id}",
                detail=title,
                agent="evolution_advisor",
                rationale=rationale,
            )
        except Exception:
            pass

        logger.info("Created proposal %s: %s [%s]", proposal.id, title, priority)
        return proposal

    def submit_for_review(self, proposal_id: str) -> bool:
        """Submit a draft proposal for human review."""
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.DRAFT:
            return False
        prop.status = ProposalStatus.PENDING_REVIEW
        self._save()
        return True

    # ── Generate from analysis ──────────────────────────

    def generate_from_analysis(self, report) -> list[ImprovementProposal]:
        """Generate proposals from a PatternReport (ExperienceAnalyzer output).

        This is the bridge between OBSERVE and PROPOSE.
        """
        proposals = []

        for opp in report.opportunities:
            ptype = ProposalType(opp.get("type", "other"))
            target = opp.get("target_agent", "")

            prop = self.create(
                title=opp.get("suggestion", "Improvement opportunity"),
                description=opp.get("reason", ""),
                proposal_type=ptype,
                target_agent=target,
                rationale=f"自动发现: {opp.get('reason', '')}",
                expected_impact=f"预期改善 {target} 的任务成功率",
                confidence=opp.get("confidence", 0.5),
                priority=opp.get("priority", "medium"),
                suggested_changes={"opportunity": opp},
            )
            self.submit_for_review(prop.id)
            proposals.append(prop)

        return proposals

    # ── Human Approval ──────────────────────────────────

    def approve(self, proposal_id: str, reviewer: str = "human",
                notes: str = "") -> bool:
        """Human approves a proposal → moves to APPROVED status."""
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status not in (ProposalStatus.PENDING_REVIEW, ProposalStatus.DRAFT):
            return False

        now = datetime.now(timezone.utc)
        prop.status = ProposalStatus.APPROVED
        prop.reviewed_at = now.isoformat()
        prop.reviewed_by = reviewer
        prop.review_notes = notes
        self._counters["approved"] += 1
        self._save()

        try:
            from kernel.audit import get_audit_log, AuditCategory
            get_audit_log().record(
                category=AuditCategory.DECISION,
                action=f"Proposal APPROVED: {proposal_id}",
                detail=prop.title,
                agent=reviewer,
                rationale=notes,
            )
        except Exception:
            pass

        logger.info("Proposal %s APPROVED by %s", proposal_id, reviewer)
        return True

    def reject(self, proposal_id: str, reviewer: str = "human",
               notes: str = "") -> bool:
        """Human rejects a proposal."""
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status not in (ProposalStatus.PENDING_REVIEW, ProposalStatus.DRAFT):
            return False

        prop.status = ProposalStatus.REJECTED
        prop.reviewed_at = datetime.now(timezone.utc).isoformat()
        prop.reviewed_by = reviewer
        prop.review_notes = notes
        self._counters["rejected"] += 1
        self._save()
        logger.info("Proposal %s REJECTED by %s", proposal_id, reviewer)
        return True

    # ── Experiment → Promote ───────────────────────────

    def mark_experimenting(self, proposal_id: str, experiment_id: str) -> bool:
        """Mark a proposal as in experiment phase."""
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.APPROVED:
            return False
        prop.status = ProposalStatus.EXPERIMENTING
        prop.experiment_id = experiment_id
        self._save()
        return True

    def promote(self, proposal_id: str, experiment_result: dict | None = None) -> bool:
        """Promote a successfully tested proposal → permanent."""
        prop = self._proposals.get(proposal_id)
        if not prop or prop.status != ProposalStatus.EXPERIMENTING:
            return False
        prop.status = ProposalStatus.PROMOTED
        self._counters["promoted"] += 1
        self._save()

        try:
            from kernel.audit import get_audit_log, AuditCategory
            get_audit_log().record(
                category=AuditCategory.DECISION,
                action=f"Proposal PROMOTED: {proposal_id}",
                detail=f"{prop.title} — experiment succeeded, promoted to permanent",
                agent="evolution_advisor",
                context=experiment_result or {},
            )
        except Exception:
            pass

        logger.info("Proposal %s PROMOTED to permanent", proposal_id)
        return True

    # ── Auto-stale ─────────────────────────────────────

    def check_stale(self) -> int:
        """Auto-expire proposals older than 30 days. Returns count of expired."""
        now = datetime.now(timezone.utc)
        expired = 0
        for prop in self._proposals.values():
            if prop.status in (ProposalStatus.DRAFT, ProposalStatus.PENDING_REVIEW):
                if prop.expires_at:
                    expires = datetime.fromisoformat(prop.expires_at)
                    if now > expires:
                        prop.status = ProposalStatus.STALE
                        self._counters["stale"] += 1
                        expired += 1
        if expired:
            self._save()
            logger.info("Auto-expired %d stale proposals", expired)
        return expired

    # ── Query ────────────────────────────────────────────

    def get(self, proposal_id: str) -> ImprovementProposal | None:
        return self._proposals.get(proposal_id)

    def list_by_status(self, status: ProposalStatus | None = None) -> list[dict]:
        """List proposals, optionally filtered by status."""
        if status:
            return [p.to_dict() for p in self._proposals.values() if p.status == status]
        return [p.to_dict() for p in self._proposals.values()]

    def list_pending_review(self) -> list[dict]:
        """Get proposals waiting for human review."""
        return self.list_by_status(ProposalStatus.PENDING_REVIEW)

    def list_active(self) -> list[dict]:
        """Get proposals that are approved or experimenting."""
        return [p.to_dict() for p in self._proposals.values()
                if p.status in (ProposalStatus.APPROVED, ProposalStatus.EXPERIMENTING)]

    def list_promoted(self) -> list[dict]:
        """Get successfully promoted proposals."""
        return self.list_by_status(ProposalStatus.PROMOTED)

    def get_stats(self) -> dict:
        return {
            **self._counters,
            "pending_review": len(self.list_pending_review()),
            "active": len(self.list_active()),
            "promoted": len(self.list_promoted()),
            "total": len(self._proposals),
        }

    # ── Persistence ─────────────────────────────────────

    def _save(self) -> None:
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            data = {
                "proposals": {pid: p.to_dict() for pid, p in self._proposals.items()},
                "counters": self._counters,
            }
            Path(self._storage_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError:
            pass

    def _load(self) -> None:
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            self._counters = data.get("counters", self._counters)
            for pid, pd in data.get("proposals", {}).items():
                prop = ImprovementProposal(
                    id=pid,
                    title=pd.get("title", ""),
                    description=pd.get("description", ""),
                    proposal_type=ProposalType(pd.get("type", "other")),
                    target_agent=pd.get("target_agent", ""),
                    rationale=pd.get("rationale", ""),
                    expected_impact=pd.get("expected_impact", ""),
                    confidence=pd.get("confidence", 0.5),
                    priority=pd.get("priority", "medium"),
                    suggested_changes=pd.get("suggested_changes", {}),
                    status=ProposalStatus(pd.get("status", "draft")),
                    created_at=pd.get("created_at", ""),
                    reviewed_at=pd.get("reviewed_at", ""),
                    reviewed_by=pd.get("reviewed_by", ""),
                    experiment_id=pd.get("experiment_id", ""),
                    expires_at=pd.get("expires_at", ""),
                )
                self._proposals[pid] = prop
            if self._proposals:
                logger.info("Loaded %d improvement proposals", len(self._proposals))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load improvements: %s", e)


# Global singleton
_registry: ImprovementRegistry | None = None


def get_improvement_registry() -> ImprovementRegistry:
    global _registry
    if _registry is None:
        _registry = ImprovementRegistry()
    return _registry
