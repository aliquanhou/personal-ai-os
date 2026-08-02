# 电商运营数字员工 - 技术架构设计

> 版本: v0.1 | 状态: MVP | 创建日期: 2026-08-03

## 1. 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                        CLI 入口 (main.py)                      │
│                    run | schedule | history                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                      EcommerceOpsAgent (runner)               │
│                    任务编排 / 执行 / 状态管理                    │
└──────┬──────────────┬──────────────┬──────────────┬──────────┘
       │              │              │              │
┌──────▼─────┐  ┌─────▼──────┐  ┌────▼──────┐  ┌────▼─────────┐
│  Loader    │  │   Rules    │  │  Reports   │  │   Audit     │
│  数据接入   │  │  规则引擎   │  │  报表生成   │  │  审计追踪    │
└──────┬─────┘  └─────┬──────┘  └────┬──────┘  └────┬─────────┘
       │              │              │              │
┌──────▼──────────────▼──────────────▼──────────────▼─────────┐
│                     Config / Storage (SQLite)                 │
│              data/  config.py  history.db                     │
└──────────────────────────────────────────────────────────────┘
```

## 2. 模块设计

### 2.1 模块结构

```
ecommerce-ops-agent/
├── main.py                    # CLI 入口
├── requirements.txt           # 依赖清单
├── README.md                  # 使用说明
├── docs/
│   ├── PRD.md                 # 产品需求文档
│   └── ARCHITECTURE.md        # 技术架构文档 (本文件)
├── agent/
│   ├── __init__.py
│   ├── config.py              # 配置中心
│   ├── models.py              # 数据模型
│   ├── loader.py              # 数据接入层
│   ├── rules.py               # 规则引擎
│   ├── reports.py             # 报表生成
│   ├── audit.py               # 审计追踪
│   ├── runner.py              # 执行引擎
│   └── history.py             # 历史记录管理
├── data/
│   ├── sample_orders.csv      # 示例订单数据
│   ├── sample_inventory.csv   # 示例库存数据
│   └── sample_products.csv    # 示例商品数据
├── outputs/
│   └── reports/               # 生成的报表输出
└── tests/
    └── test_agent.py          # 单元测试
```

### 2.2 核心类设计

```python
# agent/runner.py
class EcommerceOpsAgent:
    """电商运营数字员工 - 执行引擎"""
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.audit_log = AuditLog()
    
    def run(self, data_date=None) -> dict:
        """执行全部运营任务"""
        # 1. 加载数据
        # 2. 执行规则校验
        # 3. 生成报表
        # 4. 记录审计日志
        # 5. 返回结果摘要

# agent/rules.py
class RuleEngine:
    """规则引擎"""
    def check_orders(self, orders_df) -> list:
        """订单核对规则"""
    
    def check_inventory(self, inventory_df) -> list:
        """库存对账规则"""
    
    def clean_products(self, products_df) -> pd.DataFrame:
        """商品资料清洗规则"""

# agent/loader.py
class DataLoader:
    """数据接入层"""
    def load_orders(self, path) -> pd.DataFrame
    def load_inventory(self, path) -> pd.DataFrame
    def load_products(self, path) -> pd.DataFrame

# agent/reports.py
class ReportGenerator:
    """报表生成"""
    def generate_daily_report(self, orders, inventory, products, anomalies) -> str
```

## 3. 数据流设计

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 原始数据  │───▶│ 数据清洗  │───▶│ 规则校验  │───▶│ 报表输出  │
│ (CSV)   │    │ (loader)│    │ (rules) │    │ (report)│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                    │
                                    ▼
                              ┌─────────┐
                              │ 审计日志  │
                              │ (audit) │
                              └─────────┘
```

## 4. 数据库设计 (SQLite)

```sql
-- 审计日志表
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT
);

-- 历史记录表
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    total_orders INTEGER,
    total_amount REAL,
    anomaly_count INTEGER,
    report_path TEXT,
    attempts INTEGER DEFAULT 1
);
```

## 5. 关键设计决策

### 5.1 技术选型
| 决策点 | 选择 | 理由 |
|--------|------|------|
| 语言 | Python 3.10+ | 数据处理生态丰富（pandas） |
| 数据处理 | pandas | 成熟、高效、易用 |
| 报表生成 | openpyxl | Excel 格式支持好 |
| 存储 | SQLite | MVP 无需复杂DB，轻量可靠 |
| 调度 | 内置 scheduler | 避免额外依赖 |
| CLI | argparse | 标准库，零依赖 |

### 5.2 设计原则
1. **单一职责**：每个模块只做一件事
2. **可扩展**：规则引擎支持新规则添加
3. **可审计**：所有操作记录日志
4. **容错**：失败自动重试，不中断整体流程

### 5.3 与 AI 数字员工平台关系
本项目是 AI 数字员工平台的第一个垂直场景实现。
- 复用：Personal AI OS 记忆系统（后续接入）
- 扩展：可作为平台的任务模板
- 验证：验证"任务工厂"模式可行性

## 6. 部署方案

### 6.1 本地开发
```bash
pip install -r requirements.txt
python main.py run
```

### 6.2 生产部署
```bash
# 定时调度（每天 09:00 执行）
python main.py schedule

# 或使用 cron
0 9 * * * cd /path/to/ecommerce-ops-agent && python main.py run
```

### 6.3 Docker (可选)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "schedule"]
```

## 7. 性能指标
- 订单核对吞吐量：> 1000 条/秒
- 库存对账：< 5 秒（1万条）
- 报表生成：< 3 秒
- 内存占用：< 500MB

## 8. 安全与合规
- 数据本地存储，不依赖外部服务
- 审计日志完整记录所有操作
- 支持数据脱敏（后续版本）
- 遵循最小权限原则
