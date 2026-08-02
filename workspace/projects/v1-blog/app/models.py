"""SQLAlchemy 数据模型。"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Table, Boolean
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


# 文章-标签 多对多关联表
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Post(Base):
    """文章模型。"""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    excerpt = Column(String(500), default="")
    category = Column(String(50), default="未分类")
    status = Column(String(20), default="published")  # published / draft
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # 关系
    comments = relationship(
        "Comment", back_populates="post",
        cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")


class Comment(Base):
    """评论模型。"""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author = Column(String(100), nullable=False)
    email = Column(String(120), default="")
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="comments")


class Tag(Base):
    """标签模型。"""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)

    posts = relationship("Post", secondary=post_tags, back_populates="tags")
