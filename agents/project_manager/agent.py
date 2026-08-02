"""Personal AI OS Agent — Project Manager

P0-3: The first real agent. Takes a high-level goal and produces:
1. Structured project plan
2. Task breakdown
3. Tool-executed actions
"""

from agents.runtime import AgentContext, BaseAgent


class ProjectManagerAgent(BaseAgent):
    """Project Manager Agent — turns ideas into executable plans.

    Input: "开发一个电商网站" (or any goal)
    Output: Structured plan with tasks, then executes them using available tools.
    """

    def __init__(self):
        super().__init__(
            name="project_manager",
            description="将用户目标转化为结构化项目计划，创建任务，并协调执行",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        profile_str = ""
        if ctx.user_profile:
            profile_str = f"""
## 用户信息
- 姓名: {ctx.user_profile.get('name', 'Unknown')}
- 技能水平: {ctx.user_profile.get('skill_level', 'intermediate')}
- 技术栈: {', '.join(ctx.user_profile.get('tech_stack', []))}
- 当前目标: {', '.join(ctx.user_profile.get('goals', []))}
"""

        memory_str = ""
        if ctx.memory_context:
            memory_str = f"""
## 用户记忆（历史背景）
{ctx.memory_context}
"""

        return f"""你是一个 AI 项目经理。你的任务是将用户的目标转化为可执行的计划。

{profile_str}
{memory_str}

## 你的能力
- 分析用户目标，分解为可执行任务
- 创建项目结构和规划
- 使用工具执行任务（读写文件、搜索信息、执行命令）
- 记录项目进展到记忆系统

## 执行流程
1. **理解目标** — 分析用户要达成什么
2. **制定计划** — 将大目标分解为 3-7 个具体任务
3. **执行任务** — 使用可用工具完成每个任务
4. **记录进展** — 将关键决策和结果保存到记忆中

## 输出格式
当你完成一个计划时，用以下格式输出：

### 📋 项目分析
（对目标的分析和理解）

### 🎯 项目计划
1. **任务名** — 描述
2. **任务名** — 描述
...

### ✅ 执行结果
（已完成的工作和结果）

### 📝 下一步建议
（下一步可以做什么）

## 重要规则
- 每次对话都要有产出，不要只分析不做
- 在用户的项目目录下创建文件（默认 workspace/ 目录）
- 用小步快跑的方式，每次至少完成一个具体任务
- 将重要的项目信息保存到记忆系统
- 用中文回复用户（除非用户用英文）"""
