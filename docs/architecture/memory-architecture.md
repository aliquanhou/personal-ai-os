# Personal AI OS — Memory 架构

> **版本**: v0.5 | **存储引擎**: SQLite | **表数**: 9

---

## 为什么要 Memory 层？

普通 AI 聊天工具的问题：

```
用户: "帮我分析一个创业机会"
AI:   "好的，我认为你应该做..."
用户: (第二天) "昨天我们讨论的创业方向是什么？"
AI:   "抱歉，我没有之前的对话记录。"
```

Personal AI OS 的 Memory 层：

```
用户: "帮我分析一个创业机会"
AI:   (查询 Profile → 了解用户技术栈)
      (查询 Decisions → 回顾类似决策)
      (查询 Experiences → 避免重蹈覆辙)
      → "基于你上次决定'不做平台、先做产品'的原则，
         我建议..."
用户: (第二天) "昨天我们讨论的创业方向是什么？"
AI:   "昨天我们分析了AI工具市场。你的决策是不进入，
      原因是冷启动风险。建议先做产品验证。"
```

Memory 不是数据库 —— 它是 **决策资产**。

---

## Memory 分层模型

```
┌──────────────────────────────────────────────┐
│                  IDENTITY LAYER               │
│  Profile: 你是谁 (技能、愿景、原则、偏好)       │
│  UserGoal: 你在追求什么 (目标 + 进度)           │
├──────────────────────────────────────────────┤
│                  KNOWLEDGE LAYER              │
│  Knowledge: 你学到的知识 (概念、事实、引用)      │
│  Decisions: 你做过的决定 (上下文、选项、原因)    │
│  Experiences: 你的经验 (成功、失败、教训)        │
├──────────────────────────────────────────────┤
│                  OPERATIONAL LAYER            │
│  Conversations: 对话历史                       │
│  Tasks: 任务状态机                             │
│  Projects: 项目元数据                          │
│  DailyBriefing: 每日简报                       │
└──────────────────────────────────────────────┘
```

---

## 数据表详解

### `profile` — 用户画像

```sql
CREATE TABLE profile (
    id TEXT PRIMARY KEY,
    name TEXT,                    -- "User"
    bio TEXT,                     -- "A builder, creator, and entrepreneur."
    skill_level TEXT,             -- "intermediate"
    tech_stack TEXT,              -- JSON: ["Python", "TypeScript", "React", ...]
    goals TEXT,                   -- JSON: ["Build useful AI tools"]
    preferences TEXT,             -- JSON: {"language": "zh-CN", "timezone": "Asia/Shanghai"}
    long_term_vision TEXT,        -- "建立一家 AI 产品公司..."
    decision_principles TEXT,     -- JSON: ["快速验证优先于完美设计", ...]
    hates TEXT,                   -- JSON: ["重复造轮子", "过度工程化", ...]
    work_style TEXT,              -- JSON: {"peak_hours": "灵活", ...}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**单例**: 系统只维护一个 Profile。升级策略：新字段自动追加默认值。

### `user_goals` — 用户目标

```sql
CREATE TABLE user_goals (
    id TEXT PRIMARY KEY,
    title TEXT,                   -- "建立AI产品公司"
    description TEXT,
    category TEXT,                -- career/learning/project/life
    progress_pct REAL,            -- 0.0–100.0
    status TEXT,                  -- active/paused/achieved/abandoned
    target_date TEXT,
    milestones TEXT,              -- JSON: 里程碑列表
    priority INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### `knowledge` — 知识库

```sql
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    title TEXT,                   -- "AI产品30天开发计划"
    content TEXT,
    category TEXT,                -- tech/business/project/personal
    tags TEXT,                    -- JSON
    source TEXT,                  -- 知识来源
    importance REAL,              -- 0.0–1.0 (影响检索排序)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**检索方式**: LIKE 全文匹配（当前）。计划 v0.6+ 加入向量检索层。

### `decisions` — 决策记录

```sql
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    context TEXT,                 -- "选择后端框架"
    options TEXT,                 -- JSON: ["FastAPI", "Flask", "Django"]
    chosen TEXT,                  -- "FastAPI"
    rationale TEXT,               -- "异步支持好，适合AI应用"
    outcome TEXT,                 -- (事后填写) "运行稳定，开发效率高"
    project_id TEXT,
    created_at TIMESTAMP
);
```

**为什么重要**: 决策记录使 AI 可以回答 "上次为什么选择 FastAPI？" 而不是每次都重新分析。

### `experiences` — 经验教训

```sql
CREATE TABLE experiences (
    id TEXT PRIMARY KEY,
    title TEXT,                   -- "TODO CLI工具开发"
    description TEXT,
    lesson TEXT,                  -- "Windows shell需要bash包装"
    emotion TEXT,                 -- positive/neutral/negative
    project_id TEXT,
    created_at TIMESTAMP
);
```

**来源**: Reflection Agent 在每次任务后自动生成。

### `conversations` — 对话历史

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT,              -- 会话 ID (可关联多轮对话)
    role TEXT,                    -- user/assistant/system/tool
    content TEXT,
    metadata TEXT,                -- JSON: {"agent": "ceo", "iterations": 5}
    created_at TIMESTAMP
);
```

### `tasks` — 任务状态机

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    agent_name TEXT,
    title TEXT,
    description TEXT,
    state TEXT,                   -- created/planning/executing/waiting_human/
                                  --   verifying/done/learned/failed
    priority INTEGER,
    result TEXT,                  -- JSON: 执行结果
    reflection TEXT,              -- JSON: 反思记录
    tool_calls_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**状态转换规则**:

```
CREATED     → PLANNING, FAILED
PLANNING    → EXECUTING, WAITING_HUMAN, FAILED
EXECUTING   → WAITING_HUMAN, VERIFYING, DONE, FAILED
WAITING_HUMAN → EXECUTING, PLANNING, FAILED
VERIFYING   → DONE, EXECUTING, FAILED
DONE        → LEARNED
LEARNED     → (terminal)
FAILED      → CREATED, PLANNING  (可以重试)
```

### `daily_briefings` — 每日简报

```sql
CREATE TABLE daily_briefings (
    id TEXT PRIMARY KEY,
    date TEXT,                    -- "2026-08-02"
    greeting TEXT,
    yesterday_summary TEXT,
    discoveries TEXT,
    today_suggestions TEXT,
    long_term_progress TEXT,
    mood TEXT,
    raw_json TEXT,                -- 完整结构化数据
    created_at TIMESTAMP
);
```

---

## Memory Context 注入

Agent 执行前，Memory Manager 构建 `memory_context` 字符串注入 System Prompt：

```python
def get_memory_context(query: str) -> str:
    parts = []

    # 1. 用户画像
    profile = get_profile()
    → "## User Profile\nName: ...\nSkill Level: ...\n..."

    # 2. 活跃目标
    goals = get_user_goals(status="active")
    → "## 🎯 Active Goals\n- [project] Build AI tools [████░░░░] 50%\n"

    # 3. 最近决策
    decisions = get_recent_decisions(limit=5)
    → "## Recent Decisions\n- 选择FastAPI → Chose: ...\n"

    # 4. 活跃任务
    tasks = get_tasks_by_state(["executing", "waiting_human", "verifying"])
    → "## Active Tasks\n- [executing] 开发RAG功能\n"

    # 5. 相关知识
    knowledge = search_knowledge(query)
    → "## Relevant Knowledge\n- [project] DocSense: ...\n"

    # 6. 经验教训
    experiences = get_experiences(limit=5)
    → "## Lessons Learned\n- TODO CLI: Windows shell需要bash\n"

    return "\n".join(parts)
```

---

## 设计原则

1. **结构化优先于向量化**: 在 v0.1–v0.5，决策连续性 > 语义搜索精度。SQL 表结构直接对应"员工需要知道的"文件柜。

2. **分层注入**: 不是把所有记忆塞入 Prompt。而是按层次构建上下文：身份 → 知识 → 操作。

3. **写时持久化**: 每个 `save_*()` 调用立即写入 SQLite。不做批量写。

4. **单例模式**: `get_memory()` 全局单例。所有 Agent 共享一个 Memory 连接。适合单用户场景。

5. **渐进增强**: 当前是 LIKE 全文搜索。v0.6 计划增加可选向量检索（chromadb/sqlite-vec），不替换 SQLite。

---

## 记忆范围 (MemoryScope)

Sprint 3 引入的 MemoryScope 控制每个 Agent 可以访问哪些记忆分区：

```python
class MemoryScope(StrEnum):
    PROFILE = "profile"
    GOALS = "goals"
    KNOWLEDGE = "knowledge"
    DECISIONS = "decisions"
    EXPERIENCES = "experiences"
    CONVERSATIONS = "conversations"
    PROJECTS = "projects"
    TASKS = "tasks"
    ALL = "all"
```

**为什么重要**: 不是每个 Agent 都应该看到全部记忆。Coding Agent 不需要看 Conversations，Writing Agent 不需要看 Tasks。MemoryScope 是数据安全的第一道防线。
