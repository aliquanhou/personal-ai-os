# 电商运营数字员工 (Ecommerce Ops Agent)

一个能自主、持续、不出错地执行电商运营任务的 AI Agent。

## 功能

- **订单核对**：自动核对订单数据，检测重复、无效平台、无效状态、异常金额
- **库存对账**：自动对账系统库存与仓库库存，检测差异和负数库存
- **商品资料整理**：自动清洗和标准化商品资料，计算毛利率
- **每日运营报表**：自动生成 Excel 格式的每日运营日报
- **审计追踪**：所有操作全程留痕，可追溯
- **定时调度**：支持每日定时自动执行

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成示例数据
python main.py init-data

# 3. 立即执行一次
python main.py run

# 4. 查看历史记录
python main.py history

# 5. 查看审计日志
python main.py audit

# 6. 定时执行（每天 09:00）
python main.py schedule
```

## 项目结构

```
ecommerce-ops-agent/
├── main.py                    # CLI 入口
├── requirements.txt           # 依赖清单
├── generate_sample_data.py    # 示例数据生成
├── docs/
│   ├── PRD.md                 # 产品需求文档
│   └── ARCHITECTURE.md        # 技术架构设计
├── agent/
│   ├── __init__.py
│   ├── config.py              # 配置中心
│   ├── models.py              # 数据模型
│   ├── loader.py              # 数据接入层
│   ├── rules.py               # 规则引擎
│   ├── reports.py             # 报表生成
│   ├── audit.py               # 审计追踪
│   ├── history.py             # 历史记录管理
│   └── runner.py              # 执行引擎
├── data/                      # 数据目录（自动创建）
├── outputs/                   # 输出目录（自动创建）
│   └── reports/               # 报表输出
└── tests/
    └── test_agent.py          # 单元测试
```

## 技术栈

- Python 3.10+
- pandas (数据处理)
- openpyxl (Excel报表)
- SQLite (存储)
- pytest (测试)

## 架构

```
┌─────────────────────────────────────────────┐
│               ecommerce-ops-agent           │
├──────────┬──────────┬──────────┬────────────┤
│  数据接入  │  规则引擎  │  报表生成  │  执行引擎   │
│  (loader) │ (rules)  │ (reports)│ (runner)   │
├──────────┴──────────┴──────────┴────────────┤
│                 审计追踪 (audit)              │
├─────────────────────────────────────────────┤
│             配置中心 (config)                 │
└─────────────────────────────────────────────┘
```

## 测试

```bash
python -m pytest tests/ -v
```

## 下一步

- [ ] Web 管理界面（人工复核台）
- [ ] 更多任务类型（工单分诊、评价分析）
- [ ] AI 增强（异常智能分析）
- [ ] 多平台数据源接入（API）
