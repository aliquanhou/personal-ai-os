"""健康检查路由"""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()

settings = get_settings()


@router.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
