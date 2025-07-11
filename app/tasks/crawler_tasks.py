"""
车型数据更新相关的异步任务 - 基于Celery+Redis
"""
import asyncio
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from typing import Dict
from datetime import datetime


def _update_processing_job_status(job_id: int, status: str, started_at: bool = False, completed_at: bool = False, result_summary: str = None):
    """
    更新processing_job状态的辅助函数
    
    Args:
        job_id: 任务ID
        status: 新状态
        started_at: 是否更新开始时间
        completed_at: 是否更新完成时间
        result_summary: 结果摘要
    """
    try:
        # 导入数据库相关模块
        from app.core.database import get_sync_session
        from app.models.vehicle_update import ProcessingJob
        from sqlalchemy import update
        
        # 构建更新字典
        update_data = {"status": status}
        
        if started_at:
            update_data["started_at"] = datetime.utcnow()
        if completed_at:
            update_data["completed_at"] = datetime.utcnow()
        if result_summary:
            update_data["result_summary"] = result_summary
        
        # 执行更新
        with get_sync_session() as db:
            db.execute(
                update(ProcessingJob)
                .where(ProcessingJob.job_id == job_id)
                .values(**update_data)
            )
            db.commit()
        
        app_logger.info(f"更新processing_job状态: job_id={job_id}, status={status}")
        
    except Exception as e:
        app_logger.error(f"更新processing_job状态失败: job_id={job_id}, error={e}")
        # 不要抛出异常，避免影响主任务

@celery_app.task(bind=True, max_retries=3)
def update_vehicle_data_async(self, channel_id: int, force_update: bool = False, filters: Dict = None, job_id: int = None):
    """
    车型数据更新异步任务
    
    Args:
        channel_id: 渠道ID
        force_update: 是否强制更新
        filters: 过滤条件
        job_id: processing_job记录ID
    """
    try:
        app_logger.info(f"🚗 开始执行车型更新任务: 渠道ID {channel_id}, job_id {job_id}")
        
        # 更新processing_job状态为运行中
        if job_id:
            _update_processing_job_status(job_id, "running", started_at=True)
        
        # 更新任务状态为运行中
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'progress': 0,
                'status': f'正在更新渠道 {channel_id} 的车型数据...',
                'channel_id': channel_id,
                'job_id': job_id
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
        
        # 构建结果摘要
        result_summary = f"总爬取: {result.total_crawled}, 新增: {result.new_vehicles}, 更新: {result.updated_vehicles}, 无变化: {result.unchanged_vehicles}"
        
        # 更新processing_job状态为完成
        if job_id:
            _update_processing_job_status(job_id, "completed", completed_at=True, result_summary=result_summary)
        
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
            'message': f'渠道 {result.channel_name} 车型更新完成',
            'job_id': job_id
        }
        
    except Exception as exc:
        app_logger.error(f"❌ 车型更新任务失败: {exc}")
        
        # 更新processing_job状态为失败
        if job_id:
            _update_processing_job_status(job_id, "failed", completed_at=True, result_summary=f"任务失败: {str(exc)}")
        
        # 更新任务状态为失败
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'channel_id': channel_id,
                'job_id': job_id,
                'message': f'渠道 {channel_id} 车型更新失败: {exc}'
            }
        )
        
        # 重新抛出异常给Celery处理重试逻辑
        raise exc


@celery_app.task(bind=True, max_retries=3)
def crawl_raw_comments_async(self, channel_id: int, identifier_on_channel: str, max_pages: int = None, job_id: int = None):
    """
    原始评论爬取异步任务
    
    Args:
        channel_id: 渠道ID
        identifier_on_channel: 车型在渠道上的标识
        max_pages: 最大爬取页数限制
        job_id: processing_job记录ID
    """
    try:
        app_logger.info(f"🕷️ 开始执行评论爬取任务: 渠道ID {channel_id}, 车型 {identifier_on_channel}, job_id {job_id}")
        
        # 更新processing_job状态为运行中
        if job_id:
            _update_processing_job_status(job_id, "running", started_at=True)
        
        # 更新任务状态为运行中
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'progress': 0,
                'status': f'正在爬取车型 {identifier_on_channel} 的评论数据...',
                'channel_id': channel_id,
                'identifier_on_channel': identifier_on_channel,
                'job_id': job_id
            }
        )
        
        # 导入相关模块（避免循环导入）
        from app.services.raw_comment_update_service import raw_comment_update_service
        from app.schemas.raw_comment_update import RawCommentCrawlRequest
        
        # 创建爬取请求
        crawl_request = RawCommentCrawlRequest(
            channel_id=channel_id,
            identifier_on_channel=identifier_on_channel,
            max_pages=max_pages
        )
        
        # 执行爬取
        result = asyncio.run(raw_comment_update_service.crawl_new_comments(crawl_request))
        
        # 构建结果摘要
        result_summary = f"总页数: {result.total_pages_crawled}, 总评论: {result.total_comments_found}, 新增: {result.new_comments_count}, 耗时: {result.crawl_duration}秒"
        
        # 更新processing_job状态为完成
        if job_id:
            _update_processing_job_status(job_id, "completed", completed_at=True, result_summary=result_summary)
        
        # 更新任务状态为完成
        return {
            'channel_id': channel_id,
            'identifier_on_channel': identifier_on_channel,
            'status': 'completed',
            'result': {
                'vehicle_name': result.vehicle_channel_info.name_on_channel,
                'total_pages_crawled': result.total_pages_crawled,
                'total_comments_found': result.total_comments_found,
                'new_comments_count': result.new_comments_count,
                'crawl_duration': result.crawl_duration
            },
            'message': f'车型 {result.vehicle_channel_info.name_on_channel} 评论爬取完成，新增 {result.new_comments_count} 条评论',
            'job_id': job_id
        }
        
    except Exception as exc:
        app_logger.error(f"❌ 评论爬取任务失败: {exc}")
        
        # 更新processing_job状态为失败
        if job_id:
            _update_processing_job_status(job_id, "failed", completed_at=True, result_summary=f"任务失败: {str(exc)}")
        
        # 更新任务状态为失败
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'channel_id': channel_id,
                'identifier_on_channel': identifier_on_channel,
                'job_id': job_id,
                'message': f'车型 {identifier_on_channel} 评论爬取失败: {exc}'
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