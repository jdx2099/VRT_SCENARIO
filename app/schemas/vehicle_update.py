"""
车型数据更新相关的数据模型和校验
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ChannelType(str, Enum):
    """渠道类型枚举"""
    AUTOHOME = "autohome"
    DONGCHEDI = "dongchedi"


class VehicleInfoSchema(BaseModel):
    """车型信息schema"""
    vehicle_id: str = Field(..., description="渠道内车型ID")
    vehicle_name: str = Field(..., description="车型名称")
    brand_id: str = Field(..., description="品牌ID")
    brand_name: str = Field(..., description="品牌名称")
    manufacturer: str = Field(..., description="制造商/厂商")
    vehicle_url: Optional[str] = Field(None, description="车型详情URL")
    
    @validator('vehicle_name', 'brand_name', 'manufacturer')
    def names_must_not_be_empty(cls, v):
        if not v or v.strip() == '':
            raise ValueError('名称不能为空')
        return v.strip()


class ChannelConfigSchema(BaseModel):
    """渠道配置schema"""
    channel_id: int = Field(..., description="渠道ID")
    channel_name: str = Field(..., description="渠道名称")
    channel_description: Optional[str] = Field(None, description="渠道描述")
    url_config: Dict[str, Any] = Field(..., description="URL配置")
    
    @validator('url_config')
    def validate_url_config(cls, v):
        if not isinstance(v, dict):
            raise ValueError('URL配置必须是字典格式')
        return v


class UpdateRequestSchema(BaseModel):
    """更新请求schema"""
    channel_id: int = Field(..., ge=1, description="渠道ID，必须大于0")
    force_update: bool = Field(False, description="是否强制更新")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")


class UpdateResultSchema(BaseModel):
    """更新结果schema"""
    channel_id: int
    channel_name: str
    total_crawled: int = Field(..., ge=0, description="总爬取数量")
    new_vehicles: int = Field(..., ge=0, description="新增车型数量")
    updated_vehicles: int = Field(..., ge=0, description="更新车型数量")
    unchanged_vehicles: int = Field(..., ge=0, description="无变化车型数量")
    status: str = Field(..., description="更新状态")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    error_message: Optional[str] = Field(None, description="错误信息")


class UpdateTaskSchema(BaseModel):
    """更新任务schema"""
    task_id: str = Field(..., description="任务ID")
    channel_id: int
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="任务消息")
    created_at: datetime = Field(..., description="创建时间")


class ChannelListSchema(BaseModel):
    """支持的渠道列表schema"""
    supported_channels: Dict[int, Dict[str, Any]]
    total_count: int = Field(..., ge=0, description="渠道总数")


class VehicleStatsSchema(BaseModel):
    """车型统计schema"""
    channel_id: int
    total_vehicles: int = Field(..., ge=0, description="总车型数")
    brands_count: int = Field(..., ge=0, description="品牌数量")
    manufacturers_count: int = Field(..., ge=0, description="厂商数量")
    last_update_time: Optional[datetime] = Field(None, description="最后更新时间")


class ErrorResponseSchema(BaseModel):
    """错误响应schema"""
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    detail: Optional[str] = Field(None, description="详细信息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间") 