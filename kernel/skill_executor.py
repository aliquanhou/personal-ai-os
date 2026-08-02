# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Skill Executor (Sprint 6.5)

Injects skill prompts into AgentContext at runtime. The bridge between
the skill system and the agent execution loop.

ADR-007 compliant:
  ✅ Agent System Prompt = base role + aggregated skill prompt fragments
  ✅ Skill prompts compiled once per agent, cached
  ✅ Per-skill rating tracked after each execution
  ✅ Skill prerequisite validation before execution
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Skill information injected into an Agent's execution context."""
    agent_name: str = ""
    active_skills: list[str] = field(default_factory=list)
    skill_prompt: str = ""            # Compiled skill prompt fragment
    skill_capabilities: list[str] = field(default_factory=list)  # Aggregated capabilities
    skill_tools: list[str] = field(default_factory=list)  # Aggregated recommended tools


class SkillExecutor:
    """Prepares and injects skill context into agent execution.

    Called by AgentRuntime before agent.run() — it modifies the
    AgentContext to include skill prompts and capability metadata.
    """

    def __init__(self):
        self._prompt_cache: dict[str, str] = {}  # agent_name → compiled prompt

    def prepare(self, agent_name: str, task_capabilities: list[str] | None = None,
                force_skills: list[str] | None = None) -> SkillContext:
        """Prepare skill context for an agent execution.

        Args:
            agent_name: Which agent is about to run
            task_capabilities: What capabilities the task needs (filters skills)
            force_skills: Override — use exactly these skills

        Returns:
            SkillContext with compiled prompt and metadata
        """
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()

        if force_skills:
            # Use exactly these skills
            skill_names = force_skills
        elif task_capabilities:
            # Filter agent's skills to those matching the task
            agent_skills = registry.get_agent_skills(agent_name)
            task_set = set(task_capabilities)
            skill_names = [
                s.name for s in agent_skills
                if set(s.capabilities) & task_set
            ]
            if not skill_names:
                # If no direct match, use all agent skills as fallback
                skill_names = [s.name for s in agent_skills]
        else:
            # Use all assigned skills
            skill_names = registry.get_agent_skill_names(agent_name)

        # Compile prompt (with caching)
        cache_key = f"{agent_name}:{','.join(sorted(skill_names))}"
        if cache_key in self._prompt_cache:
            skill_prompt = self._prompt_cache[cache_key]
        else:
            skill_prompt = self._compile_prompt(agent_name, skill_names)
            self._prompt_cache[cache_key] = skill_prompt

        # Aggregate capabilities from selected skills
        all_caps: list[str] = []
        all_tools: list[str] = []
        for sn in skill_names:
            skill = registry.get_by_name(sn)
            if skill:
                for cap in skill.capabilities:
                    if cap not in all_caps:
                        all_caps.append(cap)
                for tool in skill.recommended_tools:
                    if tool not in all_tools:
                        all_tools.append(tool)

        # Validate prerequisites
        unmet = self._check_prerequisites(skill_names)
        if unmet:
            logger.warning("Agent %s missing prerequisites: %s", agent_name, unmet)

        return SkillContext(
            agent_name=agent_name,
            active_skills=skill_names,
            skill_prompt=skill_prompt,
            skill_capabilities=all_caps,
            skill_tools=all_tools,
        )

    def _compile_prompt(self, agent_name: str, skill_names: list[str]) -> str:
        """Compile skill prompt fragments for an agent."""
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()

        if not skill_names:
            return ""

        parts = ["## 🎯 激活的专业技能\n"]
        for i, sn in enumerate(skill_names, 1):
            skill = registry.get_by_name(sn)
            if not skill:
                continue
            parts.append(f"### {skill.display_name}")
            parts.append(f"等级: {skill.rating.tier} | 难度: {skill.difficulty}")
            parts.append(skill.prompt_fragment)
            parts.append("")

        return "\n".join(parts)

    def _check_prerequisites(self, skill_names: list[str]) -> list[str]:
        """Check for unmet prerequisites. Returns list of missing skill names."""
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        unmet = []
        for sn in skill_names:
            skill = registry.get_by_name(sn)
            if not skill:
                continue
            for prereq in skill.prerequisites:
                if prereq not in skill_names:
                    unmet.append(f"{sn} requires {prereq}")
        return unmet

    def inject_into_context(self, agent_name: str, base_system_prompt: str,
                            task_capabilities: list[str] | None = None) -> str:
        """Build the full system prompt: base role + skill fragments.

        This is the method AgentRuntime calls to get the agent's complete prompt.

        Args:
            agent_name: The agent's name
            base_system_prompt: The agent's role prompt (from agent.system_prompt())
            task_capabilities: Optional filter for relevant skills

        Returns:
            Complete system prompt with skills injected
        """
        ctx = self.prepare(agent_name, task_capabilities)

        if not ctx.skill_prompt:
            return base_system_prompt

        # Insert skill prompt after the first paragraph of the base prompt
        # (so the role intro comes first, then skills)
        return f"{base_system_prompt}\n\n{ctx.skill_prompt}"

    def record_execution(self, agent_name: str, success: bool, duration_ms: float,
                        skill_names: list[str] | None = None) -> None:
        """Record skill usage after agent execution for rating updates.

        Called by AgentRuntime after agent.run() completes.
        """
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()

        if skill_names is None:
            skill_names = registry.get_agent_skill_names(agent_name)

        for sn in skill_names:
            registry.record_skill_use(sn, success, duration_ms)

    def invalidate_cache(self, agent_name: str = "") -> None:
        """Clear prompt cache. Call after skill definitions change."""
        if agent_name:
            keys = [k for k in self._prompt_cache if k.startswith(agent_name)]
            for k in keys:
                del self._prompt_cache[k]
        else:
            self._prompt_cache.clear()

    def get_agent_capability_summary(self, agent_name: str) -> dict:
        """Get a summary of what an agent can do, based on skill composition."""
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        skills = registry.get_agent_skills(agent_name)

        all_caps: list[str] = []
        all_tools: list[str] = []
        for s in skills:
            for c in s.capabilities:
                if c not in all_caps:
                    all_caps.append(c)
            for t in s.recommended_tools:
                if t not in all_tools:
                    all_tools.append(t)

        return {
            "agent": agent_name,
            "skill_count": len(skills),
            "total_capabilities": len(all_caps),
            "capabilities": all_caps,
            "tools": all_tools,
            "strongest_skill": max(skills, key=lambda s: s.rating.reputation_score).name if skills else "",
            "weakest_skill": min(skills, key=lambda s: s.rating.reputation_score).name if skills else "",
        }


# Global singleton
_executor: SkillExecutor | None = None


def get_skill_executor() -> SkillExecutor:
    global _executor
    if _executor is None:
        _executor = SkillExecutor()
    return _executor
