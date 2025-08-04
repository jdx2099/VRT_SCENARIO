"""
评论处理相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProductFeature(Base):
    """产品功能表模型"""
    __tablename__ = "product_features"
    
    product_feature_id = Column(Integer, primary_key=True, autoincrement=True)
    feature_code = Column(String(255), nullable=False, unique=True, comment="产品功能的业务编码，业务上唯一")
    feature_name = Column(String(255), nullable=False, comment="产品功能的名称，如：蓝牙、智能钥匙")
    feature_description = Column(Text, nullable=True, comment="功能的详细描述（可用于生成嵌入）")
    feature_embedding = Column(Text, nullable=True, comment="功能的文本嵌入向量，以JSON数组或特定格式的文本存储")
    parent_id_fk = Column(Integer, ForeignKey("product_features.product_feature_id"), nullable=True, comment="指向父级功能ID，形成层级结构")
    hierarchy_level = Column(Integer, nullable=False, comment="层级: 1, 2, 或 3")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    parent = relationship("ProductFeature", remote_side=[product_feature_id], backref="children")
    processed_comments = relationship("ProcessedComment", backref="product_feature")


class ProcessedComment(Base):
    """已处理评论表模型"""
    __tablename__ = "processed_comments"
    
    processed_comment_id = Column(Integer, primary_key=True, autoincrement=True)
    raw_comment_id_fk = Column(Integer, ForeignKey("raw_comments.raw_comment_id"), nullable=False, comment="关联的原始评论ID")
    product_feature_id_fk = Column(Integer, ForeignKey("product_features.product_feature_id"), nullable=True, comment="检索匹配到的唯一功能模块")
    feature_similarity_score = Column(DECIMAL(18, 17), nullable=True, comment="功能模块与文本片段的相似度得分")
    job_id_fk = Column(Integer, ForeignKey("processing_jobs.job_id"), nullable=True, comment="关联到创建本条记录的任务批次")
    scene_actor = Column(String(255), nullable=True, comment="场景中的行动者/用户角色")
    scene_time_context = Column(String(255), nullable=True, comment="场景发生的时间上下文")
    scene_location_context = Column(String(255), nullable=True, comment="场景发生的地点上下文")
    scene_activity_or_task = Column(String(255), nullable=True, comment="场景中发生的活动或用户执行的任务")
    sentiment_label = Column(String(100), nullable=True, comment="情感分析标签")
    sentiment_confidence = Column(DECIMAL(5, 4), nullable=True, comment="情感分析结果的置信度")
    comment_analysis_summary = Column(Text, nullable=True, comment="对评论内容分析后给出的原因或摘要")
    comment_chunk_text = Column(Text, nullable=True, comment="用于本次分析的评论片段原文")
    comment_chunk_vector = Column(Text, nullable=True, comment="评论片段的向量表示(JSON格式存储)")
    feature_search_details = Column(JSON, nullable=True, comment="Top-K相似度检索结果详情")
    processed_at = Column(DateTime, nullable=False, default=func.current_timestamp(), comment="评论处理完成时间")
    
    # 关系 - 使用字符串引用避免循环导入
    raw_comment = relationship("RawComment", backref="processed_comments")
    processing_job = relationship("ProcessingJob", backref="processed_comments")