"""Personal AI OS API Server — FastAPI Application

Sprint 1: CEO Agent orchestration, Task State Machine, Reflection, Daily Briefing.

The API exposes all Personal AI OS capabilities:
- Chat with CEO agent (default)
- Identity & Boss Profile management
- Task lifecycle management
- Memory search & management
- Daily briefing generation
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
from kernel.workspace import get_workspace, WorkspaceManager
from memory.manager import get_memory
from tools.registry import get_tool_registry

logger = logging.getLogger(__name__)


# ── App Setup ──────────────────────────────────────────

app = FastAPI(
    title="Personal AI OS",
    description="Your personal AI operating system — AI Chief of Staff",
    version="0.2.0",
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
    """Register all agents on startup."""
    runtime = get_agent_runtime()
    runtime.register(CEOAgent())
    runtime.register(ProjectManagerAgent())
    runtime.register(CodingAgent())
    runtime.register(ResearchAgent())
    runtime.register(WritingAgent())
    runtime.register(ReflectionAgent())

    config = get_config()
    logger.info("Personal AI OS v0.2.0 starting on %s:%s", config.server.host, config.server.port)
    logger.info("Agents: %s", [a["name"] for a in runtime.list_agents()])


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
    return {"status": "ok", "version": "0.2.0", "name": "Personal AI OS"}


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
