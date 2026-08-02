# -*- coding: utf-8 -*-
"""Personal AI OS Agent — CEO / Chief of Staff

Sprint 1: The top-level orchestrator.
- Knows the user's full identity (goals, values, preferences, history)
- Breaks high-level goals into tasks using Task State Machine
- Routes to specialist agents
- Generates daily briefings
"""

from agents.runtime import AgentContext, BaseAgent


class CEOAgent(BaseAgent):
    """CEO Agent — the user's AI Chief of Staff.

    This is the primary agent users interact with. It understands the full
    context of who the user is, what they're building, and what matters to them.
    It orchestrates other specialist agents to get work done.
    """

    def __init__(self):
        super().__init__(
            name="ceo",
            description="AI 幕僚长 — 理解你的目标、协调团队、推动执行、每日简报",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        profile_str = self._build_profile_section(ctx)
        tasks_str = self._build_tasks_section()
        goals_str = self._build_goals_section()

        return f"""你是用户的 AI 幕僚长（Chief of Staff）。

你的职责不是简单地回答问题，而是像一个真正的幕僚一样：
1. 理解老板的长远目标和当前重点
2. 主动拆解任务，推动执行
3. 在关键决策点上给出判断和建议
4. 记录经验教训，持续优化

{profile_str}
{goals_str}
{tasks_str}

## 你的工作方式

### 收到目标时
1. **理解意图** — 先确认你理解了老板要什么
2. **关联长期目标** — 这个任务和老板的长期愿景有什么关系？
3. **拆解任务** — 用 save_to_memory(type="task") 创建具体任务
4. **协调执行** — 使用可用工具完成每个任务
5. **记录进展** — 关键决策和结果保存到记忆

### 输出格式
每次回复遵循这个结构：

### 🎯 理解
（你对目标的理解，以及它和长期愿景的关系）

### 📋 任务拆解
1. **任务名** — 谁来做 — 预计结果
2. **任务名** — 谁来做 — 预计结果
...

### ✅ 执行
（实际做的工作，每完成一项更新状态）

### 💡 建议/风险
（基于老板的决策原则和过往经验，给出的判断）

## 重要规则
- 每次都要有产出，不只分析不做
- 主动使用工具创建文件、搜索记忆、记录进展
- 用中文回复
- 当老板说"明天见"或类似的话时，主动生成今日简报

## ⚠️ 关键：停止探索，立即执行
**用户给你任务，你就直接做。不要：**
- ❌ 多次 ls/pwd/cd 浏览目录结构 — 最多 1-2 次确认路径
- ❌ 检查整个 workspace 的项目结构 — 不需要
- ❌ 反复探索文件系统 — 浪费时间
- ❌ 创建诊断/修复脚本而不是做任务本身

**正确做法：**
- ✅ 1-2 次列出目标路径 → 立即开始创建文件
- ✅ 用 write_file 直接创建用户要求的文件
- ✅ 用户要求什么就创建什么，不额外优化
- ✅ 用户说"停止"就立即停止，不继续优化

## ⚠️ 决策保存规则 (v1.1 Decision Confirmation Gate)
**不要自动保存任何决策到 memory。** 只有在以下情况下才能使用 save_to_memory:
1. 老板明确说"保存"、"记录"、"记住这个"
2. 任务完成后，老板确认方向正确
3. 每日简报总结时

以下情况绝对不能自动保存：
- 老板只是说"我想做X"（可能是测试想法）
- 老板说"重新设计"、"不要考虑之前方案"（应该丢弃旧决策）
- 只是分析过程中的中间步骤

如果你认为某个决策应该保存，**必须先问老板确认**:
\"我建议保存这个决策：[决策内容]。确认吗？\"
而不是直接调用 save_to_memory。

## 🆕 重新开始模式
如果用户说"重新设计"、"从头开始"、"不考虑之前方案"、"推倒重来":
- 系统会自动切换到 fresh_start 模式，历史决策和知识不会加载
- 请用全新的视角分析问题
- 不要引用过去的项目方案
- 不要自动保存任何决策
- 从零开始思考"""

    def _build_profile_section(self, ctx: AgentContext) -> str:
        """Build the user identity section of the prompt."""
        profile = ctx.user_profile
        if not profile:
            return ""

        parts = ["## 👤 老板画像"]

        parts.append(f"""
### 基本信息
- 姓名: {profile.get('name', 'Unknown')}
- 技能水平: {profile.get('skill_level', 'intermediate')}
- 技术栈: {', '.join(profile.get('tech_stack', []))}
""")

        if profile.get('long_term_vision'):
            parts.append(f"""
### 🏔️ 长期愿景
{profile['long_term_vision']}
""")

        decision_principles = profile.get('decision_principles', [])
        if isinstance(decision_principles, str):
            import json
            decision_principles = json.loads(decision_principles)
        if decision_principles:
            parts.append("### 📐 决策原则")
            for p in decision_principles:
                parts.append(f"- {p}")
            parts.append("")

        hates = profile.get('hates', [])
        if isinstance(hates, str):
            import json
            hates = json.loads(hates)
        if hates:
            parts.append(f"### ⚠️ 厌恶: {', '.join(hates)}\n")

        if ctx.memory_context:
            parts.append(f"""
### 🧠 历史背景
{ctx.memory_context}
""")

        return "\n".join(parts)

    def _build_goals_section(self) -> str:
        """Build active goals section."""
        try:
            goals = self.memory.get_user_goals(status="active")
            if not goals:
                return ""
            parts = ["## 🎯 当前目标"]
            for g in goals[:5]:
                bar = "█" * int(g['progress_pct'] / 100 * 8) + "░" * (8 - int(g['progress_pct'] / 100 * 8))
                parts.append(f"- [{g['category']}] {g['title']} [{bar}] {g['progress_pct']:.0f}%")
            return "\n".join(parts) + "\n"
        except Exception:
            return ""

    def _build_tasks_section(self) -> str:
        """Build active tasks section."""
        try:
            active = self.memory.get_tasks_by_state(
                ["executing", "waiting_human", "verifying"], limit=10
            )
            if not active:
                return ""
            parts = ["## 📋 进行中任务"]
            for t in active:
                parts.append(f"- [{t['state']}] {t['title']} (优先级: {t['priority']})")
            return "\n".join(parts) + "\n"
        except Exception:
            return ""
