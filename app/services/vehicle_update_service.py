"""
车型数据更新服务
使用简化架构，支持多渠道解析器
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.logging import app_logger
from app.schemas.vehicle_update import (
    UpdateRequestSchema, UpdateResultSchema, UpdateTaskSchema, 
    ChannelListSchema
)
from app.models.vehicle_update import Channel, Vehicle, VehicleChannelDetail, ProcessingJob
from app.utils.channel_parsers import AutoHomeParser
from app.tasks.crawler_tasks import update_vehicle_data_async


class VehicleUpdateService:
    """
    车型数据更新服务
    负责协调各个渠道的车型数据更新
    """
    
    def __init__(self):
        self.logger = app_logger
        # 渠道ID到解析器类的映射（硬编码，用于内部逻辑）
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
    
    async def get_supported_channels(self) -> ChannelListSchema:
        """
        获取支持的渠道列表（从数据库读取）
        
        Returns:
            渠道列表schema
        """
        try:
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                # 从数据库查询channels表
                result = await db.execute(select(Channel))
                channels = result.scalars().all()
                
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
    
    async def update_vehicles(self, update_request: UpdateRequestSchema) -> UpdateTaskSchema:
        """
        更新指定渠道的车型数据
        
        Args:
            update_request: 更新请求
            
        Returns:
            更新任务信息
        """
        try:
            # 验证渠道ID（检查是否有对应的解析器）
            if update_request.channel_id not in self.parser_mapping:
                raise ValueError(f"不支持的渠道ID: {update_request.channel_id}")
            
            # 从数据库获取渠道信息
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Channel).where(Channel.channel_id == update_request.channel_id)
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    raise ValueError(f"渠道ID {update_request.channel_id} 在数据库中不存在")
                
                # 创建processing_job记录
                processing_job = ProcessingJob(
                    job_type="vehicle_updating",
                    status="pending",
                    parameters={
                        "channel_id": update_request.channel_id,
                        "force_update": update_request.force_update,
                        "filters": update_request.filters or {}
                    },
                    pipeline_version="1.0.0",
                    created_by_user_id_fk=None  # 暂时没有用户系统
                )
                db.add(processing_job)
                await db.flush()  # 获取job_id
                
                # 启动异步任务，传递job_id
                task = update_vehicle_data_async.delay(
                    channel_id=update_request.channel_id,
                    force_update=update_request.force_update,
                    filters=update_request.filters or {},
                    job_id=processing_job.job_id  # 传递job_id
                )
                
                await db.commit()
                
                # 创建任务记录
                task_schema = UpdateTaskSchema(
                    task_id=task.id,
                    channel_id=update_request.channel_id,
                    status="pending",
                    message=f"已启动 {channel.channel_name} 车型更新任务",
                    created_at=datetime.utcnow(),
                    job_id=processing_job.job_id
                )
            
            self.logger.info(f"车型更新任务已启动: task_id={task.id}, job_id={processing_job.job_id}")
            
            return task_schema
            
        except Exception as e:
            self.logger.error(f"启动车型更新任务失败: {e}")
            raise
    
    async def update_vehicles_direct(self, update_request: UpdateRequestSchema) -> UpdateResultSchema:
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
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import select
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Channel).where(Channel.channel_id == update_request.channel_id)
                )
                channel = result.scalar_one_or_none()
                
                if not channel:
                    raise ValueError(f"渠道ID {update_request.channel_id} 在数据库中不存在")
                
                # 创建解析器
                parser = self._create_parser(update_request.channel_id)
                
                self.logger.info(f"开始更新 {channel.channel_name} 车型数据")
                
                # 提取车型数据
                vehicles = await parser.extract_vehicles(update_request.channel_id)
                
                # 保存到数据库
                result = await self._save_vehicles_to_db(vehicles, update_request.channel_id, update_request.force_update)
                
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
    
    async def _save_vehicles_to_db(self, vehicles: List, channel_id: int, force_update: bool = False) -> Dict[str, int]:
        """
        保存车型数据到数据库
        
        Args:
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
            # 使用异步数据库会话
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                for vehicle_data in vehicles:
                    # 检查是否已存在 - 使用异步查询
                    from sqlalchemy import select
                    result = await db.execute(
                        select(VehicleChannelDetail).where(
                            VehicleChannelDetail.channel_id_fk == channel_id,
                            VehicleChannelDetail.identifier_on_channel == vehicle_data.get("vehicle_id")
                        )
                    )
                    existing_vehicle = result.scalar_one_or_none()
                    
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
                            temp_model_year=None,  # 年款信息暂时为空，后续可以从车型名称中解析
                            last_comment_crawled_at=None  # 新车型默认从未爬取过评论
                        )
                        db.add(new_vehicle)
                        new_count += 1
                
                await db.commit()
                
        except Exception as e:
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
        # temp_model_year保持原值，不强制更新为None


# 全局服务实例
vehicle_update_service = VehicleUpdateService() 