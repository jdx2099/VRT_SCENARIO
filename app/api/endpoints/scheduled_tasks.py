"""
定时任务管理API端点
提供定时任务的查询、配置和管理功能
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.core.logging import app_logger
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务管理"])


@router.get("/status")
async def get_scheduled_tasks_status() -> Dict[str, Any]:
    """
    获取定时任务状态概览
    
    Returns:
        定时任务状态信息
    """
    try:
        app_logger.info("🔍 查询定时任务状态")
        
        # 获取Beat调度器状态
        beat_stats = celery_app.control.inspect().stats()
        
        # 获取当前配置的定时任务
        beat_schedule = celery_app.conf.beat_schedule
        
        # 构建任务状态信息
        tasks_info = []
        for task_name, task_config in beat_schedule.items():
            task_info = {
                'task_name': task_name,
                'task_function': task_config['task'],
                'schedule_seconds': task_config['schedule'],
                'schedule_human': _format_schedule(task_config['schedule']),
                'args': task_config.get('args', []),
                'options': task_config.get('options', {}),
                'enabled': True  # 当前配置中的任务都是启用的
            }
            tasks_info.append(task_info)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_scheduled_tasks': len(tasks_info),
            'beat_scheduler_running': bool(beat_stats),
            'tasks': tasks_info
        }
        
    except Exception as e:
        app_logger.error(f"❌ 获取定时任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取定时任务状态失败: {str(e)}")


from pydantic import BaseModel

class VehicleUpdateRequest(BaseModel):
    channel_ids: List[int] = None
    force_update: bool = False

@router.post("/vehicle-update/trigger")
async def trigger_vehicle_update_now(request: VehicleUpdateRequest) -> Dict[str, Any]:
    """
    立即触发车型数据更新任务
    
    Args:
        request: 请求参数，包含channel_ids和force_update
        
    Returns:
        任务执行信息
    """
    try:
        app_logger.info(f"🚀 手动触发车型更新任务: channels={request.channel_ids}, force_update={request.force_update}")
        
        # 导入定时任务函数
        from app.tasks.scheduled_tasks import scheduled_vehicle_update
        
        # 启动任务
        task = scheduled_vehicle_update.delay(request.channel_ids, request.force_update)
        
        return {
            'task_id': task.id,
            'status': 'triggered',
            'message': f'车型更新任务已启动: {task.id}',
            'channel_ids': request.channel_ids,
            'force_update': request.force_update,
            'triggered_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"❌ 触发车型更新任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发任务失败: {str(e)}")





@router.get("/tasks/{task_id}/status")
async def get_scheduled_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取定时任务执行状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    try:
        app_logger.info(f"🔍 查询定时任务状态: task_id={task_id}")
        
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


@router.get("/health-check")
async def trigger_health_check() -> Dict[str, Any]:
    """
    立即触发系统健康检查
    
    Returns:
        健康检查结果
    """
    try:
        app_logger.info("🏥 手动触发系统健康检查")
        
        # 导入健康检查函数
        from app.tasks.scheduled_tasks import health_check
        
        # 执行健康检查
        result = health_check.delay()
        
        return {
            'task_id': result.id,
            'status': 'triggered',
            'message': '健康检查任务已启动',
            'triggered_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"❌ 触发健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"触发健康检查失败: {str(e)}")


@router.get("/recent-executions")
async def get_recent_task_executions(limit: int = 10) -> Dict[str, Any]:
    """
    获取最近的定时任务执行记录
    
    Args:
        limit: 返回记录数量限制
        
    Returns:
        最近的执行记录
    """
    try:
        app_logger.info(f"📋 查询最近{limit}条定时任务执行记录")
        
        # 从数据库查询最近的processing_job记录
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import ProcessingJob
        from sqlalchemy import select, desc
        
        async with AsyncSessionLocal() as db:
            # 查询最近的定时任务记录
            result = await db.execute(
                select(ProcessingJob)
                .where(ProcessingJob.job_type.in_(['scheduled_vehicle_update', 'health_check']))
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