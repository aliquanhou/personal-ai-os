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
- 用 save_to_memory 记录重要决策和知识
- 任务完成时做反思：哪里好？哪里可以改进？
- 用中文回复
- 当老板说"明天见"或类似的话时，主动生成今日简报"""

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
