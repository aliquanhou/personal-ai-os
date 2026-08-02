# v1.0 Demo Walkthrough

> 新用户第一次启动 Personal AI OS 的完整体验流程。

---

## Step 1: 安装 (2 min)

```bash
git clone <repo-url> personal-ai-os
cd personal-ai-os
cp .env.example .env
```

编辑 `.env`，填入 API Key：

```bash
DEEPSEEK_API_KEY=sk-your-key
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat
```

---

## Step 2: 启动 (1 min)

```bash
python main.py start
```

自动输出：

```
============================================================
  Personal AI OS — First Run
  AI Chief of Staff | v1.0.0
============================================================

[1/7] OS Check...      OK  (Windows 10)
[2/7] Python...        OK  (3.12.0)
[3/7] Dependencies...  OK  (6 packages)
[4/7] Node.js...       OK  (v24.14.0)
[5/7] Git...           OK  (2.53.0)
[6/7] Configuration... OK  (API key configured)
[7/7] Port 8001...     OK  (free)

============================================================
  RESULT: 7/7 checks passed
============================================================
  Starting Personal AI OS on 127.0.0.1:8001...

  Studio:  http://localhost:3000
  API:     http://127.0.0.1:8001/health
============================================================
```

---

## Step 3: 打开 Studio (30 sec)

另一个终端：

```bash
cd studio && npm install && npm run dev
```

浏览器打开 `http://localhost:3000`

**看到的页面：**

```
┌──────────────────────────────────────────┐
│  AI OS  v1.0                              │
│                                           │
│  📬 对话   ← 默认页面                      │
│                                           │
│  你的 AI 员工已就位，输入目标开始工作        │
│                                           │
│  [输入你的目标或问题...]          [发送]    │
│                                           │
│  快捷入口：                                │
│  · 帮我分析一个创业想法                     │
│  · 创建一个新项目                          │
│  · 搜索我的知识库                          │
└──────────────────────────────────────────┘
```

---

## Step 4: 第一个任务 (1-2 min)

在聊天框输入：

> 帮我创建一个个人博客网站。FastAPI 后端，支持文章列表、文章详情、评论功能。

**Agent 的完整工作过程：**

```
🎯 理解
这是一个 Web 后端开发任务。与你的长期目标（建立 AI 产品公司）相关...

📋 任务拆解
1. 项目结构搭建 — 创建 FastAPI 应用骨架
2. 数据模型 — 文章、评论的 Pydantic schemas
3. API 路由 — GET/POST 文章 + 评论 CRUD
4. 数据库 — SQLite 持久化
5. 测试 — pytest 验证

✅ 执行
  ✓ write_file: blog/main.py (428 chars)
  ✓ write_file: blog/models.py (312 chars)
  ✓ write_file: blog/routers/posts.py (256 chars)
  ✓ write_file: blog/routers/comments.py (198 chars)
  ...
```

**切换到 Timeline 页面：**

```
⏱️ Task Timeline

Request   帮我创建一个个人博客网站
   ↓
Plan      Agent Plan — 5个任务节点
   ↓
Skill     python_backend [S]
   ↓
Execute   write_file ✅ blog/main.py
Execute   write_file ✅ blog/models.py
Execute   write_file ✅ blog/routers/posts.py
   ↓
Verify    code_review [B]
   ↓
Result    Task completed — 7 files created
```

---

## Step 5: 管理插件 (30 sec)

点击侧边栏 **Plugins**：

```
📦 Plugin Marketplace        3/5 active

── OFFICIAL ──
⭐ Coding Agent Plugin       ✅ ENABLED  [Disable]
   python_backend  database_design  testing  code_review  devops_deployment
   → coding_agent

⭐ Research Agent Plugin     ✅ ENABLED  [Disable]
   market_research
   → research_agent

⭐ Writing Agent Plugin      ✅ ENABLED  [Disable]
   technical_writing  content_writing
   → writing_agent

⭐ Knowledge & File Plugin   ⬜ disabled  [Enable]
⭐ Web Assistant Plugin      ⬜ disabled  [Enable]
```

点击 `[Enable]` 即可激活插件，立即生效。

---

## Step 6: 查看 Agent 团队 (30 sec)

点击侧边栏 **Agents**：

```
🤖 可用 Agents

ceo                  AI 幕僚长
project_manager      项目管理
coding_agent         代码编写、审查和调试
research_agent       信息搜索、分析和综合
writing_agent        写作、编辑和内容创作
reflection_agent     任务反思与经验提炼
environment_agent    环境诊断和修复
```

---

## Step 7: 查看记忆系统 (1 min)

点击侧边栏 **Memory**：

```
🧠 记忆系统

👤 用户档案
  名称: User
  技能水平: intermediate
  技术栈: Python, TypeScript, React, FastAPI
  长期愿景: 建立 AI 产品公司
  决策原则: 快速验证优先于完美设计

🔍 搜索记忆: [blog] [搜索]

  [project] Personal Blog Site
  使用 FastAPI + SQLite 构建的博客系统...
```

---

## 完成

从零到完成第一个任务：**不到 5 分钟**。

```
git clone → .env → python main.py start → npm run dev → 输入任务 → 看到结果
```

---

## 其他 Demo 任务

```bash
# CLI 模式
python main.py chat "分析新能源汽车市场的竞争格局"

# Studio 模式
"帮我写一篇 AI Agent 技术发展趋势的文章"

# 使用 Coding Agent
"修复 workspace/projects/demo-app/backend/app/main.py 的安全漏洞"
```
