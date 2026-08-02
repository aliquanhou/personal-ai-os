# Personal AI OS — Security Model

> **版本**: v0.5 | **最后审核**: 2026-08-02

---

## 安全模型概述

Personal AI OS 的安全模型基于**纵深防御**原则：

```
Layer 1: Tool Risk Level      ← 每个工具标注风险等级
Layer 2: Approval Gate        ← 高风险操作需要人工确认
Layer 3: Permission System    ← Agent 只能访问授权资源
Layer 4: Memory Scope         ← Agent 只能读取授权的记忆分区
Layer 5: Audit Trail          ← 所有操作留下不可变记录
```

---

## Layer 1: Tool Risk Level

每个工具在注册时标注风险等级：

| 风险等级 | 含义 | 示例工具 |
|:----:|------|---------|
| **safe** | 纯读取，无副作用 | `read_file`, `list_files`, `search_memory` |
| **moderate** | 写入用户文件，无系统影响 | `write_file`, `save_to_memory`, `create_project_workspace` |
| **dangerous** | 可执行任意命令 | `shell` |
| **critical** | 可能造成不可逆损坏 | (当前无工具在此级别) |

---

## Layer 2: Approval Gate

### 工作机制

```python
# Agent 执行工具调用前，Router 检查
approval_result = tools.check_approval(tool_name, args)

if approval_result.blocked:
    # 绝对禁止 → 不给 LLM 重试机会
    return "🚫 禁止执行"

if approval_result.needs_approval:
    # 需要人工确认 → 暂停，通知用户
    return "⏸️ 等待人工批准"
```

### 批准规则

| 场景 | 处理 |
|------|------|
| `read_file` 任意路径 | ✅ 自动通过 (safe) |
| `write_file` 到 `workspace/` | ✅ 自动通过 (moderate) |
| `write_file` 到 `C:\Windows` 或 `/etc/` | ⏸️ 需要批准 (路径检测) |
| `shell ls` / `shell cat` | ⚠️ 需要批准 (dangerous) |
| `shell rm -rf /` | 🚫 禁止 (critical pattern) |
| `shell DROP TABLE` | 🚫 禁止 (critical pattern) |

### 敏感路径检测

```python
DANGEROUS_PATTERNS = [
    "System32", "/etc/", "/var/", "C:\\Windows", "/boot",
    ".git/config", ".env.production", "production.yml",
]

CRITICAL_COMMANDS = [
    "rm -rf /", "DROP TABLE", "DELETE FROM", "shutdown",
    "format C:", "del /f /s C:\\", "DROP DATABASE",
]
```

**大小写不敏感**: 防止通过 `rm -rf /ETC` 绕过 `/etc/` 检测。

---

## Layer 3: Permission System

### Agent 权限声明

每个 Agent 在注册时声明其权限：

```python
# CEO — 最高权限
permissions=[
    MEMORY_READ, MEMORY_WRITE,
    READ_WORKSPACE, WRITE_WORKSPACE,
    MANAGE_AGENTS,
]

# Coding Agent — 工作区 + 安全 Shell
permissions=[
    READ_WORKSPACE, WRITE_WORKSPACE,
    EXEC_SHELL_SAFE,
]

# Writing Agent — 最小权限
permissions=[
    READ_WORKSPACE, WRITE_WORKSPACE,
]
```

### 权限级别

| 权限 | 范围 | 持有者 |
|------|------|--------|
| `read_workspace` | 读取项目文件 | 所有 Agent |
| `write_workspace` | 创建/修改项目文件 | 大多数 Agent |
| `delete_workspace` | 删除项目文件 | (当前未分配) |
| `exec_shell_safe` | 执行安全命令 | coding_agent |
| `exec_shell_full` | 执行任意命令 | (当前未分配) |
| `memory_read` | 读取记忆 | 大多数 Agent |
| `memory_write` | 写入记忆 | ceo, pm, coder, researcher, reflection |
| `memory_delete` | 删除记忆 | (当前未分配) |
| `manage_agents` | 注册/注销 Agent | ceo |
| `system_config` | 修改系统配置 | (当前未分配) |
| `external_network` | 访问外部网络 | research_agent |

**当前状态**: v0.5 的权限系统是声明式的。权限声明在 AgentDescriptor 中，但 v0.5 的执行层尚未强制校验所有权限（Approval Gate 已生效）。v0.6 计划在所有工具调用前进行完整的权限检查。

---

## Layer 4: Memory Scope

### 分区间隔

不是所有 Agent 都应该访问所有记忆。MemoryScope 限制 Agent 的记忆视野：

```
CEO:                  [ALL MEMORY]
Project Manager:      [Projects, Tasks, Knowledge]
Coding Agent:         [Knowledge, Experiences, Projects]
Research Agent:       [Knowledge, Decisions, Experiences]
Writing Agent:        [Knowledge, Conversations]
Reflection Agent:     [Experiences, Decisions, Tasks]
```

### 为什么重要

- **数据最小化**: Coding Agent 不需要看 Conversation 历史
- **防止信息泄露**: 一个受损的 Agent 只能看到其授权范围内的记忆
- **专注力**: 减少无关上下文干扰

**当前状态**: v0.5 的 MemoryScope 已声明但在 Agent 执行时尚未强制过滤。Memory Manager 目前提供全量访问。v0.6 计划在 `get_memory_context()` 中根据 Agent 的 MemoryScope 过滤数据。

---

## Layer 5: Audit Trail

所有操作 — 无论成功/失败/被拒 — 都留下审计记录。

```
审计条目覆盖:
  ✅ 每个工具调用 → ACTION
  ✅ 每个策略决策 → DECISION
  ✅ 每次费用产生 → BUDGET
  ✅ 每次权限拒绝 → SECURITY
  ✅ 每次执行异常 → ERROR

不可变性:
  ✅ JSONL 格式 → 追加写入
  ✅ 每一条即时落盘
  ✅ 按 Agent / Category / Task / 全文 可查询
```

详见 [治理层文档](governance-layer.md#p0-3-audit-log)。

---

## 安全边界

### 当前 v0.5 的安全边界

```
┌─────────────────────────────────────┐
│  Host Machine (User's PC)           │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  Personal AI OS Process       │  │
│  │                               │  │
│  │  ✅ Safe Zone:                │  │
│  │    workspace/                 │  │
│  │    data/ (sqlite, jsonl)     │  │
│  │                               │  │
│  │  ⚠️ Approval Required:        │  │
│  │    Shell execution            │  │
│  │    System paths               │  │
│  │                               │  │
│  │  🚫 Blocked:                  │  │
│  │    Destructive commands       │  │
│  │    System directory writes    │  │
│  └───────────────────────────────┘  │
│                                     │
│  External:                          │
│    LLM API calls (DeepSeek, etc.)  │
│    GitHub (未来)                    │
└─────────────────────────────────────┘
```

### 不在此范围内的（明确排除）

- **多用户隔离**: v0.5 是单用户系统。多用户需要进程隔离 + 数据库多租户。
- **网络隔离**: 当前 LLM 调用通过 HTTPS，但没有 VPN/代理层。
- **加密存储**: API Keys 在 `.env` 明文存储（标准做法）。数据库未加密。
- **输入注入**: LLM Prompt 注入是开放研究问题，当前依赖 LLM 自身的防护。

---

## 安全路线图

| 版本 | 安全增强 |
|------|---------|
| **v0.5** (当前) | Tool Risk Level + Approval Gate + Permission声明 + MemoryScope声明 + Audit |
| **v0.6** (计划) | 强制执行 Permission 和 MemoryScope；添加速率限制 |
| **v0.7** (计划) | API Key 加密存储 (keyring/os-vault)；多用户隔离 |
| **v1.0** (计划) | 独立沙箱执行 (Docker/VM)；完整权限矩阵 |

---

## 报告安全问题

如果你发现安全漏洞，请：
1. 不要在公开 Issue 中描述
2. 通过项目维护者的私下渠道报告
3. 在修复后发布安全公告
