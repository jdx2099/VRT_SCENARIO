"""
车型数据更新相关的异步任务 - 基于Celery+Redis
"""
import asyncio
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from typing import Dict

@celery_app.task(bind=True, max_retries=3)
def update_vehicle_data_async(self, channel_id: int, force_update: bool = False, filters: Dict = None):
    """
    车型数据更新异步任务
    
    Args:
        channel_id: 渠道ID
        force_update: 是否强制更新
        filters: 过滤条件
    """
    try:
        app_logger.info(f"🚗 开始执行车型更新任务: 渠道ID {channel_id}")
        
        # 更新任务状态为运行中
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'progress': 0,
                'status': f'正在更新渠道 {channel_id} 的车型数据...',
                'channel_id': channel_id
            }
        )
        
        # 导入相关模块（避免循环导入）
        from app.services.vehicle_update_service import vehicle_update_service
        from app.schemas.vehicle_update import UpdateRequestSchema
        
        # 创建更新请求
        update_request = UpdateRequestSchema(
            channel_id=channel_id,
            force_update=force_update,
            filters=filters or {}
        )
        
        # 执行更新
        result = asyncio.run(vehicle_update_service.update_vehicles_direct(update_request))
        
        # 更新任务状态为完成
        return {
            'channel_id': channel_id,
            'status': 'completed',
            'result': {
                'total_crawled': result.total_crawled,
                'new_vehicles': result.new_vehicles,
                'updated_vehicles': result.updated_vehicles,
                'unchanged_vehicles': result.unchanged_vehicles,
                'channel_name': result.channel_name
            },
            'message': f'渠道 {result.channel_name} 车型更新完成'
        }
        
    except Exception as exc:
        app_logger.error(f"❌ 车型更新任务失败: {exc}")
        
        # 更新任务状态为失败
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'channel_id': channel_id,
                'message': f'渠道 {channel_id} 车型更新失败: {exc}'
            }
        )
        
        # 重新抛出异常给Celery处理重试逻辑
        raise exc

# Celery任务状态监控
@celery_app.task
def get_task_info(task_id: str):
    """
    获取Celery任务信息
    """
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result,
            'info': result.info,
            'successful': result.successful(),
            'failed': result.failed()
        }
    except Exception as e:
        return {'error': str(e)} 