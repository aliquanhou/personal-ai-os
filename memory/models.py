# -*- coding: utf-8 -*-
"""Personal AI OS Memory Kernel — Database Models"""

import datetime as _dt
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def generate_id() -> str:
    return str(uuid.uuid4())[:12]


class Profile(Base):
    """User profile — who the user is, their context, preferences."""
    __tablename__ = "profile"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String(128), default="User")
    bio: Mapped[str] = mapped_column(Text, default="")
    skill_level: Mapped[str] = mapped_column(String(32), default="intermediate")
    tech_stack: Mapped[str] = mapped_column(Text, default="")  # JSON list
    goals: Mapped[str] = mapped_column(Text, default="")  # JSON list
    preferences: Mapped[str] = mapped_column(Text, default="{}")  # JSON object
    # New Sprint 1 fields — Boss Identity
    long_term_vision: Mapped[str] = mapped_column(Text, default="")  # 长期愿景
    decision_principles: Mapped[str] = mapped_column(Text, default="[]")  # JSON list — 决策原则
    hates: Mapped[str] = mapped_column(Text, default="[]")  # JSON list — 讨厌的事
    work_style: Mapped[str] = mapped_column(Text, default="{}")  # JSON — 工作风格
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc), onupdate=lambda: _dt.datetime.now(_dt.timezone.utc))


class UserGoal(Base):
    """Individual long-term goals with progress tracking."""
    __tablename__ = "user_goals"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="career")  # career/learning/project/life
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    status: Mapped[str] = mapped_column(String(32), default="active")  # active/paused/achieved/abandoned
    target_date: Mapped[str] = mapped_column(String(32), default="")  # ISO date or "ongoing"
    milestones_json: Mapped[str] = mapped_column("milestones", Text, default="[]")  # JSON list
    priority: Mapped[int] = mapped_column(Integer, default=0)  # higher = more important
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc), onupdate=lambda: _dt.datetime.now(_dt.timezone.utc))


class Conversation(Base):
    """A conversation session — messages exchanged with the user."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    session_id: Mapped[str] = mapped_column(String(32), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user / assistant / system / tool
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}")
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))


class KnowledgeEntry(Base):
    """Knowledge fragments — facts, concepts, references the AI has learned."""
    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="general")  # tech, business, personal, etc.
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    source: Mapped[str] = mapped_column(String(256), default="")
    embedding_id: Mapped[str] = mapped_column(String(64), default="")  # for future vector search
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc), onupdate=lambda: _dt.datetime.now(_dt.timezone.utc))


class Decision(Base):
    """Decisions the user has made — for future reference and consistency."""
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    context: Mapped[str] = mapped_column(Text)  # What was the situation
    options: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of options considered
    chosen: Mapped[str] = mapped_column(Text)  # What was chosen
    rationale: Mapped[str] = mapped_column(Text, default="")  # Why
    outcome: Mapped[str] = mapped_column(Text, default="")  # What happened (filled later)
    project_id: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))


class Experience(Base):
    """Experiences — what happened, lessons learned."""
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text, default="")  # What was learned
    emotion: Mapped[str] = mapped_column(String(32), default="neutral")
    project_id: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))


class Project(Base):
    """Projects the user is working on."""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="active")  # active/paused/completed/archived
    tasks_json: Mapped[str] = mapped_column("tasks", Text, default="[]")  # JSON list of tasks
    goals: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc), onupdate=lambda: _dt.datetime.now(_dt.timezone.utc))


# ── Sprint 1: Task State Machine ──────────────────────────

class TaskState:
    """Task state constants."""
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_HUMAN = "waiting_human"
    VERIFYING = "verifying"
    DONE = "done"
    LEARNED = "learned"
    FAILED = "failed"

    ALL = [CREATED, PLANNING, EXECUTING, WAITING_HUMAN, VERIFYING, DONE, LEARNED, FAILED]

    # Valid transitions
    TRANSITIONS = {
        CREATED: [PLANNING, FAILED],
        PLANNING: [EXECUTING, WAITING_HUMAN, FAILED],
        EXECUTING: [WAITING_HUMAN, VERIFYING, DONE, FAILED],
        WAITING_HUMAN: [EXECUTING, PLANNING, FAILED],
        VERIFYING: [DONE, EXECUTING, FAILED],
        DONE: [LEARNED],
        LEARNED: [],  # terminal
        FAILED: [CREATED, PLANNING],  # can retry
    }


class Task(Base):
    """A task in the state machine — tracks full lifecycle."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    project_id: Mapped[str] = mapped_column(String(32), default="")
    agent_name: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(32), default=TaskState.CREATED)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[str] = mapped_column("result", Text, default="{}")  # JSON — execution result
    reflection_json: Mapped[str] = mapped_column("reflection", Text, default="{}")  # JSON — post-task reflection
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc), onupdate=lambda: _dt.datetime.now(_dt.timezone.utc))
    completed_at: Mapped[_dt.datetime] = mapped_column(DateTime, nullable=True, default=None)


# ── Sprint 1: Daily Briefing ──────────────────────────────

class DailyBriefing(Base):
    """Auto-generated daily briefings from the AI Chief of Staff."""
    __tablename__ = "daily_briefings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_id)
    date: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM-DD
    greeting: Mapped[str] = mapped_column(Text, default="")
    yesterday_summary: Mapped[str] = mapped_column(Text, default="")  # 昨天完成了什么
    discoveries: Mapped[str] = mapped_column(Text, default="")  # 发现的风险/机会
    today_suggestions: Mapped[str] = mapped_column(Text, default="")  # 今天的建议
    long_term_progress: Mapped[str] = mapped_column(Text, default="")  # 长期目标进度
    mood: Mapped[str] = mapped_column(String(32), default="neutral")
    raw_json: Mapped[str] = mapped_column(Text, default="{}")  # Full structured data
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=lambda: _dt.datetime.now(_dt.timezone.utc))
