"""Personal AI OS — Skill Benchmark Runner v0.1

Evaluates Skill Router accuracy, rating stability, and gap detection
without modifying any kernel code. Runs purely against existing APIs.

Usage:
  python tests/benchmark/runner.py           # Run all cases
  python tests/benchmark/runner.py --report  # Generate HTML report
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CaseResult:
    """Result of a single benchmark case."""
    case_id: str = ""
    category: str = ""
    passed: bool = False
    # Router check
    actual_agent: str = ""
    expected_agent: str = ""
    agent_match: bool = False
    # Skill check
    actual_skills: list[str] = field(default_factory=list)
    expected_skills: list[str] = field(default_factory=list)
    skills_hit: int = 0
    skills_miss: int = 0
    skill_precision: float = 0.0  # hits / (hits + misses against expected)
    # Confidence
    confidence: float = 0.0
    # Gap check
    gap_detected: bool = False
    gap_expected: bool = False
    gap_correct: bool = False
    # Timing
    duration_ms: float = 0.0
    # Detail
    note: str = ""
    error: str = ""


@dataclass
class BenchmarkReport:
    """Aggregated benchmark results."""
    timestamp: str = ""
    total_cases: int = 0
    passed: int = 0
    failed: int = 0

    # Router accuracy
    router_accuracy: float = 0.0       # correct agent predictions
    skill_precision_avg: float = 0.0   # average skill hit rate
    confidence_avg: float = 0.0        # average router confidence
    gap_detection_accuracy: float = 0.0  # correct gap detection rate

    # Per-category breakdown
    by_category: dict = field(default_factory=dict)

    # Per-skill rating
    skill_ratings: list[dict] = field(default_factory=list)
    rating_evolution: dict = field(default_factory=dict)

    # Detailed results
    results: list[dict] = field(default_factory=list)

    # Summary
    summary: str = ""
    recommendation: str = ""


class SkillBenchmark:
    """Runs benchmark cases against the Skill system without modifying kernel."""

    def __init__(self):
        self._cases: list[dict] = []
        self._results: list[CaseResult] = []

    def load_cases(self, path: str = "") -> list[dict]:
        """Load test cases from JSON."""
        path = path or str(Path(__file__).parent / "cases.json")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self._cases = data.get("cases", [])
        return self._cases

    def run_all(self) -> BenchmarkReport:
        """Run all loaded cases and produce a report."""
        if not self._cases:
            self.load_cases()

        self._results = []
        for case in self._cases:
            result = self._run_case(case)
            self._results.append(result)

        return self._build_report()

    def _run_case(self, case: dict) -> CaseResult:
        """Execute a single benchmark case through the Skill Router."""
        start = time.time()
        result = CaseResult(
            case_id=case.get("id", "?"),
            category=case.get("category", "?"),
            expected_agent=case.get("expected_agent", ""),
            expected_skills=case.get("expected_skills", []),
            gap_expected=case.get("expect_gap", False),
            note=case.get("note", ""),
        )

        try:
            from kernel.skill_router import get_skill_router
            from kernel.skill_registry import get_skill_registry

            router = get_skill_router()
            registry = get_skill_registry()

            required_caps = case.get("required_capabilities", [])

            if not required_caps and not case.get("input"):
                # Edge case: empty input
                result.passed = True
                result.duration_ms = (time.time() - start) * 1000
                return result

            if not required_caps:
                # No capabilities to match
                result.passed = True
                result.duration_ms = (time.time() - start) * 1000
                return result

            # ── Router match ──
            plan = router.match(required_caps)
            result.actual_agent = plan.recommended_agent
            result.actual_skills = [m.skill_name for m in plan.matches]
            result.confidence = plan.confidence

            # ── Check agent match ──
            if result.expected_agent:
                result.agent_match = result.actual_agent == result.expected_agent

            # ── Check skill match ──
            if result.expected_skills:
                actual_set = set(result.actual_skills)
                expected_set = set(result.expected_skills)
                result.skills_hit = len(actual_set & expected_set)
                result.skills_miss = len(expected_set - actual_set)
                result.skill_precision = (
                    result.skills_hit / max(len(expected_set), 1)
                )

            # ── Gap detection ──
            if case.get("deficient_agent"):
                gap_analysis = router.recommend_skills_for_agent(
                    case["deficient_agent"], required_caps
                )
                result.gap_detected = len(gap_analysis.get("gaps", [])) > 0
                result.gap_correct = result.gap_detected == result.gap_expected
                if result.gap_expected:
                    result.gap_correct = result.gap_detected  # should detect gap

            # ── Determine pass/fail ──
            checks = []
            if result.expected_agent:
                checks.append(result.agent_match)
            if result.expected_skills:
                checks.append(result.skills_hit >= max(1, len(result.expected_skills) // 2))
            if result.gap_expected:
                checks.append(result.gap_correct)
            result.passed = all(checks) if checks else (result.actual_agent != "")

        except Exception as e:
            result.error = str(e)
            result.passed = False

        result.duration_ms = (time.time() - start) * 1000
        return result

    def simulate_rating_evolution(self, iterations: int = 100) -> dict:
        """Simulate skill rating changes over many uses.

        Without calling LLMs — this is a pure mathematical simulation.
        Each skill gets simulated success/failure based on its current tier.
        """
        from kernel.skill_registry import get_skill_registry
        registry = get_skill_registry()

        evolution: dict[str, list[dict]] = {}
        snapshot_every = max(1, iterations // 10)

        # Record baseline
        for skill in registry.list_all():
            evolution[skill.name] = [{
                "iteration": 0,
                "success_rate": skill.rating.success_rate,
                "reputation_score": skill.rating.reputation_score,
                "tier": skill.rating.tier,
            }]

        # Simulate based on skill category tiers
        tier_probs = {
            "S": 0.95, "A": 0.88, "B": 0.78, "C": 0.65, "D": 0.45,
        }

        for i in range(1, iterations + 1):
            for skill_name in list(evolution.keys()):
                skill = registry.get_by_name(skill_name)
                if not skill:
                    continue
                current_tier = skill.rating.tier
                success_prob = tier_probs.get(current_tier, 0.65)
                # Add some noise
                import random
                success = random.random() < success_prob
                duration = random.uniform(2000, 12000)

                registry.record_skill_use(skill_name, success, duration)

                if i % snapshot_every == 0:
                    evolution[skill_name].append({
                        "iteration": i,
                        "success_rate": round(skill.rating.success_rate, 3),
                        "reputation_score": skill.rating.reputation_score,
                        "tier": skill.rating.tier,
                    })

        return evolution

    def _build_report(self) -> BenchmarkReport:
        """Aggregate results into a structured report."""
        report = BenchmarkReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_cases=len(self._results),
            passed=sum(1 for r in self._results if r.passed),
            failed=sum(1 for r in self._results if not r.passed),
        )

        # Router accuracy: correct agent predictions
        agent_cases = [r for r in self._results if r.expected_agent]
        if agent_cases:
            report.router_accuracy = sum(1 for r in agent_cases if r.agent_match) / len(agent_cases)

        # Skill precision
        skill_cases = [r for r in self._results if r.expected_skills]
        if skill_cases:
            report.skill_precision_avg = sum(r.skill_precision for r in skill_cases) / len(skill_cases)

        # Confidence
        confidences = [r.confidence for r in self._results if r.confidence > 0]
        if confidences:
            report.confidence_avg = sum(confidences) / len(confidences)

        # Gap detection
        gap_cases = [r for r in self._results if r.gap_expected]
        if gap_cases:
            report.gap_detection_accuracy = sum(1 for r in gap_cases if r.gap_correct) / len(gap_cases)

        # By category
        for cat in set(r.category for r in self._results):
            cat_results = [r for r in self._results if r.category == cat]
            report.by_category[cat] = {
                "total": len(cat_results),
                "passed": sum(1 for r in cat_results if r.passed),
                "router_accuracy": sum(1 for r in cat_results if r.agent_match) / max(
                    sum(1 for r in cat_results if r.expected_agent), 1
                ),
            }

        # Current skill ratings
        from kernel.skill_registry import get_skill_registry
        report.skill_ratings = get_skill_registry().get_skill_ratings()

        # Detailed results
        report.results = [
            {
                "id": r.case_id,
                "category": r.category,
                "passed": r.passed,
                "agent": f"{r.actual_agent} (expected: {r.expected_agent})",
                "agent_match": r.agent_match,
                "skills_hit": r.skills_hit,
                "skills_miss": r.skills_miss,
                "skill_precision": round(r.skill_precision, 2),
                "confidence": round(r.confidence, 3),
                "gap_correct": r.gap_correct,
                "note": r.note[:80],
                "error": r.error[:80] if r.error else "",
            }
            for r in self._results
        ]

        # Summary
        pct = report.router_accuracy * 100
        report.summary = (
            f"Benchmark complete: {report.passed}/{report.total_cases} passed. "
            f"Router accuracy: {pct:.0f}%. "
            f"Skill precision: {report.skill_precision_avg:.0%}. "
            f"Gap detection: {report.gap_detection_accuracy:.0%}."
        )

        target = 0.70
        if report.router_accuracy >= target:
            report.recommendation = (
                f"✅ Router accuracy {pct:.0f}% meets target ({target:.0%}). "
                "System is ready for real-world use."
            )
        elif report.router_accuracy >= target - 0.15:
            report.recommendation = (
                f"⚠️ Router accuracy {pct:.0f}% is close to target ({target:.0%}). "
                "Consider adding more capability keywords to skill definitions."
            )
        else:
            report.recommendation = (
                f"❌ Router accuracy {pct:.0f}% is below target ({target:.0%}). "
                "Skill capability matching needs improvement before production use."
            )

        return report


def run_benchmark() -> BenchmarkReport:
    """Convenience function: load cases, run all, return report."""
    bench = SkillBenchmark()
    bench.load_cases()
    return bench.run_all()
