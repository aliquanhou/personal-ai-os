"""Personal AI OS Kernel — Event Bus

A lightweight pub/sub event system that connects all components.
Events flow through here: Agent actions, Memory updates, Tool executions, UI notifications.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    # Agent lifecycle
    AGENT_STARTED = "agent:started"
    AGENT_THINKING = "agent:thinking"
    AGENT_ACTION = "agent:action"
    AGENT_COMPLETED = "agent:completed"
    AGENT_ERROR = "agent:error"

    # Tool execution
    TOOL_CALL_START = "tool:call:start"
    TOOL_CALL_END = "tool:call:end"
    TOOL_CALL_ERROR = "tool:call:error"

    # Memory
    MEMORY_SAVED = "memory:saved"
    MEMORY_RECALLED = "memory:recalled"
    MEMORY_UPDATED = "memory:updated"

    # System
    SYSTEM_STARTUP = "system:startup"
    SYSTEM_SHUTDOWN = "system:shutdown"
    SYSTEM_ERROR = "system:error"

    # User
    USER_MESSAGE = "user:message"
    USER_ACTION = "user:action"


@dataclass
class Event:
    type: EventType
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""


Handler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Central event bus — all kernel components communicate through this."""

    def __init__(self):
        self._subscribers: dict[EventType, list[Handler]] = defaultdict(list)
        self._global_handlers: list[Handler] = []
        self._event_log: list[Event] = []
        self._max_log_size = 10000

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(handler)

    def on_any(self, handler: Handler) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        handlers = self._subscribers.get(event.type, []) + self._global_handlers
        if not handlers:
            return

        tasks = []
        for handler in handlers:
            try:
                tasks.append(asyncio.create_task(handler(event)))
            except Exception:
                logger.exception("Failed to create handler task for event %s", event.type)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        if event_type:
            return [e for e in self._event_log if e.type == event_type][-limit:]
        return self._event_log[-limit:]

    def clear_log(self) -> None:
        self._event_log.clear()


# Global singleton
_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
