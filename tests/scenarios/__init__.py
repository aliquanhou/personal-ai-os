"""Personal AI OS — Scenario Test Framework (Sprint 5)

Integration tests that simulate real workflows through the full agent pipeline.

Each scenario is a JSON file describing:
  - goal: what the user wants
  - expected_agents: which agents should be involved
  - expected_artifacts: what files should be created
  - checks: validation steps

Run with:
  python -m pytest tests/scenarios/ -v
"""

from tests.scenarios.runner import ScenarioRunner, run_scenario

__all__ = ["ScenarioRunner", "run_scenario"]
