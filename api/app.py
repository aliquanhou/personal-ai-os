"""Personal AI OS API Server — FastAPI Application

Sprint 3: Agent Organization Layer — Registry + Router + Task Graph.

The API exposes all Personal AI OS capabilities:
- Chat with CEO agent (default), now with smart routing
- Identity & Boss Profile management
- Task lifecycle management
- Memory search & management
- Daily briefing generation
- Agent Registry & Team management
- Task Graph orchestration
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.ceo import CEOAgent
from agents.coding import CodingAgent, ResearchAgent, WritingAgent
from agents.project_manager import ProjectManagerAgent
from agents.reflection import ReflectionAgent
from agents.runtime import get_agent_runtime
from kernel.config import get_config
from kernel.registry import (
    AgentDescriptor,
    AgentRegistry,
    Capability,
    MemoryScope,
    Permission as AgentPermission,
    get_agent_registry,
)
from kernel.router import AgentRouter, RoutePlan, get_agent_router
from kernel.workspace import get_workspace, WorkspaceManager
from memory.manager import get_memory
from tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


# ── App Setup ──────────────────────────────────────────

app = FastAPI(
    title="Personal AI OS",
    description="Your personal AI operating system — AI Company Organization",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Register all agents in both Runtime and AgentRegistry (Sprint 3)."""
    runtime = get_agent_runtime()
    registry = get_agent_registry()

    # ── Create agent instances ──
    ceo = CEOAgent()
    pm = ProjectManagerAgent()
    coder = CodingAgent()
    researcher = ResearchAgent()
    writer = WritingAgent()
    reflector = ReflectionAgent()

    # ── Register in Runtime (existing) ──
    for a in [ceo, pm, coder, researcher, writer, reflector]:
        runtime.register(a)

    # ── Register in AgentRegistry (Sprint 3: formal descriptors) ──
    registry.register(AgentDescriptor(
        name="ceo", description="AI 幕僚长 — 理解目标、制定策略、协调团队、每日简报",
        capabilities=[Capability.ORCHESTRATION, Capability.STRATEGY, Capability.DECISION_MAKING,
                      Capability.TASK_ROUTING, Capability.BRIEFING, Capability.MEMORY_READ,
                      Capability.MEMORY_WRITE, Capability.REFLECTION,
                      Capability.PROJECT_PLANNING, Capability.ANALYSIS],
        permissions=[AgentPermission.MEMORY_READ, AgentPermission.MEMORY_WRITE,
                     AgentPermission.READ_WORKSPACE, AgentPermission.WRITE_WORKSPACE,
                     AgentPermission.MANAGE_AGENTS],
        memory_scope=[MemoryScope.ALL],
        tier="ceo",
        input_formats=["goal", "question", "command"],
        output_formats=["strategy", "plan", "briefing", "decision"],
        agent_ref=ceo,
    ))

    registry.register(AgentDescriptor(
        name="project_manager", description="项目管理 — 将目标转化为结构化项目计划和任务",
        capabilities=[Capability.PROJECT_PLANNING, Capability.TASK_EXECUTION,
                      Capability.FILE_OPS, Capability.MEMORY_WRITE, Capability.ANALYSIS],
        permissions=[AgentPermission.MEMORY_READ, AgentPermission.MEMORY_WRITE,
                     AgentPermission.READ_WORKSPACE, AgentPermission.WRITE_WORKSPACE],
        memory_scope=[MemoryScope.PROJECTS, MemoryScope.TASKS, MemoryScope.KNOWLEDGE],
        tier="manager",
        input_formats=["goal", "project_brief"],
        output_formats=["plan", "task_list", "project"],
        agent_ref=pm,
    ))

    registry.register(AgentDescriptor(
        name="coding_agent", description="代码专家 — 编写、审查、调试代码",
        capabilities=[Capability.CODE_GENERATION, Capability.CODE_REVIEW,
                      Capability.CODE_DEBUG, Capability.FILE_OPS, Capability.SHELL_EXEC,
                      Capability.TASK_EXECUTION],
        permissions=[AgentPermission.READ_WORKSPACE, AgentPermission.WRITE_WORKSPACE,
                     AgentPermission.EXEC_SHELL_SAFE],
        memory_scope=[MemoryScope.KNOWLEDGE, MemoryScope.EXPERIENCES, MemoryScope.PROJECTS],
        tier="specialist",
        input_formats=["task", "code", "bug_report"],
        output_formats=["code", "fix", "review"],
        agent_ref=coder,
    ))

    registry.register(AgentDescriptor(
        name="research_agent", description="研究分析 — 搜索信息、分析市场、综合发现",
        capabilities=[Capability.RESEARCH, Capability.ANALYSIS, Capability.WRITING,
                      Capability.MEMORY_READ, Capability.WEB_SEARCH],
        permissions=[AgentPermission.MEMORY_READ, AgentPermission.MEMORY_WRITE,
                     AgentPermission.READ_WORKSPACE, AgentPermission.EXTERNAL_NETWORK],
        memory_scope=[MemoryScope.KNOWLEDGE, MemoryScope.DECISIONS, MemoryScope.EXPERIENCES],
        tier="specialist",
        input_formats=["question", "topic", "market"],
        output_formats=["report", "analysis", "summary"],
        agent_ref=researcher,
    ))

    registry.register(AgentDescriptor(
        name="writing_agent", description="写作助手 — 撰写文档、报告、内容创作",
        capabilities=[Capability.WRITING, Capability.FILE_OPS, Capability.MEMORY_READ],
        permissions=[AgentPermission.READ_WORKSPACE, AgentPermission.WRITE_WORKSPACE],
        memory_scope=[MemoryScope.KNOWLEDGE, MemoryScope.CONVERSATIONS],
        tier="specialist",
        input_formats=["topic", "outline", "notes"],
        output_formats=["document", "article", "report"],
        agent_ref=writer,
    ))

    registry.register(AgentDescriptor(
        name="reflection_agent", description="反思教练 — 任务后深度分析，提炼经验教训",
        capabilities=[Capability.REFLECTION, Capability.ANALYSIS,
                      Capability.MEMORY_READ, Capability.MEMORY_WRITE],
        permissions=[AgentPermission.MEMORY_READ, AgentPermission.MEMORY_WRITE],
        memory_scope=[MemoryScope.EXPERIENCES, MemoryScope.DECISIONS, MemoryScope.TASKS],
        tier="utility",
        input_formats=["task_result", "execution_log"],
        output_formats=["reflection", "lesson", "improvement_plan"],
        agent_ref=reflector,
    ))

    # Build default teams
    registry.build_default_teams()

    config = get_config()
    logger.info("Personal AI OS v0.3.0 starting on %s:%s", config.server.host, config.server.port)
    logger.info("Agent Runtime: %s", [a["name"] for a in runtime.list_agents()])
    logger.info("Agent Registry: %s agents, %s teams",
                len(registry.list_all()), len(registry.list_teams()))


# ── Models ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    agent: str = "ceo"  # Default to CEO agent
    project_slug: str = ""  # Sprint 2: Workspace project
    resume: bool = False  # Sprint 2: Resume from checkpoint


class ChatResponse(BaseModel):
    session_id: str
    agent: str
    response: str
    tool_calls: list[dict] = []
    iterations: int = 0
    checkpoint_count: int = 0  # Sprint 2


class MemoryQuery(BaseModel):
    query: str = ""
    category: str = ""
    limit: int = 20


class MemorySave(BaseModel):
    type: str = "knowledge"
    title: str
    content: str
    category: str = "general"
    importance: float = 0.5


class ProfileUpdate(BaseModel):
    name: str | None = None
    bio: str | None = None
    skill_level: str | None = None
    tech_stack: list[str] | None = None
    goals: list[str] | None = None
    long_term_vision: str | None = None
    decision_principles: list[str] | None = None
    hates: list[str] | None = None
    work_style: dict | None = None


class IdentityUpdate(BaseModel):
    long_term_vision: str | None = None
    decision_principles: list[str] | None = None
    hates: list[str] | None = None
    work_style: dict | None = None


class GoalCreate(BaseModel):
    title: str
    description: str = ""
    category: str = "project"
    target_date: str = ""
    priority: int = 0


class GoalProgressUpdate(BaseModel):
    progress_pct: float
    status: str = ""


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    project_id: str = ""
    agent_name: str = ""
    priority: int = 0


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    goals: list[str] = []


# ── Routes: Health ─────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0", "name": "Personal AI OS"}


# ── Routes: Chat ───────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to an AI agent (default: CEO).

    Sprint 2: Supports workspace project scoping and checkpoint recovery.
    """
    runtime = get_agent_runtime()
    memory = get_memory()

    session_id = req.session_id or str(uuid.uuid4())[:8]

    # Save user message
    memory.save_message(session_id, "user", req.message)

    # Execute agent
    result = await runtime.execute(
        req.agent, req.message, session_id,
        project_slug=req.project_slug,
        resume=req.resume,
    )

    return ChatResponse(
        session_id=session_id,
        agent=req.agent,
        response=result.output,
        tool_calls=result.tool_calls,
        iterations=result.iterations,
        checkpoint_count=result.checkpoint_count,
    )


# ── Routes: Agents ─────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    """List available agents."""
    runtime = get_agent_runtime()
    return {"agents": runtime.list_agents()}


# ── Routes: Boss Profile & Identity ────────────────────

@app.get("/api/identity/boss-profile")
async def get_boss_profile():
    """Get the complete boss profile — all identity layers."""
    return get_memory().get_boss_profile()


@app.put("/api/identity")
async def update_identity(req: IdentityUpdate):
    """Update identity fields."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return get_memory().update_identity(**updates)


# ── Routes: Goals ──────────────────────────────────────

@app.get("/api/goals")
async def list_goals(status: str = "", category: str = ""):
    """List user goals."""
    return {
        "goals": get_memory().get_user_goals(
            status=status or None, category=category or None
        )
    }


@app.post("/api/goals")
async def create_goal(req: GoalCreate):
    """Create a new user goal."""
    goal_id = get_memory().add_user_goal(
        req.title, req.description, req.category, req.target_date, req.priority
    )
    return {"id": goal_id, "status": "created"}


@app.put("/api/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, req: GoalProgressUpdate):
    """Update goal progress."""
    get_memory().update_goal_progress(goal_id, req.progress_pct, req.status)
    return {"status": "ok"}


# ── Routes: Memory ─────────────────────────────────────

@app.get("/api/memory/profile")
async def get_profile():
    """Get user profile."""
    return get_memory().get_profile()


@app.put("/api/memory/profile")
async def update_profile(req: ProfileUpdate):
    """Update user profile."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    return get_memory().update_profile(**updates)


@app.get("/api/memory/conversations")
async def list_sessions(limit: int = 50):
    """List conversation sessions."""
    return {"sessions": get_memory().list_sessions(limit)}


@app.get("/api/memory/conversations/{session_id}")
async def get_conversation(session_id: str, limit: int = 100):
    """Get conversation messages."""
    return {"messages": get_memory().get_conversation(session_id, limit)}


@app.post("/api/memory/search")
async def search_memory(req: MemoryQuery):
    """Search knowledge base."""
    return {"results": get_memory().search_knowledge(req.query, category=req.category or None, limit=req.limit)}


@app.post("/api/memory/save")
async def save_to_memory(req: MemorySave):
    """Save to memory."""
    memory = get_memory()
    if req.type == "knowledge":
        memory.save_knowledge(req.title, req.content, req.category, importance=req.importance)
    elif req.type == "decision":
        memory.record_decision(context=req.title, chosen=req.content)
    elif req.type == "experience":
        memory.record_experience(title=req.title, description=req.content)
    elif req.type == "task":
        memory.create_task(title=req.title, description=req.content, project_id=req.category)
    return {"status": "ok"}


@app.get("/api/memory/knowledge/{category}")
async def get_knowledge(category: str, limit: int = 50):
    """Get knowledge by category."""
    return {"entries": get_memory().get_knowledge_by_category(category, limit)}


@app.get("/api/memory/decisions")
async def get_decisions(limit: int = 20):
    """Get recent decisions."""
    return {"decisions": get_memory().get_recent_decisions(limit)}


@app.get("/api/memory/experiences")
async def get_experiences(limit: int = 50):
    """Get experiences."""
    return {"experiences": get_memory().get_experiences(limit)}


# ── Routes: Tasks ──────────────────────────────────────

@app.post("/api/tasks")
async def create_task(req: TaskCreate):
    """Create a new task."""
    task_id = get_memory().create_task(
        req.title, req.description, req.project_id, req.agent_name, req.priority
    )
    return {"id": task_id, "state": "created"}


@app.put("/api/tasks/{task_id}/transition")
async def transition_task(task_id: str, new_state: str):
    """Transition a task to a new state."""
    ok = get_memory().transition_task(task_id, new_state)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Invalid transition to '{new_state}'")
    return {"status": "ok", "state": new_state}


@app.get("/api/tasks")
async def list_tasks(state: str = "", limit: int = 50):
    """List tasks, optionally filtered by state."""
    states = [state] if state else ["created", "planning", "executing", "waiting_human", "verifying"]
    return {"tasks": get_memory().get_tasks_by_state(states, limit)}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a single task."""
    task = get_memory().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/tasks/stats")
async def get_task_stats():
    """Get task statistics."""
    return get_memory().get_task_stats()


# ── Routes: Daily Briefing ─────────────────────────────

@app.get("/api/briefing/latest")
async def get_latest_briefing():
    """Get the most recent daily briefing."""
    briefing = get_memory().get_latest_briefing()
    if not briefing:
        raise HTTPException(status_code=404, detail="No briefings yet")
    return briefing


@app.get("/api/briefing/today")
async def get_today_briefing():
    """Get today's briefing (generates if not exists)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    memory = get_memory()
    briefing = memory.get_latest_briefing()
    # If latest isn't today, generate a new one
    if not briefing or briefing.get("date") != today:
        return {"status": "not_generated", "message": "今天的简报尚未生成。发送 '生成简报' 给 CEO Agent 来生成。"}
    return briefing


# ── Sprint 2: Workspace Routes ──────────────────────────

@app.get("/api/workspace")
async def list_workspace_projects(status: str = ""):
    """List workspace projects."""
    ws = get_workspace()
    return {"projects": ws.list_projects(status=status or "")}


@app.post("/api/workspace")
async def create_workspace_project(name: str, description: str = ""):
    """Create a new workspace project."""
    ws = get_workspace()
    proj = ws.create_project(name, description)
    return proj


@app.get("/api/workspace/{slug}")
async def get_workspace_project(slug: str):
    """Get a workspace project by slug."""
    ws = get_workspace()
    proj = ws.get_project(slug)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.get("/api/workspace/{slug}/checkpoints")
async def get_project_checkpoints(slug: str):
    """Get checkpoint history for a project."""
    ws = get_workspace()
    return {"checkpoints": ws.get_checkpoints(slug)}


@app.post("/api/workspace/{slug}/checkpoint")
async def save_project_checkpoint(slug: str, step: str, details: str = ""):
    """Save a manual checkpoint."""
    ws = get_workspace()
    ws.save_checkpoint(slug, {"step": step, "completed": details})
    return {"status": "ok"}


@app.get("/api/workspace/status")
async def get_workspace_status():
    """Get overall workspace status for daily briefing."""
    ws = get_workspace()
    return ws.get_workspace_status()


# ── Sprint 2: Approval Routes ───────────────────────────

@app.get("/api/approvals/pending")
async def get_pending_approvals():
    """Get pending human approval requests."""
    reg = get_tool_registry()
    return {"pending": reg.get_pending_approvals()}


@app.post("/api/approvals/{index}/approve")
async def approve_action(index: int):
    """Approve a pending action."""
    reg = get_tool_registry()
    tool_name = reg.approve(index)
    if not tool_name:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"status": "approved", "tool": tool_name}


@app.post("/api/approvals/{index}/reject")
async def reject_action(index: int):
    """Reject a pending action."""
    reg = get_tool_registry()
    tool_name = reg.reject(index)
    if not tool_name:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"status": "rejected", "tool": tool_name}


@app.get("/api/approvals/history")
async def get_approval_history():
    """Get approval/rejection history."""
    reg = get_tool_registry()
    return {"history": reg.get_approval_history()}


# ── Sprint 2: Enhanced Daily Briefing ───────────────────

@app.post("/api/briefing/generate")
async def generate_briefing():
    """Generate today's daily briefing from current state."""
    from datetime import datetime as _dt
    today = _dt.now(timezone.utc).strftime("%Y-%m-%d")

    memory = get_memory()
    ws = get_workspace()

    # Collect state from across the system
    task_stats = memory.get_task_stats()
    workspace_status = ws.get_workspace_status()
    recent_decisions = memory.get_recent_decisions(limit=5)
    recent_experiences = memory.get_experiences(limit=5)
    profile = memory.get_profile()
    active_goals = memory.get_user_goals(status="active")

    # Build briefing
    briefing_data = {
        "greeting": f"早上好，{profile.get('name', '老板')}。",
        "yesterday_summary": f"完成 {task_stats.get('by_state', {}).get('done', 0)} 个任务。",
        "discoveries": "",
        "today_suggestions": "",
        "long_term_progress": f"长期愿景: {profile.get('long_term_vision', '')[:100]}",
        "mood": "productive",
        "raw_json": {
            "task_stats": task_stats,
            "workspace_status": workspace_status,
            "recent_decisions": recent_decisions,
            "recent_experiences": recent_experiences,
            "active_goals": active_goals,
        },
    }

    briefing_id = memory.save_daily_briefing(today, briefing_data)
    return {"id": briefing_id, "date": today, "briefing": briefing_data}


# ── Routes: Projects ────────────────────────────────────

@app.get("/api/projects")
async def list_projects(status: str = "active"):
    """List projects."""
    return {"projects": get_memory().list_projects(status)}


@app.post("/api/projects")
async def create_project(req: ProjectCreate):
    """Create a new project."""
    project_id = get_memory().create_project(req.name, req.description, req.goals)
    return {"id": project_id, "status": "created"}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    project = get_memory().get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Sprint 3: Organization Routes ────────────────────

@app.get("/api/org/registry")
async def get_agent_registry_info():
    """Get the full agent registry with capabilities."""
    registry = get_agent_registry()
    return {
        "agents": [d.to_dict() for d in registry.list_all()],
        "teams": registry.list_teams(),
    }


@app.get("/api/org/agents/{agent_name}")
async def get_agent_descriptor(agent_name: str):
    """Get a single agent's capability descriptor."""
    registry = get_agent_registry()
    desc = registry.get(agent_name)
    if not desc:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    return desc.to_dict()


@app.get("/api/org/agents/by-capability/{capability}")
async def find_agents_by_capability(capability: str):
    """Find agents with a specific capability."""
    try:
        cap = Capability(capability)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")
    registry = get_agent_registry()
    return {"agents": [d.to_dict() for d in registry.find_by_capability(cap)]}


@app.get("/api/org/teams")
async def list_teams():
    """List available team configurations."""
    registry = get_agent_registry()
    return {"teams": registry.list_teams()}


@app.get("/api/org/teams/{team_name}")
async def get_team(team_name: str):
    """Get agents in a named team."""
    registry = get_agent_registry()
    team = registry.get_team(team_name)
    return {"team": team_name, "agents": [d.to_dict() for d in team]}


@app.post("/api/org/teams")
async def create_team(team_name: str, agent_names: list[str]):
    """Define a new team configuration."""
    registry = get_agent_registry()
    registry.define_team(team_name, agent_names)
    return {"status": "created", "team": team_name, "agents": agent_names}


# ── Sprint 3: Router & Task Graph ──────────────────────

@app.post("/api/org/plan")
async def plan_goal(goal: str):
    """Analyze a goal and produce a RoutePlan (no execution).

    Returns the task breakdown and agent assignments without executing.
    """
    router = get_agent_router()
    plan = await router.plan(goal)

    graph_dict = plan.graph.to_dict() if plan.graph else None

    return {
        "goal": plan.goal,
        "analysis": plan.analysis[:500],
        "agent_assignments": plan.agent_assignments,
        "execution_order": plan.execution_order,
        "estimated_duration": plan.estimated_duration,
        "graph": graph_dict,
    }


@app.post("/api/org/execute")
async def execute_goal(goal: str, session_id: str = "", project_slug: str = ""):
    """Plan AND execute a goal using the optimal agent team.

    This is the full orchestrated execution path:
    analyze → plan → build graph → dispatch → execute → collect results.
    """
    router = get_agent_router()
    plan = await router.plan(goal)
    result = await router.execute_plan(plan, session_id, project_slug)
    return result


@app.get("/api/org/graphs")
async def list_task_graphs():
    """List all task graphs."""
    store = get_task_graph_store()
    return {"graphs": store.list_all()}


@app.get("/api/org/graphs/{graph_id}")
async def get_task_graph(graph_id: str):
    """Get a specific task graph with progress."""
    store = get_task_graph_store()
    graph = store.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    return graph.to_dict()


# ── Sprint 3: Smart Chat (routed) ──────────────────────

class SmartChatRequest(BaseModel):
    message: str
    session_id: str = ""
    project_slug: str = ""
    mode: str = "auto"  # auto / single / team
    agent: str = ""       # Preferred agent (mode=single)
    team: str = ""         # Team name (mode=team)


@app.post("/api/chat/smart")
async def smart_chat(req: SmartChatRequest):
    """Smart chat with automatic routing.

    mode=auto: Router picks the best agent(s).
    mode=single: Use a specific agent.
    mode=team: Use a named team.
    """
    router = get_agent_router()
    session_id = req.session_id or str(uuid.uuid4())[:8]

    if req.mode == "single" and req.agent:
        result = await router.quick_route(
            req.message, session_id, preferred_agent=req.agent
        )
    elif req.mode == "team" and req.team:
        # Plan with team constraint — use team agents only for planning, then execute
        plan = router.plan(req.message)
        result = await router.execute_plan(plan, session_id, req.project_slug)
    else:
        # Auto: route to best single agent for simple tasks, or full team for complex
        plan = router.plan(req.message)
        # Use quick_route for simplicity unless goal is clearly multi-step
        result = await router.quick_route(req.message, session_id)

    return {
        "session_id": session_id,
        "mode": req.mode,
        "result": result,
    }


# ── Static Files (Studio) ──────────────────────────────

studio_path = Path(__file__).parent.parent / "studio" / "dist"
if studio_path.exists():
    app.mount("/", StaticFiles(directory=str(studio_path), html=True), name="studio")


# ── Main ────────────────────────────────────────────────

def main():
    import uvicorn
    config = get_config()
    uvicorn.run(
        "api.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
