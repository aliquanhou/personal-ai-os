# Contributing to Personal AI OS

> 参与 Personal AI OS 开发的规范

---

## 核心理念

Personal AI OS 不是一个传统开源项目。它是一个 **AI 驱动的软件组织**。贡献方式有两种：

1. **人类贡献者** — 提交代码、文档、Issue
2. **AI Agent 贡献者** — 通过 Agent Registry 注册，由 Router 调度

本文档主要面向人类贡献者。

---

## 项目架构素养

在提交任何代码之前，请阅读：

1. [CLAUDE.md](CLAUDE.md) — 项目入口知识
2. [docs/architecture/overview.md](docs/architecture/overview.md) — 系统概述
3. [docs/architecture/kernel.md](docs/architecture/kernel.md) — Kernel 职责边界

---

## 新增 Agent 流程

如果你要添加一个新 Agent：

### Step 1: Agent Proposal

创建 Issue，回答：

```markdown
### Agent 提案: <Agent 名称>

**职责**: 这个 Agent 负责什么？（一句话）

**能力**: 它在 Capability 枚举中需要哪些标签？
- [ ] code_generation
- [ ] research
- [ ] ...

**权限**: 它需要访问什么？
- [ ] read_workspace
- [ ] memory_write
- [ ] ...

**记忆范围**: 哪些 MemoryScope？
- [ ] knowledge
- [ ] projects
- [ ] ...

**与其他 Agent 的关系**: 它接收谁的 Handoff？它向谁 Handoff？

**为什么需要**: 现有 Agent 为什么不能做这个？
```

### Step 2: 实现

```python
# agents/my_agent/__init__.py
from agents.my_agent.agent import MyAgent
__all__ = ["MyAgent"]

# agents/my_agent/agent.py
from agents.runtime import AgentContext, BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="my_agent", description="...")

    def system_prompt(self, ctx: AgentContext) -> str:
        return f"""你是一个...
        用户信息: {ctx.user_profile}
        历史背景: {ctx.memory_context}
        """
```

### Step 3: 注册

在 `api/app.py` 的 `startup()` 中注册：

```python
from agents.my_agent import MyAgent

my_agent = MyAgent()
runtime.register(my_agent)

registry.register(AgentDescriptor(
    name="my_agent",
    description="...",
    capabilities=[Capability....],
    permissions=[AgentPermission....],
    memory_scope=[MemoryScope....],
    tier="specialist",
    agent_ref=my_agent,
))
```

### Step 4: 测试

创建 `tests/scenarios/my_agent_test.json`：

```json
{
  "name": "my_agent_test",
  "goal": "测试我的 Agent 处理的任务",
  "expected_agents": ["my_agent"],
  "expected_tasks": [...],
  "checks": [...]
}
```

---

## 新增 Kernel 模块流程

### Step 1: 确定层叠位置

Kernel 模块按 Sprint 分层：
- **基础层** (Sprint 0-2): config, events, llm_router, workspace
- **组织层** (Sprint 3): registry, task_graph, router
- **通信层** (Sprint 4): comm_bus
- **治理层** (Sprint 5): reputation, budget, audit

新模块必须层叠在**已有模块之上**，不修改已稳定的下层。

### Step 2: 实现

```python
# kernel/new_module.py

# 使用全局单例模式
_module: NewModule | None = None

def get_new_module() -> NewModule:
    global _module
    if _module is None:
        _module = NewModule()
    return _module
```

### Step 3: 注册

在 `kernel/__init__.py` 中添加导入和导出。

### Step 4: 文档

在 `docs/architecture/` 中更新或新增对应文档。

---

## 代码规范

### Python

- Python 3.12+
- 类型提示（`Mapped[str]`, `dict[str, Any]`, `list[dict]`）
- Docstring 用三重引号
- 全局单例模式：`_instance | None = None` + `get_*()` 函数
- 日志：`logger = logging.getLogger(__name__)`

### 命名约定

```python
# 模块：snake_case
kernel/comm_bus.py, agents/runtime.py

# 类：PascalCase
class AgentRouter, class TaskGraph, class CommunicationBus

# 函数：snake_case
def get_agent_router(), def execute_plan()

# 枚举：PascalCase
class Capability(StrEnum), class MessageType(StrEnum)
```

### Commit 格式

```
feat: 新功能
fix: 修复
docs: 文档
chore: 工程杂项
refactor: 重构
test: 测试

示例:
feat: Sprint 5 — Agent Governance Layer
fix: shell tool python3 → python for Windows
docs: Personal AI OS Architecture Specification v0.5
```

---

## 测试规范

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 特定测试文件
python -m pytest tests/test_kernel.py -v

# 场景测试
python -m pytest tests/scenarios/ -v
```

### 必须测试

- 新增 Agent → 至少 1 个 Scenario Test
- 新增 Kernel 模块 → 至少 3 个单元测试
- 新增 API 端点 → 1 个请求/响应测试

---

## 沟通规范

### Issue 标签

| 标签 | 用途 |
|------|------|
| `agent-proposal` | 新 Agent 提案 |
| `kernel-module` | 新 Kernel 模块提案 |
| `bug` | Bug 报告 |
| `docs` | 文档改进 |
| `architecture` | 架构讨论 |

### Bug 报告格式

```markdown
### 描述
简洁描述 bug

### 复现
1. 执行 `python main.py serve`
2. 发送 `curl -X POST ...`
3. 观察到...

### 预期行为
应该发生什么

### 实际行为
实际发生了什么

### 环境
- OS: Windows 10
- Python: 3.12.0
- Commit: 47d65cb
```

---

## 冻结功能（当前不接受贡献）

以下功能已明确冻结，请勿提交相关 PR：

- ❌ Plugin Marketplace
- ❌ Agent Economy / 商城
- ❌ 多用户支持
- ❌ 社交功能
- ❌ WebSocket 实时通信

这些是第二阶段功能，将在 v1.0+ 解冻。
