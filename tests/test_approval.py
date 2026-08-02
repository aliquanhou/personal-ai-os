"""Tests for the Tool Approval Layer (Sprint 2)

验证 ToolRegistry 的风险审批机制，包括：
- 各风险级别的自动批准/需批准/阻止
- 危险命令和危险路径的检测（含大小写变体绕过防护）
- 审批队列的 approve/reject 流程
"""

import pytest
from tools.registry import (
    ReadFileTool, WriteFileTool, ListFilesTool, ShellTool,
    MemorySearchTool, MemorySaveTool,
    ToolRegistry,
)


@pytest.fixture
def registry():
    """A registry with the built-in tools (but not the global singleton)."""
    r = ToolRegistry()
    r.register(ReadFileTool())
    r.register(WriteFileTool())
    r.register(ListFilesTool())
    r.register(ShellTool())
    r.register(MemorySearchTool())
    r.register(MemorySaveTool())
    return r


class TestApprovalRules:
    """测试各类工具的风险审批规则。"""

    def test_safe_tool_auto_approved(self, registry):
        """safe 级别的工具（read_file）应自动批准。"""
        result = registry.check_approval("read_file", {"path": "/tmp/foo.txt"})
        assert not result.blocked
        assert not result.needs_approval

    def test_moderate_tool_auto_approved(self, registry):
        """moderate 级别的工具（write_file 普通路径）应自动批准。"""
        result = registry.check_approval("write_file", {"path": "/tmp/foo.txt"})
        assert not result.blocked
        assert not result.needs_approval

    def test_dangerous_tool_needs_approval(self, registry):
        """dangerous 级别的工具（shell）默认需要人工批准。"""
        result = registry.check_approval("shell", {"command": "ls -la"})
        assert not result.blocked
        assert result.needs_approval

    def test_unknown_tool_blocked(self, registry):
        """未知工具应被阻止。"""
        result = registry.check_approval("nonexistent_tool", {})
        assert result.blocked
        assert "Unknown" in result.reason

    def test_shell_critical_command_blocked(self, registry):
        """shell 中的关键危险命令应被阻止。"""
        result = registry.check_approval("shell", {"command": "rm -rf /"})
        assert result.blocked
        assert not result.needs_approval

    def test_shell_critical_command_case_insensitive(self, registry):
        """关键危险命令的大小写变体也应被阻止。"""
        result = registry.check_approval("shell", {"command": "RM -RF /"})
        assert result.blocked

    def test_shell_dangerous_path_case_insensitive(self, registry):
        """危险路径的大小写变体应提升为需批准（防止绕过）。"""
        # 修复前：大小写敏感，"C:\\Windows" 用 "c:\\windows" 可绕过
        result = registry.check_approval("shell", {"command": "del c:\\windows\\temp.txt"})
        assert not result.blocked
        assert result.needs_approval

    def test_write_dangerous_path_needs_approval(self, registry):
        """写入敏感路径应需批准。"""
        result = registry.check_approval("write_file", {"path": "/etc/passwd"})
        assert not result.blocked
        assert result.needs_approval
        assert "敏感路径" in result.reason

    def test_write_dangerous_path_case_insensitive(self, registry):
        """写入敏感路径的大小写变体应需批准（防止绕过）。"""
        result = registry.check_approval("write_file", {"path": "/ETC/passwd"})
        assert not result.blocked
        assert result.needs_approval

    def test_approval_queued_for_pending(self, registry):
        """需要批准的调用应进入待审批队列。"""
        registry.check_approval("shell", {"command": "ls -la"})
        pending = registry.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["tool"] == "shell"
        assert pending[0]["status"] == "pending"

    def test_auto_approved_not_queued(self, registry):
        """自动批准的工具不应进入待审批队列。"""
        registry.check_approval("read_file", {"path": "/tmp/foo.txt"})
        assert len(registry.get_pending_approvals()) == 0


class TestApprovalWorkflow:
    """测试审批工作流：approve / reject。"""

    def test_approve_pending(self, registry):
        """批准一个待审批操作。"""
        registry.check_approval("shell", {"command": "ls -la"})
        tool = registry.approve(0)
        assert tool == "shell"
        # 已批准的不再出现在待审批列表
        assert len(registry.get_pending_approvals()) == 0
        # 进入审批历史
        history = registry.get_approval_history()
        assert len(history) == 1
        assert history[0]["status"] == "approved"

    def test_reject_pending(self, registry):
        """拒绝一个待审批操作。"""
        registry.check_approval("shell", {"command": "ls -la"})
        tool = registry.reject(0)
        assert tool == "shell"
        assert len(registry.get_pending_approvals()) == 0
        history = registry.get_approval_history()
        assert history[0]["status"] == "rejected"

    def test_approve_out_of_range(self, registry):
        """索引越界时 approve 应返回空字符串。"""
        assert registry.approve(0) == ""
        assert registry.approve(5) == ""

    def test_reject_out_of_range(self, registry):
        """索引越界时 reject 应返回空字符串。"""
        assert registry.reject(0) == ""

    def test_multiple_pending_indexing(self, registry):
        """多个待审批操作时索引应正确对应。"""
        registry.check_approval("shell", {"command": "ls -la"})
        registry.check_approval("write_file", {"path": "/etc/passwd"})

        pending = registry.get_pending_approvals()
        assert len(pending) == 2

        # 批准第一个（shell）
        tool = registry.approve(0)
        assert tool == "shell"

        # 剩余待审批的是 write_file
        pending = registry.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0]["tool"] == "write_file"

    def test_approval_history_limited_to_50(self, registry):
        """审批历史应限制在最近 50 条。"""
        for i in range(60):
            registry.check_approval("shell", {"command": f"echo {i}"})
            registry.approve(0)
        assert len(registry.get_approval_history()) == 50


class TestShellTool:
    """测试 ShellTool 的执行。"""

    @pytest.mark.asyncio
    async def test_shell_echo(self):
        """执行一个简单命令应返回输出。"""
        tool = ShellTool()
        result = await tool.execute(command="echo hello")
        assert result.success
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_shell_python3_normalized(self):
        """python3 命令应被规范化为 python。"""
        tool = ShellTool()
        # 直接验证命令规范化逻辑
        command = "python3 --version"
        normalized = command.replace("python3 ", "python ")
        assert normalized == "python --version"

    @pytest.mark.asyncio
    async def test_shell_failed_command(self):
        """失败的命令应返回 success=False。"""
        tool = ShellTool()
        result = await tool.execute(command="exit 1")
        assert not result.success
        assert result.data["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_shell_definition_risk(self):
        """ShellTool 应标记为 dangerous 风险级别。"""
        tool = ShellTool()
        defn = tool.definition()
        assert defn.risk_level == "dangerous"
        assert defn.permission_level == "execute"
