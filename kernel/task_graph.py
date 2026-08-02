# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Task Graph (Sprint 3)

DAG-based task dependency system for multi-agent orchestration.

A Task Graph represents work as a directed acyclic graph:
    Task A (Research)
         |
    Task B (Planning) ── depends on A
         |
    ┌────┴────┐
    Task C    Task D    ← can run in parallel
    (Code)    (Tests)
         |
    Task E (Review) ── depends on C and D

Features:
  - DAG validation (no cycles)
  - Parallel execution groups
  - State tracking per node
  - Topological ordering
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class NodeState(StrEnum):
    PENDING = "pending"       # Waiting for dependencies
    READY = "ready"           # Dependencies met, can execute
    RUNNING = "running"       # Currently executing
    COMPLETED = "completed"   # Done successfully
    FAILED = "failed"         # Failed
    SKIPPED = "skipped"       # Skipped due to upstream failure


@dataclass
class TaskNode:
    """A single node in the task graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    assigned_agent: str = ""         # Agent name
    required_capabilities: list[str] = field(default_factory=list)
    state: NodeState = NodeState.PENDING
    dependencies: list[str] = field(default_factory=list)  # Node IDs this depends on
    dependents: list[str] = field(default_factory=list)    # Node IDs that depend on this
    result: dict = field(default_factory=dict)              # Execution result
    priority: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "required_capabilities": self.required_capabilities,
            "state": self.state.value,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "result": self.result,
            "priority": self.priority,
        }


@dataclass
class TaskGraph:
    """A DAG of tasks to execute for a project goal."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    nodes: dict[str, TaskNode] = field(default_factory=dict)
    created_at: str = ""

    def add_node(self, node: TaskNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, from_id: str, to_id: str) -> bool:
        """Add a dependency edge: `to_id` depends on `from_id`.

        Returns False if the edge would create a cycle.
        """
        if from_id not in self.nodes or to_id not in self.nodes:
            return False

        self.nodes[to_id].dependencies.append(from_id)
        self.nodes[from_id].dependents.append(to_id)

        if self._has_cycle():
            # Rollback
            self.nodes[to_id].dependencies.remove(from_id)
            self.nodes[from_id].dependents.remove(to_id)
            logger.warning("Edge %s→%s would create cycle, rejected", from_id, to_id)
            return False
        return True

    def _has_cycle(self) -> bool:
        """Detect cycles using DFS."""
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            in_stack.add(node_id)
            for dep_id in self.nodes[node_id].dependents:
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in in_stack:
                    return True
            in_stack.discard(node_id)
            return False

        for nid in self.nodes:
            if nid not in visited:
                if dfs(nid):
                    return True
        return False

    def get_ready_nodes(self) -> list[TaskNode]:
        """Get all nodes whose dependencies are met and are pending."""
        ready = []
        for node in self.nodes.values():
            if node.state != NodeState.PENDING:
                continue
            deps_met = all(
                self.nodes[dep].state == NodeState.COMPLETED
                for dep in node.dependencies
            )
            if deps_met:
                ready.append(node)
        return ready

    def get_parallel_groups(self) -> list[list[TaskNode]]:
        """Get groups of nodes that can execute in parallel.

        Each group is a list of nodes with no dependencies between them.
        Groups are ordered by topological depth.
        """
        # Compute depth for each node
        depths: dict[str, int] = {}

        def compute_depth(nid: str) -> int:
            if nid in depths:
                return depths[nid]
            node = self.nodes[nid]
            if not node.dependencies:
                depths[nid] = 0
            else:
                depths[nid] = 1 + max(compute_depth(d) for d in node.dependencies)
            return depths[nid]

        for nid in self.nodes:
            compute_depth(nid)

        # Group by depth
        by_depth: dict[int, list[TaskNode]] = defaultdict(list)
        for node in self.nodes.values():
            if node.state == NodeState.PENDING:
                by_depth[depths[node.id]].append(node)

        return [nodes for _, nodes in sorted(by_depth.items())]

    def topological_order(self) -> list[TaskNode]:
        """Return nodes in topological (execution) order."""
        in_degree = {nid: len(node.dependencies) for nid, node in self.nodes.items()}
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            nid = queue.pop(0)
            result.append(self.nodes[nid])
            for dep_id in self.nodes[nid].dependents:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)

        return result

    def get_progress(self) -> dict:
        """Get progress summary of the graph."""
        total = len(self.nodes)
        by_state = defaultdict(int)
        for node in self.nodes.values():
            by_state[node.state.value] += 1
        completed = by_state.get("completed", 0)
        return {
            "total": total,
            "completed": completed,
            "in_progress": by_state.get("running", 0),
            "pending": by_state.get("pending", 0) + by_state.get("ready", 0),
            "failed": by_state.get("failed", 0),
            "progress_pct": (completed / total * 100) if total > 0 else 0,
            "by_state": dict(by_state),
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "progress": self.get_progress(),
            "topological_order": [n.id for n in self.topological_order()],
            "parallel_groups": [
                [n.id for n in group]
                for group in self.get_parallel_groups()
            ],
        }


class TaskGraphStore:
    """Persistent store for task graphs. In-memory for now, DB later."""

    def __init__(self):
        self._graphs: dict[str, TaskGraph] = {}

    def save(self, graph: TaskGraph) -> None:
        self._graphs[graph.id] = graph

    def get(self, graph_id: str) -> TaskGraph | None:
        return self._graphs.get(graph_id)

    def get_by_goal(self, goal_prefix: str) -> TaskGraph | None:
        for g in self._graphs.values():
            if goal_prefix in g.goal:
                return g
        return None

    def list_all(self) -> list[dict]:
        return [{"id": g.id, "goal": g.goal[:100], "progress": g.get_progress()}
                for g in self._graphs.values()]


# Global singleton
_store: TaskGraphStore | None = None


def get_task_graph_store() -> TaskGraphStore:
    global _store
    if _store is None:
        _store = TaskGraphStore()
    return _store
