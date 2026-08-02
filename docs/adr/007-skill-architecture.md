# ADR-007: Skill Architecture

> **状态**: ACCEPTED
> **日期**: 2026-08-02
> **版本**: v0.6.5
> **取代**: 无（新建）
> **相关**: ADR-003 (Agent Registry), ADR-006 (Evolution Philosophy)

---

## 上下文

当前 Personal AI OS 的 Agent 能力是整体式的：

```
coding_agent:
  ├── write_code
  ├── debug
  ├── test
  ├── review
  ├── database_design
  ├── api_design
  └── ... (越来越长)
```

这种模型的问题：
1. **Agent 过重** — 能力越加越多，System Prompt 膨胀，LLM 上下文溢出
2. **注册困难** — 新增一个能力需要修改 Agent 代码
3. **评分粗粒度** — 只能评 "coding_agent 成功率 70%"，无法评 "database_design 能力" 独立评分
4. **不可复用** — research_agent 不能借用 coding_agent 的 testing skill
5. **演化困难** — 无法做 A/B test 单个能力

我们需要将能力从 Agent 身上拆离，变成独立的、可组合的 Skill。

---

## 决策

### Skill 定义

```
Skill = 名称 + 能力标签 + Prompt片段 + 推荐工具 + 前置Skill + 评分
```

### Skill 与 Agent 的关系

```
BEFORE (v0.1–v0.6):
  Agent 直接拥有 Capability 列表
  Agent 的 System Prompt 包含所有能力描述

AFTER (v0.6.5):
  Agent 拥有 Skill 列表
  Agent 的 System Prompt = 基础角色 + 聚合所有 Skill 的 prompt 片段
  Skill 独立于 Agent 存在，可被多个 Agent 使用
```

### 组织结构变化

```
现在:
  CEO
   ├── Coding Agent (所有代码能力内置)
   ├── Research Agent (所有研究能力内置)

未来:
  CEO
   ├── Developer Agent
   │     + Python Backend Skill
   │     + React Frontend Skill
   │     + Database Design Skill
   │     + Testing Skill
   │
   ├── Research Agent
   │     + Market Analysis Skill
   │     + Data Analysis Skill
   │
   └── Writer Agent
         + Technical Writing Skill
         + Copywriting Skill
```

### 核心规则

1. **Skill 独立于 Agent**: 同一个 Skill 可被多个 Agent 使用
2. **Skill 有独立评分**: Reputation Registry 追踪 per-skill 成功率
3. **Skill 有前置依赖**: database_design skill 要求 python_backend skill
4. **Skill 可演化**: Sprint 6 的 Experiment 系统可对单个 Skill 做 A/B test
5. **Skill 不替代 Agent**: Agent 仍然负责决策、协调、执行。Skill 只提供专业知识

### 评分粒度

```
BEFORE (v0.5):
  coding_agent: 成功率 70%  ← 太粗

AFTER (v0.6.5):
  coding_agent:
    Python Backend Skill: 成功率 92%
    Database Design Skill: 成功率 45%  ← 问题在这里！
    Testing Skill: 成功率 78%
```

这使 Evolution Advisor 可以精确地建议 "提升 database_design 能力" 而不是 "提升 coding_agent"。

---

## Skill Schema

```python
@dataclass
class SkillDefinition:
    name: str                    # "python_backend"
    display_name: str            # "Python Backend Development"
    description: str             # "使用 Python + FastAPI 构建后端服务"
    capabilities: list[str]      # ["code_generation", "api_design"]
    prompt_fragment: str         # 注入 System Prompt 的专业知识
    recommended_tools: list[str] # ["write_file", "shell", "search_memory"]
    prerequisites: list[str]     # 前置 Skill 名称
    category: str                # "backend" / "frontend" / "data" / "writing" / ...
    difficulty: str              # "beginner" / "intermediate" / "advanced"
    version: str                 # "1.0.0"
    rating: SkillRating          # 独立评分
```

---

## 与现有系统的关系

| 现有系统 | Sprint 6.5 影响 |
|---------|---------------|
| Agent Registry (v0.3) | AgentDescriptor.capabilities 保留，但来源从"手动声明"变为"Skill 聚合" |
| Reputation (v0.5) | 新增 per-skill 评分追踪 |
| Router (v0.3) | 能力匹配现在也考虑 Skill 评分 |
| Evolution (v0.6) | Experiment 可以针对单个 Skill |
| Communication (v0.4) | 不变 |
| Governance (v0.5) | 不变 |

---

## 不在此范围内的

- ❌ Skill Marketplace / Skill 商城
- ❌ 用户自定义 Skill（通过 UI 创建）
- ❌ Skill 打包/分发格式
- ❌ 第三方 Skill 开发者 SDK

这些是 v0.7+ 的范围。

---

## 后果

### 正面
1. Agent 更轻量，System Prompt 更聚焦
2. 能力可跨 Agent 复用
3. 细粒度评分使 Evolution Advisor 更精确
4. A/B test 可以针对单个 Skill
5. 为 v0.7 Plugin Marketplace 打好基础

### 负面
1. 增加一层抽象，系统复杂度提升
2. Skill 组合可能产生冲突（两个 Skill 的 prompt 片段矛盾）
3. Agent 初始化时间增加（需要加载多个 Skill）

### 缓解
1. Skill 冲突检测：注册时检查 prompt 冲突
2. Skill 缓存：Agent 的 System Prompt 编译一次，重用
