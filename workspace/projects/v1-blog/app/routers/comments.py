"""评论相关路由。"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api", tags=["comments"])


@router.get("/posts/{post_id}/comments", response_model=List[schemas.CommentOut])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    """获取某篇文章的评论列表。"""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return crud.get_comments(db, post_id)


@router.post("/posts/{post_id}/comments", response_model=schemas.CommentOut, status_code=201)
def create_comment(
    post_id: int,
    data: schemas.CommentCreate,
    db: Session = Depends(get_db),
):
    """发表评论。"""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    return crud.create_comment(db, post_id, data)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    """删除评论。"""
    comment = crud.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    crud.delete_comment(db, comment)
