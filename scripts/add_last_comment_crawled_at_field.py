#!/usr/bin/env python3
"""
数据库字段更新脚本：为vehicle_channel_details表添加last_comment_crawled_at字段
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.core.logging import app_logger
from sqlalchemy import text


async def add_last_comment_crawled_at_field():
    """
    为vehicle_channel_details表添加last_comment_crawled_at字段
    """
    app_logger.info("🔧 开始为vehicle_channel_details表添加last_comment_crawled_at字段")
    
    try:
        async with AsyncSessionLocal() as db:
            # 检查字段是否已存在
            check_result = await db.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'vrt_db' 
                AND TABLE_NAME = 'vehicle_channel_details' 
                AND COLUMN_NAME = 'last_comment_crawled_at'
            """))
            
            if check_result.fetchone():
                app_logger.info("ℹ️ last_comment_crawled_at字段已存在，跳过添加")
                return
            
            # 添加字段
            await db.execute(text("""
                ALTER TABLE vehicle_channel_details 
                ADD COLUMN last_comment_crawled_at TIMESTAMP NULL 
                COMMENT '上次成功爬取评论的时间，NULL表示从未爬取过' 
                AFTER temp_model_year
            """))
            
            await db.commit()
            app_logger.info("✅ 成功添加last_comment_crawled_at字段")
            
            # 验证字段添加成功
            verify_result = await db.execute(text("""
                DESCRIBE vehicle_channel_details
            """))
            
            columns = verify_result.fetchall()
            app_logger.info("📋 表结构验证:")
            for column in columns:
                if 'last_comment_crawled_at' in str(column):
                    app_logger.info(f"  ✅ {column}")
                    break
            else:
                app_logger.warning("⚠️ 未找到last_comment_crawled_at字段")
                
    except Exception as e:
        app_logger.error(f"❌ 添加字段失败: {e}")
        raise


async def main():
    """主函数"""
    app_logger.info("🚀 开始执行数据库字段更新")
    
    try:
        await add_last_comment_crawled_at_field()
        app_logger.info("🎉 数据库字段更新完成")
    except Exception as e:
        app_logger.error(f"❌ 数据库字段更新失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 