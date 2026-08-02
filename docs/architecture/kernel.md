# Personal AI OS — Kernel 架构

> **版本**: v0.5 | **模块数**: 11

---

## Kernel 的职责边界

Kernel 是 Personal AI OS 的核心基础设施层。它负责：

- **系统配置** — 环境变量、LLM 设置、服务器参数
- **事件总线** — 组件间的松耦合通信
- **Agent 注册与发现** — 能力声明、权限管理、团队定义
- **任务路由与编排** — LLM 驱动目标分析、DAG 执行
- **工作空间管理** — 项目目录结构、检查点、状态持久化
- **Agent 间通信** — 邮箱、频道、交接协议
- **治理** — 声誉、预算、审计

Kernel **不负责**:
- Agent 的具体行为逻辑（在 `agents/` 中定义）
- 用户界面（在 `studio/` 中）
- HTTP 路由（在 `api/` 中）
- 数据库 Schema（在 `memory/models.py` 中）

---

## 模块地图

```
kernel/
├── config.py          # 系统配置（环境变量 → LLM/Memory/Server 配置）
├── events.py          # 事件总线（发布/订阅，解耦组件通信）
├── llm_router.py      # LLM 路由（DeepSeek/OpenAI/Anthropic/Ollama）
├── permission.py      # 权限管理（资源类型 × 权限级别）
├── workspace.py       # 工作空间（项目目录、状态、检查点、备份）
├── registry.py        # Agent 注册（能力声明 + 权限 + 记忆分区）
├── task_graph.py      # 任务图（DAG 依赖 + 拓扑排序 + 并行组）
├── router.py          # Agent 路由（LLM 目标分析 + 能力匹配 + 编排执行）
├── comm_bus.py        # 通信总线（邮箱 + 频道 + 交接协议）
├── reputation.py      # 声誉系统（成功率 × 速度 × 一致性 = 评分）
├── budget.py          # 预算管理（模型定价 + 日/月/任务限额 + 预检查）
└── audit.py           # 审计日志（决策/行动/预算/安全/错误 五流追踪）
```

---

## 模块详细说明

### `config.py` — 系统配置

**职责**: 从 `.env` 加载配置，提供统一 Config 对象。

**关键数据结构**:
- `LLMConfig` — provider, model, api_key, base_url, temperature, max_tokens
- `MemoryConfig` — db_url, file_dir
- `ServerConfig` — host, port

**Provider 路由逻辑**:
```
DEFAULT_LLM_PROVIDER=deepseek → api.deepseek.com/v1
                              → DEEPSEEK_API_KEY
DEFAULT_LLM_PROVIDER=openai   → api.openai.com/v1
                              → OPENAI_API_KEY
DEFAULT_LLM_PROVIDER=anthropic → api.anthropic.com
                               → ANTHROPIC_API_KEY
DEFAULT_LLM_PROVIDER=ollama   → localhost:11434/v1
```

### `events.py` — 事件总线

**职责**: 组件间松耦合通信。任何 Kernel 组件都可以发布/订阅事件。

**事件类型**:
- `agent:*` — started, thinking, action, completed, error
- `tool:*` — call:start, call:end, call:error
- `memory:*` — saved, recalled, updated
- `system:*` — startup, shutdown, error
- `user:*` — message, action

**设计原则**: 组件不应直接互相调用。通过事件总线解耦。

### `llm_router.py` — LLM 路由

**职责**: 统一的 LLM 调用接口，屏蔽不同 Provider 差异。

**Provider 实现**:
- `OpenAICompatibleProvider` — DeepSeek, OpenAI, Ollama, Qwen (共享 OpenAI API 格式)
- `AnthropicProvider` — Claude (独立的 Anthropic Messages API)

**全局单例**: `get_llm_router()` — 所有 Agent 共享一个 LLM 连接。

### `workspace.py` — 工作空间管理

**职责**: 每个项目拥有标准化的文件系统结构。

**目录结构**:
```
workspace/projects/<slug>/
├── project.json       # 元数据
├── state.json         # 运行时状态（检查点历史、活跃任务）
├── decisions.json     # 项目内决策记录
├── artifacts/         # 实际产出文件（代码、文档等）
└── backups/           # 自动状态备份
```

**关键方法**: `create_project`, `save_checkpoint`, `get_last_checkpoint`, `get_workspace_status`

### `registry.py` — Agent 注册

**职责**: Agent 的形式化声明系统。

**Agent = Capability + Permission + MemoryScope**

```
ceo:
  能力: orchestration, strategy, decision_making, briefing, ...
  权限: memory_read, memory_write, manage_agents, ...
  记忆范围: all
  层级: ceo

coding_agent:
  能力: code_generation, code_review, code_debug, file_ops, shell_exec
  权限: read_workspace, write_workspace, exec_shell_safe
  记忆范围: knowledge, experiences, projects
  层级: specialist
```

**默认团队配置**:
- `product_dev` — ceo + pm + research + coding + reflection
- `quick_code` — ceo + coding
- `research` — ceo + research + writing + reflection
- `full_team` — 全部 6 个 Agent

### `task_graph.py` — 任务图

**职责**: 用 DAG 表示任务依赖关系。

**节点状态机**:
```
PENDING → READY → RUNNING → COMPLETED / FAILED / SKIPPED
```

**关键操作**:
- `add_edge(from, to)` — 添加依赖（自动检测循环）
- `topological_order()` — 拓扑排序（确定执行顺序）
- `get_parallel_groups()` — 并行组识别（同深度无依赖节点）
- `get_progress()` — 进度追踪

### `router.py` — Agent 路由与编排

**职责**: 将用户目标转化为 Agent 团队执行计划。

**核心流程**:
```
User Goal
  ↓
Router.plan(goal)          # LLM 分析 → 任务分解 → Graph 构建 → Agent 分配
  ↓
RoutePlan                  # 计划对象（不执行）
  ↓
Router.execute_plan(plan)  # 按拓扑顺序逐一执行节点
  ↓
Results + Handoff          # 节点间传递上下文
```

**两种路由模式**:
- `plan()` + `execute_plan()` — 完整编排（多 Agent，DAG 执行）
- `quick_route()` — 快速单 Agent 路由

### `comm_bus.py` — 通信总线

**职责**: Agent 间的消息传递基础设施。

**三种通信原语**:

| 原语 | 类比 | 用途 |
|------|------|------|
| **Mailbox** | 电子邮件收件箱 | Agent 间直接消息 |
| **Channel** | Slack 频道 | 团队广播 |
| **HandoffProtocol** | 工作交接单 | 上下游上下文传递 |

**消息类型**: request, response, notification, handoff, question, alert

详见 [通信层文档](communication-layer.md)。

### `reputation.py` — 声誉系统

**职责**: 追踪每个 Agent 的历史表现，影响路由质量。

**评分公式**: `reputation_score = 0.5 × success_rate + 0.3 × speed_score + 0.2 × recent_consistency`

**等级**: S(≥0.90), A(≥0.80), B(≥0.65), C(≥0.50), D(<0.50)

详见 [治理层文档](governance-layer.md)。

### `budget.py` — 预算管理

**职责**: 控制 AI 调用成本。

**预算维度**:
- 每日限额（默认 $5.00）
- 每月限额（默认 $100.00）
- 单任务限额（默认 $2.00）

**状态**: ACTIVE → WARNING(80%) → CRITICAL(95%) → EXCEEDED(100%)

详见 [治理层文档](governance-layer.md)。

### `audit.py` — 审计日志

**职责**: 不可变的事件追踪。

**审计类别**: DECISION, ACTION, BUDGET, SECURITY, ERROR, SYSTEM

**持久化**: JSONL 文件（追加写入磁盘，每一条即时保存）

详见 [治理层文档](governance-layer.md)。

---

## 模块间的依赖关系

```
config ← (无依赖，最先初始化)
  ↓
events ← (无依赖)
llm_router ← config
workspace ← (独立)
  ↓
registry ← (独立，引用 Agent 实例)
task_graph ← (独立)
  ↓
router ← registry + task_graph + llm_router + comm_bus
comm_bus ← registry（创建 Channel 时引用团队配置）
  ↓
reputation ← (独立，从 agent runtime 接收数据)
budget ← config
audit ← (独立，从 agent runtime 接收数据)
```

**设计原则**: 新增模块只能层叠在上层，不修改已稳定的下层模块。每个 Sprint 增加一层。

---

## 全局单例模式

所有 Kernel 模块使用 `get_*()` 全局单例模式：

```python
_module: SomeModule | None = None

def get_some_module() -> SomeModule:
    global _module
    if _module is None:
        _module = SomeModule()
    return _module
```

**原因**: 
- 避免依赖注入框架的复杂性
- 所有 Agent 共享同一个 LLM 连接、Memory 连接、Event Bus
- 适合个人使用场景（单用户，单进程）

**限制**: 不适合多用户/多租户场景。如果未来需要，需重构为依赖注入。
