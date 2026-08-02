# Personal AI OS — Agent Runtime

> **版本**: v0.5 | **Agent 数量**: 6

---

## Agent 是什么？

在 Personal AI OS 中，Agent 不是一个 Prompt 模板。一个 Agent 是：

```
Agent = 角色(System Prompt) + 能力(Capabilities) + 权限(Permissions) + 记忆范围(MemoryScope) + 工具(Tools) + LLM
```

---

## Agent 生命周期

```
  ┌─────────┐
  │ CREATED │  Agent 实例化
  └────┬────┘
       ↓
  ┌──────────┐
  │REGISTERED│  注册到 AgentRuntime + AgentRegistry
  └────┬─────┘
       ↓
  ┌──────────┐
  │ PLANNING │  Router 分析目标 → 分配到此 Agent
  └────┬─────┘
       ↓
  ┌───────────┐
  │ EXECUTING │  Agent.run() 主循环: think → act → observe
  └────┬──────┘
       ↓
  ┌─────────────────┐
  │WAITING_APPROVAL │  (可选) 危险操作需要人工批准
  └────┬────────────┘
       ↓
  ┌───────────┐
  │ COMPLETED │  任务完成 / 达到最大迭代 / 异常崩溃
  └────┬──────┘
       ↓
  ┌───────────┐
  │ REFLECTED │  Reflection Agent 做事后分析
  └────┬──────┘
       ↓
  ┌──────────┐
  │ LEARNED  │  经验存入 Memory，更新 Reputation
  └──────────┘
```

---

## Agent 执行循环 (Agent.run)

```
┌─────────────────────────────────────┐
│           while iteration < max      │
│                                     │
│  1. Publish AGENT_THINKING event    │
│  2. Get tool definitions            │
│  3. Call LLM with messages + tools  │
│  4. If tool_calls:                  │
│     a. Check approval layer         │
│     b. Execute tool                 │
│     c. Audit the action             │
│     d. Save checkpoint (every 3rd)  │
│     e. Append result to messages    │
│  5. If no tool_calls:               │
│     → Final response, break         │
│                                     │
│  On completion:                     │
│  - Record reputation                │
│  - Save memory                      │
│  - Save final checkpoint            │
└─────────────────────────────────────┘
```

**关键特性**:
- **批准层拦截** (Sprint 2): 每个工具调用前经过 `check_approval()` 
- **检查点保存** (Sprint 2): 每 3 个工具调用自动保存状态
- **断点恢复** (Sprint 2): 如果 `resume=True`，从上次检查点继续
- **审计日志** (Sprint 5): 每个工具调用写入审计日志
- **声誉记录** (Sprint 5): 完成时自动更新 Agent 的声誉评分

---

## 当前 Agent 团队

### CEO Agent (`agents/ceo/`)
```
名称: ceo
层级: ceo
描述: AI 幕僚长 — 理解目标、制定策略、协调团队、每日简报
能力: orchestration, strategy, decision_making, task_routing, briefing,
      memory_read, memory_write, reflection, project_planning, analysis
权限: memory_read, memory_write, read_workspace, write_workspace, manage_agents
记忆: all
```

**系统提示核心**: 包含老板画像（长期愿景、决策原则、厌恶事项）、活跃目标列表、进行中任务列表。要求每次回复有产出，不只分析不做。

### Project Manager Agent (`agents/project_manager/`)
```
名称: project_manager
层级: manager
描述: 将用户目标转化为结构化项目计划和任务
能力: project_planning, task_execution, file_ops, memory_write, analysis
权限: memory_read, memory_write, read_workspace, write_workspace
记忆: projects, tasks, knowledge
```

### Coding Agent (`agents/coding/`)
```
名称: coding_agent
层级: specialist
描述: 编写、审查、调试代码
能力: code_generation, code_review, code_debug, file_ops, shell_exec, task_execution
权限: read_workspace, write_workspace, exec_shell_safe
记忆: knowledge, experiences, projects
```

### Research Agent (`agents/coding/`)
```
名称: research_agent
层级: specialist
描述: 搜索信息、分析市场、综合发现
能力: research, analysis, writing, memory_read, web_search
权限: memory_read, memory_write, read_workspace, external_network
记忆: knowledge, decisions, experiences
```

### Writing Agent (`agents/coding/`)
```
名称: writing_agent
层级: specialist
描述: 撰写文档、报告、内容创作
能力: writing, file_ops, memory_read
权限: read_workspace, write_workspace
记忆: knowledge, conversations
```

### Reflection Agent (`agents/reflection/`)
```
名称: reflection_agent
层级: utility
描述: 任务后深度分析，提炼经验教训
能力: reflection, analysis, memory_read, memory_write
权限: memory_read, memory_write
记忆: experiences, decisions, tasks
```

---

## 定义一个新 Agent

```python
# 1. 创建 Agent 类
from agents.runtime import AgentContext, BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            description="我的专用 Agent",
        )

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个专用 Agent...
        用户信息: {ctx.user_profile}
        历史背景: {ctx.memory_context}
        队友消息: {ctx.mailbox_context}
        """

# 2. 注册到 Runtime 和 Registry
runtime = get_agent_runtime()
runtime.register(MyAgent())

registry = get_agent_registry()
registry.register(AgentDescriptor(
    name="my_agent",
    description="我的专用 Agent",
    capabilities=[Capability.CODE_GENERATION, Capability.ANALYSIS],
    permissions=[AgentPermission.READ_WORKSPACE, AgentPermission.WRITE_WORKSPACE],
    memory_scope=[MemoryScope.KNOWLEDGE, MemoryScope.PROJECTS],
    tier="specialist",
    input_formats=["task"],
    output_formats=["code"],
    agent_ref=my_agent_instance,
))

# 3. 使用
router = get_agent_router()
result = await router.quick_route("帮我做X", preferred_agent="my_agent")
```

---

## AgentContext — 上下文传递

Agent 执行时接收的完整上下文：

```python
@dataclass
class AgentContext:
    session_id: str           # 会话 ID
    goal: str                 # 当前目标
    user_profile: dict        # 用户画像（从 Memory 加载）
    memory_context: str       # 记忆上下文（从 Memory 加载）
    max_iterations: int       # 最大迭代次数（默认 30）
    current_iteration: int    # 当前迭代计数
    project_slug: str         # 所属项目
    checkpoints: list[dict]   # 检查点历史
    resume_from_checkpoint: dict | None  # 断点恢复数据
    mailbox_context: str      # 队友消息（Sprint 4）
    handoff_context: dict | None  # 上游交接上下文（Sprint 4）
```

---

## 错误处理

```
Agent 执行过程中可能的状态:

正常完成:
  AGENT_STARTED → THINKING × N → AGENT_COMPLETED

达到最大迭代:
  AGENT_STARTED → THINKING × max_iterations → AGENT_ERROR(max_iterations)

LLM 调用失败:
  AGENT_STARTED → THINKING → AGENT_ERROR(exception)
  → 返回 AgentResult(success=False, error=...)
  → 声誉记录为 failure

工具执行失败:
  AGENT_STARTED → THINKING → TOOL_CALL_START → TOOL_CALL_END(❌)
  → 错误信息注入 messages
  → Agent 可以尝试其他方案
  → 审计日志记录错误
```
