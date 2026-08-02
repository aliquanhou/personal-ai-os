"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import posts, comments, tags

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal Blog API",
    description="个人博客后端：文章列表、文章详情、评论功能",
    version="0.1.0",
)

# CORS 配置（开发环境允许前端本地调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(tags.router)


@app.get("/health", tags=["health"])
def health_check():
    """健康检查。"""
    return {"status": "ok", "service": "personal-blog"}


@app.get("/", tags=["root"])
def root():
    """根路径。"""
    return {
        "message": "Welcome to Personal Blog API",
        "docs": "/docs",
        "health": "/health",
    }
