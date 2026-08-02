# 📝 Personal Blog

一个基于 **FastAPI + SQLite** 的个人博客网站后端，包含文章列表、文章详情、评论功能。

## ✨ 功能特性

- 📄 **文章列表** — 分页、按状态/标签过滤、按发布时间排序
- 📖 **文章详情** — 单篇文章完整内容 + 关联评论
- 💬 **评论功能** — 发表、删除评论，评论关联文章
- 🗂️ **分类/标签** — 文章支持分类与标签
- 🔍 **搜索** — 按标题/内容关键词搜索

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0 |
| 数据库 | SQLite（可切换 PostgreSQL） |
| 数据校验 | Pydantic v2 |
| 自动文档 | Swagger UI / ReDoc |

## 📁 项目结构

```
v1-blog/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口
│   ├── database.py        # 数据库连接 + 会话管理
│   ├── models.py          # SQLAlchemy 模型
│   ├── schemas.py         # Pydantic 模型
│   ├── crud.py            # 数据访问层
│   └── routers/
│       ├── __init__.py
│       ├── posts.py       # 文章路由
│       └── comments.py    # 评论路由
├── seed.py                # 示例数据填充
├── requirements.txt
└── README.md
```

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（自动创建数据库并填充示例数据）
uvicorn app.main:app --reload --port 8000
```

服务启动后：

- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 🧪 手动填充示例数据

```bash
python seed.py
```

## 🔌 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/posts` | 文章列表（分页、过滤、搜索） |
| GET | `/api/posts/{id}` | 文章详情（含评论数） |
| GET | `/api/posts/{id}/comments` | 文章的评论列表 |
| POST | `/api/posts/{id}/comments` | 发表评论 |
| DELETE | `/api/comments/{id}` | 删除评论 |
| GET | `/api/tags` | 标签列表 |
| GET | `/health` | 健康检查 |

## 📊 设计说明

遵循「快速验证优先」原则，本实现：
- 使用 SQLite 零配置开箱即用，生产可平滑切换 PostgreSQL
- 评论采用**外键关联**而非嵌套 JSON，保证数据一致性
- 提供分页防止数据量大时性能问题
- API 返回结构化 JSON，便于前端 React 直接对接
