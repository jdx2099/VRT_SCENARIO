"""
原始评论更新相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from enum import Enum


class ProcessingStatus(str, Enum):
    """处理状态枚举"""
    NEW = "NEW"              # 未处理
    PROCESSING = "PROCESSING" # 处理中
    COMPLETED = "COMPLETED"   # 已完成
    FAILED = "FAILED"         # 处理失败
    SKIPPED = "SKIPPED"       # 跳过处理


class RawComment(Base):
    """原始评论表模型"""
    __tablename__ = "raw_comments"
    
    raw_comment_id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_channel_id_fk = Column(Integer, ForeignKey("vehicle_channel_details.vehicle_channel_id"), nullable=False, comment="关联的车型渠道详情ID")
    identifier_on_channel = Column(String(255), nullable=False, comment="该评论在源渠道上的业务ID")
    comment_source_url = Column(String(2048), nullable=True, comment="评论在源渠道的原始URL")
    comment_content = Column(Text, nullable=False, comment="评论原始内容文本")
    posted_at_on_channel = Column(DateTime, nullable=True, comment="评论在源渠道的发布时间")
    crawled_at = Column(DateTime, nullable=False, default=func.current_timestamp(), comment="评论爬取入库时间")
    
    # 新增：处理状态字段
    processing_status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.NEW, comment="处理状态")
    
    # 关系 - 使用字符串引用避免循环导入
    vehicle_channel_detail = relationship("VehicleChannelDetail", backref="raw_comments")


 