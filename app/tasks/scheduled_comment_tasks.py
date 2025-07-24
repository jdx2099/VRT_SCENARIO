"""
定时评论爬取任务模块 - 同步版本
基于Celery Beat实现周期性评论爬取任务
"""
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import time


@celery_app.task(bind=True, max_retries=3)
def scheduled_comment_crawl(self, max_vehicles: int = 20):
    """
    定时评论爬取任务 - 同步版本
    
    每天晚上11点执行，从vehicle_channel_details表中找到：
    1. 优先选择last_comment_crawled_at为null的车型（未爬取过）
    2. 如果都爬取过，选择距离现在爬取时间最久的车型
    
    Args:
        max_vehicles: 最大爬取车型数量，默认20个
    """
    from app.core.database import get_sync_session
    from app.models.vehicle_update import ProcessingJob, VehicleChannelDetail
    from app.services.raw_comment_update_service_sync import raw_comment_update_service_sync
    from app.schemas.raw_comment_update import RawCommentCrawlRequest
    from sqlalchemy import asc
    
    try:
        app_logger.info(f"⏰ 开始执行定时评论爬取任务: max_vehicles={max_vehicles}")
        
        # 检查是否已有对应的ProcessingJob记录（避免重复创建）
        job_id = None
        celery_task_id = self.request.id
        
        try:
            with get_sync_session() as db:
                # 查找是否已有相同celery_task_id的记录
                existing_job = db.query(ProcessingJob).filter(
                    ProcessingJob.job_type == "scheduled_comment_crawl",
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
                        job_type="scheduled_comment_crawl",
                        status="running",
                        parameters={
                            "max_vehicles": max_vehicles,
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
                    app_logger.info(f"📝 创建新的定时评论爬取任务记录: job_id={job_id}")
            
        except Exception as e:
            app_logger.error(f"❌ 处理任务记录失败: {e}")
            raise
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': max_vehicles,
                'progress': 0,
                'status': '正在查询待爬取车型...',
                'max_vehicles': max_vehicles,
                'job_id': job_id,
                'celery_task_id': celery_task_id
            }
        )
        
        # 查询待爬取的车型 - 同步版本
        vehicles_to_crawl = []
        try:
            with get_sync_session() as db:
                # 首先查询未爬取过的车型（last_comment_crawled_at为null）
                uncrawled_vehicles = db.query(VehicleChannelDetail).filter(
                    VehicleChannelDetail.last_comment_crawled_at.is_(None)
                ).limit(max_vehicles).all()
                
                app_logger.info(f"🔍 找到 {len(uncrawled_vehicles)} 个未爬取过的车型")
                
                # 如果未爬取的车型数量不足，补充已爬取但时间最久的车型
                if len(uncrawled_vehicles) < max_vehicles:
                    remaining_count = max_vehicles - len(uncrawled_vehicles)
                    
                    # 查询已爬取但时间最久的车型
                    oldest_vehicles = db.query(VehicleChannelDetail).filter(
                        VehicleChannelDetail.last_comment_crawled_at.is_not(None)
                    ).order_by(asc(VehicleChannelDetail.last_comment_crawled_at)).limit(remaining_count).all()
                    
                    app_logger.info(f"🔍 补充 {len(oldest_vehicles)} 个最早爬取的车型")
                    
                    # 合并车型列表
                    vehicles_to_crawl = list(uncrawled_vehicles) + list(oldest_vehicles)
                else:
                    vehicles_to_crawl = list(uncrawled_vehicles)
                
                vehicles_to_crawl = vehicles_to_crawl[:max_vehicles]
                
        except Exception as e:
            app_logger.error(f"❌ 查询待爬取车型失败: {e}")
            raise
        
        if not vehicles_to_crawl:
            app_logger.warning("⚠️ 没有找到需要爬取的车型")
            
            # 更新任务状态为完成
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = "定时评论爬取完成: 没有找到需要爬取的车型"
                        db.commit()
            except Exception as e:
                app_logger.error(f"❌ 更新任务记录失败: {e}")
            
            return {
                'status': 'completed',
                'message': '没有找到需要爬取的车型',
                'total_vehicles': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': []
            }
        
        app_logger.info(f"📋 准备爬取 {len(vehicles_to_crawl)} 个车型的评论")
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(vehicles_to_crawl),
                'progress': 0,
                'status': f'开始爬取 {len(vehicles_to_crawl)} 个车型的评论',
                'vehicles_count': len(vehicles_to_crawl)
            }
        )
        
        # 执行爬取任务
        completed_vehicles = 0
        results = []
        
        for vehicle in vehicles_to_crawl:
            try:
                app_logger.info(f"🔄 开始爬取车型评论: {vehicle.name_on_channel} (ID: {vehicle.vehicle_channel_id})")
                
                # 创建爬取请求
                crawl_request = RawCommentCrawlRequest(
                    channel_id=vehicle.channel_id_fk,
                    identifier_on_channel=vehicle.identifier_on_channel,
                    max_pages=None  # 限制爬取前5页，可根据需要调整
                )
                
                # 执行爬取 - 使用同步服务
                crawl_result = raw_comment_update_service_sync.crawl_new_comments(crawl_request)
                
                # 更新车型的最后爬取时间
                try:
                    with get_sync_session() as db:
                        vehicle_detail = db.get(VehicleChannelDetail, vehicle.vehicle_channel_id)
                        if vehicle_detail:
                            vehicle_detail.last_comment_crawled_at = datetime.now(timezone.utc)
                            db.commit()
                            app_logger.info(f"📝 更新车型爬取时间: {vehicle.name_on_channel}")
                except Exception as e:
                    app_logger.error(f"❌ 更新车型爬取时间失败: {e}")
                
                vehicle_result = {
                    'vehicle_channel_id': vehicle.vehicle_channel_id,
                    'vehicle_name': vehicle.name_on_channel,
                    'channel_id': vehicle.channel_id_fk,
                    'identifier_on_channel': vehicle.identifier_on_channel,
                    'new_comments_count': crawl_result.new_comments_count,
                    'crawl_duration': crawl_result.crawl_duration,
                    'status': 'success'
                }
                results.append(vehicle_result)
                
                completed_vehicles += 1
                progress = int((completed_vehicles / len(vehicles_to_crawl)) * 100)
                
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': completed_vehicles,
                        'total': len(vehicles_to_crawl),
                        'progress': progress,
                        'status': f'已完成 {completed_vehicles}/{len(vehicles_to_crawl)} 个车型',
                        'results': results
                    }
                )
                
                app_logger.info(f"✅ 车型 {vehicle.name_on_channel} 爬取完成: 新增 {crawl_result.new_comments_count} 条评论")
                
                # 添加延迟，避免过于频繁的请求
                time.sleep(2)
                
            except Exception as e:
                app_logger.error(f"❌ 车型 {vehicle.name_on_channel} 爬取失败: {e}")
                
                vehicle_result = {
                    'vehicle_channel_id': vehicle.vehicle_channel_id,
                    'vehicle_name': vehicle.name_on_channel,
                    'channel_id': vehicle.channel_id_fk,
                    'identifier_on_channel': vehicle.identifier_on_channel,
                    'error': str(e),
                    'status': 'failed'
                }
                results.append(vehicle_result)
                
                completed_vehicles += 1
                progress = int((completed_vehicles / len(vehicles_to_crawl)) * 100)
                
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': completed_vehicles,
                        'total': len(vehicles_to_crawl),
                        'progress': progress,
                        'status': f'已完成 {completed_vehicles}/{len(vehicles_to_crawl)} 个车型',
                        'results': results
                    }
                )
        
        # 汇总统计
        total_new_comments = sum(r.get('new_comments_count', 0) for r in results if r.get('status') == 'success')
        success_count = len([r for r in results if r.get('status') == 'success'])
        failed_count = len([r for r in results if r.get('status') == 'failed'])
        
        app_logger.info(f"🎉 定时评论爬取任务完成: 成功{success_count}个车型, 失败{failed_count}个车型, 总计新增{total_new_comments}条评论")
        
        # 更新任务记录为完成状态
        try:
            with get_sync_session() as db:
                job = db.get(ProcessingJob, job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                    job.result_summary = f"定时评论爬取完成: 成功{success_count}/{len(vehicles_to_crawl)}个车型, 新增{total_new_comments}条评论"
                    db.commit()
                    app_logger.info(f"📝 更新定时评论爬取任务记录为完成状态: job_id={job_id}")
        except Exception as e:
            app_logger.error(f"❌ 更新任务记录失败: {e}")
        
        return {
            'status': 'completed',
            'total_vehicles': len(vehicles_to_crawl),
            'success_count': success_count,
            'failed_count': failed_count,
            'total_new_comments': total_new_comments,
            'results': results,
            'message': f'定时评论爬取完成: 成功{success_count}/{len(vehicles_to_crawl)}个车型'
        }
        
    except Exception as exc:
        app_logger.error(f"❌ 定时评论爬取任务失败: {exc}")
        
        # 更新任务记录为失败状态
        if job_id:
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = f"定时评论爬取任务失败: {exc}"
                        db.commit()
                        app_logger.info(f"📝 更新定时评论爬取任务记录为失败状态: job_id={job_id}")
            except Exception as update_error:
                app_logger.error(f"❌ 更新任务记录失败: {update_error}")
        
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'message': f'定时评论爬取任务失败: {exc}'
            }
        )
        raise exc


@celery_app.task(bind=True, max_retries=3)
def manual_comment_crawl(self, vehicle_channel_ids: List[int] = None, max_pages_per_vehicle: int = 10):
    """
    手动触发评论爬取任务 - 同步版本
    
    Args:
        vehicle_channel_ids: 要爬取的车型ID列表，如果为None则自动选择
        max_pages_per_vehicle: 每个车型最多爬取的页数
    """
    from app.core.database import get_sync_session
    from app.models.vehicle_update import ProcessingJob, VehicleChannelDetail
    from app.services.raw_comment_update_service_sync import raw_comment_update_service_sync
    from app.schemas.raw_comment_update import RawCommentCrawlRequest
    import time
    
    try:
        app_logger.info(f"🚀 开始执行手动评论爬取任务: vehicle_ids={vehicle_channel_ids}, max_pages={max_pages_per_vehicle}")
        
        # 创建processing_job记录
        job_id = None
        try:
            with get_sync_session() as db:
                processing_job = ProcessingJob(
                    job_type="manual_comment_crawl",
                    status="running",
                    parameters={
                        "vehicle_channel_ids": vehicle_channel_ids,
                        "max_pages_per_vehicle": max_pages_per_vehicle,
                        "celery_task_id": self.request.id
                    },
                    pipeline_version="1.0.0",
                    created_by_user_id_fk=None,
                    started_at=datetime.now(timezone.utc)
                )
                db.add(processing_job)
                db.commit()
                db.refresh(processing_job)
                job_id = processing_job.job_id
            
            app_logger.info(f"📝 创建手动评论爬取任务记录: job_id={job_id}")
            
        except Exception as e:
            app_logger.error(f"❌ 创建任务记录失败: {e}")
            raise
        
        # 获取要爬取的车型列表
        vehicles_to_crawl = []
        try:
            with get_sync_session() as db:
                if vehicle_channel_ids:
                    # 使用指定的车型ID列表
                    vehicles = db.query(VehicleChannelDetail).filter(
                        VehicleChannelDetail.vehicle_channel_id.in_(vehicle_channel_ids)
                    ).all()
                else:
                    # 自动选择未爬取或最早爬取的车型
                    vehicles = db.query(VehicleChannelDetail).filter(
                        VehicleChannelDetail.last_comment_crawled_at.is_(None)
                    ).limit(10).all()
                
                vehicles_to_crawl = list(vehicles)
                
        except Exception as e:
            app_logger.error(f"❌ 查询待爬取车型失败: {e}")
            raise
        
        if not vehicles_to_crawl:
            app_logger.warning("⚠️ 没有找到需要爬取的车型")
            
            # 更新任务状态为完成
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "completed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = "手动评论爬取完成: 没有找到需要爬取的车型"
                        db.commit()
            except Exception as e:
                app_logger.error(f"❌ 更新任务记录失败: {e}")
            
            return {
                'status': 'completed',
                'message': '没有找到需要爬取的车型',
                'total_vehicles': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': []
            }
        
        app_logger.info(f"📋 准备爬取 {len(vehicles_to_crawl)} 个车型的评论")
        
        # 更新任务状态
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(vehicles_to_crawl),
                'progress': 0,
                'status': f'开始爬取 {len(vehicles_to_crawl)} 个车型的评论',
                'vehicles_count': len(vehicles_to_crawl)
            }
        )
        
        # 执行爬取任务
        completed_vehicles = 0
        results = []
        
        for vehicle in vehicles_to_crawl:
            try:
                app_logger.info(f"🔄 开始爬取车型评论: {vehicle.name_on_channel} (ID: {vehicle.vehicle_channel_id})")
                
                # 创建爬取请求
                crawl_request = RawCommentCrawlRequest(
                    channel_id=vehicle.channel_id_fk,
                    identifier_on_channel=vehicle.identifier_on_channel,
                    max_pages=max_pages_per_vehicle
                )
                
                # 执行爬取 - 使用同步服务
                crawl_result = raw_comment_update_service_sync.crawl_new_comments(crawl_request)
                
                # 更新车型的最后爬取时间
                try:
                    with get_sync_session() as db:
                        vehicle_detail = db.get(VehicleChannelDetail, vehicle.vehicle_channel_id)
                        if vehicle_detail:
                            vehicle_detail.last_comment_crawled_at = datetime.now(timezone.utc)
                            db.commit()
                            app_logger.info(f"📝 更新车型爬取时间: {vehicle.name_on_channel}")
                except Exception as e:
                    app_logger.error(f"❌ 更新车型爬取时间失败: {e}")
                
                vehicle_result = {
                    'vehicle_channel_id': vehicle.vehicle_channel_id,
                    'vehicle_name': vehicle.name_on_channel,
                    'channel_id': vehicle.channel_id_fk,
                    'identifier_on_channel': vehicle.identifier_on_channel,
                    'new_comments_count': crawl_result.new_comments_count,
                    'crawl_duration': crawl_result.crawl_duration,
                    'status': 'success'
                }
                results.append(vehicle_result)
                
                completed_vehicles += 1
                progress = int((completed_vehicles / len(vehicles_to_crawl)) * 100)
                
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': completed_vehicles,
                        'total': len(vehicles_to_crawl),
                        'progress': progress,
                        'status': f'已完成 {completed_vehicles}/{len(vehicles_to_crawl)} 个车型',
                        'results': results
                    }
                )
                
                app_logger.info(f"✅ 车型 {vehicle.name_on_channel} 爬取完成: 新增 {crawl_result.new_comments_count} 条评论")
                
                # 添加延迟，避免过于频繁的请求
                time.sleep(2)
                
            except Exception as e:
                app_logger.error(f"❌ 车型 {vehicle.name_on_channel} 爬取失败: {e}")
                
                vehicle_result = {
                    'vehicle_channel_id': vehicle.vehicle_channel_id,
                    'vehicle_name': vehicle.name_on_channel,
                    'channel_id': vehicle.channel_id_fk,
                    'identifier_on_channel': vehicle.identifier_on_channel,
                    'error': str(e),
                    'status': 'failed'
                }
                results.append(vehicle_result)
                
                completed_vehicles += 1
                progress = int((completed_vehicles / len(vehicles_to_crawl)) * 100)
                
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': completed_vehicles,
                        'total': len(vehicles_to_crawl),
                        'progress': progress,
                        'status': f'已完成 {completed_vehicles}/{len(vehicles_to_crawl)} 个车型',
                        'results': results
                    }
                )
        
        # 汇总统计
        total_new_comments = sum(r.get('new_comments_count', 0) for r in results if r.get('status') == 'success')
        success_count = len([r for r in results if r.get('status') == 'success'])
        failed_count = len([r for r in results if r.get('status') == 'failed'])
        
        app_logger.info(f"🎉 手动评论爬取任务完成: 成功{success_count}个车型, 失败{failed_count}个车型, 总计新增{total_new_comments}条评论")
        
        # 更新任务记录为完成状态
        try:
            with get_sync_session() as db:
                job = db.get(ProcessingJob, job_id)
                if job:
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
                    job.result_summary = f"手动评论爬取完成: 成功{success_count}/{len(vehicles_to_crawl)}个车型, 新增{total_new_comments}条评论"
                    db.commit()
                    app_logger.info(f"📝 更新手动评论爬取任务记录为完成状态: job_id={job_id}")
        except Exception as e:
            app_logger.error(f"❌ 更新任务记录失败: {e}")
        
        return {
            'status': 'completed',
            'total_vehicles': len(vehicles_to_crawl),
            'success_count': success_count,
            'failed_count': failed_count,
            'total_new_comments': total_new_comments,
            'results': results,
            'message': f'手动评论爬取完成: 成功{success_count}/{len(vehicles_to_crawl)}个车型'
        }
        
    except Exception as exc:
        app_logger.error(f"❌ 手动评论爬取任务失败: {exc}")
        
        # 更新任务记录为失败状态
        if job_id:
            try:
                with get_sync_session() as db:
                    job = db.get(ProcessingJob, job_id)
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.utcnow()
                        job.result_summary = f"手动评论爬取任务失败: {exc}"
                        db.commit()
                        app_logger.info(f"📝 更新手动评论爬取任务记录为失败状态: job_id={job_id}")
            except Exception as update_error:
                app_logger.error(f"❌ 更新任务记录失败: {update_error}")
        
        current_task.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'message': f'手动评论爬取任务失败: {exc}'
            }
        )
        raise exc 