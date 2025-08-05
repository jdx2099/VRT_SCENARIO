#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成产品功能向量并更新数据库中的feature_embedding字段
"""

import os
import sys
import json
import logging
from typing import List

# 添加项目根目录到Python路径
sys.path.append('/home/jdx/VRT_SCENARIO')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 使用项目配置中的同步数据库URL
DATABASE_URL = settings.SYNC_DATABASE_URL

def get_embeddings():
    """初始化嵌入模型（使用项目配置）"""
    try:
        embeddings = OpenAIEmbeddings(
            openai_api_base=settings.EMBEDDING_API_BASE,
            openai_api_key=settings.EMBEDDING_API_KEY,
            model=settings.EMBEDDING_MODEL_NAME
        )
        logger.info(f"✅ 嵌入模型初始化成功 - API: {settings.EMBEDDING_API_BASE}, 模型: {settings.EMBEDDING_MODEL_NAME}")
        return embeddings
    except Exception as e:
        logger.error(f"❌ 嵌入模型初始化失败: {e}")
        raise

def get_database_session():
    """获取数据库会话"""
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        logger.info("✅ 数据库连接成功")
        return session
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        raise

def fetch_product_features(session):
    """从数据库获取产品功能数据"""
    try:
        query = text("""
            SELECT product_feature_id, feature_code, feature_name, feature_description
            FROM product_features
            WHERE feature_name IS NOT NULL AND feature_description IS NOT NULL
            ORDER BY product_feature_id
        """)
        
        result = session.execute(query)
        features = result.fetchall()
        
        logger.info(f"✅ 从数据库获取到 {len(features)} 条产品功能数据")
        return features
    except Exception as e:
        logger.error(f"❌ 获取产品功能数据失败: {e}")
        raise

def generate_embedding_text(feature_name: str, feature_description: str) -> str:
    """生成用于嵌入的文本"""
    return f"功能名称：{feature_name}\n功能描述：{feature_description}"

def update_feature_embedding(session, product_feature_id: int, embedding_vector: List[float]):
    """更新数据库中的feature_embedding字段"""
    try:
        # 将向量转换为JSON字符串
        embedding_json = json.dumps(embedding_vector, ensure_ascii=False)
        
        query = text("""
            UPDATE product_features 
            SET feature_embedding = :embedding_json
            WHERE product_feature_id = :product_feature_id
        """)
        
        session.execute(query, {
            'embedding_json': embedding_json,
            'product_feature_id': product_feature_id
        })
        
        logger.debug(f"✅ 更新功能 {product_feature_id} 的向量数据")
    except Exception as e:
        logger.error(f"❌ 更新功能 {product_feature_id} 向量数据失败: {e}")
        raise

def main():
    """主函数"""
    logger.info("🚀 开始生成产品功能向量并更新数据库")
    
    try:
        # 初始化嵌入模型
        embeddings = get_embeddings()
        
        # 获取数据库会话
        session = get_database_session()
        
        try:
            # 获取产品功能数据
            features = fetch_product_features(session)
            
            if not features:
                logger.warning("⚠️ 没有找到需要处理的产品功能数据")
                return
            
            # 批量生成向量
            logger.info(f"🔄 开始为 {len(features)} 个功能生成向量...")
            
            success_count = 0
            error_count = 0
            
            for i, feature in enumerate(features, 1):
                product_feature_id = feature[0]
                feature_code = feature[1]
                feature_name = feature[2]
                feature_description = feature[3]
                
                try:
                    # 生成嵌入文本
                    embedding_text = generate_embedding_text(feature_name, feature_description)
                    
                    # 生成向量
                    embedding_vector = embeddings.embed_query(embedding_text)
                    
                    # 更新数据库
                    update_feature_embedding(session, product_feature_id, embedding_vector)
                    
                    success_count += 1
                    logger.info(f"✅ [{i}/{len(features)}] 功能 {feature_code} ({feature_name}) 向量生成完成")
                    
                    # 每处理10条记录提交一次
                    if i % 10 == 0:
                        session.commit()
                        logger.info(f"💾 已提交前 {i} 条记录")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ [{i}/{len(features)}] 功能 {feature_code} 处理失败: {e}")
                    continue
            
            # 最终提交
            session.commit()
            logger.info(f"💾 所有更改已提交到数据库")
            
            # 输出统计信息
            logger.info(f"\n📊 处理完成统计:")
            logger.info(f"   总数: {len(features)}")
            logger.info(f"   成功: {success_count}")
            logger.info(f"   失败: {error_count}")
            
            if success_count > 0:
                logger.info(f"\n🎉 成功为 {success_count} 个产品功能生成并存储了向量数据!")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()