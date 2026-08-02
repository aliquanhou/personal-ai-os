"""Tests for Kernel components — Event Bus, Permission, Config"""

import pytest
from kernel.events import Event, EventBus, EventType, get_event_bus
from kernel.permission import (
    PermissionManager, Permission, PermissionLevel, ResourceType, PermissionCheck,
    get_permission_manager,
)
from kernel.config import Config, LLMConfig, MemoryConfig, ServerConfig


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self, bus):
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(EventType.AGENT_STARTED, handler)

        event = Event(type=EventType.AGENT_STARTED, data={"agent": "test"})
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].data["agent"] == "test"

    @pytest.mark.asyncio
    async def test_global_handler(self, bus):
        received = []

        async def handler(event: Event):
            received.append(event.type)

        bus.on_any(handler)

        await bus.publish(Event(type=EventType.AGENT_STARTED))
        await bus.publish(Event(type=EventType.TOOL_CALL_START))

        assert len(received) == 2
        assert EventType.AGENT_STARTED in received
        assert EventType.TOOL_CALL_START in received

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, bus):
        count = 0

        async def h1(event): nonlocal count; count += 1
        async def h2(event): nonlocal count; count += 1

        bus.subscribe(EventType.MEMORY_SAVED, h1)
        bus.subscribe(EventType.MEMORY_SAVED, h2)

        await bus.publish(Event(type=EventType.MEMORY_SAVED))
        assert count == 2

    def test_get_recent_events(self, bus):
        import asyncio
        async def run():
            for i in range(5):
                await bus.publish(Event(type=EventType.USER_MESSAGE, data={"n": i}))
        asyncio.run(run())

        events = bus.get_recent_events(limit=3)
        assert len(events) == 3
        assert events[-1].data["n"] == 4

    def test_filter_events_by_type(self, bus):
        import asyncio
        async def run():
            await bus.publish(Event(type=EventType.AGENT_STARTED, data={"id": 1}))
            await bus.publish(Event(type=EventType.AGENT_COMPLETED, data={"id": 2}))
        asyncio.run(run())

        started = bus.get_recent_events(EventType.AGENT_STARTED)
        assert len(started) == 1
        assert started[0].data["id"] == 1


class TestPermissionManager:
    @pytest.fixture
    def pm(self):
        return PermissionManager()

    def test_default_allow(self, pm):
        result = pm.check("agent-1", ResourceType.FILE, PermissionLevel.READ)
        assert result.allowed

    def test_grant_and_check(self, pm):
        pm.grant("agent-1", Permission(ResourceType.FILE, PermissionLevel.WRITE))
        result = pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE)
        assert result.allowed

    def test_insufficient_level(self, pm):
        pm.grant("agent-1", Permission(ResourceType.FILE, PermissionLevel.READ))
        result = pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE)
        assert not result.allowed

    def test_path_restriction(self, pm):
        pm.grant("agent-1", Permission(ResourceType.FILE, PermissionLevel.WRITE, path="/safe/*"))
        assert pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE, path="/safe/file.txt").allowed
        # With default allow, this passes — we didn't set default_allow=False
        assert pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE, path="/unsafe/file.txt").allowed

    def test_revoke(self, pm):
        pm.grant("agent-1", Permission(ResourceType.FILE, PermissionLevel.WRITE))
        pm.revoke("agent-1", ResourceType.FILE)
        result = pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE)
        # Falls back to default allow
        assert result.allowed

    def test_strict_mode(self, pm):
        pm._default_allow = False
        result = pm.check("agent-1", ResourceType.FILE, PermissionLevel.READ)
        assert not result.allowed

    def test_permission_level_ordering(self):
        pm = PermissionManager()
        pm.grant("agent-1", Permission(ResourceType.FILE, PermissionLevel.WRITE))
        # WRITE permission should allow READ
        assert pm.check("agent-1", ResourceType.FILE, PermissionLevel.READ).allowed
        # WRITE permission should allow WRITE
        assert pm.check("agent-1", ResourceType.FILE, PermissionLevel.WRITE).allowed
        # But not EXECUTE
        assert not pm.check("agent-1", ResourceType.FILE, PermissionLevel.EXECUTE).allowed


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.llm.provider == "deepseek"
        assert config.server.port == 8000
        assert config.memory.db_url.startswith("sqlite")

    def test_config_singleton(self):
        from kernel.config import get_config, set_config
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_custom_config(self):
        config = Config(
            llm=LLMConfig(provider="openai", model="gpt-4o"),
            server=ServerConfig(port=9000),
        )
        assert config.llm.provider == "openai"
        assert config.server.port == 9000


def test_global_singletons():
    """Verify all global singletons work correctly."""
    bus1 = get_event_bus()
    bus2 = get_event_bus()
    assert bus1 is bus2

    pm1 = get_permission_manager()
    pm2 = get_permission_manager()
    assert pm1 is pm2
