"""Personal AI OS Kernel — Agent Router (Sprint 3)

Intelligent task-to-agent routing with LLM-powered analysis.

Flow:
  User Goal
     │
     ▼
  Router.analyze(goal)       ← LLM analyzes goal
     │
     ▼
  Router.plan(analysis)      ← Builds TaskGraph
     │
     ▼
  Router.dispatch(graph)     ← Routes tasks to agents
     │
     ▼
  Router.execute(graph)      ← Sequential/parallel execution
     │
     ▼
  Memory + Reflection        ← Post-execution learning

Layers on top of:
  - kernel.registry.AgentRegistry (agent capabilities)
  - kernel.task_graph.TaskGraph (DAG-based tasks)
  - agents.runtime.AgentRuntime (existing execution engine)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from kernel.registry import (
    AgentDescriptor,
    AgentRegistry,
    Capability,
    get_agent_registry,
)
from kernel.task_graph import (
    NodeState,
    TaskGraph,
    TaskGraphStore,
    TaskNode,
    get_task_graph_store,
)

logger = logging.getLogger(__name__)


# ── Domain-specific capability mapping ──────────────────

# Map task types to required capabilities for routing
TASK_CAPABILITY_MAP: dict[str, list[Capability]] = {
    "research": [Capability.RESEARCH, Capability.ANALYSIS],
    "market_analysis": [Capability.RESEARCH, Capability.ANALYSIS, Capability.STRATEGY],
    "planning": [Capability.PROJECT_PLANNING, Capability.STRATEGY],
    "coding": [Capability.CODE_GENERATION, Capability.FILE_OPS],
    "code_review": [Capability.CODE_REVIEW],
    "debug": [Capability.CODE_DEBUG, Capability.CODE_GENERATION],
    "writing": [Capability.WRITING, Capability.FILE_OPS],
    "design": [Capability.DESIGN, Capability.WRITING],
    "testing": [Capability.CODE_GENERATION, Capability.SHELL_EXEC],
    "reflection": [Capability.REFLECTION, Capability.MEMORY_WRITE],
    "briefing": [Capability.BRIEFING, Capability.MEMORY_READ],
    "orchestration": [Capability.ORCHESTRATION, Capability.DECISION_MAKING],
}


@dataclass
class RoutePlan:
    """A completed routing plan — the output of the Router."""
    goal: str
    analysis: str = ""
    graph: TaskGraph | None = None
    agent_assignments: dict[str, str] = field(default_factory=dict)  # node_id → agent_name
    execution_order: list[str] = field(default_factory=list)  # node IDs
    estimated_duration: str = ""


class AgentRouter:
    """Routes goals to agent teams using capability matching + LLM planning.

    This is the central coordinator. It:
    1. Analyzes the goal using LLM
    2. Builds a task graph with dependencies
    3. Matches tasks to agents by capability
    4. Orchestrates sequential execution through existing Runtime
    """

    def __init__(self):
        self.registry: AgentRegistry = get_agent_registry()
        self.store: TaskGraphStore = get_task_graph_store()

    async def plan(self, goal: str, profile: dict | None = None) -> RoutePlan:
        """Analyze a goal and produce a RoutePlan without executing.

        Uses LLM to:
        1. Understand the goal's domain and complexity
        2. Decompose into tasks with dependencies
        3. Match tasks to available agents

        Returns a RoutePlan — doesn't execute anything.
        """
        # Step 1: Categorize the goal and identify required capabilities
        # Build the analysis prompt
        analysis_prompt = self._build_analysis_prompt(goal, profile)

        # Step 2: Call LLM to analyze and decompose
        try:
            from kernel.llm_router import get_llm_router
            llm = get_llm_router()
            response = await llm.chat([
                {"role": "system", "content": "你是一个项目规划专家。分析用户目标，输出JSON格式的任务分解。只输出JSON，不要其他文字。"},
                {"role": "user", "content": analysis_prompt},
            ], temperature=0.3, max_tokens=2000)
            analysis = response.get("content", "")
        except Exception as e:
            logger.warning("LLM analysis failed: %s, using best-effort routing", e)
            analysis = ""

        # Step 3: Build TaskGraph from LLM analysis
        graph = self._build_task_graph(goal, analysis)

        # Step 3: Assign agents to nodes
        assignments = self._assign_agents(graph)

        # Step 4: Determine execution order
        exec_order = [n.id for n in graph.topological_order()]

        return RoutePlan(
            goal=goal,
            analysis=analysis,
            graph=graph,
            agent_assignments=assignments,
            execution_order=exec_order,
            estimated_duration=self._estimate_duration(graph),
        )

    async def execute_plan(self, plan: RoutePlan, session_id: str = "",
                           project_slug: str = "") -> dict:
        """Execute a RoutePlan by running each task through the assigned agent.

        Tasks execute in topological order. Independent tasks at same depth
        could run in parallel (future: use asyncio.gather for that).
        """
        from agents.runtime import AgentContext, get_agent_runtime

        runtime = get_agent_runtime()
        results: dict[str, dict] = {}

        if not plan.graph:
            return {"error": "No graph in plan", "results": results}

        graph = plan.graph

        # Execute nodes in topological order
        for node in graph.topological_order():
            node.state = NodeState.RUNNING
            agent_name = plan.agent_assignments.get(node.id, "ceo")

            # Build task context
            goal_context = node.description or node.title
            # Add dependency context
            dep_contexts = []
            for dep_id in node.dependencies:
                if dep_id in results and results[dep_id].get("output"):
                    dep_contexts.append(f"- {graph.nodes[dep_id].title}: {results[dep_id]['output'][:200]}")

            if dep_contexts:
                goal_context += "\n\n前面任务的输出:\n" + "\n".join(dep_contexts)

            try:
                agent_result = await runtime.execute(
                    agent_name, goal_context, session_id, project_slug
                )
                node.result = {
                    "success": agent_result.success,
                    "output": agent_result.output[:1000],
                    "tool_calls": agent_result.tool_calls,
                    "iterations": agent_result.iterations,
                    "duration_ms": agent_result.duration_ms,
                }
                node.state = NodeState.COMPLETED if agent_result.success else NodeState.FAILED
                results[node.id] = node.result

            except Exception as e:
                logger.exception("Node %s failed: %s", node.id, e)
                node.result = {"success": False, "error": str(e)}
                node.state = NodeState.FAILED
                results[node.id] = node.result
                # Dependent nodes will be skipped
                for dep_id in node.dependents:
                    dep_node = graph.nodes.get(dep_id)
                    if dep_node:
                        dep_node.state = NodeState.SKIPPED

        # Save graph to store
        self.store.save(graph)

        return {
            "goal": plan.goal,
            "graph_id": graph.id,
            "progress": graph.get_progress(),
            "results": {
                nid: {"title": graph.nodes[nid].title, "state": graph.nodes[nid].state.value,
                      "success": r.get("success", False)}
                for nid, r in results.items()
            },
        }

    def _build_analysis_prompt(self, goal: str, profile: dict | None = None) -> str:
        """Analyze a goal to understand what capabilities are needed.

        Uses available agent descriptors to determine the best team.
        """
        agents = self.registry.list_all()
        if not agents:
            return "no_agents_available"

        agent_summary = "\n".join(
            f"- **{a.name}** [{a.tier}]: {a.description} "
            f"(能力: {', '.join(c.value for c in a.capabilities)})"
            for a in agents
        )

        profile_str = ""
        if profile:
            p = profile
            profile_str = f"""
## 用户背景
- 技术栈: {', '.join(p.get('tech_stack', []))}
- 长期愿景: {p.get('long_term_vision', '')}
- 决策原则: {', '.join(p.get('decision_principles', []) if isinstance(p.get('decision_principles'), list) else [])}
"""

        return f"""分析以下用户目标，将其分解为具体的执行任务。每个任务需要指定：
1. 任务名称
2. 任务描述
3. 需要的能力标签（从下面的Agent列表中选择最匹配的Agent）
4. 依赖关系（哪些任务必须先完成）

{profile_str}

## 目标
{goal}

## 可用 Agent 团队
{agent_summary}

## 输出格式
请输出 JSON:

```json
{{
  "summary": "对目标的一句话总结",
  "domain": "目标所属领域 (coding/writing/research/planning/mixed)",
  "tasks": [
    {{
      "title": "任务名",
      "description": "详细描述",
      "agent": "最合适的Agent名字",
      "dependencies": ["依赖的任务索引 (0-based)"],
      "priority": 0
    }}
  ]
}}
```"""

    def _build_task_graph(self, goal: str, analysis: str) -> TaskGraph:
        """Build a TaskGraph from the analysis result.

        Falls back to a simple sequential graph if LLM analysis fails.
        """
        graph = TaskGraph(
            goal=goal,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # If no meaningful analysis, return a simple 1-node graph
        if not analysis or analysis == "no_agents_available":
            node = TaskNode(
                title="处理目标",
                description=goal,
                assigned_agent="ceo",
                required_capabilities=["orchestration"],
            )
            graph.add_node(node)
            return graph

        # Try to parse JSON from analysis
        tasks = self._parse_tasks_from_analysis(analysis, goal)

        # Create nodes
        for i, task in enumerate(tasks):
            node = TaskNode(
                title=task.get("title", f"Task {i+1}"),
                description=task.get("description", task.get("title", "")),
                assigned_agent=task.get("agent", "ceo"),
                required_capabilities=task.get("capabilities", []),
                priority=task.get("priority", 0),
            )
            graph.add_node(node)

        # Create edges from dependency declarations
        for i, task in enumerate(tasks):
            deps = task.get("dependencies", [])
            node_ids = list(graph.nodes.keys())
            for dep_idx in deps:
                if isinstance(dep_idx, int) and 0 <= dep_idx < len(node_ids):
                    from_id = node_ids[dep_idx]
                    to_id = node_ids[i]
                    if from_id != to_id:
                        graph.add_edge(from_id, to_id)

        return graph

    def _parse_tasks_from_analysis(self, analysis: str, goal: str) -> list[dict]:
        """Extract task list from analysis text. Handles JSON and free-text."""
        # Try JSON extraction
        try:
            # Find JSON block
            start = analysis.find("```json")
            if start >= 0:
                start += 7
                end = analysis.find("```", start)
                if end > start:
                    json_str = analysis[start:end].strip()
                    data = json.loads(json_str)
                    return data.get("tasks", [])
            # Try raw JSON
            data = json.loads(analysis)
            return data.get("tasks", [])
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback: create a single task from the goal
        return [{"title": goal[:100], "description": goal, "agent": "ceo"}]

    def _assign_agents(self, graph: TaskGraph) -> dict[str, str]:
        """Assign the best agent to each task node based on capability matching."""
        assignments: dict[str, str] = {}
        for node in graph.nodes.values():
            if node.assigned_agent:
                # Node already has a preferred agent
                assignments[node.id] = node.assigned_agent
                continue

            # Find best match by capability
            if node.required_capabilities:
                caps = [Capability(c) for c in node.required_capabilities if c in Capability.__members__]
            else:
                caps = []

            matches = self.registry.match_team(caps, max_agents=1)
            if matches:
                assignments[node.id] = matches[0].name
            else:
                assignments[node.id] = "ceo"  # Default fallback

        return assignments

    def _estimate_duration(self, graph: TaskGraph) -> str:
        """Estimate total execution duration."""
        node_count = len(graph.nodes)
        if node_count <= 1:
            return "~30s"
        elif node_count <= 3:
            return "~2-5min"
        elif node_count <= 7:
            return "~5-15min"
        else:
            return "~15-30min"

    # ── Quick route (single agent, no graph) ───────────────

    async def quick_route(self, goal: str, session_id: str = "",
                          preferred_agent: str = "") -> dict:
        """Simple routing: pick the best single agent and execute.

        Use this for simple tasks that don't need multi-agent orchestration.
        """
        from agents.runtime import get_agent_runtime

        runtime = get_agent_runtime()

        if preferred_agent:
            agent_name = preferred_agent
        else:
            # Match by capability
            analysis = self._build_analysis_prompt(goal)
            tasks = self._parse_tasks_from_analysis(analysis, goal)
            caps = []
            for t in tasks:
                for c in t.get("capabilities", []):
                    if c in Capability.__members__:
                        caps.append(Capability(c))
            matches = self.registry.match_team(caps, max_agents=1)
            agent_name = matches[0].name if matches else "ceo"

        result = await runtime.execute(agent_name, goal, session_id)
        return {
            "agent": agent_name,
            "success": result.success,
            "output": result.output,
            "tool_calls": result.tool_calls,
            "iterations": result.iterations,
            "duration_ms": result.duration_ms,
        }


# Global singleton
_router: AgentRouter | None = None


def get_agent_router() -> AgentRouter:
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router
