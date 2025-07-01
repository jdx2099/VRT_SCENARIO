"""
基础数据库模型
"""
from sqlalchemy import Column, Integer, DateTime, func
from app.core.database import Base

class BaseModel(Base):
    """
    基础模型类，包含通用字段
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 