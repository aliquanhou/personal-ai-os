"""Pydantic 数据校验模型（API 出入参）。"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ---------- 评论 Schemas ----------

class CommentBase(BaseModel):
    author: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(default="", max_length=120)
    content: str = Field(..., min_length=1)


class CommentCreate(CommentBase):
    pass


class CommentOut(CommentBase):
    id: int
    post_id: int
    is_approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- 文章 Schemas ----------

class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = ""
    category: Optional[str] = "未分类"
    status: Optional[str] = "published"
    tags: Optional[List[str]] = []


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class PostListOut(BaseModel):
    """列表视图：不含正文，含评论数。"""
    id: int
    title: str
    slug: str
    excerpt: str
    category: str
    status: str
    views: int
    tags: List[TagOut] = []
    comment_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PostDetailOut(PostListOut):
    """详情视图：含完整正文与评论。"""
    content: str
    comments: List[CommentOut] = []


# ---------- 分页响应 ----------

class PaginatedPosts(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[PostListOut]
