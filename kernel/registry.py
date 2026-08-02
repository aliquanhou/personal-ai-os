"""Personal AI OS Kernel — Agent Registry (Sprint 3)

Formal agent registration system. Each agent declares:
  - capabilities: what it can do (tags + descriptions)
  - permissions: what it's allowed to touch
  - memory_scope: what parts of memory it accesses

Plugin-style: wraps existing BaseAgent instances.
Does NOT modify agents/runtime.py internals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Capability Taxonomy ─────────────────────────────────

class Capability(StrEnum):
    """Standard capability tags. Every agent declares which ones it has."""
    # Analysis
    RESEARCH = "research"               # Market/user/competitive research
    ANALYSIS = "analysis"               # Data analysis, pattern recognition
    STRATEGY = "strategy"               # Strategic planning, decision support

    # Creation
    CODE_GENERATION = "code_generation"  # Write new code
    CODE_REVIEW = "code_review"          # Review existing code
    CODE_DEBUG = "code_debug"            # Debug and fix code
    WRITING = "writing"                  # Write documents, articles, reports
    DESIGN = "design"                    # UI/UX design, architecture

    # Execution
    PROJECT_PLANNING = "project_planning"  # Break goals into tasks
    TASK_EXECUTION = "task_execution"     # Execute predefined tasks
    FILE_OPS = "file_ops"                # File read/write/list
    SHELL_EXEC = "shell_exec"            # Run shell commands
    WEB_SEARCH = "web_search"            # Search the internet

    # Memory & Learning
    MEMORY_READ = "memory_read"          # Read from personal memory
    MEMORY_WRITE = "memory_write"        # Write to personal memory
    REFLECTION = "reflection"            # Post-task analysis and learning
    BRIEFING = "briefing"                # Generate daily briefings

    # Coordination
    ORCHESTRATION = "orchestration"      # Coordinate multiple agents
    TASK_ROUTING = "task_routing"         # Route tasks to specialists
    DECISION_MAKING = "decision_making"   # Make strategic decisions


# ── Permission Levels ───────────────────────────────────

class Permission(StrEnum):
    """What an agent is allowed to do."""
    READ_WORKSPACE = "read_workspace"      # Read project files
    WRITE_WORKSPACE = "write_workspace"    # Create/modify project files
    DELETE_WORKSPACE = "delete_workspace"  # Delete project files
    EXEC_SHELL_SAFE = "exec_shell_safe"    # Safe shell commands (ls, cat, etc.)
    EXEC_SHELL_FULL = "exec_shell_full"    # Any shell command
    MEMORY_READ = "memory_read"            # Read personal memory
    MEMORY_WRITE = "memory_write"          # Write to personal memory
    MEMORY_DELETE = "memory_delete"        # Delete memory entries
    MANAGE_AGENTS = "manage_agents"       # Register/unregister agents
    SYSTEM_CONFIG = "system_config"        # Modify system configuration
    EXTERNAL_NETWORK = "external_network"   # Access internet


# ── Memory Scope ────────────────────────────────────────

class MemoryScope(StrEnum):
    """Which memory partitions an agent can access."""
    PROFILE = "profile"           # User identity & preferences
    GOALS = "goals"               # Active goals & progress
    KNOWLEDGE = "knowledge"       # General knowledge base
    DECISIONS = "decisions"       # Past decisions
    EXPERIENCES = "experiences"   # Lessons learned
    CONVERSATIONS = "conversations"  # Chat history
    PROJECTS = "projects"         # Project metadata
    TASKS = "tasks"               # Task state machine
    ALL = "all"                   # Everything


# ── Agent Descriptor ────────────────────────────────────

@dataclass
class AgentDescriptor:
    """Formal description of an agent's capabilities, permissions, and scope.

    This wraps an existing BaseAgent instance — it's a plugin layer,
    not a replacement for BaseAgent.
    """
    name: str
    description: str
    capabilities: list[Capability] = field(default_factory=list)
    permissions: list[Permission] = field(default_factory=list)
    memory_scope: list[MemoryScope] = field(default_factory=list)
    # Metadata
    tier: str = "specialist"  # ceo / manager / specialist / utility
    input_formats: list[str] = field(default_factory=list)  # e.g. ["goal", "task", "code"]
    output_formats: list[str] = field(default_factory=list)  # e.g. ["plan", "code", "report"]
    # The actual agent instance (from agents/)
    agent_ref: Any = None  # BaseAgent instance

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "permissions": [p.value for p in self.permissions],
            "memory_scope": [s.value for s in self.memory_scope],
            "tier": self.tier,
            "input_formats": self.input_formats,
            "output_formats": self.output_formats,
        }

    def match_score(self, required_capabilities: list[Capability]) -> float:
        """How well does this agent match a set of required capabilities?

        Returns 0.0 to 1.0. Exact matches score 1.0.
        """
        if not required_capabilities:
            return 0.5
        my_caps = set(self.capabilities)
        needed = set(required_capabilities)
        hits = len(my_caps & needed)
        if hits == 0:
            return 0.0
        # Weight: more required caps matched = higher score
        return hits / len(needed)


# ── Agent Registry ───────────────────────────────────────

class AgentRegistry:
    """Central registry for the Agent Organization Layer.

    Manages agent descriptors and provides capability-based lookup.
    Layers on top of agents.runtime.AgentRuntime — doesn't replace it.
    """

    def __init__(self):
        self._descriptors: dict[str, AgentDescriptor] = {}
        self._team_configs: dict[str, list[str]] = {}  # team_name → [agent_names]

    def register(self, descriptor: AgentDescriptor) -> None:
        """Register an agent descriptor."""
        self._descriptors[descriptor.name] = descriptor
        logger.info(
            "Registered agent: %s [%s] caps=%s",
            descriptor.name, descriptor.tier,
            [c.value for c in descriptor.capabilities],
        )

    def unregister(self, name: str) -> None:
        """Remove an agent descriptor."""
        self._descriptors.pop(name, None)

    def get(self, name: str) -> AgentDescriptor | None:
        """Get a descriptor by name."""
        return self._descriptors.get(name)

    def list_all(self) -> list[AgentDescriptor]:
        """List all registered descriptors."""
        return list(self._descriptors.values())

    def list_by_tier(self, tier: str) -> list[AgentDescriptor]:
        """List agents by tier (ceo/manager/specialist/utility)."""
        return [d for d in self._descriptors.values() if d.tier == tier]

    def find_by_capability(self, capability: Capability) -> list[AgentDescriptor]:
        """Find all agents with a specific capability."""
        return [d for d in self._descriptors.values() if capability in d.capabilities]

    def match_team(self, required_capabilities: list[Capability],
                   max_agents: int = 5) -> list[AgentDescriptor]:
        """Find the best agent(s) matching a set of required capabilities.

        Returns agents sorted by match score (best first).
        """
        scored = []
        for desc in self._descriptors.values():
            score = desc.match_score(required_capabilities)
            if score > 0:
                scored.append((score, desc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [desc for _, desc in scored[:max_agents]]

    def define_team(self, team_name: str, agent_names: list[str]) -> None:
        """Define a reusable team configuration."""
        self._team_configs[team_name] = agent_names

    def get_team(self, team_name: str) -> list[AgentDescriptor]:
        """Get agents in a named team."""
        names = self._team_configs.get(team_name, [])
        return [self._descriptors[n] for n in names if n in self._descriptors]

    def list_teams(self) -> list[str]:
        """List available team configurations."""
        return list(self._team_configs.keys())

    def build_default_teams(self) -> None:
        """Build the default team configurations."""
        # Product Development Team
        self.define_team("product_dev", [
            "ceo", "project_manager", "research_agent",
            "coding_agent", "reflection_agent",
        ])
        # Quick Code Team (minimal)
        self.define_team("quick_code", [
            "ceo", "coding_agent",
        ])
        # Research Team
        self.define_team("research", [
            "ceo", "research_agent", "writing_agent", "reflection_agent",
        ])
        # Full Team (everyone)
        self.define_team("full_team", list(self._descriptors.keys()))


# Global singleton
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
