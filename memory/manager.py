"""Personal AI OS Memory Kernel — Memory Manager

The Memory Manager is the central memory system. It stores and retrieves everything
the AI needs to know about the user: profile, conversations, knowledge, decisions, experiences.

This is P0-1: The soul of Personal AI OS.
"""

import json
import logging
import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import Session

from kernel.config import get_config
from kernel.events import Event, EventType, get_event_bus
from memory.models import (
    Base,
    Conversation,
    DailyBriefing,
    Decision,
    Experience,
    KnowledgeEntry,
    Profile,
    Project,
    Task,
    TaskState,
    UserGoal,
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """Central memory manager — one interface for all memory operations."""

    def __init__(self, db_url: Optional[str] = None):
        config = get_config()
        db_url = db_url or config.memory.db_url

        # Handle sqlite relative path — convert to absolute
        if db_url.startswith("sqlite"):
            db_path = db_url.replace("sqlite:///", "").replace("sqlite+aiosqlite:///", "")
            p = Path(db_path)
            if not p.is_absolute():
                # Make relative path absolute from project root
                project_root = Path(__file__).parent.parent
                p = (project_root / db_path).resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{p.as_posix()}"

        self.engine = create_engine(
            db_url.replace("sqlite+aiosqlite:///", "sqlite:///").replace("sqlite+aiosqlite://", "sqlite://"),
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
        Base.metadata.create_all(self.engine)
        self._ensure_profile()

    def _ensure_profile(self) -> None:
        """Ensure a default profile exists with rich identity."""
        with Session(self.engine) as session:
            profile = session.query(Profile).first()
            if not profile:
                profile = Profile(
                    name="User",
                    bio="A builder, creator, and entrepreneur.",
                    skill_level="intermediate",
                    tech_stack=json.dumps(["Python", "TypeScript", "React", "FastAPI"]),
                    goals=json.dumps(["Build useful AI tools"]),
                    preferences=json.dumps({"language": "zh-CN", "timezone": "Asia/Shanghai"}),
                    long_term_vision="建立一家 AI 产品公司，创造真正有用的 AI 工具",
                    decision_principles=json.dumps([
                        "快速验证优先于完美设计",
                        "开源和本地模型优先",
                        "不做重复造轮子的事",
                        "用户体验驱动技术选型",
                    ]),
                    hates=json.dumps(["重复造轮子", "过度工程化", "不落地的概念讨论"]),
                    work_style=json.dumps({
                        "peak_hours": "灵活",
                        "communication": "直接、简洁",
                        "preferred_tools": ["VS Code", "Git", "Claude Code"],
                    }),
                )
                session.add(profile)
                session.commit()
                logger.info("Created default user profile with identity")
            else:
                # Upgrade existing profile with new fields if empty
                upgraded = False
                if not profile.long_term_vision:
                    profile.long_term_vision = "建立一家 AI 产品公司，创造真正有用的 AI 工具"
                    upgraded = True
                if not profile.decision_principles or profile.decision_principles == "[]":
                    profile.decision_principles = json.dumps([
                        "快速验证优先于完美设计",
                        "开源和本地模型优先",
                        "不做重复造轮子的事",
                    ])
                    upgraded = True
                if not profile.hates or profile.hates == "[]":
                    profile.hates = json.dumps(["重复造轮子", "过度工程化", "不落地的概念讨论"])
                    upgraded = True
                if upgraded:
                    profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
                    session.commit()
                    logger.info("Upgraded existing profile with identity fields")

    # ── Profile ──────────────────────────────────────────

    def get_profile(self) -> dict:
        """Get the user profile as a dict."""
        with Session(self.engine) as session:
            profile = session.query(Profile).first()
            if not profile:
                return {}
            return {
                "id": profile.id,
                "name": profile.name,
                "bio": profile.bio,
                "skill_level": profile.skill_level,
                "tech_stack": json.loads(profile.tech_stack or "[]"),
                "goals": json.loads(profile.goals or "[]"),
                "preferences": json.loads(profile.preferences or "{}"),
                "long_term_vision": profile.long_term_vision or "",
                "decision_principles": json.loads(profile.decision_principles or "[]"),
                "hates": json.loads(profile.hates or "[]"),
                "work_style": json.loads(profile.work_style or "{}"),
            }

    def update_profile(self, **kwargs) -> dict:
        """Update profile fields."""
        with Session(self.engine) as session:
            profile = session.query(Profile).first()
            if not profile:
                profile = Profile()
                session.add(profile)

            for key, value in kwargs.items():
                if hasattr(profile, key):
                    if key in ("tech_stack", "goals", "preferences", "decision_principles", "hates"):
                        value = json.dumps(value) if not isinstance(value, str) else value
                    setattr(profile, key, value)

            profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
            session.commit()
            return self.get_profile()

    # ── Conversations ────────────────────────────────────

    def save_message(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> str:
        """Save a single message to a conversation."""
        with Session(self.engine) as session:
            msg = Conversation(
                session_id=session_id,
                role=role,
                content=content,
                metadata_=json.dumps(metadata or {}),
            )
            session.add(msg)
            session.commit()
            return msg.id

    def get_conversation(self, session_id: str, limit: int = 100) -> list[dict]:
        """Get messages from a conversation session."""
        with Session(self.engine) as session:
            msgs = (
                session.query(Conversation)
                .filter(Conversation.session_id == session_id)
                .order_by(Conversation.created_at)
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "metadata": json.loads(m.metadata_ or "{}"),
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                }
                for m in msgs
            ]

    def list_sessions(self, limit: int = 50) -> list[str]:
        """List unique conversation session IDs."""
        with Session(self.engine) as session:
            result = session.query(Conversation.session_id).distinct().order_by(
                desc(Conversation.created_at)
            ).limit(limit).all()
            return [r[0] for r in result]

    # ── Knowledge ───────────────────────────────────────

    def save_knowledge(self, title: str, content: str, category: str = "general",
                       tags: list[str] | None = None, source: str = "",
                       importance: float = 0.5) -> str:
        """Save a knowledge entry."""
        with Session(self.engine) as session:
            entry = KnowledgeEntry(
                title=title,
                content=content,
                category=category,
                tags=json.dumps(tags or []),
                source=source,
                importance=importance,
            )
            session.add(entry)
            session.commit()
            return entry.id

    def search_knowledge(self, query: str, category: str | None = None, limit: int = 20) -> list[dict]:
        """Search knowledge entries by title/content match."""
        with Session(self.engine) as session:
            q = session.query(KnowledgeEntry)
            if category:
                q = q.filter(KnowledgeEntry.category == category)
            # Simple LIKE search (future: vector search)
            q = q.filter(
                KnowledgeEntry.title.contains(query) | KnowledgeEntry.content.contains(query)
            ).order_by(desc(KnowledgeEntry.importance)).limit(limit)
            return [
                {
                    "id": e.id,
                    "title": e.title,
                    "content": e.content[:500],
                    "category": e.category,
                    "tags": json.loads(e.tags or "[]"),
                    "importance": e.importance,
                    "created_at": e.created_at.isoformat() if e.created_at else "",
                }
                for e in q.all()
            ]

    def get_knowledge_by_category(self, category: str, limit: int = 50) -> list[dict]:
        """Get knowledge entries by category."""
        with Session(self.engine) as session:
            entries = (
                session.query(KnowledgeEntry)
                .filter(KnowledgeEntry.category == category)
                .order_by(desc(KnowledgeEntry.importance))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": e.id,
                    "title": e.title,
                    "content": e.content,
                    "category": e.category,
                    "tags": json.loads(e.tags or "[]"),
                    "importance": e.importance,
                }
                for e in entries
            ]

    # ── Decisions ───────────────────────────────────────

    def record_decision(self, context: str, chosen: str, options: list[str] | None = None,
                        rationale: str = "", project_id: str = "") -> str:
        """Record a decision the user made."""
        with Session(self.engine) as session:
            decision = Decision(
                context=context,
                options=json.dumps(options or []),
                chosen=chosen,
                rationale=rationale,
                project_id=project_id,
            )
            session.add(decision)
            session.commit()
            return decision.id

    def get_recent_decisions(self, limit: int = 20) -> list[dict]:
        """Get recent decisions."""
        with Session(self.engine) as session:
            decisions = (
                session.query(Decision)
                .order_by(desc(Decision.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": d.id,
                    "context": d.context,
                    "options": json.loads(d.options or "[]"),
                    "chosen": d.chosen,
                    "rationale": d.rationale,
                    "outcome": d.outcome,
                }
                for d in decisions
            ]

    # ── Experiences ─────────────────────────────────────

    def record_experience(self, title: str, description: str, lesson: str = "",
                          emotion: str = "neutral", project_id: str = "") -> str:
        """Record an experience/lesson learned."""
        with Session(self.engine) as session:
            exp = Experience(
                title=title,
                description=description,
                lesson=lesson,
                emotion=emotion,
                project_id=project_id,
            )
            session.add(exp)
            session.commit()
            return exp.id

    def get_experiences(self, limit: int = 50) -> list[dict]:
        """Get recorded experiences."""
        with Session(self.engine) as session:
            exps = session.query(Experience).order_by(desc(Experience.created_at)).limit(limit).all()
            return [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "lesson": e.lesson,
                    "emotion": e.emotion,
                    "project_id": e.project_id,
                }
                for e in exps
            ]

    # ── Projects ────────────────────────────────────────

    def create_project(self, name: str, description: str = "", goals: list[str] | None = None) -> str:
        """Create a new project."""
        with Session(self.engine) as session:
            project = Project(
                name=name,
                description=description,
                goals=json.dumps(goals or []),
            )
            session.add(project)
            session.commit()
            return project.id

    def get_project(self, project_id: str) -> dict | None:
        """Get a project by ID."""
        with Session(self.engine) as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                return None
            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "tasks": json.loads(project.tasks_json or "[]"),
                "goals": json.loads(project.goals or "[]"),
                "created_at": project.created_at.isoformat() if project.created_at else "",
            }

    def list_projects(self, status: str = "active") -> list[dict]:
        """List projects by status."""
        with Session(self.engine) as session:
            projects = session.query(Project).filter(Project.status == status).all()
            return [
                {"id": p.id, "name": p.name, "description": p.description, "status": p.status}
                for p in projects
            ]

    def update_project_tasks(self, project_id: str, tasks: list[dict]) -> None:
        """Update project task list."""
        with Session(self.engine) as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                project.tasks_json = json.dumps(tasks)
                project.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()

    # ── Memory Context (for LLM injection) ──────────────

    def get_memory_context(self, query: str = "", max_items: int = 10) -> str:
        """Build a memory context string to inject into LLM prompts.

        This is the key method that gives the AI its "memory" — it assembles
        relevant profile info, recent decisions, knowledge, and experiences
        into a context block the LLM can use.
        """
        parts = []

        # User profile
        profile = self.get_profile()
        if profile:
            parts.append(f"""## User Profile
Name: {profile.get('name', 'Unknown')}
Skill Level: {profile.get('skill_level', 'intermediate')}
Tech Stack: {', '.join(profile.get('tech_stack', []))}
Goals: {', '.join(profile.get('goals', []))}
""")
            # Sprint 1: Rich identity
            if profile.get('long_term_vision'):
                parts.append(f"**Long-term Vision**: {profile['long_term_vision']}\n")
            if profile.get('decision_principles'):
                principles = profile['decision_principles']
                if isinstance(principles, str):
                    import json as _json
                    principles = _json.loads(principles)
                if principles:
                    parts.append("**Decision Principles**:")
                    for p in principles:
                        parts.append(f"  - {p}")
                    parts.append("")
            if profile.get('hates'):
                hates = profile['hates']
                if isinstance(hates, str):
                    import json as _json
                    hates = _json.loads(hates)
                if hates:
                    parts.append(f"**Avoids**: {', '.join(hates)}\n")

        # Sprint 1: User Goals with progress
        goals = self.get_user_goals(status="active")
        if goals:
            parts.append("## 🎯 Active Goals")
            for g in goals:
                bar = self._progress_bar(g['progress_pct'])
                parts.append(f"- [{g['category']}] {g['title']} {bar} {g['progress_pct']:.0f}%")
            parts.append("")

        # Recent decisions
        decisions = self.get_recent_decisions(limit=5)
        if decisions:
            parts.append("## Recent Decisions")
            for d in decisions:
                parts.append(f"- {d['context']} → Chose: {d['chosen']}")
            parts.append("")

        # Active tasks
        active_tasks = self.get_tasks_by_state(["executing", "waiting_human", "verifying"], limit=5)
        if active_tasks:
            parts.append("## Active Tasks")
            for t in active_tasks:
                parts.append(f"- [{t['state']}] {t['title']}")
            parts.append("")

        # Relevant knowledge
        if query:
            knowledge = self.search_knowledge(query, limit=max_items)
            if knowledge:
                parts.append("## Relevant Knowledge")
                for k in knowledge:
                    parts.append(f"- [{k['category']}] {k['title']}: {k['content'][:300]}")
                parts.append("")

        # Recent experiences
        experiences = self.get_experiences(limit=5)
        if experiences:
            parts.append("## Lessons Learned")
            for e in experiences:
                parts.append(f"- {e['title']}: {e['lesson']}")
            parts.append("")

        return "\n".join(parts) if parts else ""

    @staticmethod
    def _progress_bar(pct: float, width: int = 8) -> str:
        filled = int(pct / 100 * width)
        return "█" * filled + "░" * (width - filled)

    # ── Sprint 1: Identity Management ────────────────────

    def get_boss_profile(self) -> dict:
        """Get the complete boss profile — all identity layers."""
        profile = self.get_profile()
        goals = self.get_user_goals()
        decisions = self.get_recent_decisions(limit=10)
        experiences = self.get_experiences(limit=20)
        active_tasks = self.get_tasks_by_state(
            ["executing", "waiting_human", "verifying"], limit=10
        )
        return {
            "profile": profile,
            "goals": goals,
            "decisions": decisions,
            "experiences": experiences,
            "active_tasks": active_tasks,
        }

    def update_identity(self, **kwargs) -> dict:
        """Update identity fields (vision, principles, hates, work_style)."""
        with Session(self.engine) as session:
            profile = session.query(Profile).first()
            if not profile:
                profile = Profile()
                session.add(profile)
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    if key in ("decision_principles", "hates"):
                        value = json.dumps(value) if not isinstance(value, str) else value
                    elif key == "work_style":
                        value = json.dumps(value) if not isinstance(value, str) else value
                    setattr(profile, key, value)
            profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
            session.commit()
            return self.get_profile()

    # ── Sprint 1: User Goals ─────────────────────────────

    def get_user_goals(self, status: str | None = None, category: str | None = None) -> list[dict]:
        """Get user goals, optionally filtered by status/category."""
        with Session(self.engine) as session:
            q = session.query(UserGoal).order_by(UserGoal.priority.desc())
            if status:
                q = q.filter(UserGoal.status == status)
            if category:
                q = q.filter(UserGoal.category == category)
            return [
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "category": g.category,
                    "progress_pct": g.progress_pct,
                    "status": g.status,
                    "target_date": g.target_date,
                    "milestones": json.loads(g.milestones_json or "[]"),
                    "priority": g.priority,
                }
                for g in q.all()
            ]

    def add_user_goal(self, title: str, description: str = "", category: str = "project",
                      target_date: str = "", priority: int = 0) -> str:
        """Add a new user goal."""
        with Session(self.engine) as session:
            goal = UserGoal(
                title=title,
                description=description,
                category=category,
                target_date=target_date,
                priority=priority,
            )
            session.add(goal)
            session.commit()
            return goal.id

    def update_goal_progress(self, goal_id: str, progress_pct: float,
                             status: str = "") -> None:
        """Update goal progress percentage."""
        with Session(self.engine) as session:
            goal = session.query(UserGoal).filter(UserGoal.id == goal_id).first()
            if goal:
                goal.progress_pct = max(0, min(100, progress_pct))
                if status:
                    goal.status = status
                goal.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()

    # ── Sprint 1: Task State Machine ─────────────────────

    def create_task(self, title: str, description: str = "", project_id: str = "",
                    agent_name: str = "", priority: int = 0) -> str:
        """Create a new task in CREATED state."""
        with Session(self.engine) as session:
            task = Task(
                title=title,
                description=description,
                project_id=project_id,
                agent_name=agent_name,
                priority=priority,
                state=TaskState.CREATED,
            )
            session.add(task)
            session.commit()
            return task.id

    def transition_task(self, task_id: str, new_state: str) -> bool:
        """Transition a task to a new state. Returns True if valid transition."""
        if new_state not in TaskState.ALL:
            return False
        with Session(self.engine) as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            allowed = TaskState.TRANSITIONS.get(task.state, [])
            if new_state not in allowed:
                return False
            task.state = new_state
            task.updated_at = datetime.datetime.now(datetime.timezone.utc)
            if new_state in (TaskState.DONE, TaskState.LEARNED, TaskState.FAILED):
                task.completed_at = datetime.datetime.now(datetime.timezone.utc)
            session.commit()
            return True

    def update_task_result(self, task_id: str, result: dict) -> None:
        """Save execution result to a task."""
        with Session(self.engine) as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.result_json = json.dumps(result)
                task.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()

    def update_task_reflection(self, task_id: str, reflection: dict) -> None:
        """Save post-task reflection."""
        with Session(self.engine) as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.reflection_json = json.dumps(reflection)
                task.state = TaskState.LEARNED
                task.updated_at = datetime.datetime.now(datetime.timezone.utc)
                session.commit()

    def get_tasks_by_state(self, states: list[str], limit: int = 50) -> list[dict]:
        """Get tasks filtered by state(s)."""
        with Session(self.engine) as session:
            tasks = (
                session.query(Task)
                .filter(Task.state.in_(states))
                .order_by(Task.priority.desc(), Task.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": t.id,
                    "project_id": t.project_id,
                    "agent_name": t.agent_name,
                    "title": t.title,
                    "description": t.description,
                    "state": t.state,
                    "priority": t.priority,
                    "result": json.loads(t.result_json or "{}"),
                    "reflection": json.loads(t.reflection_json or "{}"),
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                    "completed_at": t.completed_at.isoformat() if t.completed_at else "",
                }
                for t in tasks
            ]

    def get_task(self, task_id: str) -> dict | None:
        """Get a single task by ID."""
        tasks = self.get_tasks_by_state(TaskState.ALL, limit=1)
        # Re-query for specific ID
        with Session(self.engine) as session:
            t = session.query(Task).filter(Task.id == task_id).first()
            if not t:
                return None
            return {
                "id": t.id,
                "project_id": t.project_id,
                "agent_name": t.agent_name,
                "title": t.title,
                "description": t.description,
                "state": t.state,
                "priority": t.priority,
                "result": json.loads(t.result_json or "{}"),
                "reflection": json.loads(t.reflection_json or "{}"),
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "completed_at": t.completed_at.isoformat() if t.completed_at else "",
            }

    def get_task_stats(self) -> dict:
        """Get task statistics for daily briefing."""
        with Session(self.engine) as session:
            total = session.query(Task).count()
            by_state = {}
            for state in TaskState.ALL:
                count = session.query(Task).filter(Task.state == state).count()
                if count:
                    by_state[state] = count
            recent = (
                session.query(Task)
                .filter(Task.completed_at.isnot(None))
                .order_by(Task.completed_at.desc())
                .limit(10)
                .all()
            )
            return {
                "total": total,
                "by_state": by_state,
                "recently_completed": [
                    {"id": t.id, "title": t.title, "state": t.state}
                    for t in recent
                ],
            }

    # ── Sprint 1: Daily Briefing ─────────────────────────

    def save_daily_briefing(self, date_str: str, briefing: dict) -> str:
        """Save or update a daily briefing."""
        with Session(self.engine) as session:
            existing = session.query(DailyBriefing).filter(DailyBriefing.date == date_str).first()
            if existing:
                for k, v in briefing.items():
                    if hasattr(existing, k):
                        if k in ("yesterday_summary", "discoveries", "today_suggestions",
                                 "long_term_progress", "raw_json"):
                            v = v if isinstance(v, str) else json.dumps(v)
                        setattr(existing, k, v)
                session.commit()
                return existing.id
            else:
                b = DailyBriefing(
                    date=date_str,
                    greeting=briefing.get("greeting", ""),
                    yesterday_summary=briefing.get("yesterday_summary", ""),
                    discoveries=briefing.get("discoveries", ""),
                    today_suggestions=briefing.get("today_suggestions", ""),
                    long_term_progress=briefing.get("long_term_progress", ""),
                    mood=briefing.get("mood", "neutral"),
                    raw_json=json.dumps(briefing),
                )
                session.add(b)
                session.commit()
                return b.id

    def get_latest_briefing(self) -> dict | None:
        """Get the most recent daily briefing."""
        with Session(self.engine) as session:
            b = session.query(DailyBriefing).order_by(DailyBriefing.date.desc()).first()
            if not b:
                return None
            return {
                "id": b.id,
                "date": b.date,
                "greeting": b.greeting,
                "yesterday_summary": b.yesterday_summary,
                "discoveries": b.discoveries,
                "today_suggestions": b.today_suggestions,
                "long_term_progress": b.long_term_progress,
                "mood": b.mood,
            }


# Global singleton
_memory: Optional[MemoryManager] = None


def get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory
