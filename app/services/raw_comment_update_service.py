"""
原始评论更新服务
处理原始评论查询和更新相关业务逻辑
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import app_logger
from app.models.vehicle_update import VehicleChannelDetail
from app.models.raw_comment_update import RawComment
from app.schemas.raw_comment_update import (
    RawCommentQueryRequest, RawCommentQueryResult, 
    VehicleChannelInfo
)


class RawCommentUpdateService:
    """
    原始评论更新服务类
    负责处理原始评论相关的业务逻辑
    """
    
    def __init__(self):
        self.logger = app_logger
    
    async def get_vehicle_raw_comment_ids(self, query_request: RawCommentQueryRequest) -> RawCommentQueryResult:
        """
        根据渠道ID和车型标识获取该车型下的所有原始评论ID
        
        Args:
            query_request: 查询请求参数
            
        Returns:
            查询结果，包含车型信息和评论ID列表
            
        Raises:
            ValueError: 当车型不存在时
        """
        try:
            async with AsyncSessionLocal() as db:
                # 第一步：根据channel_id和identifier_on_channel查询车型渠道详情
                self.logger.info(f"🔍 查询车型: channel_id={query_request.channel_id}, identifier={query_request.identifier_on_channel}")
                
                vehicle_result = await db.execute(
                    select(VehicleChannelDetail).where(
                        VehicleChannelDetail.channel_id_fk == query_request.channel_id,
                        VehicleChannelDetail.identifier_on_channel == query_request.identifier_on_channel
                    )
                )
                vehicle_detail = vehicle_result.scalar_one_or_none()
                
                if not vehicle_detail:
                    raise ValueError(f"未找到匹配的车型: channel_id={query_request.channel_id}, identifier={query_request.identifier_on_channel}")
                
                self.logger.info(f"✅ 找到车型: vehicle_channel_id={vehicle_detail.vehicle_channel_id}, name={vehicle_detail.name_on_channel}")
                
                # 第二步：使用vehicle_channel_id查询所有相关的原始评论ID
                comment_result = await db.execute(
                    select(RawComment.raw_comment_id).where(
                        RawComment.vehicle_channel_id_fk == vehicle_detail.vehicle_channel_id
                    ).order_by(RawComment.raw_comment_id)
                )
                raw_comment_ids = comment_result.scalars().all()
                
                self.logger.info(f"📊 找到 {len(raw_comment_ids)} 条原始评论")
                
                # 构建车型渠道信息
                vehicle_channel_info = VehicleChannelInfo(
                    vehicle_channel_id=vehicle_detail.vehicle_channel_id,
                    channel_id=vehicle_detail.channel_id_fk,
                    identifier_on_channel=vehicle_detail.identifier_on_channel,
                    name_on_channel=vehicle_detail.name_on_channel,
                    url_on_channel=vehicle_detail.url_on_channel,
                    temp_brand_name=vehicle_detail.temp_brand_name,
                    temp_series_name=vehicle_detail.temp_series_name,
                    temp_model_year=vehicle_detail.temp_model_year
                )
                
                # 构建查询结果
                result = RawCommentQueryResult(
                    vehicle_channel_info=vehicle_channel_info,
                    raw_comment_ids=list(raw_comment_ids),
                    total_comments=len(raw_comment_ids)
                )
                
                return result
                
        except Exception as e:
            self.logger.error(f"❌ 查询车型原始评论ID失败: {e}")
            raise
    
    async def get_vehicle_by_channel_and_identifier(self, channel_id: int, identifier_on_channel: str) -> Optional[VehicleChannelDetail]:
        """
        根据渠道ID和车型标识获取车型详情
        
        Args:
            channel_id: 渠道ID
            identifier_on_channel: 车型在渠道上的标识
            
        Returns:
            车型渠道详情对象，如果不存在则返回None
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(VehicleChannelDetail).where(
                        VehicleChannelDetail.channel_id_fk == channel_id,
                        VehicleChannelDetail.identifier_on_channel == identifier_on_channel
                    )
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"❌ 查询车型详情失败: {e}")
            raise
    
    async def count_raw_comments_by_vehicle_channel_id(self, vehicle_channel_id: int) -> int:
        """
        统计指定车型渠道详情ID下的原始评论数量
        
        Args:
            vehicle_channel_id: 车型渠道详情ID
            
        Returns:
            评论数量
        """
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import func
                result = await db.execute(
                    select(func.count(RawComment.raw_comment_id)).where(
                        RawComment.vehicle_channel_id_fk == vehicle_channel_id
                    )
                )
                return result.scalar()
        except Exception as e:
            self.logger.error(f"❌ 统计原始评论数量失败: {e}")
            raise


# 全局服务实例
raw_comment_update_service = RawCommentUpdateService() 