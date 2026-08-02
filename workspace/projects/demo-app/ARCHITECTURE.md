# TaskFlow — 系统架构文档

> 版本: 0.1.0 | 更新日期: 2026-08-02
> 项目: TaskFlow — Simple Project Management API

---

## 1. 项目概述

TaskFlow 是一个简单的项目管理工具，提供任务创建、查询和项目列表功能。当前为 **v0.1.0 原型阶段**，后端采用 FastAPI + SQLite，前端 React 尚未实现（`frontend/src` 为空）。

**架构定位**: 单体单文件应用（Monolithic Single-File），所有业务逻辑集中在 `backend/app/main.py` 一个文件中。

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Web 框架 | FastAPI | 异步 ASGI 框架，自动 OpenAPI 文档 |
| 数据层 | SQLite | 文件型数据库，`database/taskflow.db` |
| 数据校验 | Pydantic v2 | 请求体模型（UserLogin / TaskCreate） |
| CORS | fastapi.middleware.cors | 跨域中间件 |
| 前端 | React (规划中) | `frontend/src` 目前为空 |

---

## 3. 目录结构

```
demo-app/
├── backend/
│   └── app/
│       └── main.py          # 全部后端逻辑（单文件 ~200 行）
├── frontend/
│   └── src/                  # 前端源码（当前为空，未实现）
├── database/
│   └── taskflow.db           # SQLite 数据库（运行时自动创建）
├── docs/                     # 文档（当前为空）
├── tests/                    # 测试（当前为空）
├── project.json              # 项目元数据
└── state.json                # 执行状态跟踪
```

---

## 4. 核心模块分析

### 4.1 数据模型（Pydantic）

| 模型 | 字段 | 说明 |
|------|------|------|
| `UserLogin` | username, password | 登录请求体，无字段约束 |
| `TaskCreate` | title, description="", project_id=1 | 任务创建，description 可选 |

**问题**: 字段无 `min_length`/`max_length` 约束，无类型强校验以外的验证。

### 4.2 数据库 Schema

```sql
-- users 表
id INTEGER PRIMARY KEY,
username TEXT UNIQUE,
password TEXT,          -- ⚠️ 明文存储
role TEXT DEFAULT 'user'

-- projects 表
id INTEGER PRIMARY KEY,
name TEXT,
owner_id INTEGER

-- tasks 表
id INTEGER PRIMARY KEY,
title TEXT,
description TEXT,
project_id INTEGER,
status TEXT DEFAULT 'todo',
assignee_id INTEGER
```

**初始化**: `init_db()` 在应用启动时自动建表并插入种子数据（含硬编码管理员）。

### 4.3 API 端点

| 方法 | 路径 | 功能 | 认证 | 风险等级 |
|------|------|------|------|---------|
| POST | `/api/login` | 用户登录 | 无（自身是认证） | 🔴 高危 |
| GET | `/api/projects` | 项目列表 | 无 | 🟠 中危 |
| POST | `/api/tasks` | 创建任务 | 无 | 🟠 中危 |
| GET | `/api/tasks` | 查询任务（按 project_id） | 无 | 🟠 中危 |
| GET | `/health` | 健康检查 | 无 | 🟢 正常 |

---

## 5. 数据流

```
┌─────────┐   HTTP    ┌──────────────────────────┐
│ Client  │ ────────▶ │ FastAPI (main.py)        │
└─────────┘           │  ├─ Pydantic 请求模型     │
                      │  ├─ 业务逻辑（内联）       │
                      │  └─ sqlite3 直接连接       │
                      └──────────┬───────────────┘
                                 │
                          ┌──────▼──────┐
                          │  SQLite DB  │
                          │ taskflow.db │
                          └─────────────┘
```

**关键特征**:
- 每个请求独立 `sqlite3.connect()`，无连接池
- 无服务层/仓储层分层，业务逻辑内联在路由函数
- 依赖注入 `get_db()` 已定义但**未被使用**

---

## 6. 安全审计报告

### 🔴 严重问题（必须立即修复）

#### S1. 密码明文存储与硬编码凭据
```python
# main.py init_db()
conn.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(1,'admin','admin123','admin')")
conn.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(2,'dev','dev123','developer')")
```
- **风险**: 数据库文件泄露即全部凭据泄露；登录用明文 SQL 比较 `password=?`
- **修复**: 使用 `passlib[bcrypt]` 哈希存储；种子数据用环境变量注入或密码哈希

#### S2. CORS 配置非法且危险
```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, ...)
```
- **风险**: `allow_origins=["*"]` 与 `allow_credentials=True` 在浏览器规范中**互斥**——带凭据的请求会被浏览器拒绝，且实际上允许任意来源访问
- **修复**: 明确指定前端来源域名，如 `allow_origins=["http://localhost:5173"]`

#### S3. 认证机制形同虚设
```python
return {"token": f"fake-jwt-{row['username']}", "user": dict(row)}
```
- **风险**: 返回的 token 是 `fake-jwt-{username}` 拼接字符串，**无签名、无过期、无校验**。任何客户端可伪造 `fake-jwt-admin` 冒充管理员
- **修复**: 使用 `python-jose` 生成标准 JWT，含 `exp` 过期时间，服务端中间件校验

#### S4. 业务 API 无任何授权检查
- `/api/projects`、`/api/tasks` 等端点均**无认证依赖**，任何人可直接调用
- **修复**: 增加 `Depends(get_current_user)` 依赖，从 JWT 解析用户

### 🟠 中等问题（应尽快修复）

#### M1. 无速率限制
- 登录接口可被暴力破解（无限次尝试）
- **修复**: 集成 `slowapi` 或增加简单 IP 限流

#### M2. 无安全响应头
- 缺少 `HSTS`、`X-Content-Type-Options`、`X-Frame-Options`、`CSP` 等
- **修复**: 使用 `secure` 中间件或 `Starlette` 自定义响应头

#### M3. 无输入长度限制
- `TaskCreate.title`、`UserLogin.username` 无长度约束，可被用于资源耗尽攻击
- **修复**: Pydantic 增加 `Field(min_length=1, max_length=200)` 等

#### M4. 无日志与异常处理
- 无访问日志、无错误日志、无全局异常处理器
- **修复**: 集成 `logging`，添加 FastAPI 异常处理器

### 🟡 架构问题（改进建议）

#### A1. 连接管理不当
- 每个请求 `sqlite3.connect()`，无连接池/复用，性能差且 FastAPI 同步阻塞
- **修复**: 使用 `get_db()` 依赖注入统一管理连接生命周期

#### A2. REST API 不完整
- 代码注释标注 `# BUG: Missing PUT/PATCH endpoint for updating task status`
- 缺少任务更新/删除端点
- **修复**: 补充 `PUT /api/tasks/{id}`、`DELETE /api/tasks/{id}`

#### A3. 单文件架构膨胀风险
- 所有逻辑集中在 main.py，随功能增加会快速失控
- **修复**: 按 `routers/`、`schemas/`、`services/`、`models/` 分层

#### A4. 配置硬编码
- `DB_PATH` 硬编码，无环境变量管理
- **修复**: 使用 `pydantic-settings` 或 `os.environ` 管理配置

#### A5. 无测试覆盖
- `tests/` 目录为空，无任何单元/集成测试
- **修复**: 使用 `pytest` + `httpx` 编写 API 测试

---

## 7. 安全基线建议（修复路线图）

| 优先级 | 事项 | 涉及端点 |
|--------|------|---------|
| P0 | 密码哈希化 + 移除硬编码凭据 | 全局 |
| P0 | 修复 CORS 配置 | 全局 |
| P0 | 实现标准 JWT 认证 | 全局 |
| P0 | 所有业务端点加认证依赖 | /api/* |
| P1 | 增加速率限制 | /api/login |
| P1 | 增加安全响应头 | 全局 |
| P1 | Pydantic 字段约束 | 全局 |
| P2 | 连接池/依赖注入统一 | 全局 |
| P2 | 补充任务更新/删除端点 | /api/tasks |
| P2 | 配置环境变量化 | 全局 |
| P2 | 编写测试 | /api/* |

---

## 8. 结论

TaskFlow 是一个**功能原型**，展示了基本的 CRUD 思路，但**安全基线远未达标**。作为 demo 项目，其价值在于演示 API 结构，但**绝不能直接部署到生产环境**。

**核心教训**: 即使是最简单的项目，认证、授权、CORS、密码哈希也是不可省略的安全底线。修复优先级应遵循 P0 → P1 → P2 顺序，先堵住认证和 CORS 漏洞，再优化架构和测试。

---

*文档由 AI 幕僚长自动生成，基于代码静态分析。*
