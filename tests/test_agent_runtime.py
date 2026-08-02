"""Tests for the Agent Runtime (P0-2)"""

import pytest
from agents.runtime import AgentRuntime, AgentContext, AgentResult, BaseAgent, get_agent_runtime


class EchoAgent(BaseAgent):
    """A simple test agent that echoes back the goal."""

    def __init__(self):
        super().__init__(name="echo", description="Echoes the goal back")

    def system_prompt(self, ctx: AgentContext) -> str:
        return "You are an echo bot. Simply repeat back what the user said."


class TestBaseAgent:
    def test_agent_creation(self):
        agent = EchoAgent()
        assert agent.name == "echo"
        assert len(agent.id) == 8
        assert agent.description == "Echoes the goal back"

    def test_system_prompt(self):
        agent = EchoAgent()
        ctx = AgentContext(goal="Hello world")
        prompt = agent.system_prompt(ctx)
        assert "echo" in prompt.lower()


class TestAgentRuntime:
    def test_register_agent(self):
        runtime = AgentRuntime()
        agent = EchoAgent()
        runtime.register(agent)

        assert runtime.get("echo") is agent
        assert runtime.get(agent.id) is agent

    def test_list_agents(self):
        runtime = AgentRuntime()
        runtime.register(EchoAgent())

        agents = runtime.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "echo"
        assert agents[0]["description"] == "Echoes the goal back"

    def test_list_agents_no_duplicates(self):
        runtime = AgentRuntime()
        runtime.register(EchoAgent())
        runtime.register(EchoAgent())  # Second one

        agents = runtime.list_agents()
        # Should only show unique agents by ID (two different instances = two unique IDs)
        assert len(agents) == 2

    def test_get_nonexistent_agent(self):
        runtime = AgentRuntime()
        assert runtime.get("nonexistent") is None


class TestAgentContext:
    def test_default_context(self):
        ctx = AgentContext()
        assert ctx.session_id == ""
        assert ctx.max_iterations == 10
        assert ctx.current_iteration == 0

    def test_context_with_data(self):
        ctx = AgentContext(
            session_id="test-session",
            goal="Build something",
            user_profile={"name": "Test User"},
            memory_context="Previous decisions...",
        )
        assert ctx.session_id == "test-session"
        assert ctx.goal == "Build something"
        assert ctx.user_profile["name"] == "Test User"


class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(
            success=True,
            output="Task completed",
            tool_calls=[{"tool": "read_file", "success": True}],
            iterations=3,
        )
        assert result.success
        assert result.output == "Task completed"

    def test_error_result(self):
        result = AgentResult(success=False, error="Something went wrong")
        assert not result.success
        assert "wrong" in result.error


def test_global_runtime_singleton():
    r1 = get_agent_runtime()
    r2 = get_agent_runtime()
    assert r1 is r2
