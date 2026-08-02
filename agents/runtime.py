# -*- coding: utf-8 -*-
"""Personal AI OS Agent Runtime — Agent Base & Lifecycle v1.5

Refactored: BaseAgent.run() split into 6 focused methods.
    _init_lifecycle()  — setup
    _build_messages()  — context assembly
    _execute_tool()    — single tool (approval → audit → lifecycle → envoy)
    _run_tool_loop()   — for-loop over LLM tool_calls
    _finalize()        — completion + memory + checkpoint + envoy
    _record_post_run() — reputation + skill recording
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
from kernel.audit import get_audit_log, AuditCategory, AuditSeverity
from kernel.reputation import get_reputation_registry
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
    goal_tracker: Any = None
    project_slug: str = ""
    checkpoints: list[dict] = field(default_factory=list)
    resume_from_checkpoint: dict | None = None
    mailbox_context: str = ""
    context_mode: str = "normal"
    handoff_context: dict | None = None


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

    # ═══════════════════════════════════════════════════════
    # ORCHESTRATOR (70 lines)
    # ═══════════════════════════════════════════════════════

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrate agent execution. Delegates to focused private methods."""
        start_time = time.time()
        state = {"tool_calls": [], "memory_updates": 0, "checkpoint_count": 0,
                 "last_checkpoint": None, "final_output": ""}

        lc = self._init_lifecycle(ctx)
        messages = self._build_messages(ctx)
        await self._emit_lifecycle(lc, ctx.goal, ctx.session_id)

        # v1.5.1: Force write_file for file-creation tasks (user-level, not system)
        if any(kw in ctx.goal for kw in
               ["创建", "main.py", "README", ".md", ".py", "文件", "生成", "编写"]):
            messages.append({"role": "user", "content": (
                "重要补充：你必须使用 write_file 工具来创建每个文件。"
                "不要使用 shell 来创建文件。不要扫描目录。"
                "直接依次调用 write_file 创建所有要求的文件，"
                "然后用 shell 运行验证。立即开始。"
            )})

        try:
            while lc.can_continue():
                lc.advance_iteration()
                ctx.current_iteration = lc.current_iteration

                if lc.current_iteration > lc.max_iterations:
                    state["final_output"] = f"（达到最大迭代次数 {lc.max_iterations}，任务中断）"
                    lc.auto_progress_to(LifecycleStage.FAILED)
                    break

                await self._emit_lifecycle(lc, f"Iter {lc.current_iteration}", ctx.session_id)
                response = await self.llm.chat(messages, tools=self.tools.list_definitions())

                if response.get("tool_calls"):
                    messages.append({
                        "role": "assistant", "content": response.get("content", ""),
                        "tool_calls": response["tool_calls"],
                    })
                    should_stop = await self._run_tool_loop(
                        response["tool_calls"], lc, messages, ctx, state)
                    if should_stop:
                        await self._finalize(lc, ctx, state)
                        break
                else:
                    state["final_output"] = response.get("content", "")
                    messages.append({"role": "assistant", "content": state["final_output"]})
                    self._append_progress(lc, state)
                    lc.auto_progress_to(LifecycleStage.COMPLETE)
                    await self._finalize(lc, ctx, state)
                    break
            else:
                if not state["final_output"]:
                    state["final_output"] = (
                        lc.forced_stop_reason
                        or f"（任务终止：阶段[{lc.stage.value}]，迭代 {lc.current_iteration}）"
                    )
                await self.event_bus.publish(Event(
                    type=EventType.AGENT_ERROR,
                    data={"agent_id": self.id,
                          "error": lc.forced_stop_reason or "Task force-stopped",
                          "lifecycle_stage": lc.stage.value,
                          "session_id": ctx.session_id},
                    source=self.name,
                ))

        except Exception as e:
            return self._handle_crash(e, ctx, state, start_time)

        # Minimum output guard — never return empty response
        if not state["final_output"].strip():
            tools_ok = sum(1 for t in state["tool_calls"] if t["success"])
            tools_total = len(state["tool_calls"])
            state["final_output"] = (
                f"任务执行完毕。\n"
                f"工具调用: {tools_ok}/{tools_total} 成功。\n"
                f"阶段: {lc.stage.value}。"
            )
        duration = (time.time() - start_time) * 1000
        self._record_post_run(ctx, state, duration)
        return AgentResult(
            success=lc.stage != LifecycleStage.FAILED,
            output=state["final_output"],
            tool_calls=state["tool_calls"],
            iterations=lc.current_iteration,
            memory_updates=state["memory_updates"],
            duration_ms=duration,
            checkpoint_count=state["checkpoint_count"],
            last_checkpoint=state["last_checkpoint"],
        )

    # ═══════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════

    def _init_lifecycle(self, ctx: AgentContext):
        """Create and initialize the TaskLifecycleController."""
        from kernel.lifecycle import TaskLifecycleController, LifecycleStage
        lc = TaskLifecycleController(ctx.goal, max_iterations=ctx.max_iterations)
        if lc.tracker.items:
            ctx.goal_tracker = lc.tracker
            logger.info("Lifecycle: %d goals, INIT → PLAN", len(lc.tracker.items))
        lc.transition(LifecycleStage.PLAN)
        return lc

    def _build_messages(self, ctx: AgentContext) -> list[dict]:
        """Assemble the message list: system prompt + handoff + mailbox + user goal."""
        base_prompt = self.system_prompt(ctx)
        try:
            base_prompt = get_skill_executor().inject_into_context(self.name, base_prompt)
        except Exception:
            pass

        messages = [{"role": "system", "content": base_prompt}]
        # v1.5.2: Team roster — so every agent knows their colleagues
        messages.append({"role": "system", "content": self._build_team_roster()})
        if ctx.handoff_context:
            hc = ctx.handoff_context
            messages.append({"role": "system", "content": (
                f"## 📋 交接上下文\n"
                f"总结: {hc.get('summary', '')}\n"
                f"完成状态: {hc.get('completion_status', '')}\n"
                f"产出物: {', '.join(hc.get('artifacts', []))}\n"
                f"警吿: {', '.join(hc.get('warnings', []))}\n"
                f"下一步: {', '.join(hc.get('next_steps', []))}\n"
            )})
        if ctx.mailbox_context:
            messages.append({"role": "system", "content": ctx.mailbox_context})
        if ctx.resume_from_checkpoint:
            ck = ctx.resume_from_checkpoint
            messages.append({"role": "system", "content": (
                f"⚠️ 断点恢复。上次执行到: {ck.get('step', '?')}。"
                f"已完成: {ck.get('completed', '?')}。请从断点处继续，不要重复。"
            )})
        messages.append({"role": "user", "content": ctx.goal})
        return messages

    # ═══════════════════════════════════════════════════════
    # TOOL EXECUTION
    # ═══════════════════════════════════════════════════════

    async def _run_tool_loop(self, tool_calls: list, lc, messages: list,
                             ctx: AgentContext, state: dict) -> bool:
        """Execute all tool calls in this LLM round. Returns True if should stop.

        Caps at MAX_TOOLS_PER_ITERATION to prevent exploration spirals.
        """
        from kernel.lifecycle import LifecycleStage

        MAX_TOOLS_PER_ITERATION = 8
        tool_idx = 0

        for tc in tool_calls:
            tool_idx += 1
            if tool_idx > MAX_TOOLS_PER_ITERATION:
                messages.append({
                    "role": "system",
                    "content": (
                        f"⚠️ 本轮已执行 {MAX_TOOLS_PER_ITERATION} 个工具调用。"
                        "请基于已获取的信息，直接执行用户要求的任务（创建文件、运行代码）。"
                        "停止浏览目录，立即开始工作。"
                    ),
                })
                break
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                func_args = {}

            await self._emit_tool_start(lc, func_name, func_args, ctx.session_id)

            # Approval gate
            gate = self._check_approval(tc, func_name, func_args, messages, state)
            if gate == "skip":
                continue

            # Execute
            result = await self.tools.execute(tool_name=func_name, **func_args)
            self._audit_tool(func_name, result, ctx)
            state["tool_calls"].append({
                "tool": func_name, "args": func_args,
                "success": result.success, "output": result.output[:500],
            })

            # Lifecycle records result
            vr = lc.record_tool_result(
                func_name, result.success,
                (result.output or "") if result.success
                else (result.error or result.output or f"{func_name} failed"),
                func_args,
            )
            await self._emit_lifecycle(lc, func_name, ctx.session_id, extra={
                "verify_result": vr.get("verify_result"),
                "recovery_message": vr.get("recovery_message", ""),
            })

            # Handle tool result
            stopped = self._handle_tool_result(
                tc, result, vr, func_name, messages)
            if stopped:
                return True

            # Checkpoint
            if len(state["tool_calls"]) % 3 == 0:
                state["last_checkpoint"] = self._save_checkpoint(
                    ctx, state["tool_calls"], state["checkpoint_count"],
                    f"iteration_{lc.current_iteration}_{func_name}")
                state["checkpoint_count"] += 1

            await self.event_bus.publish(Event(
                type=EventType.TOOL_CALL_END,
                data={"agent_id": self.id, "tool": func_name,
                      "success": result.success,
                      "lifecycle_stage": lc.stage.value,
                      "error_code": result.error_code if not result.success else "",
                      "error_message": result.error_message if not result.success else "",
                      "phase": lc.stage.value,
                      "retry_count": len([e for e in lc.error_manager.errors if e.tool_name == func_name and not e.recovered]),
                      "recovery": vr.get("recovery_message", "")[:100] if not result.success else "",
                      "duration_ms": round(result.duration_ms) if result.duration_ms else 0},
                source=self.name,
            ))

        return lc.stage in (LifecycleStage.COMPLETE, LifecycleStage.FAILED)

    def _check_approval(self, tc: dict, func_name: str, func_args: dict,
                        messages: list, state: dict) -> str:
        """Check approval layer. Returns 'skip', 'continue', or 'proceed'."""
        approval = self.tools.check_approval(func_name, func_args)
        if approval.blocked:
            state["tool_calls"].append({
                "tool": func_name, "args": func_args,
                "success": False, "output": f"🚫 {approval.reason}",
            })
            messages.append({
                "role": "tool", "tool_call_id": tc["id"],
                "content": f"Action blocked: {approval.reason}",
            })
            return "skip"
        if approval.needs_approval:
            state["tool_calls"].append({
                "tool": func_name, "args": func_args,
                "success": False, "output": f"⏸️ {approval.reason}",
            })
            messages.append({
                "role": "tool", "tool_call_id": tc["id"],
                "content": f"Requires human approval: {approval.reason}.",
            })
            return "skip"
        return "proceed"

    def _audit_tool(self, func_name: str, result, ctx: AgentContext) -> None:
        """Record tool execution in audit log."""
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

    def _handle_tool_result(self, tc: dict, result, vr: dict,
                            func_name: str, messages: list) -> bool:
        """Process tool result: inject recovery messages or pass output to LLM.
        Returns True if fatal → should stop."""
        if not result.success:
            recovery = vr.get("recovery_message", "")
            if recovery and "已停止" in recovery:
                return True  # Fatal
            if recovery:
                messages.append({
                    "role": "tool", "tool_call_id": tc["id"],
                    "content": recovery,
                })
            else:
                messages.append({
                    "role": "tool", "tool_call_id": tc["id"],
                    "content": result.output if result.success
                    else f"Error: {result.error}",
                })
        else:
            messages.append({
                "role": "tool", "tool_call_id": tc["id"],
                "content": result.output,
            })
        if not vr.get("should_continue", True):
            return True
        return False

    # ═══════════════════════════════════════════════════════
    # COMPLETION
    # ═══════════════════════════════════════════════════════

    def _append_progress(self, lc, state: dict) -> None:
        """Append goal progress to final output. Also applies minimum guard."""
        if not lc.tracker.items:
            if not state["final_output"].strip():
                state["final_output"] = "任务处理完毕。Agent 已完成当前步骤。"
            return
        progress = lc.tracker.progress()
        if not state["final_output"].strip():
            state["final_output"] = (
                f"Agent 执行完成。\n"
                f"目标进度：{progress['fulfilled']}/{progress['items']}。\n"
                f"阶段：{lc.stage.value}。"
            )
            return
        if lc.tracker.all_fulfilled():
            state["final_output"] += (
                f"\n\n✅ 任务完成：{progress['fulfilled']}/{progress['items']} 项要求已满足。"
            )
        else:
            remaining = "、".join(r.text[:40] for r in lc.tracker.remaining()[:5])
            state["final_output"] += (
                f"\n\n⚠️ 进度：{progress['fulfilled']}/{progress['items']} 已完成。待办：{remaining}"
            )

    async def _finalize(self, lc, ctx: AgentContext, state: dict) -> None:
        """Save checkpoint and emit completion event. API layer handles memory save."""
        # Note: message persistence is done by api/app.py:chat() — we only checkpoint here
        state["last_checkpoint"] = self._save_checkpoint(
            ctx, state["tool_calls"], state["checkpoint_count"], "completed")
        state["checkpoint_count"] += 1

        await self._emit_lifecycle(lc, "Completed", ctx.session_id, extra={
            "output_length": len(state["final_output"]),
            "goal_progress": lc.tracker.progress() if lc.tracker.items else None,
        })

    def _handle_crash(self, e: Exception, ctx: AgentContext,
                      state: dict, start_time: float) -> AgentResult:
        """Handle unexpected exceptions during agent execution."""
        logger.exception("Agent %s error", self.name)
        self._save_checkpoint(ctx, state["tool_calls"],
                             state["checkpoint_count"], f"crashed: {e}")
        err_duration = (time.time() - start_time) * 1000
        try:
            get_audit_log().record_error(
                self.name, str(e), detail=f"Agent {self.name} crashed",
                context={"goal": ctx.goal[:200], "iteration": ctx.current_iteration})
            get_reputation_registry().record(self.name, False, err_duration,
                                            tool_calls=len(state["tool_calls"]))
            get_skill_executor().record_execution(self.name, False, err_duration)
        except Exception:
            pass
        return AgentResult(
            success=False, error=str(e),
            tool_calls=state["tool_calls"],
            iterations=ctx.current_iteration,
            duration_ms=err_duration,
            checkpoint_count=state["checkpoint_count"],
            last_checkpoint=state["last_checkpoint"],
        )

    def _record_post_run(self, ctx: AgentContext, state: dict, duration: float) -> None:
        """Record reputation and skill execution after successful completion."""
        try:
            get_reputation_registry().record(
                self.name, True, duration,
                tool_calls=len(state["tool_calls"]),
                hit_max_iterations=ctx.current_iteration >= ctx.max_iterations)
        except Exception:
            pass
        try:
            get_skill_executor().record_execution(self.name, True, duration)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _build_team_roster() -> str:
        """Build the agent team roster for injection into system prompt."""
        from kernel.registry import get_agent_registry
        registry = get_agent_registry()
        agents = registry.list_all()
        if not agents:
            agents = get_agent_runtime().list_agents()
            lines = ["## 🤖 你的团队成员\n"]
            for a in agents:
                lines.append(f"- **{a.get('name', a.get('id', '?'))}**: {a.get('description', '')}")
        else:
            lines = ["## 🤖 你的团队成员\n"]
            for a in agents:
                lines.append(f"- **{a.name}** [{a.tier}]: {a.description}")
        lines.append(f"\n共 {len(agents)} 名成员。你是其中之一。\n")
        return "\n".join(lines)

    async def _emit_lifecycle(self, lc, action: str, session_id: str,
                             extra: dict | None = None) -> None:
        """Emit a lifecycle-aware event through the EventBus."""
        from kernel.lifecycle import LifecycleStage

        data: dict[str, Any] = {
            "agent_id": self.id, "agent_name": self.name,
            "lifecycle_stage": lc.stage.value,
            "iteration": lc.current_iteration,
            "session_id": session_id,
            "goal_progress": lc.tracker.progress(),
            "action": action,
        }
        if extra:
            data.update(extra)

        event_type = (EventType.AGENT_COMPLETED if lc.stage == LifecycleStage.COMPLETE
                      else EventType.AGENT_ERROR if lc.stage == LifecycleStage.FAILED
                      else EventType.AGENT_STARTED if lc.stage == LifecycleStage.INIT
                      else EventType.AGENT_THINKING)

        await self.event_bus.publish(Event(type=event_type, data=data, source=self.name))

    async def _emit_tool_start(self, lc, func_name: str, func_args: dict,
                               session_id: str) -> None:
        """Emit TOOL_CALL_START event."""
        await self.event_bus.publish(Event(
            type=EventType.TOOL_CALL_START,
            data={"agent_id": self.id, "tool": func_name, "args": func_args,
                  "session_id": session_id, "lifecycle_stage": lc.stage.value},
            source=self.name,
        ))

    def _save_checkpoint(self, ctx: AgentContext, tool_calls: list[dict],
                         count: int, step: str) -> dict | None:
        """Save execution checkpoint."""
        slug = ctx.project_slug or f"session_{ctx.session_id}"
        checkpoint = {
            "step": step, "iteration": ctx.current_iteration,
            "goal": ctx.goal[:200],
            "completed": f"{len([t for t in tool_calls if t['success']])}/{len(tool_calls)} tool calls succeeded",
            "last_tool": tool_calls[-1]["tool"] if tool_calls else "none",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.workspace.save_checkpoint(slug, checkpoint)
        except Exception:
            pass
        return checkpoint

    # Legacy streaming — unchanged
    async def run_stream(self, ctx: AgentContext) -> AsyncIterator[str]:
        messages = [
            {"role": "system", "content": self.system_prompt(ctx)},
            {"role": "user", "content": ctx.goal},
        ]
        while ctx.current_iteration < ctx.max_iterations:
            ctx.current_iteration += 1
            full_response = ""
            async for chunk in self.llm.chat_stream(messages, tools=self.tools.list_definitions()):
                full_response += chunk
                yield chunk
            if full_response:
                self.memory.save_message(ctx.session_id, "assistant", full_response,
                                        {"agent": self.name})
                break


# ═══════════════════════════════════════════════════════════
# AGENT RUNTIME (unchanged)
# ═══════════════════════════════════════════════════════════

from kernel.lifecycle import LifecycleStage  # noqa: E402 (used in run())

class AgentRuntime:
    """Manages agent instances, their lifecycle, and execution."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._active_runs: dict[str, AgentContext] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.id] = agent
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.id)

    def get(self, name_or_id: str) -> BaseAgent | None:
        return self._agents.get(name_or_id)

    def list_agents(self) -> list[dict]:
        seen = set()
        result = []
        for a in self._agents.values():
            if a.id not in seen:
                seen.add(a.id)
                result.append({"id": a.id, "name": a.name, "description": a.description})
        return result

    async def execute(self, agent_name: str, goal: str, session_id: str = "",
                      project_slug: str = "", resume: bool = False) -> AgentResult:
        agent = self.get(agent_name)
        if not agent:
            return AgentResult(success=False, error=f"Agent not found: {agent_name}")

        if not session_id:
            session_id = str(uuid.uuid4())[:8]

        context_mode = self._detect_context_mode(goal)
        memory_ctx = agent.memory.get_memory_context(query=goal, context_mode=context_mode)
        workspace = get_workspace()

        # v1.5.1: Don't auto-create workspace — let agent create files.
        # Auto-creating the directory before the agent runs causes the LLM
        # to see the directory already exists and think "task done."
        # if project_slug:
        #     workspace.create_project(project_slug, description=goal[:200])

        resume_data = None
        if resume and project_slug:
            resume_data = workspace.get_last_checkpoint(project_slug)

        ctx = AgentContext(
            session_id=session_id, goal=goal,
            user_profile=agent.memory.get_profile(),
            memory_context=memory_ctx, project_slug=project_slug,
            resume_from_checkpoint=resume_data, context_mode=context_mode,
        )
        self._active_runs[agent.id] = ctx
        try:
            return await agent.run(ctx)
        finally:
            self._active_runs.pop(agent.id, None)

    @staticmethod
    def _detect_context_mode(goal: str) -> str:
        gl = goal.lower()
        for kw in ["重新设计", "不要考虑之前", "从头开始", "推倒重来", "全新的",
                    "忽略之前", "重新想", "别管之前的", "清除上下文"]:
            if kw.lower() in gl:
                return "fresh_start"
        for kw in ["审计之前", "复盘", "检查之前", "回顾历史", "audit"]:
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
