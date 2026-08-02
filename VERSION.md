# VERSION

> 当前版本状态 — 单文件版本声明

```
Personal AI OS  v0.5.0
Code Name       AI Company Runtime
Git Tag         v0.5-docs-freeze
Branch          sprint-5
Commit          47d65cb
Date            2026-08-02
Python          3.12+
Node            20+
```

## 版本标识

| 组件 | 版本 |
|------|------|
| Kernel | 0.5 (11 modules) |
| Agent Runtime | 0.5 (6 agents) |
| Memory | 0.5 (9 tables) |
| API | 0.5 (50+ endpoints) |
| Studio | 0.2 (React + Tailwind) |
| Tools | 0.3 (8 tools + approval) |
| Tests | 0.5 (scenario framework) |

## 稳定性声明

| 模块 | 稳定性 | 说明 |
|------|:--:|------|
| `kernel/events` | STABLE | 自 v0.1 未变动 |
| `kernel/config` | STABLE | 自 v0.2 稳定 |
| `kernel/llm_router` | STABLE | Provider 扩展是安全的 |
| `kernel/workspace` | STABLE | 自 v0.2 稳定 |
| `kernel/registry` | STABLE | AgentDescriptor 格式稳定 |
| `kernel/task_graph` | STABLE | DAG 算法稳定 |
| `kernel/router` | EVOLVING | v0.6 计划加并行执行 |
| `kernel/comm_bus` | EVOLVING | v0.6 计划加消息持久化 |
| `kernel/reputation` | EVOLVING | 权重参数可能调整 |
| `kernel/budget` | EVOLVING | 计划加入模型价格自动更新 |
| `kernel/audit` | STABLE | JSONL 格式不会变 |
| `agents/runtime` | EVOLVING | 新上下文字段会继续增加 |
| `memory/manager` | EVOLVING | 向量检索层计划加入 |
| `tools/registry` | STABLE | ToolDefinition 格式稳定 |
| `api/app` | EVOLVING | 新端点持续增加 |

## 下一版本

```
v0.6.0  Self-Improvement Layer
        AI evolution advisor + skill optimization
        Planned: 2026-08
```
