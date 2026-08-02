"""Personal AI OS Kernel — Skill Router (Sprint 6.5)

Matches task requirements to available skills using capability + rating scoring.

ADR-007 compliant:
  ✅ Capability-based matching with skill-level rating weighting
  ✅ Prerequisite chain resolution
  ✅ Agent → skill recommendation engine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillMatch:
    """A scored match between a task requirement and a skill."""
    skill_name: str
    display_name: str
    score: float                   # 0.0–1.0
    capability_match: float        # How well capabilities match
    rating_weight: float           # Skill's reputation contribution
    agent_name: str = ""           # Agent that has this skill
    agent_available: bool = True   # Is the agent available?


@dataclass
class SkillPlan:
    """A plan for which skills to use for a task."""
    task: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    matches: list[SkillMatch] = field(default_factory=list)
    recommended_agent: str = ""
    prerequisite_chain: list[str] = field(default_factory=list)
    confidence: float = 0.5


class SkillRouter:
    """Routes task requirements to the best skills and agents.

    Layer between:
      - task_graph (what to do)
      - skill_registry (what skills exist)
      - agent_registry (who has those skills)
    """

    def __init__(self):
        pass

    def match(self, required_capabilities: list[str], preferred_agent: str = "",
              max_results: int = 5) -> SkillPlan:
        """Find the best skills matching required capabilities.

        Scoring:
          capability_match = |my_caps ∩ required| / |required|
          final_score = 0.6 × capability_match + 0.4 × skill_rating
        """
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        required_set = set(required_capabilities)
        matches: list[SkillMatch] = []

        for skill in registry.list_all():
            skill_caps = set(skill.capabilities)
            if not skill_caps & required_set:
                continue  # No overlap at all

            cap_match = len(skill_caps & required_set) / max(len(required_set), 1)
            rating = skill.rating.reputation_score
            score = round(0.6 * cap_match + 0.4 * rating, 3)

            # Find agents that have this skill
            agents = registry.get_agents_for_skill(skill.name)
            agent_name = agents[0] if agents else ""

            # If preferred_agent specified, boost its skills
            if preferred_agent and skill.name in registry.get_agent_skill_names(preferred_agent):
                score = min(1.0, score + 0.1)

            matches.append(SkillMatch(
                skill_name=skill.name,
                display_name=skill.display_name,
                score=score,
                capability_match=cap_match,
                rating_weight=rating,
                agent_name=agent_name,
                agent_available=bool(agents),
            ))

        matches.sort(key=lambda m: m.score, reverse=True)
        top_matches = matches[:max_results]

        # Determine recommended agent
        agent_scores: dict[str, float] = {}
        for m in top_matches:
            if m.agent_name:
                agent_scores[m.agent_name] = agent_scores.get(m.agent_name, 0) + m.score

        best_agent = max(agent_scores, key=agent_scores.get) if agent_scores else "ceo"
        if preferred_agent and preferred_agent in agent_scores:
            best_agent = preferred_agent

        # Build prerequisite chain
        prereq_chain = self._resolve_prerequisites(
            [m.skill_name for m in top_matches[:3]]
        )

        confidence = sum(m.score for m in top_matches[:3]) / max(len(top_matches[:3]), 1) if top_matches else 0.3

        return SkillPlan(
            task="",
            required_capabilities=required_capabilities,
            matches=top_matches,
            recommended_agent=best_agent,
            prerequisite_chain=prereq_chain,
            confidence=round(confidence, 3),
        )

    def _resolve_prerequisites(self, skill_names: list[str]) -> list[str]:
        """Resolve the full prerequisite chain for a set of skills.

        Returns the complete ordered list of skills needed,
        with prerequisites before dependent skills.
        """
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        resolved: list[str] = []
        seen: set[str] = set()

        def resolve(name: str):
            if name in seen:
                return
            skill = registry.get_by_name(name)
            if not skill:
                return
            for prereq in skill.prerequisites:
                resolve(prereq)
            seen.add(name)
            resolved.append(name)

        for sn in skill_names:
            resolve(sn)

        return resolved

    def recommend_skills_for_agent(self, agent_name: str, task_capabilities: list[str]) -> list[dict]:
        """Recommend which of the agent's existing skills to use for a task.

        Also identifies skill gaps: capabilities the agent can't cover.
        """
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        agent_skills = registry.get_agent_skills(agent_name)
        required_set = set(task_capabilities)

        covered: list[dict] = []
        uncovered: list[str] = list(required_set)

        for skill in agent_skills:
            skill_caps = set(skill.capabilities)
            overlap = skill_caps & required_set
            if overlap:
                covered.append({
                    "skill": skill.name,
                    "display_name": skill.display_name,
                    "covers": list(overlap),
                    "rating": skill.rating.to_dict(),
                })
                for c in overlap:
                    if c in uncovered:
                        uncovered.remove(c)

        # Find skills from other agents that could fill gaps
        gap_fillers: list[dict] = []
        for cap in uncovered:
            matching = registry.list_by_capability(cap)
            for skill in matching:
                agents = registry.get_agents_for_skill(skill.name)
                if agent_name not in agents:  # Don't recommend own skills
                    gap_fillers.append({
                        "capability": cap,
                        "skill": skill.name,
                        "available_on": agents,
                    })

        return {
            "agent": agent_name,
            "covered": covered,
            "gaps": uncovered,
            "gap_fillers": gap_fillers,
            "coverage_pct": round(
                (len(task_capabilities) - len(uncovered)) / max(len(task_capabilities), 1) * 100, 1
            ),
        }

    def get_best_agent_for_task(self, task_capabilities: list[str]) -> dict:
        """Find the best agent to handle a task, based on their skill composition."""
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        required_set = set(task_capabilities)
        agent_scores: dict[str, dict] = {}

        for agent_name in registry._agent_skills:
            skills = registry.get_agent_skills(agent_name)
            if not skills:
                continue

            total_cap_coverage = 0
            total_rating = 0.0
            matched_caps: set[str] = set()

            for skill in skills:
                skill_caps = set(skill.capabilities)
                overlap = skill_caps & required_set
                if overlap:
                    total_cap_coverage += len(overlap)
                    total_rating += skill.rating.reputation_score
                    matched_caps.update(overlap)

            coverage = len(matched_caps) / max(len(required_set), 1)
            avg_rating = total_rating / max(len(skills), 1)
            score = round(0.6 * coverage + 0.4 * avg_rating, 3)

            agent_scores[agent_name] = {
                "agent": agent_name,
                "score": score,
                "capability_coverage": round(coverage, 3),
                "avg_skill_rating": round(avg_rating, 3),
                "matched_capabilities": list(matched_caps),
                "skill_count": len(skills),
            }

        ranked = sorted(agent_scores.values(), key=lambda x: x["score"], reverse=True)
        return {
            "task_capabilities": task_capabilities,
            "best_agent": ranked[0] if ranked else None,
            "all_candidates": ranked[:5],
        }


# Global singleton
_router: SkillRouter | None = None


def get_skill_router() -> SkillRouter:
    global _router
    if _router is None:
        _router = SkillRouter()
    return _router
