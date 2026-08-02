# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Experience Analyzer (Sprint 6)

Reads the AI organization's historical data and discovers patterns:
  - Which agents fail most often? On what tasks?
  - What failure modes recur?
  - Where are the bottleneck points in task graphs?
  - What skills/checklists could prevent common failures?

Principle (ADR-006): OBSERVE only. Does NOT modify anything.
Output: structured PatternReport consumed by ImprovementProposal generator.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatternReport:
    """A structured report of patterns found in historical data."""
    generated_at: str = ""
    data_window: str = ""  # e.g. "last_100_tasks"

    # Agent-level patterns
    agent_stats: dict[str, dict] = field(default_factory=dict)

    # Failure patterns
    failure_patterns: list[dict] = field(default_factory=list)

    # Bottleneck analysis
    bottlenecks: list[dict] = field(default_factory=list)

    # Improvement opportunities
    opportunities: list[dict] = field(default_factory=list)

    # Summary
    summary: str = ""
    overall_health: str = "healthy"  # healthy / warning / critical

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "data_window": self.data_window,
            "agent_stats": self.agent_stats,
            "failure_patterns": self.failure_patterns,
            "bottlenecks": self.bottlenecks,
            "opportunities": self.opportunities,
            "summary": self.summary,
            "overall_health": self.overall_health,
        }


class ExperienceAnalyzer:
    """Analyzes the AI organization's history to find improvement opportunities.

    This is the OBSERVE phase. It reads data, finds patterns, produces a report.
    It never modifies anything — that's the job of ImprovementProposal.
    """

    def __init__(self):
        self._last_report: PatternReport | None = None

    def analyze(self, task_limit: int = 100, experience_limit: int = 50) -> PatternReport:
        """Run a full analysis across all available data sources.

        Returns a PatternReport suitable for feeding to the ImprovementProposal generator.
        """
        from memory.manager import get_memory
        from kernel.reputation import get_reputation_registry

        memory = get_memory()
        rep_registry = get_reputation_registry()

        report = PatternReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            data_window=f"tasks: {task_limit}, experiences: {experience_limit}",
        )

        # ── 1. Agent Performance Stats ──
        all_reps = rep_registry.get_all()
        for r in all_reps:
            report.agent_stats[r["agent_name"]] = {
                "total_tasks": r["total_tasks"],
                "success_rate": r["success_rate"],
                "reputation_score": r["reputation_score"],
                "tier": r["tier"],
                "avg_duration_ms": r["avg_duration_ms"],
                "capability_stats": r.get("capability_stats", {}),
            }

        # ── 2. Failure Pattern Analysis ──
        experiences = memory.get_experiences(limit=experience_limit)
        failures = [e for e in experiences if e.get("emotion") in ("negative", "neutral")]

        # Group by agent name mentioned in title/description
        agent_failures: dict[str, list[dict]] = defaultdict(list)
        keyword_failures: Counter = Counter()

        failure_keywords = [
            "失败", "错误", "error", "fail", "bug", "超时", "timeout",
            "数据库", "database", "权限", "permission", "编码", "encode",
            "崩溃", "crash", "内存", "memory", "死循环", "loop",
        ]

        for exp in failures:
            text = f"{exp.get('title', '')} {exp.get('description', '')} {exp.get('lesson', '')}".lower()
            # Which agent?
            for agent_name in report.agent_stats:
                if agent_name in text:
                    agent_failures[agent_name].append(exp)
            # Keyword matching
            for kw in failure_keywords:
                if kw.lower() in text:
                    keyword_failures[kw] += 1

        for agent_name, exps in sorted(agent_failures.items(), key=lambda x: -len(x[1])):
            if len(exps) >= 2:  # Only report patterns with ≥2 occurrences
                # Extract common themes from lessons
                lessons = [e.get("lesson", "") for e in exps if e.get("lesson")]
                report.failure_patterns.append({
                    "agent": agent_name,
                    "count": len(exps),
                    "frequency_pct": round(len(exps) / max(len(experiences), 1) * 100, 1),
                    "common_lessons": lessons[:5],
                    "sample_titles": [e.get("title", "") for e in exps[:3]],
                })

        # ── 3. Bottleneck Analysis ──
        tasks = memory.get_tasks_by_state(["failed", "done"], limit=task_limit)
        agent_bottlenecks: dict[str, dict] = defaultdict(lambda: {"total": 0, "failed": 0, "max_iter_hit": 0})

        for task in tasks:
            agent_name = task.get("agent_name", "unknown")
            agent_bottlenecks[agent_name]["total"] += 1
            if task["state"] == "failed":
                agent_bottlenecks[agent_name]["failed"] += 1
            reflection = task.get("reflection", {})
            if reflection and reflection.get("hit_max_iterations"):
                agent_bottlenecks[agent_name]["max_iter_hit"] += 1

        for agent_name, stats in agent_bottlenecks.items():
            if stats["total"] >= 3:
                fail_rate = stats["failed"] / stats["total"]
                if fail_rate > 0.2:  # >20% failure rate
                    report.bottlenecks.append({
                        "agent": agent_name,
                        "total_tasks": stats["total"],
                        "failed": stats["failed"],
                        "failure_rate": round(fail_rate, 2),
                        "max_iter_hit": stats["max_iter_hit"],
                    })

        # ── 4. Top Keywords ──
        top_keywords = keyword_failures.most_common(10)
        if top_keywords:
            report.failure_patterns.append({
                "type": "keyword_analysis",
                "top_keywords": [{"keyword": kw, "count": cnt} for kw, cnt in top_keywords if cnt >= 2],
            })

        # ── 5. Generate Opportunities ──
        report.opportunities = self._generate_opportunities(report)

        # ── 6. Summary ──
        report.summary = self._summarize(report)
        report.overall_health = self._compute_health(report)

        self._last_report = report
        logger.info(
            "Experience analysis: %d patterns, %d bottlenecks, %d opportunities. Health: %s",
            len(report.failure_patterns), len(report.bottlenecks),
            len(report.opportunities), report.overall_health,
        )
        return report

    def _generate_opportunities(self, report: PatternReport) -> list[dict]:
        """Generate concrete improvement opportunities from patterns."""
        opps = []

        # Opportunity 1: Agent with high failure rate → skill/checklist suggestion
        for bp in report.bottlenecks:
            if bp["failure_rate"] >= 0.3:
                opps.append({
                    "type": "add_checklist",
                    "target_agent": bp["agent"],
                    "reason": f"失败率 {bp['failure_rate']:.0%} ({bp['failed']}/{bp['total']} 任务失败)",
                    "suggestion": f"为 {bp['agent']} 增加任务前检查清单，减少常见失败",
                    "confidence": min(0.9, bp["failure_rate"] + 0.2),
                    "priority": "high" if bp["failure_rate"] > 0.4 else "medium",
                })

        # Opportunity 2: Keyword patterns → prompt optimization
        for pattern in report.failure_patterns:
            if pattern.get("type") == "keyword_analysis":
                keywords = pattern.get("top_keywords", [])
                for kw_info in keywords[:3]:
                    opps.append({
                        "type": "prompt_optimization",
                        "target_agent": "all",
                        "reason": f"关键词 '{kw_info['keyword']}' 出现在 {kw_info['count']} 次失败中",
                        "suggestion": f"在 Agent System Prompt 中增加关于 {kw_info['keyword']} 的注意事项",
                        "confidence": min(0.85, kw_info["count"] / 20 + 0.5),
                        "priority": "medium" if kw_info["count"] >= 3 else "low",
                    })

        # Opportunity 3: Low reputation agents → retraining/guidance
        for name, stats in report.agent_stats.items():
            if stats["total_tasks"] >= 5 and stats["success_rate"] < 0.6:
                opps.append({
                    "type": "agent_guidance",
                    "target_agent": name,
                    "reason": f"声誉过低: tier={stats['tier']}, success_rate={stats['success_rate']:.0%}",
                    "suggestion": f"考虑为 {name} 增加更多 System Prompt 指导或限制其执行复杂任务",
                    "confidence": 0.75,
                    "priority": "high" if stats["success_rate"] < 0.4 else "medium",
                })

        return opps

    def _summarize(self, report: PatternReport) -> str:
        parts = []
        patterns = [p for p in report.failure_patterns if p.get("agent")]
        if patterns:
            worst = patterns[0]
            parts.append(
                f"最主要失败模式: {worst['agent']} ({worst['count']} 次)。"
            )
        if report.bottlenecks:
            worst_bn = report.bottlenecks[0]
            parts.append(
                f"瓶颈: {worst_bn['agent']} 失败率 {worst_bn['failure_rate']:.0%}。"
            )
        if report.opportunities:
            high_pri = [o for o in report.opportunities if o["priority"] == "high"]
            parts.append(f"发现 {len(report.opportunities)} 个优化机会 ({len(high_pri)} 高优先级)。")
        return " ".join(parts) if parts else "系统运行正常，未发现显著模式。"

    def _compute_health(self, report: PatternReport) -> str:
        scores = [s["reputation_score"] for s in report.agent_stats.values() if s["total_tasks"] >= 3]
        if not scores:
            return "healthy"
        avg = sum(scores) / len(scores)
        if avg < 0.5:
            return "critical"
        if avg < 0.65:
            return "warning"
        return "healthy"

    def get_last_report(self) -> PatternReport | None:
        return self._last_report


# Global singleton
_analyzer: ExperienceAnalyzer | None = None


def get_experience_analyzer() -> ExperienceAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ExperienceAnalyzer()
    return _analyzer
