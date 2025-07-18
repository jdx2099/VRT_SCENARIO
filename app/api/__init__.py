"""
API路由聚合
"""
from fastapi import APIRouter
from app.api.endpoints import vehicle_update, raw_comment_update, scheduled_tasks, scheduled_comment_tasks

router = APIRouter()

# 注册车型数据更新路由
router.include_router(vehicle_update.router, tags=["车型数据更新"])

# 注册原始评论更新路由
router.include_router(raw_comment_update.router, tags=["原始评论更新"])

# 注册定时任务管理路由
router.include_router(scheduled_tasks.router, tags=["定时任务管理"])

# 注册定时评论爬取任务管理路由
router.include_router(scheduled_comment_tasks.router, tags=["定时评论爬取任务"]) 