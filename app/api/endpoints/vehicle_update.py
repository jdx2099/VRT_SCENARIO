"""
车型数据更新API端点
提供车型数据更新相关的API接口，使用schemas进行数据校验和规范化响应
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.vehicle_update_service import vehicle_update_service
from app.schemas.vehicle_update import (
    UpdateRequestSchema, UpdateResultSchema, UpdateTaskSchema,
    ChannelListSchema, ProcessingJobSchema
)
from app.core.logging import app_logger

router = APIRouter(prefix="/vehicle-update", tags=["车型数据更新"])


@router.post("/update", response_model=UpdateTaskSchema)
async def update_vehicles_async(update_request: UpdateRequestSchema) -> UpdateTaskSchema:
    """
    异步更新指定渠道的车型数据
    
    Args:
        update_request: 更新请求参数
        
    Returns:
        更新任务信息
    """
    try:
        app_logger.info(f"🚀 启动渠道 {update_request.channel_id} 车型更新任务")
        
        # 启动异步更新任务
        task = await vehicle_update_service.update_vehicles(update_request)
        
        return task
        
    except ValueError as e:
        app_logger.error(f"❌ 参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 启动更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动更新任务失败: {str(e)}")


@router.post("/update/direct", response_model=UpdateResultSchema)
async def update_vehicles_direct(update_request: UpdateRequestSchema) -> UpdateResultSchema:
    """
    直接更新指定渠道的车型数据（同步执行）
    
    Args:
        update_request: 更新请求参数
        
    Returns:
        更新结果
    """
    try:
        app_logger.info(f"🔄 开始直接更新渠道 {update_request.channel_id} 车型数据")
        
        # 直接执行更新
        result = await vehicle_update_service.update_vehicles_direct(update_request)
        
        return result
        
    except ValueError as e:
        app_logger.error(f"❌ 参数验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/channels", response_model=ChannelListSchema)
async def get_supported_channels() -> ChannelListSchema:
    """
    获取支持的渠道列表
    
    Returns:
        支持的渠道信息
    """
    try:
        channels = await vehicle_update_service.get_supported_channels()
        return channels
        
    except Exception as e:
        app_logger.error(f"❌ 获取支持渠道失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取支持渠道失败: {str(e)}")



@router.get("/sync/{task_id}/status")
async def get_sync_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取同步任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        from app.tasks.celery_app import celery_app
        
        task = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.status == "SUCCESS" else None,
            "error": str(task.info) if task.status == "FAILURE" else None
        }
        
    except Exception as e:
        app_logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/jobs/{job_id}", response_model=ProcessingJobSchema)
async def get_processing_job(job_id: int) -> ProcessingJobSchema:
    """
    获取processing_job记录详情
    
    Args:
        job_id: 任务ID
        
    Returns:
        processing_job详情
    """
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import ProcessingJob
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()
            
            if not job:
                raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")
            
            return ProcessingJobSchema.from_orm(job)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"❌ 获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}") 