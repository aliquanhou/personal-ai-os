# -*- coding: utf-8 -*-
"""Personal AI OS Agent — Reflection Agent

Sprint 1: Post-task reflection and learning.
Runs after task completion to:
1. Analyze what went well
2. Identify failures and root causes
3. Extract lessons for future tasks
4. Save experiences to memory
"""

from agents.runtime import AgentContext, BaseAgent


class ReflectionAgent(BaseAgent):
    """Reflection Agent — post-task analysis and learning.

    After every significant task, this agent reflects on the outcome
    and extracts reusable lessons. This is how the AI employee grows.
    """

    def __init__(self):
        super().__init__(
            name="reflection_agent",
            description="任务反思与经验提炼 — 从每次执行中学习成长",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个 AI 反思教练。你的任务是对刚刚完成的工作进行深度反思。

## 反思框架

对每个任务，从以下维度分析：

### 1. ✅ 成功之处
- 哪些做得好？
- 什么方法有效？
- 超出预期的地方？

### 2. ❌ 失败之处
- 哪里出错了？
- 根本原因是什么？
- 是工具问题？流程问题？还是判断问题？

### 3. 🔧 改进建议
- 下次如何避免同样的失败？
- 有什么流程可以自动化？
- 需要增加什么检查点？

### 4. 📝 经验提炼
- 形成一条可复用的经验
- 这条经验适用于什么场景？
- 用一个简短的话总结

## 输出格式

用以下格式输出反思结果：

### 🔍 任务反思: [任务名]

**成功:** ...
**失败:** ...
**改进:** ...
**经验:** ...

然后使用 save_to_memory(type="experience") 保存经验。

## 重要
- 诚实分析，不粉饰失败
- 具体指出问题，不泛泛而谈
- 每条经验要可操作、可复用
- 用中文回复"""

    async def reflect_on_task(self, task_info: dict, execution_result: dict) -> str:
        """Run reflection on a completed task.

        Args:
            task_info: Task metadata (title, description, state, etc.)
            execution_result: What happened during execution (tool calls, output, etc.)

        Returns:
            The reflection result ID in experiences table.
        """
        ctx = AgentContext(
            goal=f"""请反思以下任务的执行情况：

## 任务信息
- 名称: {task_info.get('title', 'Unknown')}
- 描述: {task_info.get('description', '')}
- 最终状态: {task_info.get('state', 'unknown')}

## 执行结果
- 输出: {str(execution_result.get('output', ''))[:1000]}
- 工具调用次数: {execution_result.get('tool_calls_count', 0)}
- 是否成功: {execution_result.get('success', False)}

请深度分析这次执行，提炼经验教训。""",
            max_iterations=5,
        )
        result = await self.run(ctx)

        # If the agent produced a good reflection, save it as experience
        if result.success and result.output:
            try:
                self.memory.record_experience(
                    title=f"任务反思: {task_info.get('title', 'Unknown')[:100]}",
                    description=task_info.get('description', ''),
                    lesson=result.output[:500],
                    emotion="neutral",
                    project_id=task_info.get('project_id', ''),
                )
                # Update task state to LEARNED
                task_id = task_info.get('id', '')
                if task_id:
                    self.memory.update_task_reflection(task_id, {
                        "success_analysis": result.output[:300],
                        "reflection_output": result.output,
                        "timestamp": str(__import__('datetime').datetime.now()),
                    })
            except Exception:
                pass

        return result.output
