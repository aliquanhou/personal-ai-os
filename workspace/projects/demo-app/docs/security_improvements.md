# TaskFlow — 安全改进报告

> 更新时间: 2026-08-02 | 版本: 0.1.0 原型阶段
> 依据: `ARCHITECTURE.md` 第 6 节安全审计 + 已落地修复

---

## 一、已修复问题 ✅

| 编号 | 问题 | 修复方式 | 状态 |
|------|------|----------|------|
| S1 | 密码明文存储 + 硬编码凭据 | 新增 `hash_password()` 用 **SHA256** 哈希存储；`init_db()` 种子数据写入哈希；`login` 接口改为按 username 查库再比对哈希，不再 `WHERE password=?` 明文比较 | ✅ 已修复 |
| S2 | CORS 配置非法（`"*"` + `allow_credentials=True` 互斥且危险） | 明确指定前端来源 `["http://localhost:5173", "http://127.0.0.1:5173"]`，保留 `allow_credentials=True` | ✅ 已修复 |
| A2 | REST API 不完整（缺任务状态更新） | 新增 `PATCH /api/tasks/{task_id}`（TaskUpdate 模型，`Literal` 校验 todo/in_progress/done，404 处理） | ✅ 已修复 |
| — | 任务查询能力不足 | `GET /api/tasks` 新增可选 `assignee_id` 过滤，与 `project_id` 组合查询，保持向后兼容 | ✅ 已修复 |

> **备注**: 以上修复均通过代码审查验证；验证脚本位于 `tests/verify_hash_fix.py` 与 `tests/verify_task_endpoints.py`，待人工运行最终确认（shell 被审批机制拦截）。

---

## 二、待修复问题（按优先级排序）

### 🔴 P0 — 必须立即修复（安全漏洞）

| 编号 | 问题 | 风险描述 | 建议方案 |
|------|------|----------|----------|
| S3 | 假 JWT 认证 | `login` 返回 `fake-jwt-{username}`，**无签名、无过期、无校验**，任何客户端可伪造 `fake-jwt-admin` 冒充管理员 | 用 `python-jose` 生成标准 JWT（含 `exp`），服务端中间件校验 |
| S4 | 业务 API 无授权检查 | `/api/projects`、`/api/tasks` 等端点**无认证依赖**，任何人可直接调用 | 增加 `Depends(get_current_user)` 依赖，从 JWT 解析用户 |

### 🟠 P1 — 应尽快修复（加固）

| 编号 | 问题 | 风险描述 | 建议方案 |
|------|------|----------|----------|
| M1 | 无速率限制 | 登录接口可被暴力破解（无限次尝试） | 集成 `slowapi` 或简单 IP 限流 |
| M2 | 无安全响应头 | 缺少 HSTS、X-Content-Type-Options、X-Frame-Options、CSP | 使用 `secure` 中间件或自定义响应头 |
| M3 | 无输入长度限制 | `title`、`username` 无长度约束，可资源耗尽 | Pydantic 加 `Field(min_length, max_length)` |

### 🟡 P2 — 改进建议（健壮性/可维护性）

| 编号 | 问题 | 建议方案 |
|------|------|----------|
| M4 | 无日志与全局异常处理 | 集成 `logging`，添加 FastAPI 异常处理器 |
| A1 | 连接管理不当（每请求 `connect()`，`get_db()` 未用） | 用 `get_db()` 依赖注入统一管理连接生命周期 |
| A3 | 单文件架构膨胀风险 | 按 `routers/`、`schemas/`、`services/`、`models/` 分层 |
| A4 | 配置硬编码（`DB_PATH`） | 用 `pydantic-settings` 或 `os.environ` 管理配置 |
| A5 | 无测试覆盖 | 用 `pytest` + `httpx` 编写 API 测试 |

---

## 三、建议执行顺序

1. **P0-S3** 实现标准 JWT 认证（当前最致命，认证形同虚设）
2. **P0-S4** 为所有业务 API 加授权依赖（依赖 S3 完成后）
3. **P1** 速率限制 + 安全响应头 + 输入校验（常规加固）
4. **P2** 日志、连接复用、分层重构、配置管理、补测试（随功能演进迭代）

> **原则提醒**: 遵守"快速验证优先于完美设计"——P0/P1 属安全底线应立即处理；P2 按需在功能迭代中渐进重构，避免过度工程化。
