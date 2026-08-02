"""数据访问层：封装数据库操作。"""
from typing import Optional, List

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import models, schemas


# ---------- 标签 ----------

def get_or_create_tags(db: Session, names: List[str]) -> List[models.Tag]:
    """按名称获取或创建标签对象。"""
    tags = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if not tag:
            tag = models.Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


# ---------- 文章 ----------

def get_posts(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    status: str = "published",
) -> tuple[List[models.Post], int]:
    """分页查询文章列表。返回 (文章列表, 总数)。"""
    query = db.query(models.Post).filter(models.Post.status == status)

    if category:
        query = query.filter(models.Post.category == category)
    if tag:
        query = query.filter(models.Post.tags.any(models.Tag.name == tag))
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(models.Post.title.ilike(like), models.Post.content.ilike(like))
        )

    total = query.count()
    posts = (
        query.order_by(models.Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return posts, total


def get_post(db: Session, post_id: int) -> Optional[models.Post]:
    return db.query(models.Post).filter(models.Post.id == post_id).first()


def get_post_by_slug(db: Session, slug: str) -> Optional[models.Post]:
    return db.query(models.Post).filter(models.Post.slug == slug).first()


def increment_views(db: Session, post: models.Post) -> None:
    """增加文章浏览量。"""
    post.views += 1
    db.commit()
    db.refresh(post)


def create_post(db: Session, data: schemas.PostCreate) -> models.Post:
    post = models.Post(
        title=data.title,
        slug=data.slug,
        content=data.content,
        excerpt=data.excerpt,
        category=data.category,
        status=data.status,
    )
    post.tags = get_or_create_tags(db, data.tags or [])
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: models.Post, data: schemas.PostUpdate) -> models.Post:
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "tags" and value is not None:
            post.tags = get_or_create_tags(db, value)
        elif value is not None:
            setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: models.Post) -> None:
    db.delete(post)
    db.commit()


# ---------- 评论 ----------

def get_comments(db: Session, post_id: int, approved_only: bool = True) -> List[models.Comment]:
    query = db.query(models.Comment).filter(models.Comment.post_id == post_id)
    if approved_only:
        query = query.filter(models.Comment.is_approved == True)  # noqa: E712
    return query.order_by(models.Comment.created_at.desc()).all()


def create_comment(db: Session, post_id: int, data: schemas.CommentCreate) -> models.Comment:
    comment = models.Comment(
        post_id=post_id,
        author=data.author,
        email=data.email,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_comment(db: Session, comment_id: int) -> Optional[models.Comment]:
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()


def delete_comment(db: Session, comment: models.Comment) -> None:
    db.delete(comment)
    db.commit()


# ---------- 统计 ----------

def get_comment_count(db: Session, post_id: int) -> int:
    return (
        db.query(func.count(models.Comment.id))
        .filter(models.Comment.post_id == post_id)
        .scalar()
        or 0
    )


def get_all_tags(db: Session) -> List[models.Tag]:
    return db.query(models.Tag).order_by(models.Tag.name).all()
