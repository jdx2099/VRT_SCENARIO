"""
定时评论爬取任务管理API端点
提供定时评论爬取任务的查询、配置和管理功能
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.core.logging import app_logger
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/scheduled-comment-tasks", tags=["定时评论爬取任务"])


class ManualCommentCrawlRequest(BaseModel):
    vehicle_channel_ids: Optional[List[int]] = None
    max_pages_per_vehicle: int = 10


@router.get("/status")
async def get_scheduled_comment_tasks_status() -> Dict[str, Any]:
    """
    获取定时评论爬取任务状态概览
    
    Returns:
        定时评论爬取任务状态信息
    """
    try:
        app_logger.info("🔍 查询定时评论爬取任务状态")
        
        # 获取Beat调度器状态
        beat_stats = celery_app.control.inspect().stats()
        
        # 获取当前配置的定时任务
        beat_schedule = celery_app.conf.beat_schedule
        
        # 查找评论爬取相关的定时任务
        comment_tasks = []
        for task_name, task_config in beat_schedule.items():
            if 'comment' in task_name.lower() or 'comment' in task_config['task'].lower():
                task_info = {
                    'task_name': task_name,
                    'task_function': task_config['task'],
                    'schedule_seconds': task_config['schedule'],
                    'schedule_human': _format_schedule(task_config['schedule']),
                    'args': task_config.get('args', []),
                    'options': task_config.get('options', {}),
                    'enabled': True
                }
                comment_tasks.append(task_info)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_scheduled_comment_tasks': len(comment_tasks),
            'beat_scheduler_running': bool(beat_stats),
            'comment_tasks': comment_tasks
        }
        
    except Exception as e:
        app_logger.error(f"❌ 获取定时评论爬取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取定时评论爬取任务状态失败: {str(e)}")


@router.post("/manual-crawl/trigger")
async def trigger_manual_comment_crawl(request: ManualCommentCrawlRequest) -> Dict[str, Any]:
    """
    手动触发评论爬取任务
    
    Args:
        request: 请求参数，包含vehicle_channel_ids和max_pages_per_vehicle
        
    Returns:
        任务执行信息
    """
    try:
        app_logger.info(f"🚀 手动触发评论爬取任务: vehicle_ids={request.vehicle_channel_ids}, max_pages={request.max_pages_per_vehicle}")
        
        # 导入定时任务函数
        from app.tasks.scheduled_comment_tasks import manual_comment_crawl
        
        # 启动任务
        task = manual_comment_crawl.delay(
            vehicle_channel_ids=request.vehicle_channel_ids,
            max_pages_per_vehicle=request.max_pages_per_vehicle
        )
        
        return {
            'task_id': task.id,
            'status': 'triggered',
            'message': f'评论爬取任务已启动: {task.id}',
            'vehicle_channel_ids': request.vehicle_channel_ids,
            'max_pages_per_vehicle': request.max_pages_per_vehicle,
            'triggered_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"❌ 触发评论爬取任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发任务失败: {str(e)}")


@router.get("/tasks/{task_id}/status")
async def get_scheduled_comment_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取定时评论爬取任务执行状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        app_logger.info(f"🔍 查询定时评论爬取任务状态: task_id={task_id}")
        
        task = celery_app.AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.status == "SUCCESS" else None,
            'error': str(task.info) if task.status == "FAILURE" else None,
            'progress': task.info.get('progress', 0) if isinstance(task.info, dict) else 0,
            'current': task.info.get('current', 0) if isinstance(task.info, dict) else 0,
            'total': task.info.get('total', 0) if isinstance(task.info, dict) else 0,
            'message': task.info.get('status', '') if isinstance(task.info, dict) else '',
            'date_done': task.date_done.isoformat() if task.date_done else None
        }
        
    except Exception as e:
        app_logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/recent-executions")
async def get_recent_comment_task_executions(limit: int = 10) -> Dict[str, Any]:
    """
    获取最近的定时评论爬取任务执行记录
    
    Args:
        limit: 返回记录数量限制
        
    Returns:
        最近的执行记录
    """
    try:
        app_logger.info(f"📋 查询最近{limit}条定时评论爬取任务执行记录")
        
        # 从数据库查询最近的processing_job记录
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import ProcessingJob
        from sqlalchemy import select, desc
        
        async with AsyncSessionLocal() as db:
            # 查询最近的评论爬取任务记录
            result = await db.execute(
                select(ProcessingJob)
                .where(ProcessingJob.job_type.in_(['scheduled_comment_crawl', 'manual_comment_crawl']))
                .order_by(desc(ProcessingJob.created_at))
                .limit(limit)
            )
            
            jobs = result.scalars().all()
            
            executions = []
            for job in jobs:
                execution = {
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'status': job.status,
                    'pipeline_version': job.pipeline_version,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'result_summary': job.result_summary
                }
                executions.append(execution)
            
            return {
                'total_count': len(executions),
                'executions': executions
            }
        
    except Exception as e:
        app_logger.error(f"❌ 查询执行记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询执行记录失败: {str(e)}")


@router.get("/vehicle-statistics")
async def get_vehicle_crawl_statistics() -> Dict[str, Any]:
    """
    获取车型评论爬取统计信息
    
    Returns:
        车型评论爬取统计信息
    """
    try:
        app_logger.info("📊 查询车型评论爬取统计信息")
        
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import VehicleChannelDetail
        from sqlalchemy import select, func, desc, asc
        
        async with AsyncSessionLocal() as db:
            # 统计总车型数
            total_result = await db.execute(
                select(func.count(VehicleChannelDetail.vehicle_channel_id))
            )
            total_vehicles = total_result.scalar()
            
            # 统计已爬取过的车型数
            crawled_result = await db.execute(
                select(func.count(VehicleChannelDetail.vehicle_channel_id))
                .where(VehicleChannelDetail.last_comment_crawled_at.is_not(None))
            )
            crawled_vehicles = crawled_result.scalar()
            
            # 统计未爬取过的车型数
            uncrawled_result = await db.execute(
                select(func.count(VehicleChannelDetail.vehicle_channel_id))
                .where(VehicleChannelDetail.last_comment_crawled_at.is_(None))
            )
            uncrawled_vehicles = uncrawled_result.scalar()
            
            # 获取最近爬取的车型
            recent_crawled_result = await db.execute(
                select(VehicleChannelDetail)
                .where(VehicleChannelDetail.last_comment_crawled_at.is_not(None))
                .order_by(desc(VehicleChannelDetail.last_comment_crawled_at))
                .limit(5)
            )
            recent_crawled = recent_crawled_result.scalars().all()
            
            # 获取最早爬取的车型（需要重新爬取的候选）
            oldest_crawled_result = await db.execute(
                select(VehicleChannelDetail)
                .where(VehicleChannelDetail.last_comment_crawled_at.is_not(None))
                .order_by(asc(VehicleChannelDetail.last_comment_crawled_at))
                .limit(5)
            )
            oldest_crawled = oldest_crawled_result.scalars().all()
            
            # 构建统计信息
            statistics = {
                'total_vehicles': total_vehicles,
                'crawled_vehicles': crawled_vehicles,
                'uncrawled_vehicles': uncrawled_vehicles,
                'crawl_rate': round((crawled_vehicles / total_vehicles * 100), 2) if total_vehicles > 0 else 0,
                'recent_crawled': [
                    {
                        'vehicle_channel_id': v.vehicle_channel_id,
                        'vehicle_name': v.name_on_channel,
                        'last_crawled_at': v.last_comment_crawled_at.isoformat() if v.last_comment_crawled_at else None
                    }
                    for v in recent_crawled
                ],
                'oldest_crawled': [
                    {
                        'vehicle_channel_id': v.vehicle_channel_id,
                        'vehicle_name': v.name_on_channel,
                        'last_crawled_at': v.last_comment_crawled_at.isoformat() if v.last_comment_crawled_at else None
                    }
                    for v in oldest_crawled
                ]
            }
            
            return statistics
        
    except Exception as e:
        app_logger.error(f"❌ 查询车型统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询车型统计信息失败: {str(e)}")


@router.get("/uncrawled-vehicles")
async def get_uncrawled_vehicles(limit: int = 20) -> Dict[str, Any]:
    """
    获取未爬取过的车型列表
    
    Args:
        limit: 返回记录数量限制
        
    Returns:
        未爬取过的车型列表
    """
    try:
        app_logger.info(f"🔍 查询未爬取过的车型列表: limit={limit}")
        
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import VehicleChannelDetail
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VehicleChannelDetail)
                .where(VehicleChannelDetail.last_comment_crawled_at.is_(None))
                .limit(limit)
            )
            
            vehicles = result.scalars().all()
            
            vehicle_list = [
                {
                    'vehicle_channel_id': v.vehicle_channel_id,
                    'vehicle_name': v.name_on_channel,
                    'channel_id': v.channel_id_fk,
                    'identifier_on_channel': v.identifier_on_channel,
                    'temp_brand_name': v.temp_brand_name,
                    'temp_series_name': v.temp_series_name,
                    'temp_model_year': v.temp_model_year
                }
                for v in vehicles
            ]
            
            return {
                'total_count': len(vehicle_list),
                'vehicles': vehicle_list
            }
        
    except Exception as e:
        app_logger.error(f"❌ 查询未爬取车型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询未爬取车型列表失败: {str(e)}")


@router.get("/oldest-crawled-vehicles")
async def get_oldest_crawled_vehicles(limit: int = 20) -> Dict[str, Any]:
    """
    获取最早爬取过的车型列表（需要重新爬取的候选）
    
    Args:
        limit: 返回记录数量限制
        
    Returns:
        最早爬取过的车型列表
    """
    try:
        app_logger.info(f"🔍 查询最早爬取过的车型列表: limit={limit}")
        
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import VehicleChannelDetail
        from sqlalchemy import select, asc
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VehicleChannelDetail)
                .where(VehicleChannelDetail.last_comment_crawled_at.is_not(None))
                .order_by(asc(VehicleChannelDetail.last_comment_crawled_at))
                .limit(limit)
            )
            
            vehicles = result.scalars().all()
            
            vehicle_list = [
                {
                    'vehicle_channel_id': v.vehicle_channel_id,
                    'vehicle_name': v.name_on_channel,
                    'channel_id': v.channel_id_fk,
                    'identifier_on_channel': v.identifier_on_channel,
                    'temp_brand_name': v.temp_brand_name,
                    'temp_series_name': v.temp_series_name,
                    'temp_model_year': v.temp_model_year,
                    'last_comment_crawled_at': v.last_comment_crawled_at.isoformat() if v.last_comment_crawled_at else None
                }
                for v in vehicles
            ]
            
            return {
                'total_count': len(vehicle_list),
                'vehicles': vehicle_list
            }
        
    except Exception as e:
        app_logger.error(f"❌ 查询最早爬取车型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询最早爬取车型列表失败: {str(e)}")


def _format_schedule(seconds: float) -> str:
    """
    格式化时间间隔为人类可读格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds/60:.1f}分钟"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}小时"
    else:
        return f"{seconds/86400:.1f}天" 