"""SQLite 数据模型定义。

核心表：
- tasks        : 任务配置中心（"任务工厂"的核心）
- task_runs    : 每次执行快照（可追溯、可复核）
- audit_logs   : 全量操作审计（信任兜底）
- reviews      : 人工复核记录（关键操作强制确认）
"""

# ---------- 表结构 DDL ----------

SCHEMA_SQL = """
-- 任务配置表
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                -- 任务名称
    task_type       TEXT NOT NULL,                -- 任务类型 (order_check/stock_reconcile/product_clean)
    params          TEXT DEFAULT '{}',            -- 规则参数 (JSON)
    schedule        TEXT DEFAULT '',              -- 调度表达式 (如 daily:09:00)
    enabled         INTEGER DEFAULT 1,            -- 是否启用
    review_required INTEGER DEFAULT 0,            -- 是否强制人工复核
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 任务执行快照表
CREATE TABLE IF NOT EXISTS task_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         INTEGER NOT NULL,             -- 关联 tasks.id
    status          TEXT NOT NULL,                -- success/failed/partial
    data_date       TEXT,                         -- 数据日期
    total_records   INTEGER DEFAULT 0,            -- 处理记录数
    anomaly_count   INTEGER DEFAULT 0,            -- 异常数
    detail          TEXT DEFAULT '',              -- 执行详情 (JSON)
    report_path     TEXT DEFAULT '',              -- 日报路径
    duration_sec    REAL DEFAULT 0,               -- 耗时
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action          TEXT NOT NULL,                -- 操作类型
    task_id         INTEGER,                      -- 关联任务 (可空)
    run_id          INTEGER,                      -- 关联执行 (可空)
    status          TEXT NOT NULL,                -- success/failed
    detail          TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now', 'localtime'))
);

-- 人工复核表
CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,             -- 关联执行
    task_id         INTEGER NOT NULL,             -- 关联任务
    decision        TEXT NOT NULL,                -- approved/modified/rejected
    comment         TEXT DEFAULT '',
    reviewed_at     TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (run_id) REFERENCES task_runs(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_runs_task ON task_runs(task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_reviews_run ON reviews(run_id);
"""

# ---------- 任务类型常量 ----------

TASK_TYPE_ORDER_CHECK = "order_check"
TASK_TYPE_STOCK_RECONCILE = "stock_reconcile"
TASK_TYPE_PRODUCT_CLEAN = "product_clean"

TASK_TYPES = {
    TASK_TYPE_ORDER_CHECK: "订单核对",
    TASK_TYPE_STOCK_RECONCILE: "库存对账",
    TASK_TYPE_PRODUCT_CLEAN: "商品资料清洗",
}

# ---------- 状态常量 ----------

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_PARTIAL = "partial"

DECISION_APPROVED = "approved"
DECISION_MODIFIED = "modified"
DECISION_REJECTED = "rejected"
