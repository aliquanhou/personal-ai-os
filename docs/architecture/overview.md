# Personal AI OS — 系统概述

> **版本**: v0.5 | **状态**: Architecture Documentation Freeze
> **最后一版更新**: 2026-08-02

---

## Personal AI OS 是什么？

**Personal AI OS** 不是聊天机器人，不是一个 Agent 框架，也不是 ChatGPT 的套壳。

它是一个 **个人 AI 操作系统** — 用 AI Agent 组织替代传统软件，让一个人可以运营一整支 AI 团队。

---

## 核心理念

```
❌ 不是：另一个 AI 聊天工具
✅ 而是：一个真正有用的 AI 员工团队

AI 团队知道：
- 你是谁（Identity）
- 你做过什么（Memory）
- 你的技术水平（Profile）
- 你的历史决策（Decisions）
- 你当前的目标（Goals）
- 如何协作完成任务（Organization）
- 如何从失败中学习（Governance）
```

---

## 架构总览

```
┌──────────────────────────────────────────────┐
│                  Studio (React UI)             │
│           localhost:3000 — 用户交互界面          │
└────────────────────┬─────────────────────────┘
                     │ HTTP REST
┌────────────────────▼─────────────────────────┐
│              API Layer (FastAPI)               │
│      localhost:8001 — 50+ Endpoints            │
│   Chat / Memory / Org / Comm / Gov / Briefing │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│           KERNEL (8 Modules)                   │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Config  │  │  Events  │  │ LLM Router│     │
│  └──────────┘  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Registry  │  │  Router  │  │Task Graph │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Workspace │  │ Comm Bus │  │Reputation │     │
│  └──────────┘  └──────────┘  └──────────┘     │
│  ┌──────────┐  ┌──────────┐                   │
│  │  Budget  │  │  Audit   │                   │
│  └──────────┘  └──────────┘                   │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│            AGENT RUNTIME (6 Agents)             │
│                                                │
│  CEO → Project Manager → Coding → Research     │
│                   → Writing → Reflection       │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│               MEMORY (SQLite)                   │
│  Profile / Goals / Knowledge / Decisions       │
│  Experiences / Conversations / Tasks / Projects│
└──────────────────────────────────────────────┘
```

---

## 版本演进

| 版本 | 标签 | 核心能力 | 状态 |
|------|------|---------|:--:|
| **v0.1** | — | Agent Loop + Memory + Tools + Studio | ✅ |
| **v0.2** | `v0.2-sprint2` | CEO Agent + Task State Machine + Reflection + Checkpoint + Approval + Briefing | ✅ |
| **v0.3** | `v0.3-sprint3` | Agent Registry + Task Graph + Router (LLM-powered task decomposition) | ✅ |
| **v0.4** | `v0.4-sprint4` | Agent Communication (Mailbox + Channel + Handoff Protocol) | ✅ |
| **v0.5** | `v0.5-sprint5` | Governance (Reputation + Budget + Audit + Scenario Tests) | ✅ |
| **v0.6** | (planned) | Self-Improvement Layer | 🔮 |
| **v1.0** | (planned) | Personal AI Company | 🔮 |

---

## 关键设计决策

### 1. 为什么用 SQLite 而不是向量数据库？

**决策**: SQLite（结构化记忆）+ 计划中的向量检索层

**原因**:
- v0.1–v0.5 阶段，结构化记忆（Profile、Decision、Experience）的价值远大于语义搜索
- 企业级 Memory 的关键是决策连续性，不是检索精度
- SQLite 零运维，适合个人使用
- 向量检索将在 v0.6+ 作为可选增强层加入，不替换 SQLite

### 2. 为什么 Agent 不是简单的 Prompt？

**决策**: Agent = Capability + Permission + MemoryScope

**原因**:
- 多 Agent 系统中，Agent 必须声明"我会什么、我能碰什么、我记得什么"
- 否则 Router 无法做能力匹配
- 否则无法做权限控制（一个写代码的 Agent 不应该删除系统文件）
- 这是治理层（Sprint 5）的基础

### 3. 为什么用 Task Graph (DAG) 而不是线性任务列表？

**决策**: 有向无环图 (DAG) 表示任务依赖关系

**原因**:
- 真实项目不是线性的：需求分析 → 并行开发(后端∥前端) → 集成测试 → 复盘
- DAG 支持并行组识别（同一深度的节点可并行执行）
- 循环检测防止死锁
- 拓扑排序确定执行顺序

### 4. 为什么 Handoff Protocol 而不是直接 Agent 调用？

**决策**: Agent 之间通过 Mailbox + HandoffContext 通信，不直接调用

**原因**:
- 直接调用会造成紧耦合：Agent A 调用 Agent B → A 依赖 B 的接口
- 规模扩大后不可维护
- Mailbox 解耦：A 完成任务 → 发送 Handoff → B 从收件箱读取 → 自动获取上下文
- 类比：真实公司的邮件交接，而不是函数调用

### 5. 为什么先做 Governance 而不是 Marketplace？

**决策**: 路线 v0.5 做治理层，v1.0+ 才考虑市场

**原因**:
- 先建商城没有商品 = 失败（Sprint 0 时已验证的方向判断）
- AI 公司需要内部管理能力（考核、预算、审计）后才适合对外开放
- Marketplace 的底座（Registry + Router + Reputation）已经在 v0.3–v0.5 建好

---

## 运行方式

```bash
# 启动后端
cd personal-ai-os
python main.py serve

# 启动前端（另一个终端）
cd studio
npm run dev

# CLI 模式
python main.py chat "帮我分析一个创业机会"
python main.py agents
python main.py memory-search "AI 产品"
python main.py profile
```

**默认服务端口**:
- API Server: `http://localhost:8001`
- Studio UI: `http://localhost:3000`

---

## 相关文档

- [Kernel 架构](kernel.md)
- [Agent Runtime](agent-runtime.md)
- [Memory 架构](memory-architecture.md)
- [路由与编排](routing-and-orchestration.md)
- [通信层](communication-layer.md)
- [治理层](governance-layer.md)
- [安全模型](security-model.md)
