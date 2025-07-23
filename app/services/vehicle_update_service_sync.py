"""
车型数据更新服务 - 同步版本
专门用于Celery任务，避免异步冲突
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_sync_session
from app.core.logging import app_logger
from app.schemas.vehicle_update import (
    UpdateRequestSchema, UpdateResultSchema, ChannelListSchema
)
from app.models.vehicle_update import Channel, Vehicle, VehicleChannelDetail, ProcessingJob
from app.utils.channel_parsers import AutoHomeParser


class VehicleUpdateServiceSync:
    """
    车型数据更新服务 - 同步版本
    专门用于Celery任务，使用pymysql驱动
    """
    
    def __init__(self):
        self.logger = app_logger
        # 渠道ID到解析器类的映射
        self.parser_mapping = self._get_parser_mapping()
    
    def _get_parser_mapping(self) -> Dict[int, Any]:
        """
        获取渠道ID到解析器类的映射
        
        Returns:
            渠道ID到解析器类的映射字典
        """
        return {
            1: AutoHomeParser,  # 汽车之家
            # 可以在这里添加更多渠道解析器
        }
    
    def _create_parser(self, channel_id: int):
        """
        创建指定渠道的解析器
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            解析器实例
        """
        if channel_id not in self.parser_mapping:
            raise ValueError(f"不支持的渠道ID: {channel_id}")
        
        parser_class = self.parser_mapping[channel_id]
        return parser_class()
    
    def get_supported_channels(self) -> ChannelListSchema:
        """
        获取支持的渠道列表（从数据库读取）- 同步版本
        
        Returns:
            渠道列表schema
        """
        try:
            with get_sync_session() as db:
                # 从数据库查询channels表
                channels = db.query(Channel).all()
                
                # 构建返回的渠道信息
                channels_info = {}
                for channel in channels:
                    channels_info[channel.channel_id] = {
                        "channel_id": channel.channel_id,
                        "channel_name": channel.channel_name,
                        "channel_description": channel.channel_description
                    }
                
                return ChannelListSchema(
                    supported_channels=channels_info,
                    total_count=len(channels_info)
                )
                
        except Exception as e:
            self.logger.error(f"获取支持渠道列表失败: {e}")
            raise
    
    def update_vehicles_direct(self, update_request: UpdateRequestSchema) -> UpdateResultSchema:
        """
        直接更新车型数据（同步执行）
        
        Args:
            update_request: 更新请求
            
        Returns:
            更新结果
        """
        start_time = datetime.utcnow()
        
        try:
            # 验证渠道ID（检查是否有对应的解析器）
            if update_request.channel_id not in self.parser_mapping:
                raise ValueError(f"不支持的渠道ID: {update_request.channel_id}")
            
            # 从数据库获取渠道信息
            with get_sync_session() as db:
                channel = db.query(Channel).filter(
                    Channel.channel_id == update_request.channel_id
                ).first()
                
                if not channel:
                    raise ValueError(f"渠道ID {update_request.channel_id} 在数据库中不存在")
                
                # 创建解析器
                parser = self._create_parser(update_request.channel_id)
                
                self.logger.info(f"开始更新 {channel.channel_name} 车型数据")
                
                # 提取车型数据 - 同步调用
                vehicles = self._extract_vehicles_sync(parser, update_request.channel_id)
                
                # 保存到数据库
                result = self._save_vehicles_to_db(db, vehicles, update_request.channel_id, update_request.force_update)
                
                end_time = datetime.utcnow()
                
                # 创建更新结果
                update_result = UpdateResultSchema(
                    channel_id=update_request.channel_id,
                    channel_name=channel.channel_name,
                    total_crawled=len(vehicles),
                    new_vehicles=result["new_count"],
                    updated_vehicles=result["updated_count"],
                    unchanged_vehicles=result["unchanged_count"],
                    status="completed",
                    start_time=start_time,
                    end_time=end_time
                )
            
            self.logger.info(f"车型更新完成: {update_result}")
            
            return update_result
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_msg = f"车型更新失败: {e}"
            self.logger.error(error_msg)
            
            return UpdateResultSchema(
                channel_id=update_request.channel_id,
                channel_name="未知渠道",
                total_crawled=0,
                new_vehicles=0,
                updated_vehicles=0,
                unchanged_vehicles=0,
                status="failed",
                start_time=start_time,
                end_time=end_time,
                error_message=error_msg
            )
    
    def _extract_vehicles_sync(self, parser, channel_id: int) -> List[dict]:
        """
        同步方式提取车型数据
        
        Args:
            parser: 解析器实例
            channel_id: 渠道ID
            
        Returns:
            车型数据列表
        """
        # 这里需要根据具体的解析器实现同步版本
        # 暂时返回空列表，后续需要实现具体的同步爬取逻辑
        try:
            # 如果解析器有同步方法，使用同步方法
            if hasattr(parser, 'extract_vehicles_sync'):
                return parser.extract_vehicles_sync(channel_id)
            else:
                # 否则需要实现同步版本的爬取逻辑
                self.logger.warning(f"解析器 {parser.__class__.__name__} 暂未实现同步版本，返回空数据")
                return []
        except Exception as e:
            self.logger.error(f"提取车型数据失败: {e}")
            raise
    
    def _save_vehicles_to_db(self, db: Session, vehicles: List[dict], channel_id: int, force_update: bool = False) -> Dict[str, int]:
        """
        保存车型数据到数据库 - 同步版本
        
        Args:
            db: 数据库会话
            vehicles: 车型数据列表
            channel_id: 渠道ID
            force_update: 是否强制更新
            
        Returns:
            保存结果统计
        """
        new_count = 0
        updated_count = 0
        unchanged_count = 0
        
        try:
            for vehicle_data in vehicles:
                # 检查是否已存在
                existing_vehicle = db.query(VehicleChannelDetail).filter(
                    VehicleChannelDetail.channel_id_fk == channel_id,
                    VehicleChannelDetail.identifier_on_channel == vehicle_data.get("vehicle_id")
                ).first()
                
                if existing_vehicle:
                    # 检查是否需要更新
                    if force_update or self._needs_update(existing_vehicle, vehicle_data):
                        self._update_vehicle_record(existing_vehicle, vehicle_data)
                        updated_count += 1
                    else:
                        unchanged_count += 1
                else:
                    # 创建新记录
                    new_vehicle = VehicleChannelDetail(
                        channel_id_fk=channel_id,
                        identifier_on_channel=vehicle_data.get("vehicle_id"),
                        name_on_channel=vehicle_data.get("vehicle_name"),
                        url_on_channel=vehicle_data.get("vehicle_url"),
                        temp_brand_name=vehicle_data.get("brand_name"),
                        temp_series_name=vehicle_data.get("manufactor"),  # 厂商名称
                        temp_model_year=None,  # 年款信息暂时为空
                        last_comment_crawled_at=None  # 新车型默认从未爬取过评论
                    )
                    db.add(new_vehicle)
                    new_count += 1
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"保存车型数据失败: {e}")
            raise
        
        return {
            "new_count": new_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count
        }
    
    def _needs_update(self, existing_vehicle, new_vehicle_data) -> bool:
        """
        检查车型记录是否需要更新
        
        Args:
            existing_vehicle: 现有车型记录
            new_vehicle_data: 新的车型数据
            
        Returns:
            是否需要更新
        """
        return (
            existing_vehicle.name_on_channel != new_vehicle_data.get("vehicle_name") or
            existing_vehicle.url_on_channel != new_vehicle_data.get("vehicle_url") or
            existing_vehicle.temp_brand_name != new_vehicle_data.get("brand_name") or
            existing_vehicle.temp_series_name != new_vehicle_data.get("manufactor")
        )
    
    def _update_vehicle_record(self, existing_vehicle, new_vehicle_data):
        """
        更新车型记录
        
        Args:
            existing_vehicle: 现有车型记录
            new_vehicle_data: 新的车型数据
        """
        existing_vehicle.name_on_channel = new_vehicle_data.get("vehicle_name")
        existing_vehicle.url_on_channel = new_vehicle_data.get("vehicle_url")
        existing_vehicle.temp_brand_name = new_vehicle_data.get("brand_name")
        existing_vehicle.temp_series_name = new_vehicle_data.get("manufactor")  # 厂商名称


# 全局服务实例
vehicle_update_service_sync = VehicleUpdateServiceSync() 