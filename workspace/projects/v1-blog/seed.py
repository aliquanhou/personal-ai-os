"""示例数据填充脚本。

用法: python seed.py
"""
from app.database import Base, engine, SessionLocal
from app import models


SAMPLE_POSTS = [
    {
        "title": "我的第一篇博客",
        "slug": "my-first-post",
        "excerpt": "欢迎来到我的个人博客，这是第一篇文章。",
        "content": """# 我的第一篇博客

欢迎来到我的个人博客！这里是我的技术笔记与生活记录。

## 关于我

我是一名热爱技术的开发者，专注于 **Python** 和 **TypeScript**，喜欢构建真正有用的 AI 工具。

## 为什么写博客

- 记录学习过程
- 分享技术经验
- 沉淀思考成果

希望这里的内容对你有所帮助。欢迎留言交流！
""",
        "category": "杂谈",
        "status": "published",
        "tags": ["欢迎", "随笔"],
    },
    {
        "title": "FastAPI 快速入门指南",
        "slug": "fastapi-quickstart",
        "excerpt": "从零开始搭建一个 FastAPI 项目，涵盖路由、模型、数据库等核心概念。",
        "content": """# FastAPI 快速入门指南

FastAPI 是一个现代、高性能的 Python Web 框架，基于 **Starlette** 和 **Pydantic**。

## 为什么选择 FastAPI

- 🚀 高性能，媲美 NodeJS 和 Go
- 📝 自动生成交互式 API 文档
- ✅ 基于类型提示的自动数据校验
- 🔧 依赖注入系统优雅简洁

## 最小示例

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}
```

## 核心概念

1. **路径操作** — 定义 API 端点
2. **Pydantic 模型** — 请求/响应数据校验
3. **依赖注入** — 复用数据库会话等资源

FastAPI 让 Python 后端开发变得简单而高效。
""",
        "category": "后端",
        "status": "published",
        "tags": ["FastAPI", "Python", "教程"],
    },
    {
        "title": "SQLAlchemy 2.0 现代 ORM 实践",
        "slug": "sqlalchemy-2-modern-orm",
        "excerpt": "探讨 SQLAlchemy 2.0 的新特性，以及如何用它构建清晰的数据层。",
        "content": """# SQLAlchemy 2.0 现代 ORM 实践

SQLAlchemy 是 Python 最强大的 ORM 工具，2.0 版本带来了全新的 API。

## 主要变化

- `session.execute()` 统一查询入口
- 类型化声明式映射
- 更清晰的 relationship 配置

## 声明式模型

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
```

## 为什么重要

类型化的 ORM 让代码更易读、更安全，配合 IDE 提示能极大提升开发效率。
""",
        "category": "后端",
        "status": "published",
        "tags": ["SQLAlchemy", "Python", "数据库"],
    },
    {
        "title": "个人 AI OS 的构想",
        "slug": "personal-ai-os-vision",
        "excerpt": "聊聊我理想中的个人 AI 操作系统：让 AI 真正融入日常，记住并帮助用户成长。",
        "content": """# 个人 AI OS 的构想

我正在打造一个个人 AI 操作系统，愿景是让 AI 成为真正的个人助理。

## 核心目标

- 🧠 **记忆** — AI 记住你的偏好、决策与经验
- 🤝 **协作** — 主动拆解任务、推动执行
- 📈 **成长** — 从每次交互中学习，持续优化

## 设计原则

1. **快速验证** — 优先于完美设计
2. **本地模型优先** — 数据自主可控
3. **不做重复造轮子** — 复用成熟方案

## 下一步

v0.2 版本将重点完善记忆与任务系统，让 AI 真正「记住」并「行动」。
""",
        "category": "AI",
        "status": "published",
        "tags": ["AI", "产品", "愿景"],
    },
]


def seed():
    """填充示例数据。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 清空旧数据（可选）
        db.query(models.Comment).delete()
        db.query(models.Post).delete()
        db.query(models.Tag).delete()
        db.commit()

        for data in SAMPLE_POSTS:
            item = dict(data)          # 复制，避免修改 SAMPLE_POSTS
            tags = item.pop("tags", [])
            post = models.Post(**item)
            db.add(post)
            db.flush()                 # 先持久化 post，获得 id

            # 创建或获取标签，并建立多对多关联
            for name in tags:
                tag = db.query(models.Tag).filter(models.Tag.name == name).first()
                if not tag:
                    tag = models.Tag(name=name)
                    db.add(tag)
                    db.flush()
                if tag not in post.tags:
                    post.tags.append(tag)
            db.flush()

            # 为前两篇文章添加示例评论
            if post.slug in ("my-first-post", "fastapi-quickstart"):
                db.add_all([
                    models.Comment(
                        post_id=post.id,
                        author="路人甲",
                        email="guest@example.com",
                        content="写得很棒，期待更多内容！",
                    ),
                    models.Comment(
                        post_id=post.id,
                        author="技术爱好者",
                        email="dev@example.com",
                        content="收藏了，对我很有帮助。",
                    ),
                ])

        db.commit()
        print(f"✅ 已填充 {len(SAMPLE_POSTS)} 篇文章及示例评论")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
