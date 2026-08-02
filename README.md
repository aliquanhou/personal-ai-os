# Personal AI OS v1.0

> 你的 AI 公司。一个人 + 一支 AI 团队。

**Personal AI OS** 不是一个聊天机器人。它是一个 AI Agent 操作系统的运行时——像一个微型的 AI 公司，有 CEO、有工程师、有研究员、有作家，协同完成你的任务。

---

## 快速开始

```bash
# 1. 克隆
git clone <repo-url> personal-ai-os
cd personal-ai-os

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key
# 推荐 DeepSeek：DEEPSEEK_API_KEY=sk-...

# 3. 一键启动（自动检测环境 + 安装依赖 + 启动服务）
python main.py start

# 4. 打开 Studio
# http://localhost:3000  (另一个终端: cd studio && npm run dev)

# 5. 开始对话
python main.py chat "帮我分析一个创业机会"
```

首次运行会自动检测：OS → Python → 依赖 → Node → Git → .env配置 → 端口。缺什么会自动安装修复。

---

## 核心理念

```
❌ 不是 ChatGPT 套壳
✅ 而是一个 AI 组织运行时

CEO 理解你的目标
Router 分配任务给专业 Agent
Agent 使用 Skill 执行
Reflection 沉淀经验
Evolution 持续优化
```

---

## 架构

```
┌──────────────────────────────────┐
│        Studio UI (React)          │
│   Chat / Workspace / Timeline     │
│   Memory / Plugins / Agents       │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│       API Server (FastAPI)        │
│       60+ Endpoints               │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│          KERNEL                   │
│  Config · Events · LLM Router    │
│  Registry · Router · Task Graph  │
│  Comm Bus · Reputation · Budget  │
│  Audit · Evolution · Plugin RT   │
│  Skill Registry · Router · Exec  │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│        AGENT RUNTIME              │
│  CEO → PM → Coder → Researcher   │
│       → Writer → Reflection      │
│       → Environment              │
└────────────┬─────────────────────┘
             │
┌────────────▼─────────────────────┐
│          MEMORY (SQLite)          │
│  Profile · Goals · Knowledge     │
│  Decisions · Experiences         │
│  Conversations · Tasks           │
└──────────────────────────────────┘
```

---

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| 前端 | React 19, TypeScript, Vite, Tailwind, Zustand |
| LLM | DeepSeek / OpenAI / Anthropic / Ollama |
| 测试 | pytest, Scenario Framework, Benchmark Suite |

---

## 配置 API Key

编辑 `.env`：

```bash
# DeepSeek (推荐 — 成本低、中文强)
DEEPSEEK_API_KEY=sk-your-key
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat

# 或 OpenAI
# OPENAI_API_KEY=sk-your-key
# DEFAULT_LLM_PROVIDER=openai
# DEFAULT_MODEL=gpt-4o

# 或本地 Ollama
# DEFAULT_LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434/v1
# DEFAULT_MODEL=llama3
```

---

## CLI 命令

```bash
python main.py start              # 一键启动（首次运行推荐）
python main.py serve              # 直接启动服务
python main.py restart --port 8001 # 精准重启（端口定位）
python main.py chat "你的目标"     # CLI 对话
python main.py agents             # 列出所有 Agent
python main.py profile            # 查看用户画像
python main.py benchmark           # 运行 Benchmark
```

---

## 插件系统

5 个官方插件开箱即用：

| 插件 | 状态 | 能力 |
|------|:--:|------|
| **Coding Agent** | ✅ 启用 | Python 开发、Web 后端、Bug 修复、测试生成 |
| **Research Agent** | ✅ 启用 | 市场分析、竞品研究、报告生成 |
| **Writing Agent** | ✅ 启用 | 文案、博客、产品介绍、技术文档 |
| **Knowledge & File** | ⬜ 可选 | 本地文件、Markdown、知识库问答 |
| **Web Assistant** | ⬜ 可选 | 网页抓取、内容提取 |

启用/禁用：Studio → Plugins 页面，一键切换。

---

## 第一个任务

```bash
python main.py chat "帮我创建一个 FastAPI 待办事项 API，包含 CRUD 和测试"
```

AI 自动：
1. CEO 分析需求
2. Router 分配给 Coding Agent + Python Backend Skill
3. 生成 `main.py` + 测试文件
4. 自动 checkpoint 保存进度
5. Timeline 显示完整执行过程

---

## 开发插件

在 `plugins/` 下创建目录和 `plugin.json`：

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "display_name": "My Custom Plugin",
  "description": "自定义能力包",
  "official": false,
  "skills": ["python_backend"],
  "target_agents": ["coding_agent"],
  "enabled": true
}
```

重启服务后自动发现。

---

## 文档

完整架构文档：[docs/architecture/](docs/architecture/)

| 文档 | 内容 |
|------|------|
| [overview.md](docs/architecture/overview.md) | 系统概述、版本演进 |
| [kernel.md](docs/architecture/kernel.md) | Kernel 14 模块 |
| [agent-runtime.md](docs/architecture/agent-runtime.md) | Agent 生命周期 |
| [memory-architecture.md](docs/architecture/memory-architecture.md) | 记忆分层模型 |
| [routing-and-orchestration.md](docs/architecture/routing-and-orchestration.md) | 路由与编排 |
| [communication-layer.md](docs/architecture/communication-layer.md) | Agent 通信 |
| [governance-layer.md](docs/architecture/governance-layer.md) | 治理层 |
| [security-model.md](docs/architecture/security-model.md) | 安全模型 |

---

## 版本

```
v1.0.0  Plugin Marketplace + Complete UI      ← 当前
v0.7.0  AI Native User Experience
v0.6.6  Production Readiness
v0.5.0  Governance Layer
v0.4.0  Agent Communication
v0.3.0  Agent Organization
v0.2.0  Reliability Layer
```

共 17 次提交，12 个版本标签，169 个源文件。

---

## 目标

**一个人 + 一支 AI 团队 = 微型企业。**

---

🤖 Built with AI | Personal AI OS v1.0.0
