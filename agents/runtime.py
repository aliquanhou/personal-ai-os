"""Personal AI OS Agent Runtime — Agent Base & Lifecycle

Sprint 2: Checkpoints, workspace integration, recovery.

Flow:
   User Goal
      ↓
   Planner (break goal into tasks)
      ↓
   Task Queue (prioritize)
      ↓
   Agent Worker (execute task with tools)
      ↓
   [CHECKPOINT] ← auto-save progress
      ↓
   Result (observe)
      ↓
   Memory Update (learn)
      ↓
   [RECOVERY] ← if crashed, resume from last checkpoint
"""

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from kernel.events import Event, EventType, get_event_bus
from kernel.llm_router import LLMRouter, get_llm_router
from kernel.workspace import WorkspaceManager, get_workspace
# Sprint 5
from kernel.audit import get_audit_log, AuditCategory, AuditSeverity
from kernel.reputation import get_reputation_registry
# Sprint 6.5
from kernel.skill_executor import get_skill_executor, SkillContext
from memory.manager import MemoryManager, get_memory
from tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to an agent when it runs."""
    session_id: str = ""
    goal: str = ""
    user_profile: dict = field(default_factory=dict)
    memory_context: str = ""
    max_iterations: int = 30
    current_iteration: int = 0
    # Sprint 2: Workspace & checkpoint
    project_slug: str = ""
    checkpoints: list[dict] = field(default_factory=list)
    resume_from_checkpoint: dict | None = None
    # Sprint 4: Inter-agent communication
    mailbox_context: str = ""  # Messages from teammates
    # v1.1: Memory context isolation mode
    context_mode: str = "normal"  # normal / fresh_start / audit
    handoff_context: dict | None = None  # Structured handoff from previous agent


@dataclass
class AgentResult:
    """Result of an agent run."""
    success: bool
    output: str = ""
    error: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    memory_updates: int = 0
    duration_ms: float = 0.0
    # Sprint 2: Checkpoint info
    checkpoint_count: int = 0
    last_checkpoint: dict | None = None


class BaseAgent(ABC):
    """Base class for all agents.

    Agents are the workers of Personal AI OS. Each agent has:
    - A system prompt defining its role
    - Access to tools
    - An LLM to reason and act
    - Memory read/write capability
    """

    def __init__(self, name: str, description: str = ""):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.llm: LLMRouter = get_llm_router()
        self.memory: MemoryManager = get_memory()
        self.tools: ToolRegistry = get_tool_registry()
        self.event_bus = get_event_bus()
        self.workspace: WorkspaceManager = get_workspace()

    @abstractmethod
    def system_prompt(self, ctx: AgentContext) -> str:
        """Return the system prompt for this agent."""
        ...

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Run the agent loop: think → act → observe → checkpoint → repeat.

        Sprint 2: Auto-saves checkpoints at each major step.
        If resuming, picks up from last checkpoint context.
        """
        start_time = time.time()
        tool_calls_log = []
        memory_updates = 0
        checkpoint_count = 0
        last_checkpoint = None

        await self.event_bus.publish(Event(
            type=EventType.AGENT_STARTED,
            data={"agent_id": self.id, "agent_name": self.name, "goal": ctx.goal},
            source=self.name,
        ))

        # Sprint 6.5: Build system prompt with skill injection
        base_prompt = self.system_prompt(ctx)
        try:
            executor = get_skill_executor()
            system_prompt = executor.inject_into_context(self.name, base_prompt)
        except Exception:
            system_prompt = base_prompt

        # Build messages — if resuming, prepend checkpoint context
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # Sprint 4: Inject handoff context from previous agent
        if ctx.handoff_context:
            hc = ctx.handoff_context
            handoff_msg = (
                f"## 📋 来自上一个 Agent 的交接上下文\n"
                f"上一个任务总结: {hc.get('summary', '')}\n"
                f"完成状态: {hc.get('completion_status', '')}\n"
                f"关键发现: {', '.join(hc.get('key_findings', []))}\n"
                f"已创建的产出物: {', '.join(hc.get('artifacts', []))}\n"
                f"警吿: {', '.join(hc.get('warnings', []))}\n"
                f"建议下一步: {', '.join(hc.get('next_steps', []))}\n"
            )
            messages.append({"role": "system", "content": handoff_msg})
        # Sprint 4: Inject mailbox context from teammates
        if ctx.mailbox_context:
            messages.append({"role": "system", "content": ctx.mailbox_context})
        if ctx.resume_from_checkpoint:
            resume_msg = (
                f"⚠️ 这是从断点恢复的执行。上一次执行到: "
                f"{ctx.resume_from_checkpoint.get('step', 'unknown')}。"
                f"已完成: {ctx.resume_from_checkpoint.get('completed', 'unknown')}。"
                f"请从断点处继续，不要重复已完成的工作。"
            )
            messages.append({"role": "system", "content": resume_msg})
            logger.info("Resuming from checkpoint in %s", ctx.project_slug or ctx.session_id)

        messages.append({"role": "user", "content": ctx.goal})

        final_output = ""

        try:
            while ctx.current_iteration < ctx.max_iterations:
                ctx.current_iteration += 1

                await self.event_bus.publish(Event(
                    type=EventType.AGENT_THINKING,
                    data={"agent_id": self.id, "iteration": ctx.current_iteration},
                    source=self.name,
                ))

                tool_defs = self.tools.list_definitions()
                response = await self.llm.chat(messages, tools=tool_defs)

                if response.get("tool_calls"):
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content", ""),
                        "tool_calls": response["tool_calls"],
                    })

                    for tc in response["tool_calls"]:
                        func_name = tc["function"]["name"]
                        try:
                            func_args = json.loads(tc["function"]["arguments"])
                        except json.JSONDecodeError:
                            func_args = {}

                        await self.event_bus.publish(Event(
                            type=EventType.TOOL_CALL_START,
                            data={"agent_id": self.id, "tool": func_name, "args": func_args},
                            source=self.name,
                        ))

                        # Sprint 2: Check approval layer
                        approval_result = self.tools.check_approval(func_name, func_args)
                        if approval_result.blocked:
                            tool_calls_log.append({
                                "tool": func_name,
                                "args": func_args,
                                "success": False,
                                "output": f"🚫 被批准层阻止: {approval_result.reason}",
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": f"Action blocked by approval layer: {approval_result.reason}",
                            })
                            continue
                        if approval_result.needs_approval:
                            tool_calls_log.append({
                                "tool": func_name,
                                "args": func_args,
                                "success": False,
                                "output": f"⏸️ 等待人工批准: {approval_result.reason}",
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": f"Action requires human approval: {approval_result.reason}. Ask the user before proceeding.",
                            })
                            # Save checkpoint before waiting
                            self._save_checkpoint(ctx, tool_calls_log, checkpoint_count, "waiting_approval")
                            continue

                        result = await self.tools.execute(tool_name=func_name, **func_args)

                        # Sprint 5: Audit every tool execution
                        try:
                            audit = get_audit_log()
                            if result.success:
                                audit.record_action(self.name, f"Tool: {func_name}",
                                                   result.output[:200], tool_name=func_name,
                                                   session_id=ctx.session_id)
                            else:
                                audit.record_error(self.name, f"Tool failed: {func_name}",
                                                  result.output[:200] if result.output else result.error)
                        except Exception:
                            pass

                        tool_calls_log.append({
                            "tool": func_name,
                            "args": func_args,
                            "success": result.success,
                            "output": result.output[:500],
                        })

                        # Sprint 2: Save checkpoint every 3 tool calls
                        if len(tool_calls_log) % 3 == 0:
                            last_checkpoint = self._save_checkpoint(
                                ctx, tool_calls_log, checkpoint_count,
                                f"iteration_{ctx.current_iteration}_after_{func_name}"
                            )
                            checkpoint_count += 1

                        await self.event_bus.publish(Event(
                            type=EventType.TOOL_CALL_END,
                            data={"agent_id": self.id, "tool": func_name, "success": result.success},
                            source=self.name,
                        ))

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result.output if result.success else f"Error: {result.error}",
                        })
                else:
                    final_output = response.get("content", "")
                    messages.append({"role": "assistant", "content": final_output})

                    # Auto-save to memory if substantive
                    if len(final_output) > 100:
                        self.memory.save_message(
                            ctx.session_id, "assistant", final_output,
                            {"agent": self.name, "iterations": ctx.current_iteration},
                        )
                        memory_updates += 1

                    # Final checkpoint
                    last_checkpoint = self._save_checkpoint(
                        ctx, tool_calls_log, checkpoint_count, "completed"
                    )
                    checkpoint_count += 1

                    await self.event_bus.publish(Event(
                        type=EventType.AGENT_COMPLETED,
                        data={"agent_id": self.id, "output_length": len(final_output)},
                        source=self.name,
                    ))
                    break

            else:
                final_output = "（达到最大迭代次数，任务可能未完成）"
                last_checkpoint = self._save_checkpoint(
                    ctx, tool_calls_log, checkpoint_count, "max_iterations_reached"
                )
                checkpoint_count += 1
                await self.event_bus.publish(Event(
                    type=EventType.AGENT_ERROR,
                    data={"agent_id": self.id, "error": "Max iterations reached"},
                    source=self.name,
                ))

        except Exception as e:
            logger.exception("Agent %s error", self.name)
            # Emergency checkpoint on crash
            self._save_checkpoint(ctx, tool_calls_log, checkpoint_count, f"crashed: {e}")
            await self.event_bus.publish(Event(
                type=EventType.AGENT_ERROR,
                data={"agent_id": self.id, "error": str(e)},
                source=self.name,
            ))
            # Sprint 5: Record failure reputation + audit error
            err_duration = (time.time() - start_time) * 1000
            try:
                audit = get_audit_log()
                audit.record_error(self.name, str(e), detail=f"Agent {self.name} crashed",
                                  context={"goal": ctx.goal[:200], "iteration": ctx.current_iteration})
                get_reputation_registry().record(self.name, False, err_duration,
                                                 tool_calls=len(tool_calls_log))
                get_skill_executor().record_execution(self.name, False, err_duration)
            except Exception:
                pass

            return AgentResult(
                success=False,
                error=str(e),
                tool_calls=tool_calls_log,
                iterations=ctx.current_iteration,
                duration_ms=err_duration,
                checkpoint_count=checkpoint_count,
                last_checkpoint=last_checkpoint,
            )

        duration = (time.time() - start_time) * 1000

        # Sprint 5: Record reputation
        try:
            rep = get_reputation_registry()
            hit_max = ctx.current_iteration >= ctx.max_iterations
            rep.record(self.name, True, duration,
                      tool_calls=len(tool_calls_log),
                      hit_max_iterations=hit_max)
        except Exception:
            pass

        # Sprint 6.5: Record skill execution
        try:
            get_skill_executor().record_execution(self.name, True, duration)
        except Exception:
            pass

        return AgentResult(
            success=True,
            output=final_output,
            tool_calls=tool_calls_log,
            iterations=ctx.current_iteration,
            memory_updates=memory_updates,
            duration_ms=duration,
            checkpoint_count=checkpoint_count,
            last_checkpoint=last_checkpoint,
        )

    def _save_checkpoint(self, ctx: AgentContext, tool_calls: list[dict],
                         count: int, step: str) -> dict | None:
        """Save a checkpoint of the current execution state."""
        slug = ctx.project_slug or f"session_{ctx.session_id}"
        checkpoint = {
            "step": step,
            "iteration": ctx.current_iteration,
            "goal": ctx.goal[:200],
            "completed": f"{len([t for t in tool_calls if t['success']])}/{len(tool_calls)} tool calls succeeded",
            "last_tool": tool_calls[-1]["tool"] if tool_calls else "none",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.workspace.save_checkpoint(slug, checkpoint)
        except Exception:
            pass  # Non-critical: don't fail the run for a checkpoint
        return checkpoint

    async def run_stream(self, ctx: AgentContext) -> AsyncIterator[str]:
        """Run agent with streaming output."""
        messages = [
            {"role": "system", "content": self.system_prompt(ctx)},
            {"role": "user", "content": ctx.goal},
        ]

        while ctx.current_iteration < ctx.max_iterations:
            ctx.current_iteration += 1

            tool_defs = self.tools.list_definitions()
            # Use streaming for final response
            full_response = ""
            async for chunk in self.llm.chat_stream(messages, tools=tool_defs):
                full_response += chunk
                yield chunk

            # For simplicity in stream mode, we don't handle tool calls
            if full_response:
                self.memory.save_message(
                    ctx.session_id, "assistant", full_response,
                    {"agent": self.name},
                )
                break


class AgentRuntime:
    """Manages agent instances, their lifecycle, and execution.

    Sprint 2: Workspace integration, recovery from checkpoints.
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._active_runs: dict[str, AgentContext] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.id] = agent
        # Also index by name
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.id)

    def get(self, name_or_id: str) -> BaseAgent | None:
        return self._agents.get(name_or_id)

    def list_agents(self) -> list[dict]:
        seen = set()
        result = []
        for agent in self._agents.values():
            if agent.id not in seen:
                seen.add(agent.id)
                result.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                })
        return result

    async def execute(self, agent_name: str, goal: str, session_id: str = "",
                      project_slug: str = "", resume: bool = False) -> AgentResult:
        """Execute an agent with a goal.

        Args:
            agent_name: Name of agent to run.
            goal: The goal/message to process.
            session_id: Conversation session ID.
            project_slug: Workspace project slug for checkpoint storage.
            resume: If True, attempt to resume from last checkpoint.
        """
        agent = self.get(agent_name)
        if not agent:
            return AgentResult(success=False, error=f"Agent not found: {agent_name}")

        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        # v1.1: Detect user intent for memory context mode
        context_mode = self._detect_context_mode(goal)
        memory_ctx = agent.memory.get_memory_context(
            query=goal, context_mode=context_mode
        )
        workspace = get_workspace()

        # Auto-create project workspace if slug provided
        if project_slug:
            workspace.create_project(project_slug, description=goal[:200])

        # Sprint 2: Check for resume from checkpoint
        resume_data = None
        if resume and project_slug:
            resume_data = workspace.get_last_checkpoint(project_slug)

        ctx = AgentContext(
            session_id=session_id,
            goal=goal,
            user_profile=agent.memory.get_profile(),
            memory_context=memory_ctx,
            project_slug=project_slug,
            resume_from_checkpoint=resume_data,
            context_mode=context_mode,
        )

        self._active_runs[agent.id] = ctx
        try:
            return await agent.run(ctx)
        finally:
            self._active_runs.pop(agent.id, None)


    @staticmethod
    def _detect_context_mode(goal: str) -> str:
        """Detect user intent for memory context filtering.

        v1.1: Parses goal text for keywords that signal context isolation intent.
        - "重新设计" / "不要考虑之前" / "推倒重来" → fresh_start
        - "审计" / "复盘" / "检查之前" → audit
        - default → normal
        """
        gl = goal.lower()
        fresh_keywords = [
            "重新设计", "不要考虑之前", "不考虑之前", "从头开始",
            "新方案", "推倒重来", "全新的", "忽略之前",
            "重新想", "别管之前的", "清除上下文",
        ]
        audit_keywords = [
            "审计之前", "复盘", "检查之前", "回顾历史",
            "review past", "audit",
        ]
        for kw in fresh_keywords:
            if kw.lower() in gl:
                return "fresh_start"
        for kw in audit_keywords:
            if kw.lower() in gl:
                return "audit"
        return "normal"


# Global singleton
_runtime: AgentRuntime | None = None


def get_agent_runtime() -> AgentRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime()
    return _runtime
