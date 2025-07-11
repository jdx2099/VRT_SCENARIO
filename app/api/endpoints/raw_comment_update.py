"""
原始评论更新API端点
提供原始评论查询相关的API接口
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.raw_comment_update_service import raw_comment_update_service
from app.schemas.raw_comment_update import (
    RawCommentQueryRequest, RawCommentQueryResult,
    RawCommentCrawlRequest, RawCommentCrawlResult, RawCommentCrawlTaskSchema
)
from app.schemas.vehicle_update import ProcessingJobSchema
from app.core.logging import app_logger

router = APIRouter(prefix="/raw-comments", tags=["原始评论更新"])


@router.post("/query", response_model=RawCommentQueryResult)
async def query_raw_comment_ids(query_request: RawCommentQueryRequest) -> RawCommentQueryResult:
    """
    查询指定车型下的所有原始评论ID
    
    根据渠道ID和车型标识，查询vehicle_channel_details表获取车型信息，
    然后查询raw_comments表获取该车型下的所有原始评论ID列表。
    
    Args:
        query_request: 查询请求参数
        
    Returns:
        查询结果，包含车型信息和评论ID列表
    """
    try:
        app_logger.info(f"🔍 开始查询原始评论ID: channel_id={query_request.channel_id}, identifier={query_request.identifier_on_channel}")
        
        # 调用服务层处理业务逻辑
        result = await raw_comment_update_service.get_vehicle_raw_comment_ids(query_request)
        
        app_logger.info(f"✅ 查询完成: 找到 {result.total_comments} 条评论")
        
        return result
        
    except ValueError as e:
        app_logger.error(f"❌ 参数验证失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 查询原始评论ID失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/vehicle/{channel_id}/{identifier}/count")
async def get_vehicle_comment_count(channel_id: int, identifier: str) -> Dict[str, Any]:
    """
    获取指定车型的评论数量
    
    Args:
        channel_id: 渠道ID
        identifier: 车型在渠道上的标识
        
    Returns:
        评论数量信息
    """
    try:
        app_logger.info(f"📊 查询车型评论数量: channel_id={channel_id}, identifier={identifier}")
        
        # 先获取车型信息
        vehicle_detail = await raw_comment_update_service.get_vehicle_by_channel_and_identifier(
            channel_id, identifier
        )
        
        if not vehicle_detail:
            raise ValueError(f"未找到匹配的车型: channel_id={channel_id}, identifier={identifier}")
        
        # 统计评论数量
        comment_count = await raw_comment_update_service.count_raw_comments_by_vehicle_channel_id(
            vehicle_detail.vehicle_channel_id
        )
        
        result = {
            "channel_id": channel_id,
            "identifier_on_channel": identifier,
            "vehicle_channel_id": vehicle_detail.vehicle_channel_id,
            "vehicle_name": vehicle_detail.name_on_channel,
            "comment_count": comment_count
        }
        
        app_logger.info(f"✅ 统计完成: {comment_count} 条评论")
        
        return result
        
    except ValueError as e:
        app_logger.error(f"❌ 参数验证失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 统计评论数量失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计失败: {str(e)}")


@router.post("/crawl", response_model=RawCommentCrawlTaskSchema)
async def crawl_new_comments_async(crawl_request: RawCommentCrawlRequest) -> RawCommentCrawlTaskSchema:
    """
    异步爬取新的原始评论
    
    这个接口会：
    1. 验证车型信息存在性
    2. 启动Celery异步任务进行评论爬取
    3. 立即返回任务ID和状态信息
    4. 前端可通过任务状态接口查询进度
    
    Args:
        crawl_request: 爬取请求参数，包含渠道ID、车型标识和可选的最大页数限制
        
    Returns:
        异步任务信息，包含task_id用于后续状态查询
    """
    try:
        app_logger.info(f"🚀 启动原始评论异步爬取: {crawl_request}")
        
        result = await raw_comment_update_service.crawl_new_comments_async(crawl_request)
        
        app_logger.info(f"✅ 原始评论爬取任务已启动: task_id={result.task_id}")
        return result
        
    except ValueError as e:
        app_logger.warning(f"⚠️ 原始评论爬取启动失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 原始评论爬取任务启动错误: {e}")
        raise HTTPException(status_code=500, detail="启动异步任务失败")


@router.post("/crawl/direct", response_model=RawCommentCrawlResult)
async def crawl_new_comments_direct(crawl_request: RawCommentCrawlRequest) -> RawCommentCrawlResult:
    """
    直接爬取新的原始评论（同步执行）
    
    这个接口会直接执行爬取过程并返回完整结果，主要用于：
    - 开发和测试环境
    - 小规模数据验证
    - 调试和排错
    
    Args:
        crawl_request: 爬取请求参数，包含渠道ID、车型标识和可选的最大页数限制
        
    Returns:
        爬取结果，包含车型信息、爬取统计和新增评论列表
    """
    try:
        app_logger.info(f"🔄 开始直接爬取原始评论: {crawl_request}")
        
        result = await raw_comment_update_service.crawl_new_comments(crawl_request)
        
        app_logger.info(f"✅ 原始评论直接爬取完成: 新增 {result.new_comments_count} 条评论")
        return result
        
    except ValueError as e:
        app_logger.warning(f"⚠️ 原始评论直接爬取失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 原始评论直接爬取系统错误: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/jobs/{job_id}", response_model=ProcessingJobSchema)
async def get_processing_job(job_id: int) -> ProcessingJobSchema:
    """
    获取ProcessingJob详情
    
    Args:
        job_id: 任务ID
        
    Returns:
        ProcessingJob详情
    """
    try:
        app_logger.info(f"🔍 查询ProcessingJob: job_id={job_id}")
        
        from app.core.database import AsyncSessionLocal
        from app.models.vehicle_update import ProcessingJob
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProcessingJob).where(ProcessingJob.job_id == job_id)
            )
            processing_job = result.scalar_one_or_none()
            
            if not processing_job:
                raise ValueError(f"未找到ProcessingJob: job_id={job_id}")
            
            job_schema = ProcessingJobSchema(
                job_id=processing_job.job_id,
                job_type=processing_job.job_type,
                parameters=processing_job.parameters,
                status=processing_job.status,
                pipeline_version=processing_job.pipeline_version,
                created_at=processing_job.created_at,
                started_at=processing_job.started_at,
                completed_at=processing_job.completed_at,
                result_summary=processing_job.result_summary
            )
            
            app_logger.info(f"✅ 查询ProcessingJob完成: {job_schema.status}")
            return job_schema
            
    except ValueError as e:
        app_logger.error(f"❌ 参数验证失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        app_logger.error(f"❌ 查询ProcessingJob失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/tasks/{task_id}/status")
async def get_crawl_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取原始评论爬取任务状态
    
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
            "error": str(task.info) if task.status == "FAILURE" else None,
            "progress": task.info.get("progress", 0) if isinstance(task.info, dict) else 0
        }
        
    except Exception as e:
        app_logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")