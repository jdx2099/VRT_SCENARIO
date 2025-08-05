"""
语义搜索服务 - 同步版本
专门用于Celery任务，实现评论文本的语义相似度检索
"""
import os
import json
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from app.core.database import get_sync_session
from app.core.config import settings
from app.core.logging import app_logger
from app.models.comment_processing import ProductFeature
from app.models.raw_comment_update import RawComment, ProcessingStatus


class SemanticSearchService:
    """
    语义搜索服务类 - 同步版本
    专门用于Celery任务，使用pymysql驱动
    """
    
    def __init__(self):
        self.logger = app_logger
        self.embeddings = None
        self.vector_store = None
        self.persist_directory = "/home/jdx/VRT_SCENARIO/db/vectorDB"
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """初始化嵌入模型"""
        try:
            self.embeddings = OpenAIEmbeddings(
                openai_api_base=settings.EMBEDDING_API_BASE,
                openai_api_key=settings.EMBEDDING_API_KEY,
                model=settings.EMBEDDING_MODEL_NAME
            )
            self.logger.info("✅ 嵌入模型初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 初始化嵌入模型失败: {e}")
            raise
    
    def _load_product_features_from_db(self) -> List[Document]:
        """从数据库加载产品功能并转换为LangChain Document对象"""
        documents = []
        try:
            with get_sync_session() as db:
                features = db.query(ProductFeature).all()
                
                for feature in features:
                    if not feature.feature_name or not feature.feature_description:
                        self.logger.warning(f"跳过不完整的功能模块: ID={feature.product_feature_id}")
                        continue
                    
                    page_content = f"功能名称：{feature.feature_name}\n功能描述：{feature.feature_description}"
                    metadata = {
                        "id": feature.feature_code,
                        "product_feature_id": feature.product_feature_id,
                        "功能模块名称": feature.feature_name,
                        "原始描述": feature.feature_description
                    }
                    doc = Document(page_content=page_content, metadata=metadata)
                    documents.append(doc)
                
                self.logger.info(f"从数据库成功加载了 {len(documents)} 个功能模块")
                return documents
                
        except Exception as e:
            self.logger.error(f"❌ 从数据库加载产品功能失败: {e}")
            raise
    
    def _create_vector_store(self) -> Chroma:
        """创建或加载向量存储"""
        try:
            # 确保持久化目录存在
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # 检查是否已存在持久化的向量数据库
            if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
                self.logger.info(f"🔄 从持久化存储加载向量数据库: {self.persist_directory}")
                try:
                    vector_store = Chroma(
                        persist_directory=self.persist_directory,
                        embedding_function=self.embeddings
                    )
                    # 验证向量存储是否有效
                    collection = vector_store._collection
                    if collection.count() > 0:
                        self.logger.info(f"✅ 成功加载向量数据库，包含 {collection.count()} 个文档")
                        return vector_store
                    else:
                        self.logger.warning("⚠️ 持久化向量数据库为空，将重新创建")
                except Exception as load_error:
                    self.logger.warning(f"⚠️ 加载持久化向量数据库失败: {load_error}，将重新创建")
            
            # 创建新的向量数据库
            documents = self._load_product_features_from_db()
            if not documents:
                raise ValueError("没有可用的产品功能数据")
            
            self.logger.info(f"🔨 正在创建新的向量存储，包含 {len(documents)} 个文档...")
            vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # 持久化向量数据库
            vector_store.persist()
            self.logger.info(f"✅ 向量存储创建并持久化成功，存储路径: {self.persist_directory}")
            return vector_store
            
        except Exception as e:
            self.logger.error(f"❌ 创建/加载向量存储失败: {e}")
            raise
    
    def get_vector_store(self) -> Chroma:
        """获取向量存储实例"""
        if self.vector_store is None:
            self.vector_store = self._create_vector_store()
        return self.vector_store
    
    def split_comment_into_chunks(self, comment_text: str) -> List[Dict[str, str]]:
        """
        将评论文本按章节拆分为文本块
        
        Args:
            comment_text: 原始评论文本
            
        Returns:
            文本块列表，每个包含source_section和chunk_text
        """
        chunks = []
        sections = re.split(r'(【[^】]+】)', comment_text)
        
        current_section_title = "评论开头"
        for part in sections:
            part = part.strip()
            if not part:
                continue
            
            if part.startswith("【") and part.endswith("】"):
                current_section_title = part
            else:
                chunk_text = part
                if len(chunk_text) > 5:  # 过滤太短的文本
                    chunks.append({
                        "source_section": current_section_title,
                        "chunk_text": chunk_text
                    })
        
        return chunks
    
    def search_similar_features(self, query_text: str, k: int = 1) -> List[Tuple[Document, float]]:
        """
        搜索与查询文本最相似的功能模块
        
        Args:
            query_text: 查询文本
            k: 返回的结果数量
            
        Returns:
            相似度搜索结果列表，每个元素为(Document, score)
        """
        try:
            vector_store = self.get_vector_store()
            results = vector_store.similarity_search_with_score(query_text, k=k)
            return results
        except Exception as e:
            self.logger.error(f"❌ 语义搜索失败: {e}")
            raise
    
    def process_comment_chunks(self, raw_comment_id: int, comment_text: str) -> List[Dict]:
        """
        处理评论文本块，进行语义搜索
        
        Args:
            raw_comment_id: 原始评论ID
            comment_text: 评论文本
            
        Returns:
            处理结果列表
        """
        try:
            # 拆分文本块
            chunks = self.split_comment_into_chunks(comment_text)
            self.logger.info(f"评论 {raw_comment_id} 拆分为 {len(chunks)} 个文本块")
            
            results = []
            
            for chunk in chunks:
                section_title = chunk["source_section"]
                chunk_text = chunk["chunk_text"]
                
                self.logger.debug(f"正在处理章节: {section_title}")
                
                # 进行语义搜索
                search_results = self.search_similar_features(chunk_text, k=1)
                
                if search_results:
                    doc, score = search_results[0]
                    
                    # 检查相似度阈值
                    if score < settings.SEMANTIC_SIMILARITY_THRESHOLD:
                        # 生成评论片段的向量
                        chunk_vector = self.embeddings.embed_query(chunk_text)
                        
                        result = {
                            "raw_comment_id": raw_comment_id,
                            "product_feature_id": doc.metadata.get("product_feature_id"),
                            "feature_similarity_score": float(score),
                            "comment_chunk_text": chunk_text,
                            "comment_chunk_vector": json.dumps(chunk_vector),
                            "feature_search_details": {
                                "source_section": section_title,
                                "matched_feature_code": doc.metadata.get("id"),
                                "matched_feature_name": doc.metadata.get("功能模块名称"),
                                "similarity_score": float(score),
                                "search_query_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
                            }
                        }
                        results.append(result)
                        
                        self.logger.info(f"✅ 找到匹配: {doc.metadata.get('功能模块名称')} (分数: {score:.4f})")
                    else:
                        self.logger.debug(f"❌ 相似度过低: {score:.4f} >= {settings.SEMANTIC_SIMILARITY_THRESHOLD}")
                else:
                    self.logger.warning(f"未找到匹配的功能模块: {section_title}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 处理评论文本块失败: {e}")
            raise
    
    def get_pending_comments(self, limit: int = 20) -> List[RawComment]:
        """
        获取待处理的原始评论
        
        Args:
            limit: 限制数量
            
        Returns:
            待处理的原始评论列表
        """
        try:
            with get_sync_session() as db:
                comments = db.query(RawComment).filter(
                    RawComment.processing_status == ProcessingStatus.NEW
                ).limit(limit).all()
                
                self.logger.info(f"获取到 {len(comments)} 条待处理评论")
                return comments
                
        except Exception as e:
            self.logger.error(f"❌ 获取待处理评论失败: {e}")
            raise
    
    def update_comment_status(self, raw_comment_id: int, status: ProcessingStatus):
        """
        更新评论处理状态
        
        Args:
            raw_comment_id: 原始评论ID
            status: 新状态
        """
        try:
            with get_sync_session() as db:
                comment = db.get(RawComment, raw_comment_id)
                if comment:
                    comment.processing_status = status
                    db.commit()
                    self.logger.debug(f"更新评论 {raw_comment_id} 状态为: {status.value}")
                else:
                    self.logger.warning(f"未找到评论: {raw_comment_id}")
                    
        except Exception as e:
            self.logger.error(f"❌ 更新评论状态失败: {e}")
            raise


# 创建服务实例
semantic_search_service = SemanticSearchService()