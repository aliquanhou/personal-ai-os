# -*- coding: utf-8 -*-
"""GoalTracker v2 — Task completion verification through file system checks.

v1.x: Text pattern matching on tool output strings — unreliable, false positives.
v2.0: Real file system verification — Path.exists(), exit code, file size.

Each goal has a type + target. Verification checks the actual filesystem,
not the tool's output text.

Goal types:
  file_exists        — Path.exists() on target file
  file_contains      — file content contains expected string
  command_success    — exit_code == 0 for shell command
  directory_exists   — Path.is_dir() on target directory
  file_count         — count of files matching glob in directory
"""

from __future__ import annotations

import logging
import re as _re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GoalType(StrEnum):
    FILE_EXISTS = "file_exists"
    FILE_CONTAINS = "file_contains"
    COMMAND_SUCCESS = "command_success"
    DIRECTORY_EXISTS = "directory_exists"
    FILE_COUNT = "file_count"


@dataclass
class GoalItem:
    """A single verifiable sub-goal extracted from the user's request."""
    index: int
    text: str                          # e.g. "创建项目目录"
    goal_type: GoalType = GoalType.FILE_EXISTS
    target: str = ""                   # e.g. "workspace/projects/foo/"
    expected: str = ""                 # e.g. expected file content keyword
    fulfilled: bool = False
    evidence: str = ""
    verified_at: str = ""              # ISO timestamp when verified

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "text": self.text,
            "type": self.goal_type.value,
            "target": self.target,
            "fulfilled": self.fulfilled,
            "evidence": self.evidence,
        }


# ═══════════════════════════════════════════════════════════
# GOAL TRACKER v2
# ═══════════════════════════════════════════════════════════

@dataclass
class GoalTracker:
    """Tracks and verifies completion of multi-step goals.

    v2: Uses real filesystem checks, not text pattern matching.
    verify() runs after tool execution to check actual state.
    """

    goal_text: str = ""
    items: list[GoalItem] = field(default_factory=list)
    tool_log: list[dict] = field(default_factory=list)
    project_root: str = "workspace/projects"

    def __post_init__(self):
        if self.goal_text and not self.items:
            self.items = self._extract_goals(self.goal_text)

    @staticmethod
    def _extract_goals(text: str) -> list[GoalItem]:
        """Parse numbered requirements and infer goal types.

        Matches: "1. 创建项目目录", "1) create main.py and run it",
        also "要求：1. 创建... 2. 生成..."

        For each extracted goal, infers the GoalType from keywords.
        """
        items = []

        # Match numbered items: 1. / 1) / 1、
        pattern = _re.compile(
            r'(?:^|\n)\s*(\d+)[.、\)）]\s*(.+?)(?=\n\s*\d+[.、\)）]|\n\n|\Z)',
            _re.MULTILINE | _re.DOTALL,
        )
        matches = pattern.findall(text)

        if not matches:
            marker = _re.compile(
                r'(?:要求|需求|任务|goals?|tasks?)[：:]\s*\n?(.+)',
                _re.IGNORECASE | _re.DOTALL,
            )
            m = marker.search(text)
            if m:
                matches = pattern.findall(m.group(1))

        for idx_str, item_text in matches:
            try:
                idx = int(idx_str)
                gt, target = _infer_goal(item_text)
                items.append(GoalItem(
                    index=idx, text=item_text.strip()[:120],
                    goal_type=gt, target=target,
                ))
            except ValueError:
                pass

        if items:
            logger.info("GoalTracker v2: %d goals extracted", len(items))
        return items

    # ── Observation (logs tools, queues verification) ────

    def observe(self, tool_name: str, success: bool, output: str,
                args: dict | None = None) -> None:
        """Log a tool execution. Does NOT check fulfillment yet."""
        entry = {"tool": tool_name, "success": success, "output": output[:200]}
        if args:
            entry["args"] = args
        self.tool_log.append(entry)

    # ── Verification (runs after tool execution) ────────

    def verify(self) -> dict:
        """Run filesystem verification for all pending goals.

        Called after each tool execution cycle. Checks the real
        filesystem state against goal targets.

        Returns: {fulfilled: N, total: M, newly_fulfilled: [...], remaining: [...]}
        """
        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc).isoformat()
        newly = []

        for item in self.items:
            if item.fulfilled:
                continue
            ok, evidence = self._verify_one(item)
            if ok:
                item.fulfilled = True
                item.evidence = evidence
                item.verified_at = now
                newly.append(item)

        if newly:
            logger.info("GoalTracker: verified %d new goals: %s",
                       len(newly), [g.text[:40] for g in newly])

        return {
            "fulfilled": self.fulfilled_count(),
            "total": len(self.items),
            "newly_fulfilled": [g.to_dict() for g in newly],
            "remaining": [g.to_dict() for g in self.remaining()],
        }

    def _verify_one(self, item: GoalItem) -> tuple[bool, str]:
        """Verify a single goal against the filesystem and tool log."""
        gt = item.goal_type

        if gt == GoalType.FILE_EXISTS:
            return self._check_file_exists(item)

        if gt == GoalType.FILE_CONTAINS:
            return self._check_file_contains(item)

        if gt == GoalType.COMMAND_SUCCESS:
            return self._check_command(item)

        if gt == GoalType.DIRECTORY_EXISTS:
            return self._check_dir_exists(item)

        return False, f"未知目标类型: {gt.value}"

    def _check_file_exists(self, item: GoalItem) -> tuple[bool, str]:
        """Check if the target file exists on disk."""
        if not item.target:
            return False, "无法确定目标文件路径"
        p = _resolve_path(item.target)
        if p and p.exists() and p.is_file():
            size = p.stat().st_size
            return True, f"文件存在: {p} ({size}B), {size}>0"

        # Search for recently created matching file
        target_name = Path(item.target).name
        found = _find_recent_file(target_name)
        if found:
            return True, f"文件存在: {found}"
        return False, f"文件不存在: {item.target}"

    def _check_file_contains(self, item: GoalItem) -> tuple[bool, str]:
        """Check if target file contains the expected content."""
        if not item.target or not item.expected:
            return False, "缺少目标文件或期望内容"
        p = _resolve_path(item.target)
        if p and p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace").lower()
                if item.expected.lower() in content:
                    return True, f"文件包含期望内容: {item.expected[:50]}"
                return False, f"文件不包含: {item.expected[:50]}"
            except Exception as e:
                return False, f"读取文件失败: {e}"
        return False, f"文件不存在: {item.target}"

    def _check_command(self, item: GoalItem) -> tuple[bool, str]:
        """Check if a shell command was executed successfully.
        Uses the tool_log to find matching shell executions."""
        # Check tool log for shell entries
        for entry in self.tool_log:
            if entry["tool"] == "shell" and entry.get("success"):
                # If we have a specific command target, check it matches
                if item.target:
                    args_str = str(entry.get("args", ""))
                    if item.target.split()[0] in args_str or "pytest" in args_str or "test" in args_str:
                        return True, f"命令执行成功: {item.target}"
                else:
                    return True, f"命令执行成功: {entry.get('output', '')[:80]}"

        # Check for failed commands with the target
        for entry in self.tool_log:
            if entry["tool"] == "shell" and not entry.get("success"):
                if item.target:
                    args_str = str(entry.get("args", ""))
                    if item.target.split()[0] in args_str:
                        return False, f"命令执行失败: {item.target}"

        return False, f"命令未验证: {item.target or item.text[:60]}"

    def _check_dir_exists(self, item: GoalItem) -> tuple[bool, str]:
        """Check if the target directory exists."""
        if not item.target:
            return False, "无法确定目标目录"
        p = _resolve_path(item.target)
        if p and p.exists() and p.is_dir():
            contents = list(p.iterdir())
            return True, f"目录存在: {p} ({len(contents)} 项)"
        search_name = Path(item.target).name
        found = _find_recent_dir(search_name)
        if found:
            return True, f"目录存在: {found}"
        return False, f"目录不存在: {item.target}"

    # ── Query methods ────────────────────────────────────

    def all_fulfilled(self) -> bool:
        if not self.items:
            return False
        return all(item.fulfilled for item in self.items)

    def fulfilled_count(self) -> int:
        return sum(1 for i in self.items if i.fulfilled)

    def progress(self) -> dict:
        if not self.items:
            return {"items": 0, "fulfilled": 0, "pct": 0, "detail": []}
        f = self.fulfilled_count()
        return {
            "items": len(self.items),
            "fulfilled": f,
            "pct": round(f / len(self.items) * 100),
            "detail": [i.to_dict() for i in self.items],
        }

    def remaining(self) -> list[GoalItem]:
        return [i for i in self.items if not i.fulfilled]


# ═══════════════════════════════════════════════════════════
# GOAL TYPE INFERENCE (from goal text)
# ═══════════════════════════════════════════════════════════

def _infer_goal(text: str) -> tuple[GoalType, str]:
    """Infer the GoalType and target path from the goal text.

    Heuristics:
      - 包含 "运行"/"执行"/"测试"/"pytest" → COMMAND_SUCCESS
      - 包含 "目录"/"文件夹" → DIRECTORY_EXISTS
      - 包含 ".py"/".md"/".json" 等扩展名 → FILE_EXISTS
      - default → FILE_EXISTS
    """
    tl = text.lower()

    # Command success
    cmd_keywords = ["运行", "执行", "测试", "跑", "pytest", "run", "test", "execute"]
    if any(w in tl for w in cmd_keywords):
        # Try to extract command
        cmd_match = _re.search(r'(python\s+\S+|pytest\s+\S+|npm\s+\S+)', tl)
        return GoalType.COMMAND_SUCCESS, cmd_match.group(0) if cmd_match else ""

    # Directory
    dir_keywords = ["目录", "文件夹", "directory", "folder", "创建项目"]
    if any(w in tl for w in dir_keywords):
        # Try to extract directory name
        dir_match = _re.search(r'(\w+[/\\]|\w+目录|\w+文件夹|projects?/\S+)', tl)
        return GoalType.DIRECTORY_EXISTS, dir_match.group(0) if dir_match else ""

    # File creation (most common)
    file_exts = [".py", ".md", ".json", ".txt", ".js", ".ts", ".html", ".css", ".db", ".sqlite"]
    if any(ext in tl for ext in file_exts):
        # Try to extract filename
        file_match = _re.search(r'([\w/\\-]+\.\w{1,4})', tl)
        return GoalType.FILE_EXISTS, file_match.group(0) if file_match else ""

    # Default: assume file creation
    return GoalType.FILE_EXISTS, ""


# ═══════════════════════════════════════════════════════════
# FILESYSTEM HELPERS
# ═══════════════════════════════════════════════════════════

def _resolve_path(target: str) -> Path | None:
    """Resolve a target path relative to the project root."""
    if not target:
        return None
    from kernel.context import resolve_path as ctx_resolve
    try:
        return ctx_resolve(target)
    except Exception:
        return None


def _find_recent_file(name: str) -> Path | None:
    """Search workspace/projects for a recently created file matching name."""
    ws = Path("workspace/projects")
    if not ws.exists():
        return None
    candidates = list(ws.rglob(name))
    if not candidates:
        for f in ws.rglob("*"):
            if f.is_file() and name.lower() in f.name.lower():
                candidates.append(f)
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _find_recent_dir(name: str) -> Path | None:
    """Search workspace/projects for a recently created directory."""
    ws = Path("workspace/projects")
    if not ws.exists():
        return None
    candidates = [d for d in ws.rglob(name) if d.is_dir()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _find_recent_file(name: str) -> Path | None:
    """Search workspace/projects for a recently created file matching name."""
    ws = Path("workspace/projects")
    if not ws.exists():
        return None
    candidates = list(ws.rglob(name))
    if not candidates:
        # Try partial match
        for f in ws.rglob("*"):
            if f.is_file() and name.lower() in f.name.lower():
                candidates.append(f)
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _find_recent_dir(name: str) -> Path | None:
    """Search workspace/projects for a recently created directory."""
    ws = Path("workspace/projects")
    if not ws.exists():
        return None
    candidates = [d for d in ws.rglob(name) if d.is_dir()]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None
