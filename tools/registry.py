# -*- coding: utf-8 -*-
"""Personal AI OS Tools — Tool Registry & Built-in Tools v1.4

All tools return the unified kernel.ToolResult contract.
Separate stdout/stderr. Structured error codes. No None returns.
"""

import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from kernel.tool_contract import ToolResult, ToolErrorCode, ContractViolation, ToolContract
from kernel.context import get_project_root, resolve_path

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by agents."""
    name: str
    description: str
    parameters: dict
    category: str = "general"
    permission_level: str = "read"
    risk_level: str = "safe"
    handler: Any = None


@dataclass
class ApprovalResult:
    """Sprint 2: Result of an approval check."""
    blocked: bool = False
    needs_approval: bool = False
    reason: str = ""


RISK_RULES = {
    "safe":           ApprovalResult(),
    "moderate":       ApprovalResult(reason="Auto-approved: moderate risk"),
    "workspace_safe": ApprovalResult(reason="Auto-approved: workspace scoped"),
    "dangerous":      ApprovalResult(needs_approval=True, reason="需要人工批准：高风险操作"),
    "critical":       ApprovalResult(needs_approval=True, reason="需要人工批准：关键操作"),
}

DANGEROUS_PATTERNS = [
    "System32", "/etc/", "/var/", "C:\\Windows", "/boot",
    ".git/config", ".env.production", "production.yml",
]
CRITICAL_COMMANDS = [
    "rm -rf /", "DROP TABLE", "DELETE FROM", "shutdown",
    "format C:", "del /f /s C:\\", "DROP DATABASE",
]

WORKSPACE_SAFE_COMMANDS = [
    "pytest", "python ", "python3 ", "npm test", "npm run", "pip install",
    "git status", "git diff", "git log", "git add", "git commit",
    "ls ", "cat ", "head ", "tail ", "wc ", "find ", "grep ",
    "echo ", "which ", "pwd", "mkdir ", "touch ",
    "curl http://localhost", "curl http://127.0.0.1",
    "cd /d/claude/personal-ai-os/workspace", "cd workspace", "cd projects",
]

SYSTEM_RISK_COMMANDS = [
    "pip install --global", "npm install -g", "sudo ", "su ",
    "git push", "git reset --hard origin", "git clean -fd",
    "chmod 777", "chown ", "systemctl ", "service ",
    "apt-get", "yum ", "brew ", "docker rm", "docker system prune",
    "rm ", "mv /", "cp /", "> /dev/",
]


class BaseTool(ABC):
    @abstractmethod
    def definition(self) -> ToolDefinition: ...
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...


# ── Helpers ──────────────────────────────────────────────

def _find_bash() -> str:
    """Find the path to bash.exe for subprocess calls."""
    import os
    candidates = [
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Windows\System32\bash.exe",
        "/usr/bin/bash", "/bin/bash",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    for d in os.environ.get("PATH", "").split(os.pathsep):
        c = os.path.join(d, "bash.exe")
        if os.path.isfile(c):
            return c
    return "bash"


def _run_cmd(args: list[str], timeout: int = 10) -> tuple[str, str, int]:
    """Run a command, return (stdout, stderr, exit_code)."""
    result = subprocess.run(args, capture_output=True, timeout=timeout,
                            encoding="utf-8", errors="replace")
    return (result.stdout or "").strip(), (result.stderr or "").strip(), result.returncode


# ═══════════════════════════════════════════════════════════
# BUILT-IN TOOLS (v1.4 — unified ToolResult contract)
# ═══════════════════════════════════════════════════════════

class ReadFileTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a file at the given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "offset": {"type": "integer", "description": "Line offset", "default": 0},
                    "limit": {"type": "integer", "description": "Max lines", "default": 200},
                },
                "required": ["path"],
            },
            category="file", permission_level="read", risk_level="safe",
        )

    async def execute(self, path: str = "", offset: int = 0, limit: int = 200) -> ToolResult:
        t0 = time.time()
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult.fail(ToolErrorCode.FILE_NOT_FOUND, f"文件不存在: {path}",
                                       duration_ms=(time.time() - t0) * 1000)
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            return ToolResult.ok(
                stdout="\n".join(lines[offset:offset + limit]),
                data={"total_lines": len(lines), "offset": offset, "limit": limit},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.FILE_NOT_FOUND, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class WriteFileTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
            category="file", permission_level="write", risk_level="moderate",
        )

    async def execute(self, path: str = "", content: str = "") -> ToolResult:
        t0 = time.time()
        try:
            p = resolve_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult.ok(
                stdout=f"File written: {p} ({len(content)} chars)",
                data={"path": str(p), "size": len(content)},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.WRITE_FAILED, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class ListFilesTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="list_files",
            description="List files in a directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
                },
                "required": ["path"],
            },
            category="file", permission_level="read", risk_level="safe",
        )

    async def execute(self, path: str = ".", pattern: str = "*") -> ToolResult:
        t0 = time.time()
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult.fail(ToolErrorCode.DIRECTORY_NOT_FOUND, f"目录不存在: {path}",
                                       duration_ms=(time.time() - t0) * 1000)
            files = sorted(p.glob(pattern))
            lines = []
            for f in files[:200]:
                prefix = "[D]" if f.is_dir() else "[F]"
                size = f.stat().st_size if f.is_file() else 0
                lines.append(f"{prefix} {f.name} ({size}B)")
            return ToolResult.ok(
                stdout="\n".join(lines),
                data={"count": len(files), "path": str(p.absolute())},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.DIRECTORY_NOT_FOUND, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class ShellTool(BaseTool):
    """v1.4: Separates stdout/stderr. Structured error codes on failure."""

    def definition(self):
        return ToolDefinition(
            name="shell",
            description="""Execute a shell command and return the output.

On Windows: commands run through bash (Git Bash). Use Unix-style syntax.""",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command (bash syntax)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                },
                "required": ["command"],
            },
            category="process", permission_level="execute", risk_level="workspace_safe",
        )

    async def execute(self, command: str = "", timeout: int = 30) -> ToolResult:
        t0 = time.time()
        try:
            import platform
            command = command.replace("python3 ", "python ").replace("python3\n", "python\n")
            if command.startswith("python3 "):
                command = "python " + command[8:]
            if command == "python3":
                command = "python"

            if platform.system() == "Windows":
                bash = _find_bash()
                result = subprocess.run(
                    [bash, "-c", command],
                    capture_output=True, text=True, timeout=timeout,
                    cwd=str(get_project_root()),
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                )
            else:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    timeout=timeout, cwd=str(get_project_root()),
                )

            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            duration = (time.time() - t0) * 1000

            if result.returncode == 0 and not stderr:
                return ToolResult.ok(stdout=stdout, duration_ms=duration)

            if result.returncode != 0:
                code = ToolContract.classify_error(stderr or stdout)
                return ToolResult.fail(
                    error_code=code,
                    error_message=stderr or stdout or f"命令退出码 {result.returncode}",
                    stdout=stdout,
                    stderr=stderr,
                    data={"exit_code": result.returncode},
                    duration_ms=duration,
                )

            # returncode == 0 but has stderr (warnings, etc.)
            return ToolResult.ok(
                stdout=stdout,
                stderr=stderr,
                data={"exit_code": result.returncode},
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            return ToolResult.fail(ToolErrorCode.TIMEOUT, f"命令超时 ({timeout}s)",
                                   duration_ms=timeout * 1000)
        except FileNotFoundError:
            return ToolResult.fail(ToolErrorCode.SHELL_NOT_FOUND, "Shell 不可用",
                                   duration_ms=(time.time() - t0) * 1000)
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.UNKNOWN_ERROR, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class MemorySearchTool(BaseTool):
    def __init__(self, memory_manager=None):
        self._memory = memory_manager

    @property
    def memory(self):
        if self._memory is None:
            from memory.manager import get_memory
            self._memory = get_memory()
        return self._memory

    def definition(self):
        return ToolDefinition(
            name="search_memory",
            description="Search the user's personal memory.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Category filter", "default": ""},
                },
                "required": ["query"],
            },
            category="memory", permission_level="read", risk_level="safe",
        )

    async def execute(self, query: str = "", category: str = "") -> ToolResult:
        t0 = time.time()
        try:
            results = self.memory.search_knowledge(query, category=category or None)
            return ToolResult.ok(
                stdout=json.dumps(results, ensure_ascii=False, indent=2),
                data={"results": results},
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.UNKNOWN_ERROR, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class MemorySaveTool(BaseTool):
    def __init__(self, memory_manager=None):
        self._memory = memory_manager

    @property
    def memory(self):
        if self._memory is None:
            from memory.manager import get_memory
            self._memory = get_memory()
        return self._memory

    def definition(self):
        return ToolDefinition(
            name="save_to_memory",
            description="Save a fact, knowledge, or decision to personal memory.",
            parameters={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["knowledge", "decision", "experience", "task"]},
                    "title": {"type": "string", "description": "Title or summary"},
                    "content": {"type": "string", "description": "Full content"},
                    "category": {"type": "string", "description": "Category", "default": "general"},
                    "importance": {"type": "number", "description": "Importance 0.0-1.0", "default": 0.5},
                },
                "required": ["type", "title", "content"],
            },
            category="memory", permission_level="write", risk_level="moderate",
        )

    async def execute(self, type: str = "knowledge", title: str = "", content: str = "",
                      category: str = "general", importance: float = 0.5) -> ToolResult:
        t0 = time.time()
        try:
            if type == "knowledge":
                self.memory.save_knowledge(title, content, category=category, importance=importance)
            elif type == "decision":
                self.memory.record_decision(context=title, chosen=content)
            elif type == "experience":
                self.memory.record_experience(title=title, description=content)
            elif type == "task":
                task_id = self.memory.create_task(title=title, description=content, project_id=category)
                return ToolResult.ok(stdout=f"Task created: {task_id} — {title}",
                                    duration_ms=(time.time() - t0) * 1000)
            return ToolResult.ok(stdout=f"Saved {type}: {title}",
                                duration_ms=(time.time() - t0) * 1000)
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.WRITE_FAILED, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class CreateProjectTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="create_project_workspace",
            description="Create a new project workspace with standardized structure.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name"},
                    "description": {"type": "string", "description": "Short description", "default": ""},
                },
                "required": ["name"],
            },
            category="project", permission_level="write", risk_level="safe",
        )

    async def execute(self, name: str = "", description: str = "") -> ToolResult:
        t0 = time.time()
        try:
            from kernel.workspace import get_workspace
            ws = get_workspace()
            proj = ws.create_project(name, description)
            return ToolResult.ok(
                stdout=f"Project created: {proj['slug']} at {proj['path']}",
                data=proj,
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.WRITE_FAILED, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


class SaveCheckpointTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="save_checkpoint",
            description="Save an execution checkpoint to the project workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "project_slug": {"type": "string", "description": "Project slug/name"},
                    "step": {"type": "string", "description": "Current step description"},
                    "details": {"type": "string", "description": "What was completed", "default": ""},
                },
                "required": ["project_slug", "step"],
            },
            category="project", permission_level="write", risk_level="safe",
        )

    async def execute(self, project_slug: str = "", step: str = "", details: str = "") -> ToolResult:
        t0 = time.time()
        try:
            from kernel.workspace import get_workspace
            ws = get_workspace()
            ws.save_checkpoint(project_slug, {"step": step, "completed": details})
            return ToolResult.ok(stdout=f"Checkpoint saved: {step}",
                                duration_ms=(time.time() - t0) * 1000)
        except Exception as e:
            return ToolResult.fail(ToolErrorCode.WRITE_FAILED, str(e),
                                   duration_ms=(time.time() - t0) * 1000)


# ═══════════════════════════════════════════════════════════
# TOOL REGISTRY (v1.4 — contract enforcement)
# ═══════════════════════════════════════════════════════════

class ToolRegistry:
    """Central registry for all available tools with contract enforcement."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._pending_approvals: list[dict] = []
        self._approval_history: list[dict] = []

    def register(self, tool: BaseTool) -> None:
        name = tool.definition().name
        self._tools[name] = tool
        logger.info("Registered tool: %s", name)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.definition().name,
                    "description": t.definition().description,
                    "parameters": t.definition().parameters,
                },
            }
            for t in self._tools.values()
        ]

    # ── Approval Layer ────────────────────────────────────

    def check_approval(self, name: str, args: dict) -> ApprovalResult:
        tool = self.get(name)
        if not tool:
            return ApprovalResult(blocked=True, reason=f"Unknown tool: {name}")

        defn = tool.definition()
        risk = defn.risk_level

        if name == "shell":
            command = args.get("command", "")
            cl = command.lower()
            for pattern in CRITICAL_COMMANDS:
                if pattern.lower() in cl:
                    return ApprovalResult(blocked=True,
                                         reason=f"禁止：命令包含危险操作 '{pattern}'")
            for pattern in SYSTEM_RISK_COMMANDS:
                if pattern.lower() in cl:
                    return ApprovalResult(needs_approval=True,
                                         reason=f"需要批准：系统级操作 '{pattern}'")
            for pattern in WORKSPACE_SAFE_COMMANDS:
                if cl.startswith(pattern.lower()):
                    risk = "workspace_safe"
                    break
            else:
                workspace_paths = ["workspace/", "workspace\\", "projects/"]
                if any(wp in cl for wp in workspace_paths):
                    risk = "workspace_safe"
                else:
                    for pattern in DANGEROUS_PATTERNS:
                        if pattern.lower() in cl:
                            risk = "dangerous"
                            break

        if name == "write_file":
            path = args.get("path", "")
            pl = path.lower()
            for pattern in DANGEROUS_PATTERNS:
                if pattern.lower() in pl:
                    return ApprovalResult(needs_approval=True,
                                         reason=f"需要批准：写入敏感路径 '{path}'")

        result = RISK_RULES.get(risk, RISK_RULES["safe"])
        if result.needs_approval:
            self._pending_approvals.append({
                "tool": name, "args": {k: str(v)[:200] for k, v in args.items()},
                "risk": risk, "reason": result.reason,
                "timestamp": str(time.time()), "status": "pending",
            })
        return result

    def get_pending_approvals(self) -> list[dict]:
        return [a for a in self._pending_approvals if a["status"] == "pending"]

    def approve(self, index: int) -> str:
        pending = [a for a in self._pending_approvals if a["status"] == "pending"]
        if 0 <= index < len(pending):
            pending[index]["status"] = "approved"
            self._approval_history.append(pending[index])
            return pending[index]["tool"]
        return ""

    def reject(self, index: int) -> str:
        pending = [a for a in self._pending_approvals if a["status"] == "pending"]
        if 0 <= index < len(pending):
            pending[index]["status"] = "rejected"
            self._approval_history.append(pending[index])
            return pending[index]["tool"]
        return ""

    def get_approval_history(self) -> list[dict]:
        return self._approval_history[-50:]

    # ── Contract-enforced execution ───────────────────────

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with contract enforcement on the result."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult.fail(ToolErrorCode.UNKNOWN_ERROR,
                                   f"Tool not found: {tool_name}")

        try:
            result = await tool.execute(**kwargs)
            if result is None:
                raise ContractViolation(f"Tool '{tool_name}' returned None")
            result.validate()
            return result
        except ContractViolation as e:
            logger.warning("Tool contract violation: %s — %s", tool_name, e)
            return ToolResult.fail(ToolErrorCode.INTERNAL_ERROR,
                                   f"工具协议违反: {tool_name} — {e}")
        except Exception as e:
            logger.exception("Tool execution error: %s", tool_name)
            return ToolResult.fail(ToolErrorCode.UNKNOWN_ERROR, str(e))

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# ═══════════════════════════════════════════════════════════
# GLOBAL SINGLETON
# ═══════════════════════════════════════════════════════════

_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.register(ReadFileTool())
        _registry.register(WriteFileTool())
        _registry.register(ListFilesTool())
        _registry.register(ShellTool())
        _registry.register(MemorySearchTool())
        _registry.register(MemorySaveTool())
        _registry.register(CreateProjectTool())
        _registry.register(SaveCheckpointTool())
    return _registry
