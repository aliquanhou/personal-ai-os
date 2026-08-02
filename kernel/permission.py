# -*- coding: utf-8 -*-
"""Personal AI OS Kernel — Permission System

Controls what agents and tools can do. Simple allow/deny with scope tracking.
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

logger = logging.getLogger(__name__)


class PermissionLevel(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(StrEnum):
    FILE = "file"
    NETWORK = "network"
    PROCESS = "process"
    MEMORY = "memory"
    PLUGIN = "plugin"


@dataclass
class Permission:
    resource: ResourceType
    level: PermissionLevel
    path: str = "*"  # Scope restriction, e.g., "/home/user/projects/*"
    granted: bool = True


@dataclass
class PermissionCheck:
    allowed: bool
    reason: str = ""
    required_level: Optional[PermissionLevel] = None


class PermissionManager:
    """Manages permissions for agents and tools."""

    def __init__(self):
        self._permissions: dict[str, list[Permission]] = {}
        self._default_allow: bool = True

    def grant(self, agent_id: str, permission: Permission) -> None:
        """Grant a permission to an agent."""
        if agent_id not in self._permissions:
            self._permissions[agent_id] = []
        self._permissions[agent_id].append(permission)

    def revoke(self, agent_id: str, resource: ResourceType, path: str = "*") -> None:
        """Revoke a permission."""
        if agent_id not in self._permissions:
            return
        self._permissions[agent_id] = [
            p for p in self._permissions[agent_id]
            if not (p.resource == resource and p.path == path)
        ]

    def check(
        self,
        agent_id: str,
        resource: ResourceType,
        level: PermissionLevel,
        path: str = "*",
    ) -> PermissionCheck:
        """Check if an agent has permission."""
        if agent_id not in self._permissions:
            if self._default_allow:
                return PermissionCheck(allowed=True, reason="Default allow")
            return PermissionCheck(allowed=False, reason="No permissions configured")

        for perm in self._permissions[agent_id]:
            if perm.resource != resource:
                continue
            if not self._path_matches(perm.path, path):
                continue
            if not perm.granted:
                return PermissionCheck(allowed=False, reason=f"Denied by rule: {perm.resource}:{perm.path}")
            if self._level_sufficient(perm.level, level):
                return PermissionCheck(allowed=True, reason="Granted")
            else:
                return PermissionCheck(
                    allowed=False,
                    reason=f"Insufficient level: have {perm.level}, need {level}",
                    required_level=perm.level,
                )

        if self._default_allow:
            return PermissionCheck(allowed=True, reason="Default allow (no matching rule)")
        return PermissionCheck(allowed=False, reason="No matching permission")

    @staticmethod
    def _path_matches(pattern: str, actual: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return actual.startswith(pattern[:-1])
        return pattern == actual

    @staticmethod
    def _level_sufficient(have: PermissionLevel, need: PermissionLevel) -> bool:
        levels = {PermissionLevel.READ: 1, PermissionLevel.WRITE: 2, PermissionLevel.EXECUTE: 3, PermissionLevel.ADMIN: 4}
        return levels.get(have, 0) >= levels.get(need, 0)


# Global singleton
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager
