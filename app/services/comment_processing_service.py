"""
评论处理服务 - 同步版本
专门用于Celery任务，负责评论的结构化处理和存储
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_sync_session
from app.core.logging import app_logger
from app.models.comment_processing import ProcessedComment
from app.models.raw_comment_update import RawComment, ProcessingStatus
from app.models.vehicle_update import ProcessingJob
from app.services.semantic_search_service import semantic_search_service


class CommentProcessingService:
    """
    评论处理服务类 - 同步版本
    专门用于Celery任务，使用pymysql驱动
    """
    
    def __init__(self):
        self.logger = app_logger
    
    def save_processed_comments(self, processing_results: List[Dict], job_id: Optional[int] = None) -> int:
        """
        保存处理结果到processed_comments表
        
        Args:
            processing_results: 处理结果列表
            job_id: 任务批次ID
            
        Returns:
            保存的记录数量
        """
        if not processing_results:
            return 0
        
        try:
            with get_sync_session() as db:
                saved_count = 0
                
                for result in processing_results:
                    processed_comment = ProcessedComment(
                        raw_comment_id_fk=result["raw_comment_id"],
                        product_feature_id_fk=result["product_feature_id"],
                        feature_similarity_score=result["feature_similarity_score"],
                        job_id_fk=job_id,
                        comment_chunk_text=result["comment_chunk_text"],
                        comment_chunk_vector=result["comment_chunk_vector"],
                        feature_search_details=result["feature_search_details"],
                        processed_at=datetime.now(timezone.utc)
                    )
                    
                    db.add(processed_comment)
                    saved_count += 1
                
                db.commit()
                self.logger.info(f"✅ 成功保存 {saved_count} 条处理结果")
                return saved_count
                
        except Exception as e:
            self.logger.error(f"❌ 保存处理结果失败: {e}")
            raise
    
    def process_single_comment(self, raw_comment: RawComment, job_id: Optional[int] = None) -> List[Dict]:
        """
        处理单条评论
        
        Args:
            raw_comment: 原始评论对象
            job_id: 任务批次ID
            
        Returns:
            处理结果列表
        """
        try:
            self.logger.info(f"🔄 开始处理评论: {raw_comment.raw_comment_id}")
            
            # 更新状态为处理中
            semantic_search_service.update_comment_status(
                raw_comment.raw_comment_id, 
                ProcessingStatus.PROCESSING
            )
            
            # 进行语义搜索处理
            results = semantic_search_service.process_comment_chunks(
                raw_comment.raw_comment_id,
                raw_comment.comment_content
            )
            
            if results:
                # 保存处理结果
                saved_count = self.save_processed_comments(results, job_id)
                
                # 更新状态为已完成
                semantic_search_service.update_comment_status(
                    raw_comment.raw_comment_id,
                    ProcessingStatus.COMPLETED
                )
                
                self.logger.info(f"✅ 评论 {raw_comment.raw_comment_id} 处理完成，保存 {saved_count} 条结果")
            else:
                # 没有找到匹配的功能模块，标记为跳过
                semantic_search_service.update_comment_status(
                    raw_comment.raw_comment_id,
                    ProcessingStatus.SKIPPED
                )
                
                self.logger.info(f"⚠️ 评论 {raw_comment.raw_comment_id} 未找到匹配功能模块，已跳过")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 处理评论 {raw_comment.raw_comment_id} 失败: {e}")
            
            # 更新状态为失败
            try:
                semantic_search_service.update_comment_status(
                    raw_comment.raw_comment_id,
                    ProcessingStatus.FAILED
                )
            except:
                pass
            
            raise
    
    def process_batch_comments(self, limit: int = 20, job_id: Optional[int] = None) -> Dict:
        """
        批量处理评论
        
        Args:
            limit: 处理数量限制
            job_id: 任务批次ID
            
        Returns:
            处理结果统计
        """
        try:
            self.logger.info(f"🚀 开始批量处理评论，限制数量: {limit}")
            
            # 获取待处理的评论
            pending_comments = semantic_search_service.get_pending_comments(limit)
            
            if not pending_comments:
                self.logger.info("📭 没有待处理的评论")
                return {
                    "total_comments": 0,
                    "processed_count": 0,
                    "failed_count": 0,
                    "skipped_count": 0,
                    "total_results": 0
                }
            
            processed_count = 0
            failed_count = 0
            skipped_count = 0
            total_results = 0
            
            for comment in pending_comments:
                try:
                    results = self.process_single_comment(comment, job_id)
                    if results:
                        processed_count += 1
                        total_results += len(results)
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    self.logger.error(f"❌ 处理评论 {comment.raw_comment_id} 失败: {e}")
                    failed_count += 1
            
            summary = {
                "total_comments": len(pending_comments),
                "processed_count": processed_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "total_results": total_results
            }
            
            self.logger.info(f"📊 批量处理完成: {summary}")
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 批量处理评论失败: {e}")
            raise
    
    def get_processing_statistics(self) -> Dict:
        """
        获取处理统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with get_sync_session() as db:
                # 统计各状态的评论数量
                stats = {}
                for status in ProcessingStatus:
                    count = db.query(RawComment).filter(
                        RawComment.processing_status == status
                    ).count()
                    stats[status.value] = count
                
                # 统计已处理评论的总数
                processed_total = db.query(ProcessedComment).count()
                stats["processed_results_total"] = processed_total
                
                self.logger.info(f"📊 处理统计: {stats}")
                return stats
                
        except Exception as e:
            self.logger.error(f"❌ 获取处理统计失败: {e}")
            raise


# 创建服务实例
comment_processing_service = CommentProcessingService()