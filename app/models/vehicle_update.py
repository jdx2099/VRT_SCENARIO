"""
车型数据更新相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Channel(Base):
    """渠道表模型"""
    __tablename__ = "channels"
    
    channel_id = Column(Integer, primary_key=True, autoincrement=True)
    channel_name = Column(String(255), nullable=False, unique=True, comment="渠道名称，如：汽车之家")
    channel_base_url = Column(String(512), nullable=True, comment="渠道的基础网址")
    channel_description = Column(Text, nullable=True, comment="渠道描述信息")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    
    # 关系
    vehicle_channel_details = relationship("VehicleChannelDetail", back_populates="channel")


class Vehicle(Base):
    """标准车型表模型"""
    __tablename__ = "vehicles"
    
    vehicle_id = Column(Integer, primary_key=True, autoincrement=True)
    brand_name = Column(String(255), nullable=False, comment="品牌名称")
    manufacturer_name = Column(String(255), nullable=True, comment="制造商名称")
    series_name = Column(String(255), nullable=False, comment="车系名称")
    model_year = Column(String(50), nullable=True, comment="年款")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    vehicle_channel_details = relationship("VehicleChannelDetail", back_populates="vehicle")


class VehicleChannelDetail(Base):
    """车型渠道详情表模型"""
    __tablename__ = "vehicle_channel_details"
    
    vehicle_channel_id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id_fk = Column(Integer, ForeignKey("vehicles.vehicle_id"), nullable=True, comment="关联到标准车型表，前期可为空")
    channel_id_fk = Column(Integer, ForeignKey("channels.channel_id"), nullable=False, comment="关联到渠道表")
    identifier_on_channel = Column(String(255), nullable=False, comment="该车型在源渠道上的业务ID")
    name_on_channel = Column(String(255), nullable=False, comment="该车型在源渠道上的显示名称")
    url_on_channel = Column(String(2048), nullable=True, comment="该车型在源渠道上的页面URL")
    temp_brand_name = Column(String(255), nullable=True, comment="临时冗余字段：品牌名称")
    temp_series_name = Column(String(255), nullable=True, comment="临时冗余字段：车系名称")
    temp_model_year = Column(String(50), nullable=True, comment="临时冗余字段：年款")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    vehicle = relationship("Vehicle", back_populates="vehicle_channel_details")
    channel = relationship("Channel", back_populates="vehicle_channel_details")


class ProcessingJob(Base):
    """任务批次表模型"""
    __tablename__ = "processing_jobs"
    
    job_id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(100), nullable=False, comment="任务类型，如：comment_processing, vehicle_consolidation")
    status = Column(String(50), nullable=False, default="pending", comment="任务状态: pending, running, completed, failed")
    parameters = Column(JSON, nullable=True, comment="任务启动时的参数")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result_summary = Column(Text, nullable=True, comment="任务结果摘要") 