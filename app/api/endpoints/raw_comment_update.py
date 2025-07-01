"""
原始评论更新API端点
提供原始评论查询相关的API接口
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.services.raw_comment_update_service import raw_comment_update_service
from app.schemas.raw_comment_update import (
    RawCommentQueryRequest, RawCommentQueryResult
)
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