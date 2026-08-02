# Personal AI OS — 路由与编排

> **版本**: v0.5 | **核心模块**: `kernel/router.py`, `kernel/registry.py`, `kernel/task_graph.py`

---

## 概述

路由与编排层是 Personal AI OS 的"项目经理系统"。它负责：

1. 理解用户目标（通过 LLM 分析）
2. 将大目标分解为具体任务
3. 匹配每个任务到最合适的 Agent
4. 构建任务依赖图（DAG）
5. 按拓扑顺序执行任务
6. 在任务间传递上下文（Handoff）

---

## 核心流程

```
用户目标: "开发一个AI客服系统"
          │
          ▼
   ┌──────────────────┐
   │  Router.plan()   │
   │  LLM 分析目标     │
   │  ↓               │
   │  任务分解         │
   │  ↓               │
   │  能力匹配         │
   │  ↓               │
   │  RoutePlan       │
   └──────┬───────────┘
          │
          ▼
   ┌──────────────────┐
   │  TaskGraph       │
   │                  │
   │  需求分析         │ ← research_agent
   │    ↓              │
   │  系统设计         │ ← project_manager
   │    ↓              │
   │  后端开发 ∥ 前端开发│ ← coding_agent (parallel)
   │    ↓              │
   │  集成测试         │ ← coding_agent
   │    ↓              │
   │  项目复盘         │ ← reflection_agent
   └──────┬───────────┘
          │
          ▼
   ┌──────────────────┐
   │  Router.execute   │
   │  拓扑排序执行      │
   │  每步保存检查点    │
   │  节点间 Handoff    │
   │  完成后声誉记录    │
   └──────────────────┘
```

---

## Agent Router

### `plan()` — 计划（不执行）

```python
async def plan(goal: str) -> RoutePlan:
    # 1. 构建分析 Prompt（包含可用 Agent 列表）
    prompt = _build_analysis_prompt(goal, profile)

    # 2. 调用 LLM 做任务分解
    response = await llm.chat(prompt)

    # 3. 解析 JSON → TaskNodes + 依赖关系
    tasks = _parse_tasks_from_analysis(response.content)

    # 4. 构建 TaskGraph (DAG)
    graph = _build_task_graph(goal, tasks)

    # 5. 能力匹配 → Agent 分配
    assignments = _assign_agents(graph)

    return RoutePlan(goal, graph, assignments, ...)
```

### `execute_plan()` — 执行计划

```python
async def execute_plan(plan: RoutePlan) -> dict:
    # 1. 获取拓扑排序
    order = plan.graph.topological_order()

    for node in order:
        # 2. 收集上游 Agent 的 Handoff 上下文
        handoff = collect_handoffs_from_dependencies(node)

        # 3. 注入手交上下文
        goal = prepend_handoff(node.goal, handoff)

        # 4. 执行 Agent
        result = await runtime.execute(agent_name, goal)

        # 5. 发送 Handoff 到下游 Agent
        send_handoff_to_dependents(node, result)

        # 6. 保存结果，更新节点状态
        node.result = result
        node.state = COMPLETED / FAILED

    return graph.get_progress()
```

### `quick_route()` — 快速路由

单 Agent 模式：跳过 DAG，直接匹配最合适的 Agent 执行。

```python
async def quick_route(goal: str) -> dict:
    # 能力匹配 → 选最佳 Agent → 直接执行
    matches = registry.match_team(required_caps, max_agents=1)
    agent = matches[0]
    result = await runtime.execute(agent.name, goal)
    return result
```

---

## Task Graph — DAG 任务依赖

### 为什么是 DAG？

真实项目任务不是线性的：

```
✅ 正确的 DAG 模型:
   需求分析 → 架构设计 → [后端开发, 前端开发] → 集成测试 → 复盘

❌ 错误的线性模型:
   需求分析 → 系统设计 → 后端开发 → 前端开发 → 集成测试 → 复盘
   (前端白白等待后端完成，实际上它们可以并行)
```

### 核心方法

```python
graph = TaskGraph(goal="开发AI客服")

# 添加节点
a = TaskNode(title="需求分析", assigned_agent="research_agent")
b = TaskNode(title="架构设计", assigned_agent="project_manager")
c = TaskNode(title="后端开发", assigned_agent="coding_agent")
d = TaskNode(title="前端开发", assigned_agent="coding_agent")

graph.add_node(a); graph.add_node(b)
graph.add_node(c); graph.add_node(d)

# 建立依赖
graph.add_edge(a.id, b.id)  # b 依赖 a
graph.add_edge(b.id, c.id)  # c 依赖 b
graph.add_edge(b.id, d.id)  # d 依赖 b  (c 和 d 可并行!)

# 查询
graph.topological_order()   # [a, b, c, d]
graph.get_parallel_groups()  # [[a], [b], [c, d]]
graph.get_progress()         # {'total': 4, 'completed': 0, ...}
```

### 循环检测

```python
def _has_cycle(graph) -> bool:
    # DFS + in-stack 标记
    # 如果发现 back edge → 拒绝添加
    # add_edge() 自动检测，有循环时返回 False
```

### 节点状态机

```
PENDING  → 等待依赖完成
READY    → 依赖已满足，可执行
RUNNING  → 正在执行的 Agent
COMPLETED → 执行成功
FAILED   → 执行失败
SKIPPED  → 上游失败导致跳过
```

---

## 能力匹配机制

### 匹配算法

```python
def match_team(required_capabilities: list[Capability], max_agents: int = 5):
    scored = []
    for agent in all_agents:
        # 基础分 = 能力匹配度
        capability_score = len(my_caps ∩ required_caps) / len(required_caps)

        # Sprint 5: 声誉加权
        final_score = 0.6 * capability_score + 0.4 * reputation_score

        scored.append((final_score, agent))

    scored.sort(reverse=True)
    return [agent for _, agent in scored[:max_agents]]
```

### 任务类型 → 能力映射

```python
TASK_CAPABILITY_MAP = {
    "research":       [RESEARCH, ANALYSIS],
    "market_analysis": [RESEARCH, ANALYSIS, STRATEGY],
    "planning":       [PROJECT_PLANNING, STRATEGY],
    "coding":         [CODE_GENERATION, FILE_OPS],
    "code_review":    [CODE_REVIEW],
    "debug":          [CODE_DEBUG, CODE_GENERATION],
    "writing":        [WRITING, FILE_OPS],
    "testing":        [CODE_GENERATION, SHELL_EXEC],
    "reflection":     [REFLECTION, MEMORY_WRITE],
    "briefing":       [BRIEFING, MEMORY_READ],
    "orchestration":  [ORCHESTRATION, DECISION_MAKING],
}
```

---

## RoutePlan — 计划数据结构

```python
@dataclass
class RoutePlan:
    goal: str                          # 原始目标
    analysis: str                      # LLM 分析结果
    graph: TaskGraph | None            # 任务依赖图
    agent_assignments: dict[str, str]  # node_id → agent_name
    execution_order: list[str]         # 拓扑排序后的 node IDs
    estimated_duration: str            # 预估耗时
```

**用途**: RoutePlan 是计划的「快照」。用户可以：
- 先看计划，确认后再执行
- 修改 agent_assignments 再执行
- 将计划持久化（存储在 TaskGraphStore 中）

---

## LLM 分析 Prompt 模板

```markdown
分析以下用户目标，将其分解为具体的执行任务。
每个任务需要指定：
1. 任务名称和描述
2. 需要的能力标签
3. 依赖关系

## 用户背景
- 技术栈: Python, TypeScript, React, FastAPI
- 长期愿景: 建立AI产品公司
- 决策原则: 快速验证优先于完美设计

## 目标
{goal}

## 可用 Agent 团队
- ceo: 编排、策略、决策
- project_manager: 项目规划、任务执行
- coding_agent: 代码生成、审查、调试
- research_agent: 研究分析
- writing_agent: 写作内容创作
- reflection_agent: 反思学习

## 输出格式 (JSON)
{
  "tasks": [
    {"title": "...", "description": "...", "agent": "...", "dependencies": [...]}
  ]
}
```

---

## 两种路由模式对比

| 特性 | `plan() + execute_plan()` | `quick_route()` |
|------|--------------------------|-----------------|
| Agent 数量 | 多 Agent 团队 | 单个 Agent |
| 任务分解 | LLM 分解 + DAG | 无分解，直接执行 |
| 上下文传递 | Handoff Protocol | 无 |
| 并行执行 | 支持（同深度节点） | 不支持 |
| 适用场景 | 复杂项目（3+ 步骤） | 简单任务（代码片段、问题回答） |
| 耗时 | 较长（多次 LLM 调用） | 较短（单次调用） |

---

## 设计权衡

### 为什么不是全自动编排？
所有用户输入都经过 LLM 分析会有延迟和成本。`quick_route()` 是 "快速通道"——简单任务不需要全套编排。

### 为什么不是完全并行？
当前 v0.5 的 `execute_plan()` 是顺序执行（即使有并行组）。未来 v0.6 计划用 `asyncio.gather()` 并行执行同深度节点。

### 为什么能力匹配是静态的？
当前的能力声明是手动定义的。v0.6 计划让 Agent 根据实际表现动态调整能力标签（通过声誉系统反馈）。
