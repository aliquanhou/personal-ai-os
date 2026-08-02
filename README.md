# Personal AI OS v0.1

> 你的个人 AI 员工 — 会记忆、会执行、会成长。

**Personal AI OS** 不是一个炫酷的 AI 聊天工具，而是一个能真实落地、逐步成长的个人 AI 操作系统。

---

## 核心理念

```
❌ 不是：又一个 ChatGPT 套壳
✅ 而是：一个真正有用的 AI 员工

AI 知道：
- 你是谁
- 你做过什么项目
- 你的技术水平
- 你的历史决定
- 你当前的目标
```

---

## 架构

```
Personal AI OS
│
├── Kernel (内核)
│   ├── Agent Runtime  — Agent 生命周期管理
│   ├── Memory Runtime — 个人记忆系统
│   ├── Event Bus      — 事件总线
│   ├── Permission     — 权限控制
│   └── LLM Router     — 多模型路由
│
├── Memory (记忆)
│   ├── Profile        — 用户档案
│   ├── Conversations  — 对话历史
│   ├── Knowledge      — 知识库
│   ├── Decisions      — 决策记录
│   └── Experiences    — 经验教训
│
├── Agents (智能体)
│   ├── Project Manager — 项目管理
│   ├── Coding Agent    — 代码编写
│   ├── Research Agent  — 研究分析
│   └── Writing Agent   — 写作助手
│
├── Tools (工具)
│   ├── File Operations — 文件读写
│   ├── Shell Execution — 命令执行
│   ├── Memory Search   — 记忆搜索
│   └── Plugin System   — 插件扩展
│
├── API (接口层)
│   └── FastAPI REST + WebSocket
│
└── Studio (工作室)
    └── React + TypeScript + Tailwind
```

---

## 快速开始

### 1. 安装

```bash
cd personal-ai-os

# Python 依赖
pip install -e ".[dev]"

# 前端依赖
cd studio && npm install && cd ..
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，至少配置一个 LLM API Key
```

### 3. 启动

```bash
# 启动后端
python main.py serve

# 另一个终端，启动前端
cd studio && npm run dev
```

打开 http://localhost:3000

### 4. CLI 模式

```bash
# 直接对话
python main.py chat "帮我分析一个电商创业想法"

# 搜索记忆
python main.py memory-search "用户偏好"

# 查看 agents
python main.py agents

# 查看用户档案
python main.py profile
```

---

## 第一个场景：AI 创业助手

```
用户: "我要做一个赚钱项目。"

AI 自动:
1. 分析市场
2. 制定计划
3. 建项目目录
4. 创建任务
5. 写代码
6. 测试
7. 发布
```

---

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| 前端 | React 19, TypeScript, Vite, Tailwind, Zustand |
| LLM | DeepSeek / OpenAI / Anthropic / Ollama |
| 缓存 | Redis (可选) |

---

## 开发路线

- [x] P0-1: Memory Kernel — 个人记忆系统
- [x] P0-2: Agent Lifecycle — Agent 生命周期
- [x] P0-3: Project Manager Agent — 第一个 Agent
- [x] Web UI — Studio 工作室
- [ ] P1: Plugin Marketplace
- [ ] P1: WebSocket 实时通信
- [ ] P1: 多 Agent 协作
- [ ] P2: 向量记忆搜索
- [ ] P2: 本地 Ollama 深度集成

---

## 目标

**30 天做出一个你自己每天愿意使用的 AI 员工。**

---

🤖 Built with AI | Personal AI OS v0.1
