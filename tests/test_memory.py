"""Tests for the Memory Kernel (P0-1)"""

import pytest
from memory.manager import MemoryManager
from memory.models import Base, Profile, Conversation, KnowledgeEntry, Decision, Experience, Project


class TestMemoryManager:
    """Test the memory manager with an in-memory SQLite database."""

    @pytest.fixture
    def memory(self):
        """Create an in-memory memory manager for testing."""
        mgr = MemoryManager(db_url="sqlite:///:memory:")
        return mgr

    def test_default_profile_created(self, memory):
        """A default profile should be created automatically."""
        profile = memory.get_profile()
        assert profile["name"] == "User"
        assert isinstance(profile["tech_stack"], list)

    def test_update_profile(self, memory):
        """Profile should be updatable."""
        memory.update_profile(name="张三", skill_level="advanced")
        profile = memory.get_profile()
        assert profile["name"] == "张三"
        assert profile["skill_level"] == "advanced"

    def test_update_profile_tech_stack(self, memory):
        """Tech stack should be updated correctly."""
        memory.update_profile(tech_stack=["Python", "Rust", "Go"])
        profile = memory.get_profile()
        assert "Rust" in profile["tech_stack"]

    def test_save_and_get_conversation(self, memory):
        """Messages should be saved and retrievable."""
        sid = "test-session-1"
        memory.save_message(sid, "user", "Hello")
        memory.save_message(sid, "assistant", "Hi there!")

        msgs = memory.get_conversation(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_list_sessions(self, memory):
        """Should list unique session IDs."""
        memory.save_message("s1", "user", "a")
        memory.save_message("s1", "assistant", "b")
        memory.save_message("s2", "user", "c")

        sessions = memory.list_sessions()
        assert len(sessions) == 2
        assert "s1" in sessions
        assert "s2" in sessions

    def test_save_and_search_knowledge(self, memory):
        """Knowledge should be searchable."""
        memory.save_knowledge(
            title="Python Best Practices",
            content="Use type hints and write docstrings.",
            category="tech",
            tags=["python", "coding"],
            importance=0.8,
        )
        memory.save_knowledge(
            title="Cooking Tips",
            content="Always salt your pasta water.",
            category="life",
            tags=["cooking"],
            importance=0.3,
        )

        results = memory.search_knowledge("Python")
        assert len(results) >= 1
        assert results[0]["title"] == "Python Best Practices"

        # Category filter
        results = memory.search_knowledge("salt", category="life")
        assert len(results) >= 1
        assert results[0]["title"] == "Cooking Tips"

    def test_get_knowledge_by_category(self, memory):
        """Should filter knowledge by category."""
        memory.save_knowledge("A", "content", category="tech")
        memory.save_knowledge("B", "content", category="life")

        tech = memory.get_knowledge_by_category("tech")
        assert len(tech) == 1
        assert tech[0]["title"] == "A"

    def test_record_and_get_decisions(self, memory):
        """Decisions should be recorded and retrievable."""
        memory.record_decision(
            context="选择数据库",
            chosen="PostgreSQL",
            options=["MySQL", "PostgreSQL", "MongoDB"],
            rationale="需要 JSON 支持和强事务",
        )

        decisions = memory.get_recent_decisions()
        assert len(decisions) == 1
        assert decisions[0]["chosen"] == "PostgreSQL"
        assert len(decisions[0]["options"]) == 3

    def test_record_experience(self, memory):
        """Experiences should be recordable."""
        memory.record_experience(
            title="Docker 部署踩坑",
            description="端口映射配置错误导致服务不可达",
            lesson="始终检查 docker-compose ports 配置",
            emotion="frustrated",
        )

        exps = memory.get_experiences()
        assert len(exps) == 1
        assert exps[0]["title"] == "Docker 部署踩坑"

    def test_create_and_get_project(self, memory):
        """Projects should be creatable and retrievable."""
        pid = memory.create_project(
            name="电商网站",
            description="一个完整的电商平台",
            goals=["用户注册登录", "商品展示", "购物车", "订单系统"],
        )

        project = memory.get_project(pid)
        assert project is not None
        assert project["name"] == "电商网站"
        assert len(project["goals"]) == 4

    def test_list_projects(self, memory):
        """Should list projects by status."""
        pid1 = memory.create_project("Active Project")
        pid2 = memory.create_project("Done Project")

        # Manually update status for the second project via internal API
        from memory.models import Project
        from sqlalchemy.orm import Session
        with Session(memory.engine) as session:
            p = session.query(Project).filter(Project.id == pid2).first()
            if p:
                p.status = "completed"
                session.commit()

        active = memory.list_projects("active")
        assert len(active) >= 1
        assert active[0]["name"] == "Active Project"

    def test_update_project_tasks(self, memory):
        """Project tasks should be updatable."""
        pid = memory.create_project("Test Project")
        tasks = [
            {"id": "1", "title": "Task 1", "status": "pending"},
            {"id": "2", "title": "Task 2", "status": "done"},
        ]
        memory.update_project_tasks(pid, tasks)

        project = memory.get_project(pid)
        assert len(project["tasks"]) == 2
        assert project["tasks"][0]["status"] == "pending"

    def test_memory_context(self, memory):
        """Memory context should include profile and relevant info."""
        memory.update_profile(name="李四", goals=["学习 AI", "创业"])
        memory.save_knowledge("AI 学习路线", "从 Python 开始学 ML...", category="tech")
        memory.record_decision(context="学习方向", chosen="深度学习")

        ctx = memory.get_memory_context(query="AI")
        assert "李四" in ctx
        assert "AI 学习路线" in ctx


class TestModels:
    """Test model instantiation."""

    def test_profile_creation(self):
        """Profile object creation — id is set on INSERT by SQLAlchemy default."""
        p = Profile(name="Test", skill_level="beginner", bio="", tech_stack="[]", goals="[]", preferences="{}")
        assert p.name == "Test"
        # id is set by the database on INSERT (SQLAlchemy Column default)
        # Before INSERT, it will be None — this is expected behavior

    def test_conversation_creation(self):
        c = Conversation(session_id="s1", role="user", content="hello")
        assert c.session_id == "s1"
        assert c.role == "user"

    def test_knowledge_creation(self):
        k = KnowledgeEntry(title="T1", content="C1", category="tech", importance=0.9)
        assert k.importance == 0.9

    def test_decision_creation(self):
        d = Decision(context="ctx", chosen="opt1", options='["opt1", "opt2"]')
        assert d.chosen == "opt1"
