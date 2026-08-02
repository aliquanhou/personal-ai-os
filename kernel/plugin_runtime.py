"""Personal AI OS Kernel — Plugin Runtime (Sprint 8)

Plugin lifecycle manager. Builds on AgentRegistry + SkillRegistry.

Plugin = directory with plugin.json manifest.
  {
    "name": "python-dev",
    "version": "1.0.0",
    "display_name": "Python Development Pack",
    "skills": ["python_backend", "testing"],
    "target_agents": ["coding_agent"],
    "enabled": true
  }

Operations: list, install (activate), uninstall (deactivate), enable, disable.
All plugins live in plugins/<name>/ and are auto-discovered on startup.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent.parent / "plugins"


class PluginRuntime:
    """Manages the lifecycle of all plugins.

    Discovery: scans plugins/ for directories containing plugin.json.
    Activation: assigns skills to target agents via SkillRegistry.
    Deactivation: removes skill assignments.
    """

    def __init__(self):
        self._plugins: dict[str, dict] = {}       # name → manifest
        self._active: set[str] = set()            # currently enabled plugins
        self._plugin_dir = PLUGINS_DIR

    def discover(self) -> list[dict]:
        """Scan plugins/ directory and load all manifests. Returns list of discovered."""
        discovered = []
        if not self._plugin_dir.exists():
            self._plugin_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(self._plugin_dir.iterdir()):
            if not path.is_dir():
                continue
            manifest_path = path / "plugin.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                name = manifest.get("name", path.name)
                manifest["_path"] = str(path)
                manifest["_discovered_at"] = datetime.now(timezone.utc).isoformat()
                self._plugins[name] = manifest
                if manifest.get("enabled", True):
                    self._active.add(name)
                discovered.append(self._info(name, manifest))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Invalid plugin manifest %s: %s", manifest_path, e)

        logger.info("Discovered %d plugins (%d enabled)", len(discovered), len(self._active))
        return discovered

    def activate_all(self) -> dict:
        """Activate all enabled plugins — assign skills to agents."""
        from kernel.skill_registry import get_skill_registry

        registry = get_skill_registry()
        results = {"activated": 0, "skipped": 0, "errors": []}

        for name in list(self._active):
            manifest = self._plugins.get(name)
            if not manifest:
                continue
            try:
                skills = manifest.get("skills", [])
                agents = manifest.get("target_agents", [])
                for agent in agents:
                    current = set(registry.get_agent_skill_names(agent))
                    current.update(skills)
                    registry.assign_to_agent(agent, list(current))
                results["activated"] += 1
            except Exception as e:
                results["errors"].append(f"{name}: {e}")
                results["skipped"] += 1

        logger.info("Plugin activation: %d activated, %d skipped", results["activated"], results["skipped"])
        return results

    def install(self, name: str) -> bool:
        """Enable an already-discovered plugin and activate its skills."""
        if name not in self._plugins:
            self.discover()
        if name not in self._plugins:
            return False
        self._active.add(name)
        self._plugins[name]["enabled"] = True
        self._save_manifest(name)
        self._apply_skills(name, activate=True)
        logger.info("Plugin installed: %s", name)
        return True

    def uninstall(self, name: str) -> bool:
        """Disable a plugin and remove its skill assignments."""
        if name not in self._plugins:
            return False
        self._apply_skills(name, activate=False)
        self._active.discard(name)
        self._plugins[name]["enabled"] = False
        self._save_manifest(name)
        logger.info("Plugin uninstalled: %s", name)
        return True

    def remove(self, name: str) -> bool:
        """Permanently delete a plugin directory."""
        if name not in self._plugins:
            return False
        self.uninstall(name)
        plugin_path = Path(self._plugins[name].get("_path", str(self._plugin_dir / name)))
        if plugin_path.exists():
            shutil.rmtree(plugin_path)
        del self._plugins[name]
        logger.info("Plugin removed: %s", name)
        return True

    def list_all(self) -> list[dict]:
        """List all discovered plugins."""
        if not self._plugins:
            self.discover()
        return [self._info(name, m) for name, m in self._plugins.items()]

    def list_active(self) -> list[dict]:
        return [self._info(name, m) for name, m in self._plugins.items() if name in self._active]

    def get(self, name: str) -> dict | None:
        if name in self._plugins:
            return self._info(name, self._plugins[name])
        return None

    def _info(self, name: str, manifest: dict) -> dict:
        return {
            "name": name,
            "version": manifest.get("version", "0.0.0"),
            "display_name": manifest.get("display_name", name),
            "description": manifest.get("description", ""),
            "author": manifest.get("author", ""),
            "category": manifest.get("category", "general"),
            "icon": manifest.get("icon", ""),
            "official": manifest.get("official", False),
            "skills": manifest.get("skills", []),
            "target_agents": manifest.get("target_agents", []),
            "enabled": name in self._active,
            "path": manifest.get("_path", ""),
        }

    def _apply_skills(self, plugin_name: str, activate: bool) -> None:
        """Add or remove plugin skills from target agents."""
        from kernel.skill_registry import get_skill_registry

        manifest = self._plugins.get(plugin_name)
        if not manifest:
            return
        registry = get_skill_registry()
        skills = set(manifest.get("skills", []))
        for agent in manifest.get("target_agents", []):
            current = set(registry.get_agent_skill_names(agent))
            if activate:
                current.update(skills)
            else:
                current.difference_update(skills)
            registry.assign_to_agent(agent, list(current))

    def _save_manifest(self, name: str) -> None:
        manifest = self._plugins.get(name)
        if not manifest:
            return
        path = Path(manifest.get("_path", ""))
        if not path.exists():
            return
        manifest_path = path / "plugin.json"
        data = {k: v for k, v in manifest.items() if not k.startswith("_")}
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# Global singleton
_runtime: PluginRuntime | None = None


def get_plugin_runtime() -> PluginRuntime:
    global _runtime
    if _runtime is None:
        _runtime = PluginRuntime()
    return _runtime
