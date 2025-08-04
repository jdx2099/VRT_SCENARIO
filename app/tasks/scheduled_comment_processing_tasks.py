"""
定时评论语义处理任务模块 - 同步版本
基于Celery Beat实现周期性评论语义分析和结构化提取任务
"""
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from datetime import datetime, timezone
from typing import Dict, Optional
import time


@celery_app.task(bind=True, max_retries=3)
def scheduled_comment_semantic_processing(self, batch_size: int = 20):
    """
    定时评论语义处理任务 - 同步版本
    
    从raw_comments表中找到processing_status为'new'的评论，
    每次处理指定数量的评论，进行语义相似度检索和结构化提取
    
    Args:
        batch_size: 每批处理的评论数量，默认20条
    """
    from app.core.database import get_sync_session
    from app.models.vehicle_update import ProcessingJob
    from app.services.comment_processing_service import comment_processing_service
    
    try:
        app_logger.info(f"⏰ 开始执行定时评论语义处理任务: batch_size={batch_size}")
        
        # 检查是否已有对应的ProcessingJob记录（避免重复创建）
        job_id = None
        celery_task_id = self.request.id
        
        try:
            with get_sync_session() as db:
                # 查找是否已有相同celery_task_id的记录
                existing_job = db.query(ProcessingJob).filter(
                    ProcessingJob.job_type == "scheduled_comment_semantic_processing",
                    ProcessingJob.parameters.contains({"celery_task_id": celery_task_id})
                ).first()
                
                if existing_job:
                    # 如果找到现有记录，使用它
                    job_id = existing_job.job_id
                    app_logger.info(f"🔄 发现现有任务记录，继续执行: job_id={job_id}, celery_task_id={celery_task_id}")
                    
                    # 如果状态是running，说明任务被中断后重新启动
                    if existing_job.status == "running":
                        app_logger.info(f"🔄 任务被中断后重新启动，继续执行: job_id={job_id}")
                else:
                    # 创建新的任务记录
                    processing_job = ProcessingJob(
                        job_type="scheduled_comment_semantic_processing",
                        status="running",
                        parameters={
                            "batch_size": batch_size,
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
                    app_logger.info(f"📝 创建新的评论语义处理任务记录: job_id={job_id}")
            
        except Exception as e:
            app_logger.error(f"❌ 处理任务记录失败: {e}")
            raise
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': batch_size,
                'progress': 0,
                'status': '正在查询待处理评论...',
                'batch_size': batch_size,
                'job_id': job_id,
                'celery_task_id': celery_task_id
            }
        )
        
        # 获取处理前的统计信息
        try:
            pre_stats = comment_processing_service.get_processing_statistics()
            app_logger.info(f"📊 处理前统计: {pre_stats}")
        except Exception as e:
            app_logger.warning(f"⚠️ 获取处理前统计失败: {e}")
            pre_stats = {}
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': batch_size,
                'progress': 0,
                'status': f'开始处理 {batch_size} 条评论的语义分析',
                'pre_stats': pre_stats
            }
        )
        
        # 执行批量处理
        start_time = time.time()
        
        try:
            processing_result = comment_processing_service.process_batch_comments(
                limit=batch_size,
                job_id=job_id
            )
            
            processing_duration = time.time() - start_time
            
            # 获取处理后的统计信息
            try:
                post_stats = comment_processing_service.get_processing_statistics()
                app_logger.info(f"📊 处理后统计: {post_stats}")
            except Exception as e:
                app_logger.warning(f"⚠️ 获取处理后统计失败: {e}")
                post_stats = {}
            
            # 更新任务状态为完成
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "completed"
                        job.completed_at = datetime.now(timezone.utc)
                        job.result_summary = f"评论语义处理完成: 处理{processing_result['processed_count']}条，跳过{processing_result['skipped_count']}条，失败{processing_result['failed_count']}条，生成{processing_result['total_results']}条结果"
                        db.commit()
            except Exception as e:
                app_logger.error(f"❌ 更新任务记录失败: {e}")
            
            # 构建最终结果
            final_result = {
                'status': 'completed',
                'job_id': job_id,
                'celery_task_id': celery_task_id,
                'processing_duration': processing_duration,
                'batch_size': batch_size,
                'processing_result': processing_result,
                'pre_stats': pre_stats,
                'post_stats': post_stats,
                'message': f"评论语义处理任务完成: 处理了{processing_result['total_comments']}条评论，生成{processing_result['total_results']}条结构化结果"
            }
            
            app_logger.info(f"✅ 定时评论语义处理任务完成: {final_result}")
            
            # 更新最终任务状态
            current_task.update_state(
                state='SUCCESS',
                meta=final_result
            )
            
            return final_result
            
        except Exception as e:
            app_logger.error(f"❌ 批量处理评论失败: {e}")
            
            # 更新任务状态为失败
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.now(timezone.utc)
                        job.result_summary = f"评论语义处理失败: {str(e)}"
                        db.commit()
            except Exception as update_e:
                app_logger.error(f"❌ 更新失败任务记录失败: {update_e}")
            
            raise
        
    except Exception as e:
        app_logger.error(f"❌ 定时评论语义处理任务失败: {e}")
        
        # 更新任务状态
        current_task.update_state(
            state='FAILURE',
            meta={
                'status': 'failed',
                'error': str(e),
                'message': f'定时评论语义处理任务失败: {e}'
            }
        )
        
        raise


@celery_app.task(bind=True)
def get_comment_processing_status(self, job_id: Optional[int] = None):
    """
    获取评论处理状态统计
    
    Args:
        job_id: 可选的任务ID，用于获取特定任务的详情
    """
    from app.core.database import get_sync_session
    from app.models.vehicle_update import ProcessingJob
    from app.services.comment_processing_service import comment_processing_service
    
    try:
        app_logger.info(f"📊 获取评论处理状态统计: job_id={job_id}")
        
        # 获取基本统计信息
        stats = comment_processing_service.get_processing_statistics()
        
        result = {
            'status': 'success',
            'statistics': stats,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # 如果指定了job_id，获取任务详情
        if job_id:
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        result['job_details'] = {
                            'job_id': job.job_id,
                            'job_type': job.job_type,
                            'status': job.status,
                            'parameters': job.parameters,
                            'created_at': job.created_at.isoformat() if job.created_at else None,
                            'started_at': job.started_at.isoformat() if job.started_at else None,
                            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                            'result_summary': job.result_summary,
                            'pipeline_version': job.pipeline_version
                        }
                    else:
                        result['job_details'] = None
                        result['message'] = f"未找到任务ID: {job_id}"
            except Exception as e:
                app_logger.error(f"❌ 获取任务详情失败: {e}")
                result['job_details'] = None
                result['error'] = f"获取任务详情失败: {e}"
        
        app_logger.info(f"✅ 评论处理状态统计获取完成: {result}")
        return result
        
    except Exception as e:
        app_logger.error(f"❌ 获取评论处理状态失败: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'message': f'获取评论处理状态失败: {e}'
        }