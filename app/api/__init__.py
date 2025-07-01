"""
API路由聚合
"""
from fastapi import APIRouter
from app.api.endpoints import vehicle_update

router = APIRouter()

# 注册车型数据更新路由
router.include_router(vehicle_update.router, tags=["车型数据更新"]) 