"""
定时任务模块 - 基于Celery Beat实现周期性任务 (同步版本)
"""
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List


@celery_app.task(bind=True, max_retries=3)
def scheduled_vehicle_update(self, channel_ids: List[int] = None, force_update: bool = False):
    """
    定时车型数据更新任务 - 同步版本
    
    Args:
        channel_ids: 要更新的渠道ID列表，如果为None则更新所有渠道
        force_update: 是否强制更新
    """
    from app.core.database import get_sync_session
    from app.models.vehicle_update import ProcessingJob
    from app.services.vehicle_update_service_sync import vehicle_update_service_sync
    from app.schemas.vehicle_update import UpdateRequestSchema
    
    try:
        app_logger.info(f"⏰ 开始执行定时车型更新任务: channels={channel_ids}, force_update={force_update}")
        
        # 检查是否已有对应的ProcessingJob记录（避免重复创建）
        celery_task_id = self.request.id
        
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'progress': 0,
                'status': '正在执行定时车型更新...',
                'channel_ids': channel_ids,
                'force_update': force_update,
                'celery_task_id': celery_task_id
            }
        )
        
        # 获取所有渠道 - 使用同步服务
        if not channel_ids:
            channels = vehicle_update_service_sync.get_supported_channels()
            channel_ids = [channel_id for channel_id in channels.supported_channels.keys()]
        total_channels = len(channel_ids)
        completed_channels = 0
        results = []
        
        for channel_id in channel_ids:
            # 每个渠道都写入一条processing_jobs
            job_id = None
            try:
                # 检查是否已有对应的ProcessingJob记录
                with get_sync_session() as db:
                    # 查找是否已有相同celery_task_id和channel_id的记录
                    existing_job = db.query(ProcessingJob).filter(
                        ProcessingJob.job_type == "scheduled_vehicle_update",
                        ProcessingJob.parameters.contains({
                            "celery_task_id": celery_task_id,
                            "channel_id": channel_id
                        })
                    ).first()
                    
                    if existing_job:
                        # 如果找到现有记录，使用它
                        job_id = existing_job.job_id
                        app_logger.info(f"🔄 发现现有任务记录，继续执行: job_id={job_id}, channel_id={channel_id}")
                        
                        # 如果状态是running，说明任务被中断后重新启动
                        if existing_job.status == "running":
                            app_logger.info(f"🔄 任务被中断后重新启动，继续执行: job_id={job_id}")
                    else:
                        # 创建新的任务记录
                        processing_job = ProcessingJob(
                            job_type="scheduled_vehicle_update",
                            status="running",
                            parameters={
                                "channel_id": channel_id,
                                "force_update": force_update,
                                "celery_task_id": celery_task_id
                            },
                            pipeline_version="1.0.0",
                            created_by_user_id_fk=None,
                            started_at=datetime.now(timezone.utc)
                        )
                        db.add(processing_job)
                        db.commit()
                        db.refresh(processing_job)
                        job_id = processing_job.job_id
                        app_logger.info(f"📝 创建新的定时任务记录: job_id={job_id}, channel_id={channel_id}")
                
                # 执行更新 - 使用同步服务
                update_request = UpdateRequestSchema(
                    channel_id=channel_id,
                    force_update=force_update,
                    filters={}
                )
                result = vehicle_update_service_sync.update_vehicles_direct(update_request)
                
                # 更新任务记录为完成状态 - 同步版本
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = f"定时车型更新完成: 新增{result.new_vehicles}个, 更新{result.updated_vehicles}个, 未变{result.unchanged_vehicles}个"
                        db.commit()
                        app_logger.info(f"📝 更新定时任务记录为完成状态: job_id={job_id}")
                channel_result = {
                    'channel_id': channel_id,
                    'channel_name': result.channel_name,
                    'total_crawled': result.total_crawled,
                    'new_vehicles': result.new_vehicles,
                    'updated_vehicles': result.updated_vehicles,
                    'unchanged_vehicles': result.unchanged_vehicles,
                    'status': 'success',
                    'job_id': job_id
                }
                results.append(channel_result)
                completed_channels += 1
                progress = int((completed_channels / total_channels) * 100)
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': completed_channels,
                        'total': total_channels,
                        'progress': progress,
                        'status': f'已完成 {completed_channels}/{total_channels} 个渠道',
                        'results': results
                    }
                )
                app_logger.info(f"✅ 渠道 {channel_id} 更新完成: 新增{result.new_vehicles}个, 更新{result.updated_vehicles}个")
            except Exception as e:
                app_logger.error(f"❌ 渠道 {channel_id} 更新失败: {e}")
                # 更新任务记录为失败状态 - 同步版本
                if job_id:
                    with get_sync_session() as db:
                        job = db.get(ProcessingJob, job_id)
                        if job:
                            job.status = "failed"
                            job.completed_at = datetime.utcnow()
                            job.result_summary = f"定时车型更新任务失败: {e}"
                            db.commit()
                            app_logger.info(f"📝 更新定时任务记录为失败状态: job_id={job_id}")
                channel_result = {
                    'channel_id': channel_id,
                    'channel_name': f'渠道{channel_id}',
                    'error': str(e),
                    'status': 'failed',
                    'job_id': job_id
                }
                results.append(channel_result)
                completed_channels += 1
        # 汇总统计
        total_new = sum(r.get('new_vehicles', 0) for r in results if r.get('status') == 'success')
        total_updated = sum(r.get('updated_vehicles', 0) for r in results if r.get('status') == 'success')
        success_count = len([r for r in results if r.get('status') == 'success'])
        failed_count = len([r for r in results if r.get('status') == 'failed'])
        app_logger.info(f"🎉 定时车型更新任务完成: 成功{success_count}个渠道, 失败{failed_count}个渠道, 总计新增{total_new}个车型, 更新{total_updated}个车型")
        return {
            'status': 'completed',
            'total_channels': total_channels,
            'success_count': success_count,
            'failed_count': failed_count,
            'total_new_vehicles': total_new,
            'total_updated_vehicles': total_updated,
            'results': results,
            'message': f'定时车型更新完成: 成功{success_count}/{total_channels}个渠道'
        }
    except Exception as exc:
        app_logger.error(f"❌ 定时车型更新任务失败: {exc}")
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'message': f'定时车型更新任务失败: {exc}'
            }
        )
        raise exc





@celery_app.task
def health_check():
    """
    系统健康检查任务 - 同步版本
    """
    processing_job_id = None
    try:
        app_logger.info("🏥 执行系统健康检查...")
        
        # 创建processing_job记录 - 同步版本
        from app.core.database import get_sync_session
        from app.models.vehicle_update import ProcessingJob
        
        with get_sync_session() as db:
            processing_job = ProcessingJob(
                job_type="health_check",
                status="running",
                parameters={
                    "celery_task_id": health_check.request.id
                },
                pipeline_version="1.0.0",
                created_by_user_id_fk=None,
                started_at=datetime.utcnow()
            )
            db.add(processing_job)
            db.commit()
            db.refresh(processing_job)
            processing_job_id = processing_job.job_id
        
        app_logger.info(f"📝 创建健康检查任务记录: job_id={processing_job_id}")
        
        # 检查数据库连接
        from app.core.database import sync_engine
        from sqlalchemy import text
        with sync_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            db_status = "healthy" if result.fetchone() else "unhealthy"
        
        # 检查Redis连接
        from app.core.config import settings
        import redis
        try:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            redis_status = "healthy"
        except:
            redis_status = "unhealthy"
        
        health_info = {
            'timestamp': datetime.now().isoformat(),
            'database': db_status,
            'redis': redis_status,
            'overall': "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
        }
        
        app_logger.info(f"✅ 健康检查完成: {health_info}")
        
        # 更新processing_job记录为完成状态 - 同步版本
        with get_sync_session() as db:
            job = db.get(ProcessingJob, processing_job_id)
            if job:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.result_summary = f"健康检查完成: {health_info['overall']}"
                db.commit()
                app_logger.info(f"📝 更新健康检查任务记录为完成状态: job_id={processing_job_id}")
        
        return health_info
        
    except Exception as e:
        app_logger.error(f"❌ 健康检查失败: {e}")
        
        # 更新processing_job记录为失败状态 - 同步版本
        if processing_job_id:
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, processing_job_id)
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = f"健康检查失败: {e}"
                        db.commit()
                        app_logger.info(f"📝 更新健康检查任务记录为失败状态: job_id={processing_job_id}")
            except Exception as update_error:
                app_logger.error(f"❌ 更新健康检查任务记录失败: {update_error}")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'overall': 'unhealthy'
        } 