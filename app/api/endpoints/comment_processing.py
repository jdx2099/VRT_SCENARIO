"""
评论语义处理API端点
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.tasks.scheduled_comment_processing_tasks import (
    scheduled_comment_semantic_processing,
    get_comment_processing_status
)
from app.services.semantic_search_service import semantic_search_service
from app.core.logging import app_logger

router = APIRouter(prefix="/comment-processing", tags=["评论语义处理"])


class CommentProcessingRequest(BaseModel):
    """评论处理请求模型"""
    batch_size: int = Field(default=20, ge=1, le=100, description="批处理大小，1-100之间")


class CommentProcessingResponse(BaseModel):
    """评论处理响应模型"""
    task_id: str = Field(description="Celery任务ID")
    message: str = Field(description="响应消息")
    batch_size: int = Field(description="批处理大小")


class ProcessingStatusResponse(BaseModel):
    """处理状态响应模型"""
    status: str = Field(description="状态")
    statistics: Dict[str, Any] = Field(description="统计信息")
    timestamp: str = Field(description="时间戳")
    job_details: Optional[Dict[str, Any]] = Field(default=None, description="任务详情")


class SemanticSearchRequest(BaseModel):
    """语义搜索请求模型"""
    comment_text: str = Field(description="评论文本")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量，1-20之间")


class SemanticSearchResult(BaseModel):
    """语义搜索结果模型"""
    feature_code: str = Field(description="功能代码")
    feature_name: str = Field(description="功能名称")
    feature_description: str = Field(description="功能描述")
    similarity_score: float = Field(description="相似度分数")


class SemanticSearchResponse(BaseModel):
    """语义搜索响应模型"""
    query_text: str = Field(description="查询文本")
    results: list[SemanticSearchResult] = Field(description="搜索结果")
    total_count: int = Field(description="结果总数")


@router.post("/start-semantic-processing", response_model=CommentProcessingResponse)
async def start_semantic_processing(request: CommentProcessingRequest):
    """
    启动评论语义处理任务
    
    从raw_comments表中找到processing_status为'new'的评论，
    进行语义相似度检索和结构化提取
    """
    try:
        app_logger.info(f"🚀 启动评论语义处理任务: batch_size={request.batch_size}")
        
        # 启动异步任务
        task = scheduled_comment_semantic_processing.delay(batch_size=request.batch_size)
        
        response = CommentProcessingResponse(
            task_id=task.id,
            message=f"评论语义处理任务已启动，批处理大小: {request.batch_size}",
            batch_size=request.batch_size
        )
        
        app_logger.info(f"✅ 评论语义处理任务启动成功: task_id={task.id}")
        return response
        
    except Exception as e:
        app_logger.error(f"❌ 启动评论语义处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")


@router.get("/status", response_model=ProcessingStatusResponse)
async def get_processing_status(job_id: Optional[int] = None):
    """
    获取评论处理状态统计
    
    Args:
        job_id: 可选的任务ID，用于获取特定任务的详情
    """
    try:
        app_logger.info(f"📊 获取评论处理状态: job_id={job_id}")
        
        # 启动状态查询任务
        task = get_comment_processing_status.delay(job_id=job_id)
        result = task.get(timeout=30)  # 30秒超时
        
        if result.get('status') == 'success':
            response = ProcessingStatusResponse(
                status=result['status'],
                statistics=result['statistics'],
                timestamp=result['timestamp'],
                job_details=result.get('job_details')
            )
            
            app_logger.info(f"✅ 评论处理状态获取成功")
            return response
        else:
            app_logger.error(f"❌ 获取评论处理状态失败: {result}")
            raise HTTPException(status_code=500, detail=result.get('message', '获取状态失败'))
        
    except Exception as e:
        app_logger.error(f"❌ 获取评论处理状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取特定Celery任务的状态
    
    Args:
        task_id: Celery任务ID
    """
    try:
        from app.tasks.celery_app import celery_app
        
        app_logger.info(f"📋 获取任务状态: task_id={task_id}")
        
        # 获取任务结果
        task_result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None,
            "info": task_result.info if hasattr(task_result, 'info') else None
        }
        
        app_logger.info(f"✅ 任务状态获取成功: {response}")
        return response
        
    except Exception as e:
        app_logger.error(f"❌ 获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.post("/manual-processing")
async def manual_processing(request: CommentProcessingRequest):
    """
    手动触发评论语义处理（同步执行，用于测试）
    
    注意：这是同步执行，可能会超时，建议用于小批量测试
    """
    try:
        from app.services.comment_processing_service import comment_processing_service
        
        app_logger.info(f"🔧 手动触发评论语义处理: batch_size={request.batch_size}")
        
        # 直接执行处理
        result = comment_processing_service.process_batch_comments(
            limit=request.batch_size
        )
        
        response = {
            "status": "completed",
            "message": f"手动处理完成: 处理了{result['total_comments']}条评论",
            "result": result
        }
        
        app_logger.info(f"✅ 手动评论语义处理完成: {response}")
        return response
        
    except Exception as e:
        app_logger.error(f"❌ 手动评论语义处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动处理失败: {str(e)}")


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索API
    
    根据输入的评论文本，搜索最相似的产品功能
    """
    try:
        app_logger.info(f"🔍 执行语义搜索: {request.comment_text[:50]}...")
        
        # 执行语义搜索
        search_results = semantic_search_service.search_similar_features(
            request.comment_text, 
            k=request.top_k
        )
        
        # 转换结果格式
        results = []
        for doc, score in search_results:
            result = SemanticSearchResult(
                feature_code=doc.metadata.get("id", ""),
                feature_name=doc.metadata.get("功能模块名称", ""),
                feature_description=doc.page_content,
                similarity_score=float(score)
            )
            results.append(result)
        
        response = SemanticSearchResponse(
            query_text=request.comment_text,
            results=results,
            total_count=len(results)
        )
        
        app_logger.info(f"✅ 语义搜索完成: 找到{len(results)}个相似功能")
        return response
        
    except Exception as e:
        app_logger.error(f"❌ 语义搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"语义搜索失败: {str(e)}")