# CLAUDE.md — Personal AI OS

> AI 员工入职文档。每个 Claude 实例在这个仓库中工作时，首先阅读此文件。

---

## 项目身份

**Personal AI OS** v0.5 — 个人 AI 操作系统。

不是一个聊天机器人。不是一个 Agent 框架。是一个用 AI Agent 组织替代传统软件的运行时。

## 架构 (2029 行文档 → `docs/architecture/`)

| 文档 | 内容 |
|------|------|
| [overview.md](docs/architecture/overview.md) | 系统概述、版本演进、关键设计决策 |
| [kernel.md](docs/architecture/kernel.md) | Kernel 11 模块的职责边界和依赖关系 |
| [agent-runtime.md](docs/architecture/agent-runtime.md) | Agent 生命周期和 6 Agent 规格 |
| [memory-architecture.md](docs/architecture/memory-architecture.md) | 9 表分层记忆模型和 Context 注入 |
| [routing-and-orchestration.md](docs/architecture/routing-and-orchestration.md) | Router/Plan/Execute 和 DAG 编排 |
| [communication-layer.md](docs/architecture/communication-layer.md) | Mailbox/Channel/Handoff 通信协议 |
| [governance-layer.md](docs/architecture/governance-layer.md) | Reputation/Budget/Audit 治理支柱 |
| [security-model.md](docs/architecture/security-model.md) | 5 层纵深防御和安全路线图 |

## 版本线

```
v0.5-sprint5  Agent Governance     ← 当前
v0.4-sprint4  Agent Communication
v0.3-sprint3  Agent Organization
v0.2-sprint2  Reliability Layer
```

Git tags: `v0.2-sprint2`, `v0.3-sprint3`, `v0.4-sprint4`, `v0.5-sprint5`

## 运行

```bash
# 后端
python main.py serve --host 127.0.0.1 --port 8001

# 前端
cd studio && npm run dev

# CLI
python main.py chat "帮我分析一个创业机会"
```

## 关键文件

| 用途 | 路径 |
|------|------|
| API 入口 | `api/app.py` (50+ endpoints) |
| Agent 基类 | `agents/runtime.py` (BaseAgent + AgentRuntime) |
| Kernel 模块 | `kernel/` (11 modules) |
| Memory 管理 | `memory/manager.py` + `memory/models.py` |
| 工具系统 | `tools/registry.py` (8 tools + approval layer) |
| 配置 | `kernel/config.py` + `.env` |
| LLM 路由 | `kernel/llm_router.py` |

## 全局单例模式

所有 Kernel 和 Memory 模块使用 `get_*()` 单例：
`get_agent_runtime()`, `get_memory()`, `get_agent_registry()`, `get_agent_router()`, `get_comm_bus()`, `get_reputation_registry()`, `get_budget_manager()`, `get_audit_log()`, `get_workspace()`

## 新增模块规则

1. 新增 Kernel 模块只能层叠在现有模块之上，不修改已稳定的下层
2. 每个新增模块在 `kernel/__init__.py` 中注册导出
3. 模块间依赖通过 `get_*()` 单例获取，不使用依赖注入
4. 所有模块的 import 使用绝对路径（从项目根开始）

## 当前冻结功能

- ❌ Plugin Marketplace
- ❌ Agent Economy
- ❌ 多用户支持
- ❌ 社交功能
- ❌ WebSocket 实时通信

## 下一步 (v0.6)

Self-Improvement Layer: AI 根据历史任务自动优化 Prompt / Router / Skills
