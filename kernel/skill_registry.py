"""Personal AI OS Kernel — Skill Registry (Sprint 6.5)

Decouples professional capabilities from agents. Each Skill is a standalone
unit of expertise that can be attached to any agent, rated independently,
and evolved through the Experiment system.

ADR-007 compliant:
  ✅ Skill = name + capabilities + prompt_fragment + tools + prerequisites + rating
  ✅ Skills are independent of agents — composable, reusable
  ✅ Per-skill rating for fine-grained Evolution analysis
  ✅ Prerequisite validation
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SkillCategory(StrEnum):
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATA = "data"
    DEVOPS = "devops"
    WRITING = "writing"
    RESEARCH = "research"
    DESIGN = "design"
    TESTING = "testing"
    SECURITY = "security"
    BUSINESS = "business"
    GENERAL = "general"


class SkillDifficulty(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class SkillRating:
    """Multi-dimensional rating for a single skill.

    Sprint 6.6: Split from binary success/failure into 4 phases:
      - planning: did the agent choose the right approach?
      - code_gen: did the generated artifact work?
      - validation: did tests/verification pass?
      - deployment: did it run successfully in target environment?

    Composite score weights vary by skill category.
    """
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    avg_duration_ms: float = 0.0
    reputation_score: float = 0.5

    # Sprint 6.6: Phase-level tracking
    planning_ok: int = 0          # Agent planned correctly
    planning_total: int = 0
    code_gen_ok: int = 0          # Generated artifact was correct
    code_gen_total: int = 0
    validation_ok: int = 0        # Tests/verification passed
    validation_total: int = 0
    deployment_ok: int = 0        # Ran successfully in target env
    deployment_total: int = 0
    human_interventions: int = 0  # How many times human had to step in

    def _phase_rate(self, ok: int, total: int) -> float:
        if total == 0:
            return 0.5  # Neutral — no data yet
        return ok / total

    @property
    def planning_rate(self) -> float:
        return self._phase_rate(self.planning_ok, self.planning_total)

    @property
    def code_gen_rate(self) -> float:
        return self._phase_rate(self.code_gen_ok, self.code_gen_total)

    @property
    def validation_rate(self) -> float:
        return self._phase_rate(self.validation_ok, self.validation_total)

    @property
    def deployment_rate(self) -> float:
        return self._phase_rate(self.deployment_ok, self.deployment_total)

    @property
    def success_rate(self) -> float:
        if self.total_uses == 0:
            return 0.5
        return self.successful_uses / self.total_uses

    @property
    def tier(self) -> str:
        s = self.reputation_score
        if s >= 0.90:
            return "S"
        if s >= 0.80:
            return "A"
        if s >= 0.65:
            return "B"
        if s >= 0.50:
            return "C"
        return "D"

    @property
    def weakest_phase(self) -> str:
        """Returns the phase with the lowest score — useful for Evolution Advisor."""
        phases = {
            "planning": self.planning_rate,
            "code_gen": self.code_gen_rate,
            "validation": self.validation_rate,
            "deployment": self.deployment_rate,
        }
        return min(phases, key=phases.get)

    def record(self, success: bool, duration_ms: float,
               phases: dict | None = None) -> None:
        """Record a skill execution.

        Args:
            success: overall success/failure
            duration_ms: execution time
            phases: optional dict with phase-level results
                    {"planning": True, "code_gen": True, "validation": False, "deployment": None}
        """
        self.total_uses += 1
        if success:
            self.successful_uses += 1
        else:
            self.failed_uses += 1

        self.avg_duration_ms = (
            (self.avg_duration_ms * (self.total_uses - 1) + duration_ms)
            / max(self.total_uses, 1)
        )

        # Sprint 6.6: Phase-level tracking
        if phases:
            if "planning" in phases and phases["planning"] is not None:
                self.planning_total += 1
                if phases["planning"]:
                    self.planning_ok += 1
            if "code_gen" in phases and phases["code_gen"] is not None:
                self.code_gen_total += 1
                if phases["code_gen"]:
                    self.code_gen_ok += 1
            if "validation" in phases and phases["validation"] is not None:
                self.validation_total += 1
                if phases["validation"]:
                    self.validation_ok += 1
            if "deployment" in phases and phases["deployment"] is not None:
                self.deployment_total += 1
                if phases["deployment"]:
                    self.deployment_ok += 1
        else:
            # Legacy: if no phases provided, mark all relevant phases as this result
            if self.code_gen_total > 0 or self.planning_total > 0:
                # Already have data — don't assume all phases
                pass
            else:
                # First use — mark code-gen and planning as this result
                self.planning_total += 1
                if success:
                    self.planning_ok += 1
                self.code_gen_total += 1
                if success:
                    self.code_gen_ok += 1

        # Sprint 6.6: Composite score weights phases differently per category
        # Default: all 4 phases equal weight
        phase_scores = [
            self.planning_rate,
            self.code_gen_rate,
            self.validation_rate if self.validation_total > 0 else self.planning_rate,
            self.deployment_rate if self.deployment_total > 0 else self.planning_rate,
        ]
        avg_phase = sum(phase_scores) / len(phase_scores)

        self.reputation_score = round(
            0.3 * self.success_rate + 0.5 * avg_phase + 0.2 * min(1.0, 30000 / max(self.avg_duration_ms, 1000)),
            3,
        )

    def to_dict(self) -> dict:
        return {
            "total_uses": self.total_uses,
            "successful_uses": self.successful_uses,
            "failed_uses": self.failed_uses,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 0),
            "reputation_score": self.reputation_score,
            "tier": self.tier,
            # Sprint 6.6: Phase-level breakdown
            "phases": {
                "planning": {"rate": round(self.planning_rate, 3), "n": self.planning_total},
                "code_gen": {"rate": round(self.code_gen_rate, 3), "n": self.code_gen_total},
                "validation": {"rate": round(self.validation_rate, 3), "n": self.validation_total},
                "deployment": {"rate": round(self.deployment_rate, 3), "n": self.deployment_total},
            },
            "weakest_phase": self.weakest_phase,
            "human_interventions": self.human_interventions,
        }


@dataclass
class SkillDefinition:
    """A standalone unit of professional expertise.

    Skills are NOT agents. They are capability modules that agents equip.
    """
    id: str = field(default_factory=lambda: f"skill-{str(uuid.uuid4())[:8]}")
    name: str = ""                        # "python_backend"
    display_name: str = ""                # "Python Backend Development"
    description: str = ""                 # What this skill provides
    capabilities: list[str] = field(default_factory=list)  # Capability tags
    prompt_fragment: str = ""             # Injected into Agent System Prompt
    recommended_tools: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)  # Required skill names
    category: str = "general"
    difficulty: str = "intermediate"
    version: str = "1.0.0"
    rating: SkillRating = field(default_factory=SkillRating)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "capabilities": self.capabilities,
            "prompt_fragment": self.prompt_fragment[:200],
            "recommended_tools": self.recommended_tools,
            "prerequisites": self.prerequisites,
            "category": self.category,
            "difficulty": self.difficulty,
            "version": self.version,
            "rating": self.rating.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SkillRegistry:
    """Central catalog of all available Skills.

    Skills are registered once and can be assigned to any agent.
    This is the "skills department" of the AI organization.
    """

    def __init__(self, storage_path: str = ""):
        self._skills: dict[str, SkillDefinition] = {}
        self._name_index: dict[str, str] = {}  # skill_name → skill_id
        self._agent_skills: dict[str, list[str]] = {}  # agent_name → [skill_names]
        self._storage_path = storage_path or str(
            Path(__file__).parent.parent / "data" / "skills.json"
        )
        self._load()
        if not self._skills:
            self._register_defaults()

    # ── Registration ───────────────────────────────────

    def register(self, skill: SkillDefinition) -> str:
        """Register a skill. Returns the skill ID."""
        from datetime import datetime, timezone
        skill.created_at = datetime.now(timezone.utc).isoformat()

        self._skills[skill.id] = skill
        self._name_index[skill.name] = skill.id

        logger.info("Registered skill: %s (%s) [%s]", skill.name, skill.display_name, skill.category)
        self._save()
        return skill.id

    def unregister(self, name: str) -> bool:
        """Remove a skill by name."""
        skill_id = self._name_index.pop(name, None)
        if skill_id:
            self._skills.pop(skill_id, None)
            # Remove from agent assignments
            for agent_name in self._agent_skills:
                self._agent_skills[agent_name] = [
                    s for s in self._agent_skills[agent_name] if s != name
                ]
            self._save()
            return True
        return False

    # ── Agent Assignment ───────────────────────────────

    def assign_to_agent(self, agent_name: str, skill_names: list[str]) -> bool:
        """Assign skills to an agent. Validates prerequisites."""
        # Validate all skills exist and prerequisites are met
        for sn in skill_names:
            skill = self.get_by_name(sn)
            if not skill:
                logger.warning("Cannot assign unknown skill '%s' to %s", sn, agent_name)
                return False
            for prereq in skill.prerequisites:
                if prereq not in skill_names:
                    logger.warning(
                        "Skill '%s' requires '%s' which is not assigned to %s",
                        sn, prereq, agent_name,
                    )
                    return False

        self._agent_skills[agent_name] = skill_names
        logger.info("Assigned %d skills to %s: %s", len(skill_names), agent_name, skill_names)
        self._save()
        return True

    def get_agent_skills(self, agent_name: str) -> list[SkillDefinition]:
        """Get all skills assigned to an agent."""
        names = self._agent_skills.get(agent_name, [])
        return [self.get_by_name(n) for n in names if self.get_by_name(n)]

    def get_agent_skill_names(self, agent_name: str) -> list[str]:
        return self._agent_skills.get(agent_name, [])

    # ── Query ────────────────────────────────────────────

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def get_by_name(self, name: str) -> SkillDefinition | None:
        skill_id = self._name_index.get(name)
        if skill_id:
            return self._skills.get(skill_id)
        return None

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def list_by_category(self, category: str) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.category == category]

    def list_by_capability(self, capability: str) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if capability in s.capabilities]

    def list_unassigned(self) -> list[SkillDefinition]:
        """Skills not assigned to any agent."""
        all_assigned: set[str] = set()
        for names in self._agent_skills.values():
            all_assigned.update(names)
        return [s for s in self._skills.values() if s.name not in all_assigned]

    def get_agents_for_skill(self, skill_name: str) -> list[str]:
        """Which agents have this skill?"""
        return [a for a, names in self._agent_skills.items() if skill_name in names]

    # ── Rating ──────────────────────────────────────────

    def record_skill_use(self, skill_name: str, success: bool, duration_ms: float,
                        phases: dict | None = None) -> bool:
        """Record a skill usage for rating.

        Args:
            skill_name: which skill was used
            success: overall success/failure
            duration_ms: execution time
            phases: optional phase-level breakdown
                    {"planning": True, "code_gen": True, "validation": False, "deployment": None}
        """
        skill = self.get_by_name(skill_name)
        if not skill:
            return False
        skill.rating.record(success, duration_ms, phases=phases)
        skill.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        self._save()
        return True

    def get_skill_ratings(self) -> list[dict]:
        """Get ratings for all skills, sorted by reputation."""
        rated = [(s.name, s.display_name, s.rating) for s in self._skills.values()]
        rated.sort(key=lambda x: x[2].reputation_score, reverse=True)
        return [
            {"name": name, "display_name": dn, "rating": r.to_dict()}
            for name, dn, r in rated
        ]

    def get_agent_skill_profile(self, agent_name: str) -> dict:
        """Get an agent's skill composition with individual ratings."""
        skills = self.get_agent_skills(agent_name)
        return {
            "agent": agent_name,
            "skill_count": len(skills),
            "skills": [
                {
                    "name": s.name,
                    "display_name": s.display_name,
                    "category": s.category,
                    "rating": s.rating.to_dict(),
                }
                for s in skills
            ],
            "strongest": max(skills, key=lambda s: s.rating.reputation_score).name if skills else "",
            "weakest": min(skills, key=lambda s: s.rating.reputation_score).name if skills else "",
        }

    # ── Prompt Compilation ──────────────────────────────

    def compile_skill_prompt(self, agent_name: str) -> str:
        """Build the skill portion of an agent's system prompt.

        Concatenates all assigned skills' prompt fragments with headers.
        """
        skills = self.get_agent_skills(agent_name)
        if not skills:
            return ""

        parts = ["## 🎯 已激活的专业技能\n"]
        for i, skill in enumerate(skills, 1):
            parts.append(f"### 技能 {i}: {skill.display_name}")
            parts.append(f"分类: {skill.category} | 难度: {skill.difficulty} | 评分: {skill.rating.tier}")
            parts.append(f"{skill.prompt_fragment}\n")

        return "\n".join(parts)

    def get_total_skill_count(self) -> int:
        return len(self._skills)

    def get_stats(self) -> dict:
        assigned_count = sum(len(names) for names in self._agent_skills.values())
        return {
            "total_skills": len(self._skills),
            "assigned_skills": assigned_count,
            "unassigned_skills": len(self.list_unassigned()),
            "agents_with_skills": len(self._agent_skills),
            "by_category": {
                cat.value: len(self.list_by_category(cat.value))
                for cat in SkillCategory
                if self.list_by_category(cat.value)
            },
        }

    # ── Default Skills ──────────────────────────────────

    def _register_defaults(self) -> None:
        """Register the standard skill library."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        defaults = [
            SkillDefinition(
                name="python_backend",
                display_name="Python Backend Development",
                description="使用 Python + FastAPI 构建后端服务和应用",
                capabilities=["code_generation", "api_design"],
                prompt_fragment=(
                    "你是 Python 后端专家。\n"
                    "- 使用 FastAPI 构建 REST API\n"
                    "- 使用 Pydantic 进行数据验证\n"
                    "- 使用 SQLAlchemy 进行数据库操作\n"
                    "- 遵循 PEP 8 代码规范\n"
                    "- 编写类型注解和 docstring\n"
                    "- 优先异步 (async/await) 模式"
                ),
                recommended_tools=["write_file", "shell", "search_memory", "read_file"],
                category="backend", difficulty="intermediate",
                created_at=now,
            ),
            SkillDefinition(
                name="frontend_react",
                display_name="React Frontend Development",
                description="使用 React + TypeScript + Tailwind 构建前端界面",
                capabilities=["code_generation", "design"],
                prompt_fragment=(
                    "你是 React 前端专家。\n"
                    "- 使用 React 19 + TypeScript\n"
                    "- 使用 Tailwind CSS 进行样式设计\n"
                    "- 使用 Vite 作为构建工具\n"
                    "- 组件化设计，单一职责\n"
                    "- 使用 Zustand 进行状态管理\n"
                    "- 移动端优先的响应式设计"
                ),
                recommended_tools=["write_file", "read_file", "list_files"],
                category="frontend", difficulty="intermediate",
                created_at=now,
            ),
            SkillDefinition(
                name="database_design",
                display_name="Database Design",
                description="数据库 Schema 设计、优化和迁移管理",
                capabilities=["code_generation", "design"],
                prerequisites=["python_backend"],  # 需要先有后端基础
                prompt_fragment=(
                    "你是数据库设计专家。\n"
                    "- 设计规范化 Schema（至少 3NF）\n"
                    "- 正确使用索引和外键\n"
                    "- 编写数据库迁移脚本\n"
                    "- 考虑查询性能和数据完整性\n"
                    "- 使用 SQLAlchemy Alembic 管理迁移\n"
                    "- 设计前先画 ER 图（文字描述）"
                ),
                recommended_tools=["write_file", "shell"],
                category="data", difficulty="advanced",
                created_at=now,
            ),
            SkillDefinition(
                name="testing",
                display_name="Software Testing",
                description="编写单元测试、集成测试和 E2E 测试",
                capabilities=["code_generation", "code_review"],
                prompt_fragment=(
                    "你是软件测试专家。\n"
                    "- 使用 pytest 编写单元测试\n"
                    "- 测试覆盖率目标 > 80%\n"
                    "- 使用 pytest-asyncio 测试异步代码\n"
                    "- 测试用例命名：test_<功能>_<场景>\n"
                    "- 每个 PR 必须包含对应测试\n"
                    "- 使用 pytest-mock 进行 mock"
                ),
                recommended_tools=["write_file", "shell", "read_file"],
                category="testing", difficulty="intermediate",
                created_at=now,
            ),
            SkillDefinition(
                name="market_research",
                display_name="Market Research",
                description="市场分析、竞品调研和用户洞察",
                capabilities=["research", "analysis", "strategy"],
                prompt_fragment=(
                    "你是市场研究专家。\n"
                    "- 分析市场规模、增长趋势和关键玩家\n"
                    "- 构建竞品对比矩阵（功能、定价、定位）\n"
                    "- 识别用户痛点和未满足需求\n"
                    "- 使用 SWOT 框架分析机会\n"
                    "- 数据驱动，每个结论附依据\n"
                    "- 最终输出包含可执行建议"
                ),
                recommended_tools=["search_memory", "write_file", "read_file"],
                category="business", difficulty="intermediate",
                created_at=now,
            ),
            SkillDefinition(
                name="technical_writing",
                display_name="Technical Writing",
                description="编写技术文档、API 文档和用户手册",
                capabilities=["writing", "file_ops"],
                prompt_fragment=(
                    "你是技术写作专家。\n"
                    "- 使用 Markdown 编写文档\n"
                    "- 文档结构：概述 → 快速开始 → 详细指南 → API 参考\n"
                    "- 每个功能配示例代码\n"
                    "- 使用主动语态，避免被动\n"
                    "- 代码块标注语言类型\n"
                    "- 面向目标读者调整深度"
                ),
                recommended_tools=["write_file", "read_file", "list_files"],
                category="writing", difficulty="beginner",
                created_at=now,
            ),
            SkillDefinition(
                name="content_writing",
                display_name="Content Writing",
                description="撰写博客文章、产品文案、营销内容和社交媒体帖子",
                capabilities=["writing", "file_ops"],
                prompt_fragment=(
                    "你是内容创作专家。\n"
                    "- 撰写引人入胜的博客文章和社交媒体内容\n"
                    "- 产品发布公告和营销文案\n"
                    "- 面向不同受众调整写作风格\n"
                    "- SEO 友好的内容结构\n"
                    "- 使用 Markdown 格式输出"
                ),
                recommended_tools=["write_file", "search_memory"],
                category="writing", difficulty="beginner",
                created_at=now,
            ),
            SkillDefinition(
                name="code_review",
                display_name="Code Review",
                description="代码审查：发现 Bug、安全问题和改进建议",
                capabilities=["code_review", "code_debug", "analysis"],
                prompt_fragment=(
                    "你是代码审查专家。\n"
                    "- 关注：正确性 → 安全性 → 性能 → 可读性 → 规范\n"
                    "- 每个问题附具体行号和修复建议\n"
                    "- 区分：必须修复（bug/安全）vs 建议改进（风格/优化）\n"
                    "- 检查 SQL 注入、XSS、敏感信息泄露\n"
                    "- 检查错误处理是否完整\n"
                    "- 检查是否有对应的测试"
                ),
                recommended_tools=["read_file", "list_files"],
                category="testing", difficulty="advanced",
                created_at=now,
            ),
            SkillDefinition(
                name="devops_deployment",
                display_name="DevOps & Deployment",
                description="CI/CD 配置、Docker 容器化和服务部署",
                capabilities=["code_generation", "shell_exec"],
                prerequisites=["python_backend"],
                prompt_fragment=(
                    "你是 DevOps 专家。\n"
                    "- 编写 Dockerfile 和 docker-compose.yml\n"
                    "- 配置 GitHub Actions CI/CD\n"
                    "- 使用环境变量管理配置（12-Factor App）\n"
                    "- 健康检查端点 + 优雅关闭\n"
                    "- 日志输出到 stdout（不写文件）\n"
                    "- 优先单容器部署，够用不再加复杂度"
                ),
                recommended_tools=["write_file", "shell"],
                category="devops", difficulty="advanced",
                created_at=now,
            ),
        ]

        for skill in defaults:
            self.register(skill)

        # ── Default Agent Skill Assignments ──
        self.assign_to_agent("coding_agent", [
            "python_backend", "frontend_react", "database_design",
            "testing", "code_review", "devops_deployment",
        ])
        self.assign_to_agent("research_agent", [
            "market_research",
        ])
        self.assign_to_agent("writing_agent", [
            "technical_writing", "content_writing",
        ])
        self.assign_to_agent("project_manager", [])  # PM relies on orchestration, not skills
        self.assign_to_agent("ceo", [])  # CEO delegates, doesn't execute skills
        self.assign_to_agent("reflection_agent", [])

        logger.info("Registered %d default skills, assigned to %d agents",
                     len(self._skills), len(self._agent_skills))

    # ── Persistence ─────────────────────────────────────

    def _save(self) -> None:
        try:
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)
            data = {
                "skills": {s.name: s.to_dict() for s in self._skills.values()},
                "agent_skills": self._agent_skills,
            }
            Path(self._storage_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError:
            pass

    def _load(self) -> None:
        path = Path(self._storage_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            self._agent_skills = data.get("agent_skills", {})
            for name, sd in data.get("skills", {}).items():
                skill = SkillDefinition(
                    name=name,
                    display_name=sd.get("display_name", ""),
                    description=sd.get("description", ""),
                    capabilities=sd.get("capabilities", []),
                    prompt_fragment=sd.get("prompt_fragment", ""),
                    recommended_tools=sd.get("recommended_tools", []),
                    prerequisites=sd.get("prerequisites", []),
                    category=sd.get("category", "general"),
                    difficulty=sd.get("difficulty", "intermediate"),
                    version=sd.get("version", "1.0.0"),
                    created_at=sd.get("created_at", ""),
                    updated_at=sd.get("updated_at", ""),
                )
                rating_data = sd.get("rating", {})
                skill.rating = SkillRating(
                    total_uses=rating_data.get("total_uses", 0),
                    successful_uses=rating_data.get("successful_uses", 0),
                    failed_uses=rating_data.get("failed_uses", 0),
                    avg_duration_ms=rating_data.get("avg_duration_ms", 0),
                    reputation_score=rating_data.get("reputation_score", 0.5),
                    human_interventions=rating_data.get("human_interventions", 0),
                    # Sprint 6.6: Phase-level
                    planning_ok=rating_data.get("planning_ok", 0),
                    planning_total=rating_data.get("planning_total", 0),
                    code_gen_ok=rating_data.get("code_gen_ok", 0),
                    code_gen_total=rating_data.get("code_gen_total", 0),
                    validation_ok=rating_data.get("validation_ok", 0),
                    validation_total=rating_data.get("validation_total", 0),
                    deployment_ok=rating_data.get("deployment_ok", 0),
                    deployment_total=rating_data.get("deployment_total", 0),
                )
                skill.id = sd.get("id", skill.id)
                self._skills[skill.id] = skill
                self._name_index[skill.name] = skill.id
            if self._skills:
                logger.info("Loaded %d skills, %d agent assignments",
                           len(self._skills), len(self._agent_skills))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load skills: %s", e)


# Global singleton
_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
