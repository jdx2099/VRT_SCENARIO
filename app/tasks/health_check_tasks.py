"""
系统健康检查任务模块
"""
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from datetime import datetime, timezone


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
                started_at=datetime.now(timezone.utc)
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
                job.completed_at = datetime.now(timezone.utc)
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
                        job.completed_at = datetime.now(timezone.utc)
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