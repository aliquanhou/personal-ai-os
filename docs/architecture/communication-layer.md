# Personal AI OS — Agent Communication Layer

> **版本**: v0.4+ | **核心模块**: `kernel/comm_bus.py`

---

## 设计动机

在 v0.3 及之前，Agent 之间没有通信机制。Router 充当了中介：收集上一个 Agent 的输出，拼接到下一个 Agent 的输入。

```
v0.3 方式 (Router 中介):
  Agent A → [result] → Router → [拼接字符串] → Agent B

问题:
  - Router 成为瓶颈
  - 上下文传递是非结构化的
  - 无法支持多对多通信
  - 无法做消息审计
```

v0.4 引入了正式的通信基础设施：

```
v0.4 方式 (Communication Bus):
  Agent A → [HandoffContext] → CommBus → [Mailbox] → Agent B
                                     → [Channel] → Agent C, D, E
```

---

## 三种通信原语

### 1. Mailbox — 点对点消息

**类比**: 企业电子邮件

每个 Agent 有一个独立的收件箱。

```python
# Agent A 发送
msg = AgentMessage(
    sender="research_agent",
    recipient="coding_agent",
    msg_type=MessageType.HANDOFF,
    subject="市场调研完成",
    body="发现目标客户主要需求是自动回复...",
)

comm_bus.route(msg)  # 投递到 coding_agent 的 inbox

# Agent B 收到 — 在执行前检查 inbox
mailbox = comm_bus.get_mailbox("coding_agent")
unread = mailbox.get_unread(msg_type=MessageType.HANDOFF)
context = mailbox.get_context_for_task(task_id)
```

**特性**:
- 未读/已读追踪
- 按类型筛选（HANDOFF, REQUEST, ALERT...）
- 自动注入 Agent 的 System Prompt
- 发送/接收均已记录

### 2. Channel — 团队广播

**类比**: Slack 频道

一个频道 → 所有成员收到消息。

```python
# Create channel from team
comm_bus.create_channel("product_dev", ["ceo", "pm", "coder", "researcher"])

# CEO broadcasts
msg = AgentMessage(
    sender="ceo",
    recipient="team:product_dev",
    msg_type=MessageType.NOTIFICATION,
    subject="全员通知：启动CSV项目",
    body="请各成员准备。需求文档已上传。",
)

delivered = comm_bus.route(msg)  # → 4 收到 (除了发送者)

# Channel history (可审计)
history = comm_bus.get_channel_history("product_dev")
```

**特性**:
- 消息历史保留（最多 500 条）
- 成员管理（join/leave）
- 置顶消息支持
- 自动拒绝向不存在的频道发送

### 3. Handoff Protocol — 上下文交接

**类比**: 工作交接单 — 这是 Sprint 4 最有价值的创新。

```python
# Agent A 完成任务后，构建 Handoff
hc = HandoffContext(
    task_id="task_001",
    from_agent="research_agent",
    to_agent="coding_agent",
    summary="市场调研完成，客户核心需求是自动回复",
    completion_status="done",
    key_findings=[
        "80%客户需求是自动回复常见问题",
        "竞品定价范围 $20-200/月",
        "开源方案 > SaaS方案 (客户偏好)"
    ],
    artifacts=["docs/market_research.md", "docs/competitor_analysis.md"],
    decisions=["目标用户: 小型电商(10-100人)"],
    next_steps=[
        "设计对话流程",
        "选择LLM服务商",
        "搭建FastAPI后端框架"
    ],
    warnings=[
        "竞品已在开发类似功能",
        "客户对延迟敏感，需考虑响应时间优化"
    ],
    open_questions=["是否需要多语言支持？", "对接哪些电商平台？"]
)

# 通过 CommBus 投递 → Agent B 执行前自动注入上下文
comm_bus.handoff("research_agent", "coding_agent", hc)
```

**为什么重要**:
```
没有 Handoff:
  coding_agent 收到: "开发客服系统"
  → 需要重新理解客户是谁、做什么、为什么
  → 浪费迭代次数和 tokens

有 Handoff:
  coding_agent 收到:
    "开发客服系统。
     上一个Agent(research_agent)已确认：
     - 客户核心需求: 自动回复
     - 竞品定价: $20-200/月
     - 技术决策: FastAPI + DeepSeek
     - 警告: 竞品在开发类似功能
     你的任务: 设计对话流程 + 搭建后端框架"
  → 立即开始工作，无需重新探索
```

---

## 消息类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `REQUEST` | 请求队友做事 | "请帮我review这段代码" |
| `RESPONSE` | 回复请求 | "review完成，建议优化X" |
| `NOTIFICATION` | 通知（不要求回复） | "项目已部署到staging" |
| `HANDOFF` | 任务交接 | "我的工作完成，你来继续" |
| `QUESTION` | 需要澄清 | "在继续之前，这个参数是什么意思？" |
| `ALERT` | 紧急通知 | "⚠️ API调用失败率超50%" |

**优先级**: LOW, NORMAL, HIGH, URGENT

---

## 通信注入

Agent 执行前，Mailbox 上下文自动注入 System Prompt：

```python
# Agent Runtime (agents/runtime.py)
# 在构建 messages 时:

if ctx.mailbox_context:
    messages.append({
        "role": "system",
        "content": ctx.mailbox_context
    })
```

注入格式：

```
## 📬 收件箱 — 来自队友的消息

⚠️ research_agent 发来警告: 数据库连接池耗尽
   需要立即扩容，否则后端会崩溃

📋 project_manager 交接任务: 项目计划已完成
   ## 项目计划
   - Phase 1 (D1-5): 基础搭建...
   - Phase 2 (D6-15): ...

📩 coding_agent 请求: review代码
   请查看这个PR的变更
```

---

## 组织状态监控

```python
status = comm_bus.get_organization_status()
# {
#   "agents": {
#     "ceo":             {"inbox_total": 5,  "inbox_unread": 2, "sent_total": 12},
#     "coding_agent":    {"inbox_total": 8,  "inbox_unread": 1, "sent_total": 5},
#     ...
#   },
#   "channels": {
#     "product_dev":     {"members": 5, "message_count": 23},
#     "quick_code":      {"members": 2, "message_count": 3},
#   },
#   "total_messages_routed": 87
# }
```

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/comm/status` | GET | 组织通信状态 |
| `/api/comm/inbox/{agent}` | GET | Agent 收件箱 |
| `/api/comm/inbox/{agent}/clear` | POST | 清空收件箱（已读） |
| `/api/comm/message` | POST | 发送消息 |
| `/api/comm/handoff` | POST | 创建交接 |
| `/api/comm/channel/{team}` | GET | 频道历史 |

---

## 设计权衡

### 为什么不直接用 Event Bus？
Event Bus 是系统内部的事件机制（发布/订阅，没有持久化）。Communication Bus 是 Agent 间的显式消息传递（有收件箱、有类型、有审计）。两者互补：Event Bus 用于 Kernel 内部解耦，Comm Bus 用于 Agent 间协作。

### 为什么不用消息队列？
RabbitMQ/Kafka 适合微服务之间的异步通信。但 Personal AI OS 是单进程应用，Agent 执行是同步的（一个完成再下一个）。使用内存 Mailbox 足够，未来需要持久化时可以接入 SQLite/Redis。

### 为什么 Channel 消息历史有限制？
每个 Channel 保留最近 500 条消息。对于 AI Agent 团队（每次任务生成 5-20 条消息），这覆盖了 25-100 个任务的上下文。超出范围的旧消息通过 Memory 系统保存（作为经验/决策），而不是保留在 Channel 中。
