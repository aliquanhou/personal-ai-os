# Changelog

All notable changes to Personal AI OS.

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [0.5.0] — 2026-08-02

### 新增
- **Governance Layer** (`kernel/reputation.py`, `kernel/budget.py`, `kernel/audit.py`)
- Agent Reputation System — 成功率 × 速度 × 一致性 = 评分 (S/A/B/C/D)
- Cost Budget Manager — 日/月/任务预算限制，8 模型定价表
- Audit Log — 5 类审计流，JSONL 持久化，全文搜索
- Scenario Test Framework — JSON 驱动集成测试，10/10 通过
- 15 governance API endpoints
- 自动审计：每个工具调用写入审计日志
- 自动声誉：每次 Agent 执行后更新评分

### 修复
- `tools/registry.py` 文件损坏恢复（从 git 历史重建）

---

## [0.4.0] — 2026-08-02

### 新增
- **Agent Communication Layer** (`kernel/comm_bus.py`)
- AgentMailbox — 每个 Agent 独立收件箱，未读追踪
- TeamChannel — 团队频道，广播消息，消息历史
- HandoffContext — 标准化任务交接协议
- 三种消息类型：REQUEST, RESPONSE, NOTIFICATION, HANDOFF, QUESTION, ALERT
- 7 communication API endpoints
- 消息审计：所有路由消息记录

### 变更
- Agent Runtime 注入 mailbox_context 和 handoff_context
- Router.execute_plan() 自动发送 Handoff 到下游节点

---

## [0.3.0] — 2026-08-02

### 新增
- **Agent Organization Layer** (`kernel/registry.py`, `kernel/router.py`, `kernel/task_graph.py`)
- Agent Registry — Capability + Permission + MemoryScope 形式化声明
- Agent Router — LLM 驱动目标分析 + 任务分解 + 能力匹配
- Task Graph — DAG 任务依赖，循环检测，拓扑排序，并行组识别
- Team 配置系统（4 个默认团队）
- 10+ organization API endpoints
- Smart Chat endpoint（auto/single/team 三种模式）

### 变更
- Startup 注册从手动列表 → AgentRegistry 形式化
- `api/app.py` 版本升到 0.3.0

---

## [0.2.0] — 2026-08-01

### 新增
- **Reliability Layer** (`kernel/workspace.py`)
- Workspace Manager — 项目标准化目录结构（project.json/state.json/decisions.json/artifacts/backups）
- Agent Checkpoint — 每 3 次工具调用自动保存，崩溃后可恢复
- Human Approval Layer — 工具风险等级（safe/moderate/dangerous/critical）+ 批准门
- Daily Briefing 系统
- 敏感路径/命令检测（大小写不敏感）
- Shell 工具：bash 包装（Windows 兼容），python3 → python 自动修正
- `AgentPermission`, `MemoryScope` 枚举

### 变更
- AgentContext 扩展：project_slug, checkpoints, resume_from_checkpoint
- AgentResult 扩展：checkpoint_count, last_checkpoint
- `tools/registry.py` — 所有工具添加 risk_level

---

## [0.1.0] — 2026-08-01

### 新增
- **初始架构** — Personal AI OS v0.1
- Agent Runtime — think → act → observe → learn 循环
- Memory Kernel — Profile, Conversations, Knowledge, Decisions, Experiences
- LLM Router — DeepSeek/OpenAI/Anthropic/Ollama 统一接口
- Tool System — read_file, write_file, list_files, shell, search_memory, save_to_memory
- FastAPI REST API
- React Studio 前端（Vite + Tailwind）
- CLI 模式（chat, memory-search, agents, profile）
- User Identity Memory（Profile 扩展 vision/principles/hates/work_style）
- CEO Agent — 幕僚长，利用老板原则做判断
- Planner Agent — 目标分解
- Task State Machine — 8 状态 + 转换校验
- Reflection Agent — 4 维度任务反思
- UserGoal 追踪（进度 + 里程碑）
- Default Teams（product_dev, quick_code, research, full_team）

---

## 版本命名规则

```
v{major}.{minor}-{sprint-tag}

major:  架构跃迁（Runtime → Organization → Communication → Governance）
minor:  功能迭代
sprint-tag: sprint2, sprint3, sprint4, sprint5, docs-freeze
```

### 标签映射

| Tag | Version | 关键提交 |
|-----|---------|---------|
| `v0.5-docs-freeze` | 0.5.0 | `47d65cb` — Architecture docs + CLAUDE.md |
| `v0.5-sprint5` | 0.5.0 | `2bef484` — Governance Layer |
| `v0.4-sprint4` | 0.4.0 | `f4d2980` — Communication Layer |
| `v0.3-sprint3` | 0.3.0 | `bcde0d2` — Organization Layer |
| `v0.2-sprint2` | 0.2.0 | `343d2b3` — Reliability Layer |
