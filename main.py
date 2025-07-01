"""
FastAPI 应用主入口文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.config import settings
from app.core.logging import app_logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="基于爬虫和大模型的用户反馈结构化解析系统",
    debug=settings.DEBUG
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    app_logger.info(f"🚀 {settings.PROJECT_NAME} v{settings.VERSION} 正在启动...")
    app_logger.info(f"📋 调试模式: {settings.DEBUG}")
    app_logger.info(f"🌐 允许的来源: {settings.ALLOWED_ORIGINS}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    app_logger.info("👋 应用正在关闭...")

# 移除程序化启动代码，使用标准的uvicorn命令行启动
# 开发环境: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# 生产环境: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 