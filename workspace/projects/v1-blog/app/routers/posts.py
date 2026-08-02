"""文章相关路由。"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=schemas.PaginatedPosts)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """文章列表：支持分页、分类/标签过滤、关键词搜索。"""
    posts, total = crud.get_posts(
        db, page=page, page_size=page_size,
        category=category, tag=tag, search=search,
    )
    # 附加评论数
    items = []
    for p in posts:
        item = schemas.PostListOut.model_validate(p)
        item.comment_count = crud.get_comment_count(db, p.id)
        items.append(item)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "items": items,
    }


@router.get("/{post_id}", response_model=schemas.PostDetailOut)
def get_post_detail(
    post_id: int,
    db: Session = Depends(get_db),
):
    """文章详情：完整正文 + 评论列表。访问时浏览量 +1。"""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    crud.increment_views(db, post)

    detail = schemas.PostDetailOut.model_validate(post)
    detail.comment_count = crud.get_comment_count(db, post.id)
    detail.comments = crud.get_comments(db, post.id)
    return detail


@router.post("", response_model=schemas.PostDetailOut, status_code=201)
def create_post(
    data: schemas.PostCreate,
    db: Session = Depends(get_db),
):
    """创建文章。"""
    # slug 唯一性检查
    existing = crud.get_post_by_slug(db, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="slug 已存在")
    return crud.create_post(db, data)


@router.put("/{post_id}", response_model=schemas.PostDetailOut)
def update_post(
    post_id: int,
    data: schemas.PostUpdate,
    db: Session = Depends(get_db),
):
    """更新文章。"""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return crud.update_post(db, post, data)


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    """删除文章（级联删除评论）。"""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    crud.delete_post(db, post)
