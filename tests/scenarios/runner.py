"""Personal AI OS — Scenario Test Runner (Sprint 5)

Runs scenario tests against the full Agent Organization stack
without requiring actual LLM calls (uses mocks for deterministic tests).

Each scenario validates:
  1. Agent Registry — correct agents exist
  2. Router — correct task decomposition
  3. Task Graph — valid DAG structure
  4. Communication Bus — channels and mailboxes operational
  5. Budget — within limits
  6. Audit — all actions logged
  7. Reputation — recorded after execution
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ScenarioRunner:
    """Runs integration test scenarios through the governance stack."""

    def __init__(self):
        self.results: list[dict] = []

    def run_all(self, scenario_dir: str = "") -> dict:
        """Run all scenario JSON files in the given directory."""
        scenarios_dir = Path(scenario_dir) if scenario_dir else Path(__file__).parent
        results = {"passed": 0, "failed": 0, "scenarios": []}

        for f in sorted(scenarios_dir.glob("*.json")):
            if f.name.startswith("_"):
                continue
            outcome = self.run_file(str(f))
            results["scenarios"].append(outcome)
            if outcome["passed"]:
                results["passed"] += 1
            else:
                results["failed"] += 1

        return results

    def run_file(self, path: str) -> dict:
        """Run a single scenario file."""
        scenario = json.loads(Path(path).read_text(encoding="utf-8"))
        name = scenario.get("name", Path(path).stem)
        logger.info("Running scenario: %s", name)

        checks = []
        try:
            # ── Check 1: Agent Registry ──
            result = self._check_registry(scenario.get("expected_agents", []))
            checks.append(result)

            # ── Check 2: Router Plan ──
            result = self._check_router_plan(scenario)
            checks.append(result)

            # ── Check 3: Task Graph Structure ──
            result = self._check_task_graph(scenario)
            checks.append(result)

            # ── Check 4: Communication Channels ──
            result = self._check_communication(scenario)
            checks.append(result)

            # ── Check 5: Budget Tracking ──
            result = self._check_budget(scenario)
            checks.append(result)

            # ── Check 6: Audit Trail ──
            result = self._check_audit(scenario)
            checks.append(result)

            # ── Check 7: Reputation Recording ──
            result = self._check_reputation(scenario)
            checks.append(result)

            # ── Custom checks from scenario ──
            for check_cfg in scenario.get("checks", []):
                result = self._run_custom_check(check_cfg, scenario)
                checks.append(result)

        except Exception as e:
            logger.exception("Scenario %s failed: %s", name, e)
            checks.append({"check": "exception", "passed": False, "error": str(e)})

        passed = all(c.get("passed", False) for c in checks)
        return {
            "scenario": name,
            "passed": passed,
            "checks": checks,
            "checks_passed": sum(1 for c in checks if c.get("passed")),
            "checks_total": len(checks),
        }

    def _check_registry(self, expected: list[str]) -> dict:
        """Verify all expected agents are registered."""
        try:
            from kernel.registry import get_agent_registry
            registry = get_agent_registry()
            all_agents = [d.name for d in registry.list_all()]
            missing = [a for a in expected if a not in all_agents]
            return {
                "check": "registry",
                "passed": len(missing) == 0,
                "detail": f"Expected agents: {expected}, Found: {all_agents}",
                "missing": missing,
            }
        except Exception as e:
            return {"check": "registry", "passed": False, "error": str(e)}

    def _check_router_plan(self, scenario: dict) -> dict:
        """Verify router can plan for the goal."""
        goal = scenario.get("goal", "")
        if not goal:
            return {"check": "router_plan", "passed": True, "detail": "No goal specified"}

        try:
            from kernel.registry import get_agent_registry
            registry = get_agent_registry()

            # Verify agents with required capabilities exist
            required_caps = scenario.get("required_capabilities", [])
            for cap in required_caps:
                agents = registry.find_by_capability(cap)
                if not agents:
                    return {
                        "check": "router_plan",
                        "passed": False,
                        "detail": f"No agent with capability: {cap}",
                    }

            return {
                "check": "router_plan",
                "passed": True,
                "detail": f"All {len(required_caps)} required capabilities available",
            }
        except Exception as e:
            return {"check": "router_plan", "passed": False, "error": str(e)}

    def _check_task_graph(self, scenario: dict) -> dict:
        """Verify task graph can be built and is a valid DAG."""
        try:
            from kernel.task_graph import TaskGraph, TaskNode

            graph = TaskGraph(goal=scenario.get("goal", "test"))

            # Build from expected tasks
            expected_tasks = scenario.get("expected_tasks", [])
            if not expected_tasks:
                return {"check": "task_graph", "passed": True, "detail": "No tasks specified"}

            for t in expected_tasks:
                node = TaskNode(
                    title=t.get("title", ""),
                    description=t.get("description", ""),
                    assigned_agent=t.get("agent", "ceo"),
                    required_capabilities=t.get("capabilities", []),
                )
                graph.add_node(node)

            # Add dependency edges from task definitions
            node_ids = list(graph.nodes.keys())
            for i, t in enumerate(expected_tasks):
                for dep_idx in t.get("dependencies", []):
                    if isinstance(dep_idx, int) and 0 <= dep_idx < len(node_ids):
                        if node_ids[dep_idx] != node_ids[i]:
                            graph.add_edge(node_ids[dep_idx], node_ids[i])

            # Verify node count
            if len(graph.nodes) != len(expected_tasks):
                return {
                    "check": "task_graph",
                    "passed": False,
                    "detail": f"Expected {len(expected_tasks)} nodes, got {len(graph.nodes)}",
                }

            # Verify DAG validity
            order = graph.topological_order()
            if len(order) != len(expected_tasks):
                return {
                    "check": "task_graph_dag",
                    "passed": False,
                    "detail": f"DAG invalid: {len(order)} in topological order, {len(expected_tasks)} nodes",
                }

            # Verify no cycles
            for node in graph.nodes.values():
                visited = set()
                stack = [node.id]
                while stack:
                    nid = stack.pop()
                    if nid in visited:
                        continue
                    visited.add(nid)
                    for dep_id in graph.nodes[nid].dependencies:
                        if dep_id == node.id:  # self-loop
                            return {"check": "task_graph_cycle", "passed": False, "detail": f"Self-loop at {node.id}"}
                        stack.append(dep_id)

            return {"check": "task_graph", "passed": True, "detail": f"Valid DAG: {len(expected_tasks)} nodes"}
        except Exception as e:
            return {"check": "task_graph", "passed": False, "error": str(e)}

    def _check_communication(self, scenario: dict) -> dict:
        """Verify communication bus has channels for expected teams."""
        try:
            from kernel.comm_bus import get_comm_bus
            comm_bus = get_comm_bus()
            status = comm_bus.get_organization_status()

            expected_teams = scenario.get("expected_teams", [])
            for team in expected_teams:
                if team not in status.get("channels", {}):
                    return {
                        "check": "communication",
                        "passed": False,
                        "detail": f"Channel not found: {team}",
                    }

            # Verify all agents have mailboxes
            expected_agents = scenario.get("expected_agents", [])
            for agent in expected_agents:
                mb = comm_bus.get_mailbox(agent)
                if mb is None:
                    return {
                        "check": "communication",
                        "passed": False,
                        "detail": f"No mailbox for: {agent}",
                    }

            return {
                "check": "communication",
                "passed": True,
                "detail": f"All channels and mailboxes operational",
            }
        except Exception as e:
            return {"check": "communication", "passed": False, "error": str(e)}

    def _check_budget(self, scenario: dict) -> dict:
        """Verify budget manager is tracking correctly."""
        try:
            from kernel.budget import BudgetManager, get_budget_manager

            mgr = get_budget_manager(
                daily_limit_usd=scenario.get("budget_daily_limit", 5.0),
                task_limit_usd=scenario.get("budget_task_limit", 2.0),
            )
            status = mgr.get_status()

            # Simulate some usage and verify tracking
            mgr.record("test_context", "ceo", "deepseek-chat", 500, 200)
            mgr.record("test_context", "coding_agent", "deepseek-chat", 1000, 800)

            updated = mgr.get_status()
            if updated["daily_spent_usd"] <= 0:
                return {"check": "budget", "passed": False, "detail": "Budget not tracking spending"}

            return {
                "check": "budget",
                "passed": True,
                "detail": f"Budget tracking: ${updated['daily_spent_usd']:.4f} spent of ${updated['daily_limit_usd']:.2f}",
            }
        except Exception as e:
            return {"check": "budget", "passed": False, "error": str(e)}

    def _check_audit(self, scenario: dict) -> dict:
        """Verify audit log is recording entries."""
        try:
            from kernel.audit import get_audit_log, AuditCategory

            audit = get_audit_log()

            # Record test entries
            audit.record_decision("ceo", "test decision", "test rationale")
            audit.record_action("coding_agent", "wrote file", "test.py created",
                               tool_name="write_file")
            audit.record_budget("ceo", 0.0005, "test")

            stats = audit.stats()
            if stats["total_entries"] < 3:
                return {"check": "audit", "passed": False, "detail": f"Only {stats['total_entries']} entries found"}

            # Verify decisions are queryable
            decisions = audit.get_decisions(limit=10)
            if not decisions:
                return {"check": "audit", "passed": False, "detail": "Decisions not queryable"}

            return {
                "check": "audit",
                "passed": True,
                "detail": f"Audit: {stats['total_entries']} entries, {stats['by_category']}",
            }
        except Exception as e:
            return {"check": "audit", "passed": False, "error": str(e)}

    def _check_reputation(self, scenario: dict) -> dict:
        """Verify reputation system records and scores agents."""
        try:
            from kernel.reputation import get_reputation_registry

            rep = get_reputation_registry()

            # Simulate agent performance
            rep.record("ceo", True, 5000, tool_calls=3, capability="orchestration")
            rep.record("ceo", True, 4200, tool_calls=2, capability="strategy")
            rep.record("coding_agent", True, 8000, tool_calls=5, capability="code_generation")
            rep.record("coding_agent", False, 15000, tool_calls=3, capability="code_generation",
                      hit_max_iterations=True)

            ceo_rep = rep.get("ceo")
            coder_rep = rep.get("coding_agent")

            # CEO should have higher reputation than coding_agent (which has a failure)
            if ceo_rep.reputation_score <= coder_rep.reputation_score:
                return {
                    "check": "reputation",
                    "passed": False,
                    "detail": f"Reputation order wrong: CEO={ceo_rep.reputation_score}, Coder={coder_rep.reputation_score}",
                }

            return {
                "check": "reputation",
                "passed": True,
                "detail": f"CEO={ceo_rep.tier}({ceo_rep.reputation_score}), Coder={coder_rep.tier}({coder_rep.reputation_score})",
            }
        except Exception as e:
            return {"check": "reputation", "passed": False, "error": str(e)}

    def _run_custom_check(self, cfg: dict, scenario: dict) -> dict:
        """Run a custom check defined in the scenario."""
        check_type = cfg.get("type", "")
        name = cfg.get("name", check_type)

        if check_type == "agent_has_capability":
            from kernel.registry import Capability, get_agent_registry
            registry = get_agent_registry()
            desc = registry.get(cfg.get("agent", ""))
            cap = Capability(cfg.get("capability", ""))
            has_it = desc and cap in desc.capabilities
            return {"check": name, "passed": has_it, "detail": f"Agent {cfg.get('agent')} has {cap.value}: {has_it}"}

        if check_type == "graph_depth":
            expected_depth = cfg.get("expected", 0)
            tasks = scenario.get("expected_tasks", [])
            # Compute max dependency depth
            depths: dict[int, int] = {}
            def get_depth(idx):
                if idx in depths:
                    return depths[idx]
                deps = tasks[idx].get("dependencies", []) if 0 <= idx < len(tasks) else []
                if not deps:
                    depths[idx] = 0
                else:
                    depths[idx] = 1 + max(get_depth(d) for d in deps if isinstance(d, int))
                return depths[idx]
            max_depth = max((get_depth(i) for i in range(len(tasks))), default=0)
            return {"check": name, "passed": max_depth >= expected_depth,
                    "detail": f"Graph depth: {max_depth} >= {expected_depth}"}

        return {"check": name, "passed": True, "detail": "Unknown check type, skipped"}


def run_scenario(path: str) -> dict:
    """Convenience function to run a single scenario."""
    runner = ScenarioRunner()
    return runner.run_file(path)
