# Personal AI OS 用户手册

> **版本**: v0.3.0  
> **你的个人 AI 员工 — 会记忆、会执行、会成长。**

Personal AI OS 不是一个炫酷的 AI 聊天工具，而是一个能真实落地、逐步成长的**个人 AI 操作系统**。它了解你是谁、你做过什么项目、你的技术水平、你的历史决定和你当前的目标——就像一个真正懂你的 AI 员工。

---

## 目录

1. [系统简介](#1-系统简介)
2. [环境要求](#2-环境要求)
3. [安装步骤](#3-安装步骤)
4. [配置说明](#4-配置说明)
5. [快速上手](#5-快速上手)
6. [Web 界面（Studio）](#6-web-界面studio)
7. [命令行工具（CLI）](#7-命令行工具cli)
8. [智能体（Agents）](#8-智能体agents)
9. [记忆系统](#9-记忆系统)
10. [工作区与项目管理](#10-工作区与项目管理)
11. [常用场景示例](#11-常用场景示例)
12. [故障排查](#12-故障排查)
13. [常见问题（FAQ）](#13-常见问题faq)

---

## 1. 系统简介

Personal AI OS 采用"**AI 公司组织**"的架构，内置 6 个各司其职的 AI 智能体（Agent），它们可以互相协作，共同完成复杂任务：

| 智能体 | 角色 | 核心能力 |
|--------|------|----------|
| **CEO** | 幕僚长 | 理解目标、制定策略、协调团队、每日简报 |
| **项目主管** | 项目经理 | 将目标转化为结构化项目计划和任务 |
| **代码专家** | 开发者 | 编写、审查、调试代码 |
| **研究分析员** | 研究员 | 搜索信息、分析市场、综合发现 |
| **写作助手** | 写作者 | 撰写文档、报告、内容创作 |
| **反思教练** | 教练 | 任务后深度分析，提炼经验教训 |

### 核心特性

- 🧠 **长期记忆**：记住你的偏好、项目、决策和经验
- 🤖 **多智能体协作**：智能路由任务给最合适的智能体
- 📁 **工作区管理**：为每个项目建立独立目录和检查点
- 🔌 **工具系统**：文件操作、Shell 执行、记忆搜索、插件扩展
- 🌐 **REST API + WebSocket**：可编程接入
- 🖥️ **Web 工作室**：可视化交互界面

---

## 2. 环境要求

| 依赖 | 版本要求 |
|------|----------|
| **Python** | ≥ 3.12 |
| **Node.js** | ≥ 18（运行 Studio 前端需要） |
| **npm** | ≥ 9 |
| **Redis**（可选） | 用于任务队列 |

### 支持的 LLM 提供商

- **DeepSeek**（默认）
- **OpenAI**
- **Anthropic**
- **Qwen**（通义千问）
- **Ollama**（本地模型）

---

## 3. 安装步骤

### 3.1 获取代码

```bash
git clone <your-repo-url> personal-ai-os
cd personal-ai-os
```

### 3.2 安装 Python 依赖

```bash
# 安装核心依赖 + 开发依赖
pip install -e ".[dev]"
```

> **提示**：建议使用虚拟环境（venv 或 conda）隔离依赖。

```bash
# 创建并激活虚拟环境（可选但推荐）
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# 或
.venv\Scripts\activate      # Windows
```

### 3.3 安装前端依赖（可选）

如果你需要使用 Web 界面（Studio）：

```bash
cd studio
npm install
cd ..
```

---

## 4. 配置说明

### 4.1 创建配置文件

```bash
cp .env.example .env
```

### 4.2 配置项详解

打开 `.env` 文件，按需修改以下配置：

```ini
# ── LLM 提供商（至少配置一个 API Key）──

# DeepSeek（默认推荐）
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥

# OpenAI
OPENAI_API_KEY=sk-你的OpenAI密钥
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=sk-ant-你的Anthropic密钥

# Qwen（通义千问）
QWEN_API_KEY=你的通义千问密钥

# ── 默认模型设置 ──
DEFAULT_LLM_PROVIDER=deepseek     # 可选: deepseek / openai / anthropic / ollama / qwen
DEFAULT_MODEL=deepseek-chat       # 可选: gpt-4o / claude-sonnet-5 / llama3 / qwen-plus

# ── 数据库 ──
DATABASE_URL=sqlite+aiosqlite:///data/personal_ai_os.db

# ── Redis（可选，用于任务队列）──
REDIS_URL=redis://localhost:6379/0

# ── 服务器 ──
HOST=127.0.0.1
PORT=8000

# ── 记忆目录 ──
MEMORY_DIR=./memory_data

# ── 安全 ──
SECRET_KEY=请在生产环境修改为随机字符串
```

### 4.3 配置本地 Ollama（可选）

如果你希望完全离线使用：

```bash
# 1. 安装 Ollama
# 2. 拉取模型
ollama pull llama3

# 3. 在 .env 中配置
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_MODEL=llama3
```

---

## 5. 快速上手

### 5.1 启动后端服务

```bash
python main.py serve
```

启动成功后，终端会显示类似信息：

```
INFO: Personal AI OS v0.3.0 starting on 127.0.0.1:8000
INFO: Agent Runtime: ['ceo', 'project_manager', 'coding_agent', ...]
INFO: Agent Registry: 6 agents, N teams
```

### 5.2 启动前端（可选）

在另一个终端：

```bash
cd studio
npm run dev
```

打开浏览器访问 **http://localhost:3000**

### 5.3 验证服务

```bash
# 检查健康状态
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status": "ok", "version": "0.3.0", "name": "Personal AI OS"}
```

### 5.4 开始第一个对话

```bash
# 方式一：CLI 模式
python main.py chat "帮我分析一个电商创业想法"

# 方式二：API 调用
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我分析一个电商创业想法"}'
```

---

## 6. Web 界面（Studio）

Studio 是基于 React 的可视化工作台，提供完整的图形化交互体验。

### 6.1 功能模块

- 💬 **对话面板**：与 CEO 或指定智能体对话
- 🗂️ **项目管理**：查看和管理工作区项目
- 🧠 **记忆中心**：浏览知识库、决策记录、经验教训
- 📋 **任务看板**：跟踪任务状态
- 📊 **每日简报**：查看系统生成的每日工作简报

### 6.2 使用流程

1. 启动后端 `python main.py serve`
2. 启动前端 `cd studio && npm run dev`
3. 浏览器打开 `http://localhost:3000`
4. 在对话框中输入你的目标或问题

---

## 7. 命令行工具（CLI）

Personal AI OS 提供了完整的 CLI 工具，方便命令行操作。

### 7.1 命令总览

```bash
python main.py <命令> [参数]
```

| 命令 | 说明 | 示例 |
|------|------|------|
| `serve` | 启动服务 | `python main.py serve` |
| `chat` | 与智能体对话 | `python main.py chat "写一个计划"` |
| `memory-search` | 搜索记忆 | `python main.py memory-search "用户偏好"` |
| `agents` | 列出所有智能体 | `python main.py agents` |
| `profile` | 查看用户档案 | `python main.py profile` |

### 7.2 chat 命令详解

```bash
# 基本用法：与默认 CEO 智能体对话
python main.py chat "帮我制定一个学习计划"

# 指定智能体
python main.py chat "帮我写一段 Python 代码" --agent coding_agent

# 指定智能体（用 --agent 参数）
python main.py chat "分析一下这个市场" --agent research_agent
```

### 7.3 其他常用命令

```bash
# 搜索记忆库
python main.py memory-search "技术栈偏好"

# 查看所有可用智能体
python main.py agents

# 查看当前用户档案
python main.py profile
```

---

## 8. 智能体（Agents）

系统内置 6 个智能体，可通过 `/api/agents` 查看完整列表。

### 8.1 智能体一览

| 名称 | 描述 | 适用场景 |
|------|------|----------|
| `ceo` | AI 幕僚长 | 目标理解、策略制定、任务协调 |
| `project_manager` | 项目主管 | 项目规划、任务拆解 |
| `coding_agent` | 代码专家 | 代码编写、审查、调试 |
| `research_agent` | 研究分析员 | 市场调研、信息搜集 |
| `writing_agent` | 写作助手 | 文档撰写、内容创作 |
| `reflection_agent` | 反思教练 | 经验总结、流程改进 |

### 8.2 智能路由（Smart Routing）

系统默认使用 **CEO** 智能体处理对话。CEO 会根据任务的复杂度自动决定：

- **简单任务**：直接由单个智能体处理
- **复杂任务**：拆分为多个子任务，分配给不同智能体协作完成

### 8.3 指定智能体对话

```bash
# CLI
python main.py chat "..." --agent coding_agent

# API
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "...", "agent": "research_agent"}'
```

---

## 9. 记忆系统

Personal AI OS 的核心优势之一是其**长期记忆**能力。系统会自动记录和积累以下信息：

### 9.1 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **用户档案** | 用户基本信息、技能、偏好 | 姓名、技术栈、目标 |
| **知识库** | 沉淀的知识和经验 | 技术方案、行业洞察 |
| **对话历史** | 与用户的完整对话记录 | 每次对话的会话记录 |
| **决策记录** | 重要的历史决策 | 技术选型、方向决策 |
| **经验教训** | 任务后的反思总结 | 成功经验、失败教训 |
| **目标与任务** | 用户的长期目标和当前任务 | 创业目标、开发任务 |

### 9.2 记忆相关操作

```bash
# 搜索记忆
python main.py memory-search "电商"

# 查看用户档案
python main.py profile
```

通过 API：

```bash
# 搜索知识库
curl -X POST http://127.0.0.1:8000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "电商", "limit": 10}'

# 保存知识
curl -X POST http://127.0.0.1:8000/api/memory/save \
  -H "Content-Type: application/json" \
  -d '{"type": "knowledge", "title": "AI趋势", "content": "2025年AI趋势分析...", "category": "行业洞察"}'
```

---

## 10. 工作区与项目管理

### 10.1 工作区概念

每个项目在工作区中拥有独立的**目录**和**检查点**系统：

```
workspace/
└── 项目slug/
    ├── project.json      # 项目元数据
    ├── state.json        # 项目状态
    ├── decisions.json    # 决策记录
    ├── artifacts/        # 产出物
    └── backups/          # 备份
```

### 10.2 创建项目

```bash
# 通过 API 创建项目
curl -X POST "http://127.0.0.1:8000/api/workspace?name=电商创业计划&description=分析电商创业可行性"
```

### 10.3 断点续传（Checkpoint）

系统会在任务执行过程中自动保存检查点。如果任务中断，可以从上次断点继续：

```bash
# 对话时启用断点恢复
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "继续之前的任务", "project_slug": "电商创业计划", "resume": true}'
```

---

## 11. 常用场景示例

### 场景一：创业想法分析

```
用户: "我要做一个 AI 写作工具，帮我分析一下"
```

CEO 智能体会自动：
1. 分析市场需求和竞争格局
2. 制定产品规划和开发计划
3. 创建项目工作区
4. 拆解任务分配给各智能体
5. 输出完整的分析报告

### 场景二：开发一个小工具

```
用户: "帮我写一个 Python 脚本，批量重命名文件"
```

系统会：
1. 调用 coding_agent 编写代码
2. 自动测试和调试
3. 保存到工作区
4. 记录经验到记忆库

### 场景三：每日工作简报

```
用户: "生成今天的简报"
```

系统会汇总：
- 昨日任务完成情况
- 工作区项目进展
- 近期决策记录
- 今日建议事项

### 场景四：研究分析

```
用户: "研究一下 2025 年 AI 教育市场"
```

研究分析员会：
1. 搜索相关信息
2. 综合分析和总结
3. 生成市场分析报告
4. 存入知识库

---

## 12. 故障排查

### 12.1 服务无法启动

**检查项**：
- Python 版本是否为 3.12+：`python --version`
- 依赖是否安装完整：`pip list | grep fastapi`
- `.env` 文件是否存在：`ls -la .env`
- 端口是否被占用：`lsof -i :8000`

### 12.2 API 调用报错

**常见错误**：
- `401`：API Key 未配置或无效，检查 `.env`
- `404`：接口路径错误，对照 API 文档检查
- `500`：内部错误，查看后端日志

### 12.3 LLM 无响应

**检查项**：
- API Key 是否有效
- 网络是否可达（`curl https://api.deepseek.com`）
- 账户余额是否充足
- 模型名称是否正确

### 12.4 前端无法连接后端

**检查项**：
- 后端是否已启动
- CORS 是否配置正确
- 端口是否一致

---

## 13. 常见问题（FAQ）

**Q1: 必须配置 DeepSeek 吗？**

不需要。你可以使用 OpenAI、Anthropic、Qwen 或本地 Ollama。只需在 `.env` 中设置 `DEFAULT_LLM_PROVIDER` 和对应的 API Key。

**Q2: 记忆数据存在哪里？**

默认存在 SQLite 数据库 `data/personal_ai_os.db`。可通过 `DATABASE_URL` 配置改为其他数据库。

**Q3: 可以完全离线使用吗？**

可以。配置本地 Ollama 模型即可完全离线运行。

**Q4: 如何备份数据？**

直接备份 `data/` 目录（数据库）和 `memory_data/` 目录（记忆文件）即可。

**Q5: 系统会记住我的所有对话吗？**

是的，对话历史会保存在记忆中。你可以在记忆中心查看和管理。

**Q6: 如何让系统更懂我？**

多与系统互动，并主动通过 API 保存你的偏好、决策和知识。系统会自动积累这些信息。

---

## 附：技术栈速览

| 层 | 技术 |
|---|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| 前端 | React 19, TypeScript, Vite, Tailwind, Zustand |
| LLM | DeepSeek / OpenAI / Anthropic / Ollama / Qwen |
| 缓存 | Redis（可选） |

---

> 🤖 **Personal AI OS** — 30 天做出一个你自己每天愿意使用的 AI 员工。
