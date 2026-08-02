"""Personal AI OS Kernel — Agent Communication Layer (Sprint 4)

Three communication primitives for multi-agent collaboration:

1. MAILBOX — Direct agent-to-agent messaging
   Agent A sends a message to Agent B's inbox. B reads it before its next action.

2. CHANNEL — Team-scoped broadcast
   All agents in a team share a channel. Messages broadcast to all members.

3. CONTEXT PROTOCOL — Structured handoff
   When Agent A finishes and Agent B starts, context passes through a
   standardized format so B knows what A did, what was found, and what's next.

Design principle: Plugin layer on top of existing Runtime.
No deep changes to BaseAgent — agents opt into communication.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# MESSAGE TYPES
# ═══════════════════════════════════════════════════════════

class MessageType(StrEnum):
    REQUEST = "request"         # "请帮我做X"
    RESPONSE = "response"       # "我已完成X，结果是Y"
    NOTIFICATION = "notification"  # "FYI: X发生了"
    HANDOFF = "handoff"         # "我的工作完成了，这是上下文，你来继续"
    QUESTION = "question"       # "在继续之前，我需要确认X"
    ALERT = "alert"             # "⚠️ 发现问题，需要关注"


class MessagePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AgentMessage:
    """A message from one agent to another (or to a team channel)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""            # Agent name
    recipient: str = ""         # Agent name, or "team:<team_name>", or "broadcast"
    msg_type: MessageType = MessageType.NOTIFICATION
    priority: MessagePriority = MessagePriority.NORMAL
    subject: str = ""
    body: str = ""
    context: dict = field(default_factory=dict)  # Structured handoff data
    reply_to: str = ""          # Message ID this replies to
    task_id: str = ""           # Related task ID
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.msg_type.value,
            "priority": self.priority.value,
            "subject": self.subject,
            "body": self.body[:500],
            "context_keys": list(self.context.keys()) if self.context else [],
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "read": self.read,
        }


# ═══════════════════════════════════════════════════════════
# CONTEXT PROTOCOL — STANDARDIZED HANDOFF FORMAT
# ═══════════════════════════════════════════════════════════

@dataclass
class HandoffContext:
    """Standardized context passed when one agent hands off to another.

    This is the lingua franca of the AI company. Every agent that finishes
    a task produces a HandoffContext. The next agent consumes it.
    """
    task_id: str = ""
    from_agent: str = ""
    to_agent: str = ""

    # What was accomplished
    summary: str = ""               # One-paragraph summary of what was done
    completion_status: str = ""     # "done" | "partial" | "blocked"

    # Key outputs
    key_findings: list[str] = field(default_factory=list)   # Discoveries
    artifacts: list[str] = field(default_factory=list)      # Files created/modified
    decisions: list[str] = field(default_factory=list)      # Decisions made

    # For the next agent
    next_steps: list[str] = field(default_factory=list)     # Recommended next actions
    warnings: list[str] = field(default_factory=list)        # Things to watch out for
    open_questions: list[str] = field(default_factory=list)  # Unresolved issues

    # Raw data
    raw_output: str = ""            # Full output from the agent
    metadata: dict = field(default_factory=dict)

    def to_message(self, recipient: str) -> AgentMessage:
        """Convert to an AgentMessage for sending."""
        return AgentMessage(
            sender=self.from_agent,
            recipient=recipient,
            msg_type=MessageType.HANDOFF,
            subject=f"Handoff: {self.summary[:80]}",
            body=self._format_body(),
            context={
                "findings": self.key_findings,
                "artifacts": self.artifacts,
                "decisions": self.decisions,
                "next_steps": self.next_steps,
                "warnings": self.warnings,
                "open_questions": self.open_questions,
            },
            task_id=self.task_id,
        )

    def _format_body(self) -> str:
        parts = [f"## 任务交接: {self.from_agent} → {self.to_agent}\n"]
        parts.append(f"### 完成情况: {self.completion_status}")
        parts.append(f"\n{self.summary}\n")
        if self.key_findings:
            parts.append("### 🔍 关键发现")
            for f in self.key_findings:
                parts.append(f"- {f}")
        if self.artifacts:
            parts.append("\n### 📁 产出物")
            for a in self.artifacts:
                parts.append(f"- {a}")
        if self.decisions:
            parts.append("\n### 📐 已做决策")
            for d in self.decisions:
                parts.append(f"- {d}")
        if self.next_steps:
            parts.append("\n### ➡️ 建议下一步")
            for s in self.next_steps:
                parts.append(f"- {s}")
        if self.warnings:
            parts.append("\n### ⚠️ 警告")
            for w in self.warnings:
                parts.append(f"- {w}")
        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# AGENT MAILBOX
# ═══════════════════════════════════════════════════════════

class AgentMailbox:
    """Per-agent inbox for receiving messages from other agents.

    Each agent gets one mailbox. Before processing a task, the agent
    checks its inbox for relevant context from teammates.
    """

    def __init__(self, owner_name: str):
        self.owner = owner_name
        self._inbox: list[AgentMessage] = []
        self._sent: list[AgentMessage] = []
        self._max_inbox = 200

    def receive(self, msg: AgentMessage) -> None:
        """Receive a message into the inbox."""
        self._inbox.append(msg)
        if len(self._inbox) > self._max_inbox:
            self._inbox = self._inbox[-self._max_inbox:]

    def send(self, msg: AgentMessage) -> None:
        """Record a sent message."""
        self._sent.append(msg)

    def get_unread(self, msg_type: MessageType | None = None,
                   from_agent: str = "", limit: int = 20) -> list[AgentMessage]:
        """Get unread messages, optionally filtered."""
        msgs = [m for m in self._inbox if not m.read]
        if msg_type:
            msgs = [m for m in msgs if m.msg_type == msg_type]
        if from_agent:
            msgs = [m for m in msgs if m.sender == from_agent]
        return msgs[-limit:]

    def get_context_for_task(self, task_id: str = "") -> str:
        """Build a context string from inbox messages relevant to a task.

        This is injected into the agent's system prompt so it knows
        what teammates have communicated to it.
        """
        relevant = [m for m in self._inbox if not m.read]
        if task_id:
            relevant = [m for m in relevant if m.task_id == task_id or not m.task_id]

        handoffs = [m for m in relevant if m.msg_type == MessageType.HANDOFF]
        requests = [m for m in relevant if m.msg_type == MessageType.REQUEST]
        alerts = [m for m in relevant if m.msg_type == MessageType.ALERT]

        if not (handoffs or requests or alerts):
            return ""

        parts = ["## 📬 收件箱 — 来自队友的消息\n"]

        for m in alerts[:3]:
            parts.append(f"⚠️ **{m.sender}** 发来警告: {m.subject}")
            parts.append(f"   {m.body[:200]}\n")

        for m in handoffs[:3]:
            parts.append(f"📋 **{m.sender}** 交接任务: {m.subject}")
            parts.append(f"   {m.body[:300]}\n")

        for m in requests[:3]:
            parts.append(f"📩 **{m.sender}** 请求: {m.subject}")
            parts.append(f"   {m.body[:200]}\n")

        return "\n".join(parts)

    def mark_read(self, msg_id: str) -> None:
        for m in self._inbox:
            if m.id == msg_id:
                m.read = True

    def mark_all_read(self) -> None:
        for m in self._inbox:
            m.read = True

    def stats(self) -> dict:
        unread = len([m for m in self._inbox if not m.read])
        return {
            "owner": self.owner,
            "inbox_total": len(self._inbox),
            "inbox_unread": unread,
            "sent_total": len(self._sent),
        }


# ═══════════════════════════════════════════════════════════
# TEAM CHANNEL
# ═══════════════════════════════════════════════════════════

class TeamChannel:
    """A communication channel shared by a team of agents.

    Messages posted to a channel are delivered to all members' mailboxes.
    """

    def __init__(self, team_name: str):
        self.name = team_name
        self.members: list[str] = []
        self._history: list[AgentMessage] = []
        self._max_history = 500
        self._pinned: list[str] = []  # Pinned message IDs

    def join(self, agent_name: str) -> None:
        if agent_name not in self.members:
            self.members.append(agent_name)

    def leave(self, agent_name: str) -> None:
        if agent_name in self.members:
            self.members.remove(agent_name)

    def broadcast(self, msg: AgentMessage, mailboxes: dict[str, AgentMailbox]) -> int:
        """Broadcast a message to all members. Returns delivery count."""
        self._history.append(msg)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        delivered = 0
        for member in self.members:
            if member != msg.sender and member in mailboxes:
                mailboxes[member].receive(msg)
                delivered += 1
        return delivered

    def pin(self, msg_id: str) -> None:
        if msg_id not in self._pinned:
            self._pinned.append(msg_id)

    def get_pinned(self) -> list[AgentMessage]:
        return [m for m in self._history if m.id in self._pinned]

    def get_recent(self, limit: int = 50) -> list[AgentMessage]:
        return self._history[-limit:]


# ═══════════════════════════════════════════════════════════
# COMMUNICATION BUS (CENTRAL ROUTER)
# ═══════════════════════════════════════════════════════════

class CommunicationBus:
    """Central hub for all inter-agent communication.

    Routes messages, manages mailboxes, and maintains channels.
    This is the "nervous system" of the AI company.
    """

    def __init__(self):
        self._mailboxes: dict[str, AgentMailbox] = {}    # agent_name → mailbox
        self._channels: dict[str, TeamChannel] = {}      # team_name → channel
        self._message_log: list[AgentMessage] = []        # All messages (for audit)

    # ── Mailbox management ───────────────────────────

    def register_agent(self, agent_name: str) -> AgentMailbox:
        """Create a mailbox for an agent."""
        if agent_name not in self._mailboxes:
            self._mailboxes[agent_name] = AgentMailbox(agent_name)
        return self._mailboxes[agent_name]

    def get_mailbox(self, agent_name: str) -> AgentMailbox | None:
        return self._mailboxes.get(agent_name)

    # ── Message routing ──────────────────────────────

    def route(self, msg: AgentMessage) -> int:
        """Route a message to its recipient(s). Returns delivery count."""
        self._message_log.append(msg)

        # Record in sender's sent box
        if msg.sender in self._mailboxes:
            self._mailboxes[msg.sender].send(msg)

        delivered = 0

        # Team broadcast
        if msg.recipient.startswith("team:"):
            team_name = msg.recipient[5:]
            channel = self._channels.get(team_name)
            if channel:
                delivered = channel.broadcast(msg, self._mailboxes)
        # Broadcast to all
        elif msg.recipient == "broadcast":
            for name, mb in self._mailboxes.items():
                if name != msg.sender:
                    mb.receive(msg)
                    delivered += 1
        # Direct message
        elif msg.recipient in self._mailboxes:
            self._mailboxes[msg.recipient].receive(msg)
            delivered = 1

        return delivered

    # ── Channel management ───────────────────────────

    def create_channel(self, team_name: str, members: list[str]) -> TeamChannel:
        """Create a team communication channel."""
        channel = TeamChannel(team_name)
        for member in members:
            channel.join(member)
            self.register_agent(member)
        self._channels[team_name] = channel
        return channel

    def get_channel(self, team_name: str) -> TeamChannel | None:
        return self._channels.get(team_name)

    def setup_default_channels(self) -> None:
        """Create channels for default teams."""
        from kernel.registry import get_agent_registry
        registry = get_agent_registry()
        for team_name in registry.list_teams():
            team = registry.get_team(team_name)
            members = [d.name for d in team]
            self.create_channel(team_name, members)
            logger.info("Created channel: %s (%d members)", team_name, len(members))

    # ── Handoff protocol ─────────────────────────────

    def handoff(self, from_agent: str, to_agent: str, context: HandoffContext) -> int:
        """Execute a formal handoff from one agent to another.

        The handoff context is converted to a message and routed.
        Both agents get a record.
        """
        context.from_agent = from_agent
        context.to_agent = to_agent
        msg = context.to_message(to_agent)
        return self.route(msg)

    # ── Status & stats ───────────────────────────────

    def get_organization_status(self) -> dict:
        """Get the communication status of the entire agent organization."""
        agent_stats = {}
        for name, mb in self._mailboxes.items():
            agent_stats[name] = mb.stats()

        channel_stats = {}
        for name, ch in self._channels.items():
            channel_stats[name] = {
                "members": ch.members,
                "message_count": len(ch._history),
            }

        return {
            "agents": agent_stats,
            "channels": channel_stats,
            "total_messages_routed": len(self._message_log),
        }

    def get_agent_inbox(self, agent_name: str) -> dict:
        """Get an agent's inbox status and messages."""
        mb = self._mailboxes.get(agent_name)
        if not mb:
            return {"error": f"No mailbox for {agent_name}"}
        return {
            "stats": mb.stats(),
            "unread": [m.to_dict() for m in mb.get_unread(limit=20)],
        }

    def get_channel_history(self, team_name: str, limit: int = 50) -> list[dict]:
        """Get recent messages from a team channel."""
        ch = self._channels.get(team_name)
        if not ch:
            return []
        return [m.to_dict() for m in ch.get_recent(limit)]

    def clear_agent_inbox(self, agent_name: str) -> None:
        """Mark all messages read for an agent (usually after context injection)."""
        mb = self._mailboxes.get(agent_name)
        if mb:
            mb.mark_all_read()


# Global singleton
_bus: CommunicationBus | None = None


def get_comm_bus() -> CommunicationBus:
    global _bus
    if _bus is None:
        _bus = CommunicationBus()
    return _bus
