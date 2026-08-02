"""Personal AI OS Tools — Tool Registry & Built-in Tools

The Tool system allows agents to perform real actions:
- File operations (read, write, list)
- Shell command execution
- Web search
- Memory operations
- Project management
"""

import json
import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: str = ""
    error: str = ""
    data: Any = None
    duration_ms: float = 0.0


@dataclass
class ToolDefinition:
    """Definition of a tool that can be called by agents."""
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters
    category: str = "general"
    permission_level: str = "read"
    risk_level: str = "safe"  # Sprint 2: safe/moderate/dangerous/critical
    handler: Any = None


@dataclass
class ApprovalResult:
    """Sprint 2: Result of an approval check."""
    blocked: bool = False
    needs_approval: bool = False
    reason: str = ""


RISK_RULES = {
    "safe": ApprovalResult(blocked=False, needs_approval=False, reason=""),
    "moderate": ApprovalResult(blocked=False, needs_approval=False, reason="Auto-approved: moderate risk"),
    "dangerous": ApprovalResult(blocked=False, needs_approval=True, reason="需要人工批准：高风险操作"),
    "critical": ApprovalResult(blocked=False, needs_approval=True, reason="需要人工批准：关键操作"),
}

DANGEROUS_PATTERNS = [
    "System32", "/etc/", "/var/", "C:\\Windows", "/boot",
    ".git/config", ".env.production", "production.yml",
]
CRITICAL_COMMANDS = [
    "rm -rf /", "DROP TABLE", "DELETE FROM", "shutdown",
    "format C:", "del /f /s C:\\", "DROP DATABASE",
]


def _find_bash() -> str:
    """Find the path to bash.exe for subprocess calls. Prefers Git Bash.

    On Windows, subprocess.run(['bash', ...]) often fails because Python's
    environment doesn't include Git Bash's /usr/bin in PATH. This resolves
    the actual bash.exe location.
    """
    import os
    candidates = [
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Windows\System32\bash.exe",
        "/usr/bin/bash",
        "/bin/bash",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_dir, "bash.exe")
        if os.path.isfile(candidate):
            return candidate
    return "bash"


class BaseTool(ABC):
    """Base class for all tools."""

    @abstractmethod
    def definition(self) -> ToolDefinition:
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...


# ── Built-in Tools ──────────────────────────────────────

class ReadFileTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a file at the given path.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "offset": {"type": "integer", "description": "Line offset to start reading from", "default": 0},
                    "limit": {"type": "integer", "description": "Max number of lines to read", "default": 200},
                },
                "required": ["path"],
            },
            category="file",
            permission_level="read",
            risk_level="safe",
        )

    async def execute(self, path: str = "", offset: int = 0, limit: int = 200) -> ToolResult:
        start = time.time()
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"File not found: {path}", duration_ms=(time.time() - start) * 1000)
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            selected = lines[offset:offset + limit]
            return ToolResult(
                success=True,
                output="\n".join(selected),
                data={"total_lines": len(lines), "offset": offset, "limit": limit},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)


class WriteFileTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["path", "content"],
            },
            category="file",
            permission_level="write",
            risk_level="moderate",
        )

    async def execute(self, path: str = "", content: str = "") -> ToolResult:
        start = time.time()
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"File written: {path} ({len(content)} chars)",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)


class ListFilesTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="list_files",
            description="List files in a directory.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "pattern": {"type": "string", "description": "Glob pattern to filter (e.g., *.py)", "default": "*"},
                },
                "required": ["path"],
            },
            category="file",
            permission_level="read",
            risk_level="safe",
        )

    async def execute(self, path: str = ".", pattern: str = "*") -> ToolResult:
        start = time.time()
        try:
            p = Path(path)
            if not p.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")
            files = sorted(p.glob(pattern))
            output = []
            for f in files[:200]:
                prefix = "[D]" if f.is_dir() else "[F]"
                size = f.stat().st_size if f.is_file() else 0
                output.append(f"{prefix} {f.name} ({size}B)")
            return ToolResult(
                success=True,
                output="\n".join(output),
                data={"count": len(files), "path": str(p.absolute())},
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)


class ShellTool(BaseTool):
    def definition(self):
        return ToolDefinition(
            name="shell",
            description="""Execute a shell command and return the output.

On Windows: commands run through bash (Git Bash). Use Unix-style syntax:
  - mkdir -p dir/          (not 'md' or 'mkdir dir\\')
  - ls -la                 (not 'dir')
  - python script.py       (not 'python3')
  - export VAR=val         (for env vars)
  - cd /d/path && command  (for changing directory)
  - command1 && command2   (for chaining)""",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute (bash syntax)"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                },
                "required": ["command"],
            },
            category="process",
            permission_level="execute",
            risk_level="dangerous",
        )

    async def execute(self, command: str = "", timeout: int = 30) -> ToolResult:
        start = time.time()
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
                    capture_output=True, text=True,
                    timeout=timeout, cwd=str(Path.cwd()),
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
                )
            else:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    timeout=timeout, cwd=str(Path.cwd()),
                )
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr
            return ToolResult(
                success=result.returncode == 0,
                output=output[:10000],
                data={"exit_code": result.returncode},
                duration_ms=(time.time() - start) * 1000,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s", duration_ms=timeout * 1000)
        except Exception as e:
            return ToolResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)


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
            description="Search the user's personal memory for relevant knowledge, decisions, and experiences.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Knowledge category filter", "default": ""},
                },
                "required": ["query"],
            },
            category="memory",
            permission_level="read",
            risk_level="safe",
        )

    async def execute(self, query: str = "", category: str = "") -> ToolResult:
        start = time.time()
        try:
            results = self.memory.search_knowledge(query, category=category or None)
            return ToolResult(
                success=True,
                output=json.dumps(results, ensure_ascii=False, indent=2),
                data=results,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
            description="Save a fact, knowledge, or decision to the user's personal memory.",
            parameters={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["knowledge", "decision", "experience", "task"]},
                    "title": {"type": "string", "description": "Title or summary"},
                    "content": {"type": "string", "description": "Full content"},
                    "category": {"type": "string", "description": "Category (for knowledge)", "default": "general"},
                    "importance": {"type": "number", "description": "Importance 0.0-1.0", "default": 0.5},
                },
                "required": ["type", "title", "content"],
            },
            category="memory",
            permission_level="write",
            risk_level="moderate",
        )

    async def execute(self, type: str = "knowledge", title: str = "", content: str = "",
                      category: str = "general", importance: float = 0.5) -> ToolResult:
        start = time.time()
        try:
            if type == "knowledge":
                self.memory.save_knowledge(title, content, category=category, importance=importance)
            elif type == "decision":
                self.memory.record_decision(context=title, chosen=content)
            elif type == "experience":
                self.memory.record_experience(title=title, description=content)
            elif type == "task":
                task_id = self.memory.create_task(title=title, description=content, project_id=category)
                return ToolResult(
                    success=True,
                    output=f"Task created: {task_id} — {title}",
                    duration_ms=(time.time() - start) * 1000,
                )
            return ToolResult(
                success=True,
                output=f"Saved {type}: {title}",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Sprint 3: Workspace Tools ────────────────────────────

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
            category="project",
            permission_level="write",
            risk_level="safe",
        )

    async def execute(self, name: str = "", description: str = "") -> ToolResult:
        start = time.time()
        try:
            from kernel.workspace import get_workspace
            ws = get_workspace()
            proj = ws.create_project(name, description)
            return ToolResult(
                success=True,
                output=f"Project workspace created: {proj['slug']} at {proj['path']}",
                data=proj,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
            category="project",
            permission_level="write",
            risk_level="safe",
        )

    async def execute(self, project_slug: str = "", step: str = "", details: str = "") -> ToolResult:
        start = time.time()
        try:
            from kernel.workspace import get_workspace
            ws = get_workspace()
            ws.save_checkpoint(project_slug, {"step": step, "completed": details})
            return ToolResult(
                success=True,
                output=f"Checkpoint saved: {step}",
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Sprint 6.5: Server Restart Tool ──────────────────────

class ServerRestartTool(BaseTool):
    """Precision server restart — kills process on a specific port, restarts cleanly.

    Unlike global 'taskkill -f -im python.exe' which kills ALL Python processes,
    this tool uses platform-specific port lookup to target only the server process.

    On Windows: netstat -ano | findstr :PORT → taskkill /PID
    On Linux:   lsof -ti :PORT → kill (or ss -tlnp)
    """

    def definition(self):
        return ToolDefinition(
            name="restart_server",
            description="""Stop and restart the Personal AI OS API server on a given port.

Only kills the process listening on the specified port — never all Python processes.
After stopping, starts a new server instance using 'python main.py serve --no-reload'.

On Windows (via bash): kills via netstat + taskkill /PID.
On Linux: kills via lsof -ti or ss.

Safe to run repeatedly — if no process is on the port, skips kill and restarts.""",
            parameters={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Server port (default: 8001)", "default": 8001},
                    "host": {"type": "string", "description": "Bind host (default: 127.0.0.1)", "default": "127.0.0.1"},
                    "project_dir": {"type": "string", "description": "Project root directory (default: auto-detect)", "default": ""},
                },
                "required": [],
            },
            category="process",
            permission_level="execute",
            risk_level="dangerous",
        )

    async def execute(self, port: int = 8001, host: str = "127.0.0.1",
                      project_dir: str = "") -> ToolResult:
        start = time.time()
        try:
            import platform
            import os

            # Resolve project directory
            if not project_dir:
                project_dir = str(Path(__file__).parent.parent)

            system = platform.system()
            kill_output = ""

            # ── Step 1: Kill process on target port ──
            if system == "Windows":
                kill_output = await self._kill_port_windows(port)
            else:
                kill_output = await self._kill_port_linux(port)

            # Brief wait for OS to release the port
            time.sleep(1.5)

            # ── Step 2: Start new server ──
            serve_cmd = (
                f"cd {project_dir} && "
                f"python main.py serve --host {host} --port {port} --no-reload"
            )

            is_windows = system == "Windows"
            if is_windows:
                serve_process = subprocess.Popen(
                    ["bash", "-c", serve_cmd],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=project_dir,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
            else:
                serve_process = subprocess.Popen(
                    serve_cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=project_dir,
                )

            # ── Step 3: Verify startup ──
            time.sleep(3)
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"http://{host}:{port}/health")
                    if resp.status_code == 200:
                        data = resp.json()
                        return ToolResult(
                            success=True,
                            output=(
                                f"Server restarted successfully.\n"
                                f"  Killed: {kill_output.strip() or 'no process found'}\n"
                                f"  Started: PID {serve_process.pid} on {host}:{port}\n"
                                f"  Health: {data.get('status', 'ok')} v{data.get('version', '?')}"
                            ),
                            data={
                                "pid": serve_process.pid,
                                "port": port,
                                "host": host,
                                "version": data.get("version", ""),
                            },
                            duration_ms=(time.time() - start) * 1000,
                        )
            except Exception as health_err:
                # Server might still be starting — return partial success
                return ToolResult(
                    success=True,
                    output=(
                        f"Server process started (PID {serve_process.pid}).\n"
                        f"  Killed: {kill_output.strip() or 'no process found'}\n"
                        f"  Health check: not yet responding ({health_err})"
                    ),
                    data={"pid": serve_process.pid, "port": port, "host": host},
                    duration_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Server restart failed: {e}",
                duration_ms=(time.time() - start) * 1000,
            )

    def _run_cmd(self, args: list[str], timeout: int = 10) -> str:
        """Run a command safely and return stdout, handling encoding issues."""
        import os
        result = subprocess.run(
            args, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return (result.stdout or "").strip()

    async def _kill_port_windows(self, port: int) -> str:
        """Find and kill the process on a given port using netstat + taskkill /PID."""
        import os

        bash = _find_bash()
        output = self._run_cmd(
            [bash, "-c", f"netstat -ano | grep ':{port} ' | grep LISTENING | head -5"],
        )

        killed = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit():
                    kill_output = self._run_cmd(["taskkill", "/PID", pid, "/F"])
                    killed.append(f"PID {pid}: {kill_output}")

        if not killed:
            return f"no process found on port {port}"
        return "; ".join(killed)

    async def _kill_port_linux(self, port: int) -> str:
        """Find and kill the process on a given port using lsof or ss."""
        import os

        output = self._run_cmd(["lsof", "-ti", f":{port}"])
        pids = [p for p in output.split("\n") if p.strip()]

        if not pids:
            bash = _find_bash()
            output = self._run_cmd(
                [bash, "-c", f"ss -tlnp 'sport = :{port}' | grep -oP 'pid=\\K\\d+'"],
            )
            pids = [p for p in output.split("\n") if p.strip()]

        killed = []
        for pid in pids:
            kill_output = self._run_cmd(["kill", pid])
            killed.append(f"PID {pid}: {kill_output or 'terminated'}")

        if not killed:
            return f"no process found on port {port}"
        return "; ".join(killed)


# ── Tool Registry ───────────────────────────────────────

class ToolRegistry:
    """Central registry for all available tools with approval layer."""

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

    # ── Sprint 2: Approval Layer ─────────────────────────

    def check_approval(self, name: str, args: dict) -> ApprovalResult:
        tool = self.get(name)
        if not tool:
            return ApprovalResult(blocked=True, needs_approval=False, reason=f"Unknown tool: {name}")

        defn = tool.definition()
        risk = defn.risk_level

        if name == "shell":
            command = args.get("command", "")
            cl = command.lower()
            for pattern in CRITICAL_COMMANDS:
                if pattern.lower() in cl:
                    return ApprovalResult(blocked=True, needs_approval=False,
                                         reason=f"禁止：命令包含危险操作 '{pattern}'")
            for pattern in DANGEROUS_PATTERNS:
                if pattern.lower() in cl:
                    risk = "dangerous"
                    break

        if name == "write_file":
            path = args.get("path", "")
            pl = path.lower()
            for pattern in DANGEROUS_PATTERNS:
                if pattern.lower() in pl:
                    return ApprovalResult(blocked=False, needs_approval=True,
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

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.exception("Tool execution error: %s", tool_name)
            return ToolResult(success=False, error=str(e))

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# Global singleton
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
        _registry.register(ServerRestartTool())
    return _registry
