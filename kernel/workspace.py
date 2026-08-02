"""Personal AI OS Kernel — Workspace Manager

Sprint 2: Project state management with lifecycle tracking.

Every project gets a standardized directory structure:
    workspace/projects/<project-name>/
    ├── project.json       — metadata (name, description, goals, status)
    ├── state.json         — runtime state (checkpoints, active tasks, last action)
    ├── decisions.json     — decisions made within this project
    ├── artifacts/          — actual project files (code, docs, etc.)
    └── backups/            — auto-backups of state transitions
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Project root for all workspaces
WORKSPACE_ROOT = Path(__file__).parent.parent / "workspace" / "projects"


class WorkspaceManager:
    """Manages project workspaces — the filesystem home for AI employee work.

    Each project is a self-contained directory. The AI can save/load state,
    checkpoint progress, and recover from failures.
    """

    def __init__(self, root: Path | None = None):
        self.root = root or WORKSPACE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    # ── Project Lifecycle ────────────────────────────────

    def create_project(self, name: str, description: str = "",
                       goals: list[str] | None = None) -> dict:
        """Create a new project workspace."""
        slug = self._slugify(name)
        project_dir = self.root / slug
        if project_dir.exists():
            # Project already exists — return existing
            return self.get_project(slug)

        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "artifacts").mkdir(exist_ok=True)
        (project_dir / "backups").mkdir(exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        project_meta = {
            "name": name,
            "slug": slug,
            "description": description,
            "goals": goals or [],
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        (project_dir / "project.json").write_text(
            json.dumps(project_meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        state = {
            "last_checkpoint": None,
            "checkpoint_history": [],
            "active_tasks": [],
            "last_action": {"type": "created", "timestamp": now},
            "status": "active",
        }
        (project_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        (project_dir / "decisions.json").write_text("[]", encoding="utf-8")

        logger.info("Created project workspace: %s", slug)
        return self.get_project(slug)

    def get_project(self, slug: str) -> dict | None:
        """Get project metadata."""
        project_dir = self.root / slug
        if not project_dir.exists():
            return None
        meta = self._read_json(project_dir / "project.json")
        state = self._read_json(project_dir / "state.json")
        decisions = self._read_json(project_dir / "decisions.json")
        artifacts = self._list_artifacts(project_dir / "artifacts")
        return {
            "slug": slug,
            "path": str(project_dir),
            "meta": meta or {},
            "state": state or {},
            "decisions": decisions or [],
            "artifacts": artifacts,
        }

    def list_projects(self, status: str = "") -> list[dict]:
        """List all projects, optionally filtered by status."""
        projects = []
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and (d / "project.json").exists():
                meta = self._read_json(d / "project.json")
                if meta:
                    if status and meta.get("status") != status:
                        continue
                    projects.append({"slug": d.name, "name": meta.get("name", d.name),
                                    "status": meta.get("status", "unknown"),
                                    "updated_at": meta.get("updated_at", "")})
        return projects

    def update_project_status(self, slug: str, status: str) -> bool:
        """Update project status (active/paused/completed/archived)."""
        return self._update_meta(slug, {"status": status})

    def delete_project(self, slug: str, archive: bool = True) -> bool:
        """Delete (or archive) a project."""
        project_dir = self.root / slug
        if not project_dir.exists():
            return False
        if archive:
            archive_dir = self.root / "_archived"
            archive_dir.mkdir(exist_ok=True)
            target = archive_dir / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(project_dir), str(target))
            logger.info("Archived project: %s → %s", slug, target.name)
        else:
            shutil.rmtree(project_dir)
            logger.info("Deleted project: %s", slug)
        return True

    # ── State & Checkpoints ─────────────────────────────

    def save_checkpoint(self, slug: str, checkpoint: dict) -> bool:
        """Save an execution checkpoint."""
        project_dir = self.root / slug
        if not project_dir.exists():
            return False

        now = datetime.now(timezone.utc).isoformat()
        checkpoint["timestamp"] = now

        state = self._read_json(project_dir / "state.json") or {}
        state["last_checkpoint"] = checkpoint
        history = state.get("checkpoint_history", [])
        history.append(checkpoint)
        # Keep last 50 checkpoints
        if len(history) > 50:
            history = history[-50:]
        state["checkpoint_history"] = history
        state["last_action"] = {"type": "checkpoint", "step": checkpoint.get("step", ""), "timestamp": now}

        self._write_json(project_dir / "state.json", state)

        # Backup state
        backup_path = project_dir / "backups" / f"state_{now.replace(':', '-')[:19]}.json"
        self._write_json(backup_path, state)

        return True

    def get_checkpoints(self, slug: str) -> list[dict]:
        """Get checkpoint history for a project."""
        state = self._read_json(self.root / slug / "state.json") or {}
        return state.get("checkpoint_history", [])

    def get_last_checkpoint(self, slug: str) -> dict | None:
        """Get the most recent checkpoint."""
        state = self._read_json(self.root / slug / "state.json") or {}
        return state.get("last_checkpoint")

    # ── Decisions ─────────────────────────────────────────

    def record_decision(self, slug: str, context: str, chosen: str,
                        rationale: str = "") -> bool:
        """Record a decision within a project."""
        project_dir = self.root / slug
        if not project_dir.exists():
            return False

        decisions = self._read_json(project_dir / "decisions.json") or []
        decisions.append({
            "context": context,
            "chosen": chosen,
            "rationale": rationale,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._write_json(project_dir / "decisions.json", decisions)
        return True

    # ── Artifacts ─────────────────────────────────────────

    def get_artifacts_dir(self, slug: str) -> Path:
        """Get the artifacts directory path for a project."""
        return self.root / slug / "artifacts"

    def list_artifacts(self, slug: str) -> list[dict]:
        """List all artifacts in a project."""
        return self._list_artifacts(self.root / slug / "artifacts")

    # ── Daily Status ─────────────────────────────────────

    def get_workspace_status(self) -> dict:
        """Get overall workspace status for daily briefing."""
        projects = self.list_projects()
        total = len(projects)
        active = len([p for p in projects if p["status"] == "active"])

        recent_actions = []
        for p in projects:
            proj = self.get_project(p["slug"])
            if proj and proj["state"].get("last_action"):
                recent_actions.append({
                    "project": p["name"],
                    "action": proj["state"]["last_action"],
                })

        return {
            "total_projects": total,
            "active_projects": active,
            "recent_actions": recent_actions[-10:],
            "projects": projects,
        }

    # ── Helpers ────────────────────────────────────────────

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert a project name to a filesystem-safe slug."""
        slug = name.lower().strip()
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug)
        slug = "-".join(slug.split("-")) or "project"  # remove double dashes
        return slug[:64]

    def _read_json(self, path: Path) -> dict | list | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", path, e)
            return None

    def _write_json(self, path: Path, data: dict | list) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _update_meta(self, slug: str, updates: dict) -> bool:
        project_dir = self.root / slug
        if not project_dir.exists():
            return False
        meta = self._read_json(project_dir / "project.json") or {}
        meta.update(updates)
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_json(project_dir / "project.json", meta)
        return True

    def _list_artifacts(self, artifacts_dir: Path) -> list[dict]:
        if not artifacts_dir.exists():
            return []
        result = []
        for f in sorted(artifacts_dir.rglob("*")):
            if f.is_file():
                result.append({
                    "path": str(f.relative_to(artifacts_dir)),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                })
        return result[:200]


# Global singleton
_workspace: WorkspaceManager | None = None


def get_workspace() -> WorkspaceManager:
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceManager()
    return _workspace
