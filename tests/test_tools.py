"""Tests for the Tool Calling system"""

import pytest
from pathlib import Path
from tools.registry import (
    ReadFileTool, WriteFileTool, ListFilesTool,
    MemorySearchTool, MemorySaveTool,
    ToolRegistry, get_tool_registry,
)


class TestFileTools:
    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return tmp_path

    @pytest.mark.asyncio
    async def test_read_file(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("line 1\nline 2\nline 3")

        tool = ReadFileTool()
        result = await tool.execute(path=str(f))
        assert result.success
        assert "line 1" in result.output

    @pytest.mark.asyncio
    async def test_read_file_with_offset(self, tmp_dir):
        f = tmp_dir / "test.txt"
        f.write_text("line 1\nline 2\nline 3\nline 4\nline 5")

        tool = ReadFileTool()
        result = await tool.execute(path=str(f), offset=2, limit=2)
        assert result.success
        lines = result.output.split("\n")
        assert lines[0] == "line 3"
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        tool = ReadFileTool()
        result = await tool.execute(path="/nonexistent/file.txt")
        assert not result.success

    @pytest.mark.asyncio
    async def test_write_file(self, tmp_dir):
        f = tmp_dir / "output.txt"
        tool = WriteFileTool()
        result = await tool.execute(path=str(f), content="hello world")
        assert result.success
        assert f.read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_directories(self, tmp_dir):
        f = tmp_dir / "deep" / "nested" / "file.txt"
        tool = WriteFileTool()
        result = await tool.execute(path=str(f), content="nested content")
        assert result.success
        assert f.read_text() == "nested content"

    @pytest.mark.asyncio
    async def test_list_files(self, tmp_dir):
        (tmp_dir / "a.py").write_text("")
        (tmp_dir / "b.py").write_text("")
        (tmp_dir / "c.txt").write_text("")

        tool = ListFilesTool()
        result = await tool.execute(path=str(tmp_dir), pattern="*.py")
        assert result.success
        assert result.data["count"] == 2
        assert "a.py" in result.output
        assert "b.py" in result.output
        assert "c.txt" not in result.output

    @pytest.mark.asyncio
    async def test_list_nonexistent_dir(self):
        tool = ListFilesTool()
        result = await tool.execute(path="/nonexistent")
        assert not result.success


class TestMemoryTools:
    @pytest.mark.asyncio
    async def test_memory_search(self):
        from memory.manager import MemoryManager
        memory = MemoryManager(db_url="sqlite:///:memory:")
        memory.save_knowledge("Test", "test content", category="test")

        tool = MemorySearchTool(memory_manager=memory)
        result = await tool.execute(query="test")
        assert result.success
        assert len(result.data) >= 1

    @pytest.mark.asyncio
    async def test_memory_save_knowledge(self):
        from memory.manager import MemoryManager
        memory = MemoryManager(db_url="sqlite:///:memory:")

        tool = MemorySaveTool(memory_manager=memory)
        result = await tool.execute(
            type="knowledge", title="New Fact", content="Something useful", category="general"
        )
        assert result.success

        # Verify it was saved
        results = memory.search_knowledge("New Fact")
        assert len(results) == 1


class TestToolRegistry:
    def test_register_and_get_tool(self):
        registry = ToolRegistry()
        tool = ReadFileTool()
        registry.register(tool)

        assert registry.get("read_file") is tool

    def test_list_definitions(self):
        registry = ToolRegistry()
        registry.register(ReadFileTool())
        registry.register(WriteFileTool())

        defs = registry.list_definitions()
        assert len(defs) == 2
        names = [d["function"]["name"] for d in defs]
        assert "read_file" in names
        assert "write_file" in names

    @pytest.mark.asyncio
    async def test_execute_tool(self, tmp_path):
        registry = ToolRegistry()
        registry.register(WriteFileTool())

        f = tmp_path / "test.txt"
        result = await registry.execute("write_file", path=str(f), content="test")
        assert result.success

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent_tool")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_global_registry_has_builtins(self):
        registry = get_tool_registry()
        names = registry.tool_names
        assert "read_file" in names
        assert "write_file" in names
        assert "list_files" in names
        assert "shell" in names
        assert "search_memory" in names
        assert "save_to_memory" in names
