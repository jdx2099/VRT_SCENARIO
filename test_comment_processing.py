#!/usr/bin/env python3
"""
评论语义处理模块测试脚本
"""
import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import get_sync_session
from app.services.semantic_search_service import semantic_search_service
from app.services.comment_processing_service import comment_processing_service
from app.models.raw_comment_update import RawComment, ProcessingStatus
from app.models.comment_processing import ProductFeature, ProcessedComment
from app.core.logging import app_logger


def test_database_connection():
    """测试数据库连接"""
    print("🔗 测试数据库连接...")
    try:
        with get_sync_session() as session:
            # 测试查询
            result = session.execute("SELECT 1 as test").fetchone()
            print(f"✅ 数据库连接成功: {result}")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def test_product_features():
    """测试产品功能模块数据"""
    print("\n📋 测试产品功能模块数据...")
    try:
        with get_sync_session() as session:
            # 查询产品功能模块数量
            count = session.query(ProductFeature).count()
            print(f"📊 产品功能模块总数: {count}")
            
            if count > 0:
                # 显示前5个功能模块
                features = session.query(ProductFeature).limit(5).all()
                print("🔍 前5个功能模块:")
                for feature in features:
                    print(f"  - {feature.feature_code}: {feature.feature_name}")
                return True
            else:
                print("⚠️ 没有找到产品功能模块数据，请先导入数据")
                return False
                
    except Exception as e:
        print(f"❌ 查询产品功能模块失败: {e}")
        return False


def test_raw_comments():
    """测试原始评论数据"""
    print("\n💬 测试原始评论数据...")
    try:
        with get_sync_session() as session:
            # 查询待处理评论数量
            new_count = session.query(RawComment).filter(
                RawComment.processing_status == ProcessingStatus.NEW
            ).count()
            
            total_count = session.query(RawComment).count()
            
            print(f"📊 原始评论总数: {total_count}")
            print(f"📊 待处理评论数: {new_count}")
            
            if new_count > 0:
                # 显示前3条待处理评论
                comments = session.query(RawComment).filter(
                    RawComment.processing_status == ProcessingStatus.NEW
                ).limit(3).all()
                
                print("🔍 前3条待处理评论:")
                for comment in comments:
                    content_preview = comment.comment_content[:100] + "..." if len(comment.comment_content) > 100 else comment.comment_content
                    print(f"  - ID {comment.raw_comment_id}: {content_preview}")
                return True
            else:
                print("⚠️ 没有找到待处理的评论")
                return False
                
    except Exception as e:
        print(f"❌ 查询原始评论失败: {e}")
        return False


def test_semantic_search_service():
    """测试语义搜索服务"""
    print("\n🔍 测试语义搜索服务...")
    try:
        # 初始化服务
        print("🚀 初始化语义搜索服务...")
        semantic_search_service._initialize_embeddings()
        semantic_search_service._load_product_features()
        semantic_search_service._create_vector_store()
        
        # 测试文本分块
        test_text = "这个车的前碰撞预警系统很好用，在高速上能及时提醒我前方有障碍物。自适应巡航控制也很智能，能够自动调节车速。"
        chunks = semantic_search_service.split_text(test_text)
        print(f"📝 测试文本分块: {len(chunks)} 个块")
        for i, chunk in enumerate(chunks):
            print(f"  块 {i+1}: {chunk}")
        
        # 测试语义搜索
        if chunks:
            results = semantic_search_service.search_similar_features(chunks[0])
            print(f"🎯 语义搜索结果: {len(results)} 个匹配")
            for result in results[:3]:  # 显示前3个结果
                print(f"  - {result['feature_code']}: {result['feature_name']} (相似度: {result['similarity_score']:.3f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 语义搜索服务测试失败: {e}")
        return False


def test_comment_processing():
    """测试评论处理服务"""
    print("\n⚙️ 测试评论处理服务...")
    try:
        # 获取一条待处理评论进行测试
        with get_sync_session() as session:
            comment = session.query(RawComment).filter(
                RawComment.processing_status == ProcessingStatus.NEW
            ).first()
            
            if not comment:
                print("⚠️ 没有找到待处理的评论，跳过处理测试")
                return True
            
            print(f"🎯 测试处理评论 ID: {comment.raw_comment_id}")
            print(f"📝 评论内容: {comment.comment_content[:200]}...")
            
            # 处理单条评论
            result = comment_processing_service.process_single_comment(comment.raw_comment_id)
            print(f"✅ 处理结果: {result}")
            
            return True
            
    except Exception as e:
        print(f"❌ 评论处理测试失败: {e}")
        return False


def test_batch_processing():
    """测试批量处理"""
    print("\n📦 测试批量处理...")
    try:
        # 批量处理3条评论
        result = comment_processing_service.process_batch_comments(limit=3)
        print(f"✅ 批量处理结果: {result}")
        return True
        
    except Exception as e:
        print(f"❌ 批量处理测试失败: {e}")
        return False


def test_processing_statistics():
    """测试处理统计"""
    print("\n📊 测试处理统计...")
    try:
        stats = comment_processing_service.get_processing_statistics()
        print(f"✅ 处理统计: {stats}")
        return True
        
    except Exception as e:
        print(f"❌ 处理统计测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 评论语义处理模块测试开始")
    print("=" * 60)
    
    # 测试配置
    print(f"🔧 配置信息:")
    print(f"  - 嵌入模型API: {settings.EMBEDDING_API_BASE}")
    print(f"  - 嵌入模型名称: {settings.EMBEDDING_MODEL_NAME}")
    print(f"  - 相似度阈值: {settings.SEMANTIC_SIMILARITY_THRESHOLD}")
    
    tests = [
        ("数据库连接", test_database_connection),
        ("产品功能模块", test_product_features),
        ("原始评论数据", test_raw_comments),
        ("语义搜索服务", test_semantic_search_service),
        ("评论处理服务", test_comment_processing),
        ("批量处理", test_batch_processing),
        ("处理统计", test_processing_statistics),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                failed += 1
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"🧪 测试完成: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    
    if failed == 0:
        print("🎉 所有测试通过！评论语义处理模块可以正常使用。")
    else:
        print("⚠️ 部分测试失败，请检查配置和数据。")


if __name__ == "__main__":
    main()