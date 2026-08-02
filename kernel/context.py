# -*- coding: utf-8 -*-
"""Kernel Task Context — shared workspace root for all tools.

Solves the 'cwd drift' problem: ShellTool uses Path.cwd() (which is
studio/), WriteFileTool resolves from project_root. This module
provides a single source of truth for the working directory.

All tools call get_project_root() to get the same base path.
"""

from __future__ import annotations

from pathlib import Path

# Cached project root — computed once per process
_project_root: Path | None = None


def get_project_root() -> Path:
    """Return the project root directory (parent of kernel/).

    All tools should resolve relative paths against this directory,
    NOT against os.getcwd() which varies based on where the server
    was started.
    """
    global _project_root
    if _project_root is None:
        # kernel/context.py → kernel/ → project root
        _project_root = Path(__file__).parent.parent.resolve()
    return _project_root


def resolve_path(path: str, base: str = "workspace/projects") -> Path:
    """Resolve a relative path to an absolute one under the project root.

    If the path is already absolute, return it as-is.
    If the path already starts with 'workspace/projects/', resolve relative
    to project root (avoids double-prefixing).
    Otherwise resolve against <project_root>/<base>.
    """
    p = Path(path)
    if p.is_absolute():
        return p

    # Strip leading 'workspace/projects/' if present (LLM often includes it)
    clean = path.replace("\\", "/")
    if clean.startswith("workspace/projects/"):
        return (get_project_root() / clean).resolve()

    return (get_project_root() / base / path).resolve()


def get_workspace_root() -> Path:
    """Return the workspace/projects directory."""
    return get_project_root() / "workspace" / "projects"
