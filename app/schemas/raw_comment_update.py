"""
原始评论更新相关的数据校验模式
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RawCommentQueryRequest(BaseModel):
    """查询原始评论请求模式"""
    channel_id: int = Field(..., description="渠道ID", ge=1)
    identifier_on_channel: str = Field(..., description="车型在渠道上的标识", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": 1,
                "identifier_on_channel": "s3170"
            }
        }


class VehicleChannelInfo(BaseModel):
    """车型渠道信息模式"""
    vehicle_channel_id: int = Field(..., description="车型渠道详情ID")
    channel_id: int = Field(..., description="渠道ID")
    identifier_on_channel: str = Field(..., description="车型在渠道上的标识")
    name_on_channel: str = Field(..., description="车型在渠道上的名称")
    url_on_channel: Optional[str] = Field(None, description="车型在渠道上的URL")
    temp_brand_name: Optional[str] = Field(None, description="临时品牌名称")
    temp_series_name: Optional[str] = Field(None, description="临时车系名称")
    temp_model_year: Optional[str] = Field(None, description="临时年款")
    last_comment_crawled_at: Optional[datetime] = Field(None, description="上次成功爬取评论的时间")
    
    class Config:
        from_attributes = True


class RawCommentInfo(BaseModel):
    """原始评论信息模式"""
    raw_comment_id: int = Field(..., description="原始评论ID")
    identifier_on_channel: str = Field(..., description="评论在渠道上的标识")
    comment_source_url: Optional[str] = Field(None, description="评论源URL")
    comment_content: str = Field(..., description="评论内容")
    posted_at_on_channel: Optional[datetime] = Field(None, description="评论在渠道上的发布时间")
    crawled_at: datetime = Field(..., description="评论爬取时间")
    
    # 新增：处理状态字段
    processing_status: str = Field(..., description="处理状态: new, processing, completed, failed, skipped")
    
    class Config:
        from_attributes = True


class RawCommentQueryResult(BaseModel):
    """查询原始评论结果模式"""
    vehicle_channel_info: VehicleChannelInfo = Field(..., description="车型渠道信息")
    raw_comment_ids: List[int] = Field(..., description="该车型下的所有原始评论ID列表")
    total_comments: int = Field(..., description="评论总数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_channel_info": {
                    "vehicle_channel_id": 123,
                    "channel_id": 1,
                    "identifier_on_channel": "s3170",
                    "name_on_channel": "奥迪A3",
                    "url_on_channel": "https://www.autohome.com.cn/spec/s3170/",
                    "temp_brand_name": "奥迪",
                    "temp_series_name": "一汽奥迪",
                    "temp_model_year": None
                },
                "raw_comment_ids": [1, 2, 3, 4, 5],
                "total_comments": 5
            }
        }


class RawCommentCrawlRequest(BaseModel):
    """原始评论爬取请求模式"""
    channel_id: int = Field(..., description="渠道ID", ge=1)
    identifier_on_channel: str = Field(..., description="车型在渠道上的标识", min_length=1)
    max_pages: Optional[int] = Field(None, description="最大爬取页数限制", ge=1, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": 1,
                "identifier_on_channel": "s7855",
                "max_pages": 10
            }
        }


class NewCommentInfo(BaseModel):
    """新评论信息模式"""
    identifier_on_channel: str = Field(..., description="评论在渠道上的标识")
    comment_content: str = Field(..., description="评论内容")
    posted_at_on_channel: Optional[datetime] = Field(None, description="评论在渠道上的发布时间")
    comment_source_url: Optional[str] = Field(None, description="评论源URL")


class RawCommentCrawlResult(BaseModel):
    """原始评论爬取结果模式"""
    vehicle_channel_info: VehicleChannelInfo = Field(..., description="车型渠道信息")
    total_pages_crawled: int = Field(..., description="爬取的总页数")
    total_comments_found: int = Field(..., description="发现的评论总数")
    new_comments_count: int = Field(..., description="新增评论数量")
    new_comments: List[NewCommentInfo] = Field(..., description="新增评论列表")
    crawl_duration: float = Field(..., description="爬取耗时(秒)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_channel_info": {
                    "vehicle_channel_id": 1,
                    "channel_id": 1,
                    "identifier_on_channel": "s7855",
                    "name_on_channel": "奥迪A5L"
                },
                "total_pages_crawled": 5,
                "total_comments_found": 87,
                "new_comments_count": 3,
                "new_comments": [
                    {
                        "identifier_on_channel": "123456",
                        "comment_content": "这款车的动力表现很不错",
                        "posted_at_on_channel": "2024-01-20T10:30:00"
                    }
                ],
                "crawl_duration": 15.5
            }
        }


class RawCommentCrawlTaskSchema(BaseModel):
    """原始评论爬取任务模式"""
    task_id: str = Field(..., description="任务ID")
    job_id: int = Field(..., description="processing_job记录ID")
    channel_id: int = Field(..., description="渠道ID")
    identifier_on_channel: str = Field(..., description="车型在渠道上的标识")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="任务消息")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc123-def456-ghi789",
                "job_id": 1,
                "channel_id": 1,
                "identifier_on_channel": "s7855", 
                "status": "pending",
                "message": "已启动奥迪A5L原始评论爬取任务",
                "created_at": "2024-01-20T10:30:00"
            }
        }


