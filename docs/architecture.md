# Personal AI OS — 架构文档

## 设计原则

1. **先有用，再完善** — 每个版本必须产生可运行的新能力
2. **记忆优先** — AI 不知道用户是谁，就没有价值
3. **工具驱动** — Agent 通过工具执行真实操作
4. **逐步成长** — 从单一 Agent 到多 Agent 协作

## 数据流

```
用户输入 (Chat / API)
     │
     ▼
Agent Runtime
     │
     ├── 读取 Memory Context (用户档案、知识、决策)
     ├── 构建 System Prompt
     ├── LLM Router → 调用模型
     │
     ▼
模型响应
     │
     ├── 纯文本 → 直接返回用户
     └── Tool Call → Tool Registry → 执行工具 → 返回结果 → 继续推理
     │
     ▼
Memory Update (保存对话、知识、决策)
     │
     ▼
Event Bus (通知 UI 更新)
```

## Agent 生命周期

```
START
  │
  ▼
[Build Context] ← Memory (Profile + Knowledge + Decisions)
  │
  ▼
[Think] ← LLM
  │
  ├── Tool Call? → [Execute Tool] → [Observe] → [Think]
  │
  └── No Tool Call → [Final Response]
  │
  ▼
[Memory Update] → Save conversation, extract knowledge
  │
  ▼
END
```

## 记忆系统设计

```
memory/
├── profile.json       — 用户档案 (自动维护)
├── conversations/     — 对话历史 (SQLite)
├── knowledge/         — 知识碎片 (SQLite, 未来 +向量)
├── decisions/         — 决策记录 (SQLite)
└── experiences/       — 经验教训 (SQLite)
```

## 扩展方向

### Plugin 系统

```python
# 任何 Python 函数都可以成为 Tool
@register_tool(
    name="send_email",
    description="发送邮件",
    parameters={...}
)
async def send_email(to: str, subject: str, body: str):
    ...
```

### 多 Agent 协作

```
Coordinator Agent
    │
    ├── Project Manager Agent (规划)
    ├── Coding Agent (执行)
    └── Review Agent (审查)
```

### 本地优先

- SQLite 作为主存储（零配置）
- Ollama 本地模型支持（隐私优先）
- 所有数据存储在本地
