# Personal AI OS — Governance Layer

> **版本**: v0.5 | **核心模块**: `kernel/reputation.py`, `kernel/budget.py`, `kernel/audit.py`

---

## 治理层解决什么问题？

AI 公司有员工，也需要：

- **考核** — 哪个 Agent 做得好？哪个需要改进？
- **预算** — 花了多少钱？还剩多少？要不要继续？
- **审计** — 谁做了什么决定？为什么？有什么依据？

没有治理层的 AI 系统是一个黑箱。有治理层的 AI 系统是一个可问责的组织。

---

## 三大支柱

```
┌──────────────────────────────────────┐
│           GOVERNANCE LAYER            │
│                                      │
│  ┌──────────┐ ┌────────┐ ┌────────┐  │
│  │Reputation│ │ Budget │ │ Audit  │  │
│  │  声誉     │ │ 预算   │ │ 审计   │  │
│  │          │ │        │ │        │  │
│  │谁靠谱?    │ │花多少?  │ │为什么?  │  │
│  └────┬─────┘ └───┬────┘ └───┬────┘  │
│       │           │          │        │
│       ▼           ▼          ▼        │
│  Router     Agent.run()  Agent.run()  │
│  (能力×声誉)  (预检查)     (每步记录)    │
└──────────────────────────────────────┘
```

---

## P0-1: Agent Reputation System

### 评分模型

```
Reputation Score = 0.5 × success_rate + 0.3 × speed_score + 0.2 × recent_consistency
```

| 因子 | 权重 | 计算方式 |
|------|:--:|------|
| success_rate | 50% | successful_tasks / total_tasks |
| speed_score | 30% | min(1.0, 30000 / avg_duration_ms) |
| recent_consistency | 20% | 最近 10 次任务的成功率 |

### Tier 体系

| Tier | 分数范围 | 含义 |
|:----:|---------|------|
| **S** | ≥ 0.90 | 精英 — 持续高表现 |
| **A** | ≥ 0.80 | 优秀 — 可靠执行者 |
| **B** | ≥ 0.65 | 良好 — 大多数时候靠谱 |
| **C** | ≥ 0.50 | 一般 — 需要关注 |
| **D** | < 0.50 | 差 — 不应分配关键任务 |

### 与 Router 集成

```python
# v0.3: 只看能力
best_agent = match_by_capability(required_caps)

# v0.5: 能力 × 声誉
best_agent = match_by_capability_and_reputation(required_caps)
# score = 0.6 × capability_match + 0.4 × reputation_score
```

### 数据采集

Agent 每次执行完成后，自动记录：

```python
rep.record(
    agent_name="coding_agent",
    success=True,
    duration_ms=8000,
    tool_calls=5,
    hit_max_iterations=False,
    capability="code_generation"
)
```

### 持久化

存储到 `data/reputation.json`。重启后恢复。

---

## P0-2: Cost Budget Manager

### 预算维度

| 维度 | 默认值 | 说明 |
|------|--------|------|
| daily_limit | $5.00 | 每日 AI 调用预算 |
| monthly_limit | $100.00 | 每月 AI 调用预算 |
| task_limit | $2.00 | 单个任务预算上限 |

### 模型定价表 ($/1M tokens)

| 模型 | 输入 | 输出 | 说明 |
|------|------|------|------|
| deepseek-chat | $0.14 | $0.28 | 主力模型，性价比最高 |
| deepseek-reasoner | $0.55 | $2.19 | 推理任务 |
| gpt-4o | $2.50 | $10.00 | OpenAI 旗舰 |
| gpt-4o-mini | $0.15 | $0.60 | OpenAI 轻量 |
| claude-sonnet-5 | $3.00 | $15.00 | 最强大，最贵 |
| claude-haiku-4.5 | $0.80 | $4.00 | 快速轻量 |
| qwen-plus | $0.80 | $2.00 | 阿里通义千问 |
| llama3-70b | $0.59 | $0.79 | 开源本地部署 |

### 预算状态机

```
ACTIVE ─── 正常使用
  │
  ├── 80% → WARNING (仍然允许，但提示)
  │
  ├── 95% → CRITICAL (仍然允许，强烈警告)
  │
  └── 100% → EXCEEDED (拒绝执行)
```

### 与 Agent 执行集成

```python
# 执行前检查
check = budget.check("task_001", estimated_input=2000, estimated_output=500)
if not check["allowed"]:
    return AgentResult(success=False, error=f"预算不足")

# 执行后记录
budget.record("task_001", "coding_agent", "deepseek-chat",
              input_tokens=1500, output_tokens=400)
```

### 成本追踪

```python
status = budget.get_status()
# {
#   "daily_limit_usd": 5.00,
#   "daily_spent_usd": 1.234,
#   "daily_remaining_usd": 3.766,
#   "status": "active",
#   ...
# }

# 每个 Agent 的成本
agent_costs = budget.get_agent_costs()
# {
#   "ceo":           {"total_tokens": 5000, "estimated_cost_usd": 0.0014},
#   "coding_agent":  {"total_tokens": 8000, "estimated_cost_usd": 0.008},
#   ...
# }
```

---

## P0-3: Audit Log

### 五条审计流

| 类别 | 记录内容 | 严重度 |
|------|---------|:--:|
| **DECISION** | 策略选择 + 理由 + 替代方案 | IMPORTANT |
| **ACTION** | 工具调用 + 结果 | INFO |
| **BUDGET** | 费用记录 | INFO |
| **SECURITY** | 权限检查 / 批准事件 | WARNING |
| **ERROR** | 异常 / 失败 | CRITICAL |

### 格式

```
audit-00042 | 2026-08-02T19:23:00Z | DECISION | IMPORTANT
Agent: ceo
Action: 选择FastAPI作为后端框架
Rationale: 异步支持好，与用户技术栈匹配，历史项目成功率更高
Context: alternatives=["Flask", "Django"], basis="decision #234"
```

### 自动采集

每次 Agent 执行自动记录：
- 每个工具调用 → ACTION
- Agent 失败 → ERROR
- 权限拒绝 → SECURITY

手动记录（API）：
- 策略决策 → DECISION
- 费用记录 → BUDGET

### 查询能力

```python
audit = get_audit_log()

# 按 Agent
audit.get_by_agent("ceo", limit=50)

# 按类别
audit.get_by_category(AuditCategory.DECISION, limit=50)

# 按任务
audit.get_by_task("task_001")

# 全文搜索
audit.search("FastAPI")  # → 找到所有提到 FastAPI 的审计条目

# 统计
audit.stats()
# {
#   "total_entries": 342,
#   "by_category": {"action": 280, "decision": 35, "error": 20, ...},
#   "by_agent": {"ceo": 120, "coding_agent": 180, ...},
# }
```

### 持久化

即时追加到 `data/audit_log.jsonl`（每行一条 JSON）。即使系统崩溃，已写入的审计条目不会丢失。

---

## API 端点 (15 个)

### Reputation
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/gov/reputation` | GET | 所有 Agent 声誉 |
| `/api/gov/reputation/{agent}` | GET | 单个 Agent 声誉 |
| `/api/gov/reputation/record` | POST | 记录任务结果 |
| `/api/gov/reputation/team/{team}` | GET | 团队健康评估 |

### Budget
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/gov/budget` | GET | 预算状态 |
| `/api/gov/budget/agents` | GET | Agent 成本分布 |
| `/api/gov/budget/transactions` | GET | 交易历史 |
| `/api/gov/budget/record` | POST | 记录使用 |
| `/api/gov/budget/check` | POST | 预检查 |

### Audit
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/gov/audit` | GET | 审计日志（可筛选） |
| `/api/gov/audit/decisions` | GET | 决策列表 |
| `/api/gov/audit/search` | GET | 全文搜索 |
| `/api/gov/audit/stats` | GET | 审计统计 |

### Scenario Tests
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/gov/scenarios` | GET | 场景测试列表 |
| `/api/gov/scenarios/run` | POST | 执行场景测试 |

---

## 设计原则

1. **治理层是观察者，不是执行者**: 声誉/预算/审计不改变 Agent 的执行逻辑，只记录和影响决策（如 Router 选人时参考声誉分数）。

2. **自动采集优先于手动记录**: 工具调用、执行结果、失败异常全部自动记录。只有策略决策需要手动调用 API。

3. **非阻塞**: 审计日志写入失败不应阻止 Agent 执行。声誉记录失败不应导致任务失败。

4. **持久化即时性**: 审计日志每一条都即时追加到磁盘（JSONL 格式），不做批量刷新。

5. **预算不应该扼杀创新**: 默认预算设置较高（$5/天，$100/月），主要是防止失控，不是限制使用。
