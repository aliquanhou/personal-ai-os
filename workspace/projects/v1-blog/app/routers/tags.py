"""标签相关路由。"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=List[schemas.TagOut])
def list_tags(db: Session = Depends(get_db)):
    """获取所有标签。"""
    return crud.get_all_tags(db)
