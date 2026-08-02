# ADR-006: AI Evolution Philosophy

> **状态**: ACCEPTED
> **日期**: 2026-08-02
> **版本**: v0.6
> **取代**: 无（新建）
> **相关**: ADR-005 Governance Layer, Sprint 2 Approval Layer

---

## 上下文

Personal AI OS v0.5 已经建立了完整的 AI Agent 组织：
Memory → Decision → Planning → Execution → Communication → Governance。

现在需要回答一个关键问题：**AI 系统是否应该能够改变自己？**

如果允许无限制的自我修改，会破坏 v0.5 建立的 Governance Layer。
如果完全不允许优化，AI 系统将无法从经验中变得更好。

我们需要在"AI 失控自改"和"AI 永不进步"之间找到正确的平衡点。

---

## 决策

### 核心原则

```
AI 系统可以：
  ✅ 观察自己的行为模式
  ✅ 从历史数据中发现规律
  ✅ 提出优化建议（Proposal）
  ✅ 在受控环境中测试建议（Experiment）
  ✅ 报告实验结果

AI 系统不能（未经 Human Approval）：
  ❌ 修改自己的 System Prompt
  ❌ 修改 Agent 的 Capability/Permission/MemoryScope 声明
  ❌ 修改 TaskGraph 的执行逻辑
  ❌ 修改 Governance 层的规则（预算、声誉权重、审计）
  ❌ 注册/注销 Agent
  ❌ 修改 Kernel 模块代码
  ❌ 修改批准层的规则
```

### 演化流程

```
┌────────────────────────────────────────────┐
│               AI DOMAIN                     │
│                                            │
│  Observation                               │
│     ↓                                      │
│  Pattern Analysis (ExperienceAnalyzer)     │
│     ↓                                      │
│  Proposal Generation (ImprovementProposal) │
│     ↓                                      │
│  ─── Human Approval Gate ───               │
│     ↓                                      │
│  Experiment (A/B Test)                     │
│     ↓                                      │
│  Result Analysis                           │
│     ↓                                      │
│  ─── Human Promotion Gate ───              │
│     ↓                                      │
│  System Evolution                          │
└────────────────────────────────────────────┘
```

**两道 Human Gate**:
1. **Approval Gate**: Proposal → 人类审核 → 通过后进入实验阶段
2. **Promotion Gate**: 实验结果 → 人类审核 → 通过后正式生效

### 演化范围

| 可演化内容 | 方式 | Human Gate |
|-----------|------|:--:|
| Agent System Prompt 优化 | 建议文字 → 人类确认 → 生效 | ✅ |
| Skill/Checklist 增加 | Proposal → Approval → Experiment → Promotion | ✅ |
| Router 参数调整 | 建议值 → 人类确认 → 应用 | ✅ |
| Budget 阈值调整 | 建议值 → 人类确认 → 应用 | ✅ |
| Capability 标签调整 | 建议 → 人类手动修改 Registry | ✅ |
| 新 Scenario Test 建议 | 生成 JSON → 人类审核 → 添加 | ✅ |
| Kernel 模块代码 | ❌ 不在此范围内。只能人类修改 | ❌ |
| Agent 数量/权限 | ❌ 不在此范围内。只能人类修改 | ❌ |

---

## 后果

### 正面

1. **安全第一**: 两道 Human Gate 确保 AI 不会失控
2. **渐进优化**: A/B Experiment 确保每个改进都被验证
3. **可追溯**: 所有 Proposal/Approval/Experiment/Promotion 都通过 Audit Log 记录
4. **与现有 Governance 兼容**: 推荐层叠在 v0.5 之上，不修改其规则

### 负面

1. **演化速度慢**: 每次改进需要人工参与，不适合快速迭代场景
2. **Human Bottleneck**: 如果 Proposal 太多，人类审核会成为瓶颈
3. **A/B Test 成本**: 实验需要并行运行不同版本 Agent，增加 LLM 调用成本

### 缓解措施

1. Proposal 优先级排序：Confidence × Impact → 只展示最重要的建议
2. Experiment 预算限制：单次实验最长 10 个任务
3. 自动过期：Proposal 如果 30 天未被审核，自动标记为 stale

---

## 与其他 ADR 的关系

- **ADR-005 (Governance)**: 治理层是演化层的约束。演化建议不能绕过 Governance。
- **Sprint 2 (Approval Layer)**: 复用已有的批准机制（pending/approved/rejected）。
- **Sprint 4 (Communication)**: Evolution Advisor 通过 Comm Bus 向 CEO Agent 发送建议。

---

## 演化路线图

```
v0.6 — AI Evolution Advisor
  ├── ExperienceAnalyzer (观察 + 模式发现)
  ├── ImprovementProposal (建议生成)
  └── ExperimentRunner (A/B 测试)

v0.7 — AI Skill Ecosystem
  ├── 根据优化建议生成可复用 Skill
  └── Skill 版本管理

v0.8 — AI Professional Team
  ├── 基于历史的团队组合优化
  └── Agent 专业分工自动建议
```
