#!/usr/bin/env python3
"""
数据库枚举值迁移脚本
将 processing_status 字段的枚举定义和数据从小写改为大写
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.logging import app_logger as logger
from app.core.database import get_sync_session
from sqlalchemy import text

def migrate_enum_values():
    """迁移枚举值从小写到大写"""
    logger.info("🚀 开始迁移 processing_status 枚举值...")
    
    try:
        with get_sync_session() as session:
            # 1. 首先检查当前数据分布
            logger.info("📊 检查当前数据分布...")
            result = session.execute(text("""
                SELECT processing_status, COUNT(*) as count 
                FROM raw_comments 
                GROUP BY processing_status
            """))
            
            current_data = result.fetchall()
            logger.info("当前数据分布:")
            for row in current_data:
                logger.info(f"  {row[0]}: {row[1]} 条记录")
            
            # 2. 更新数据值（从小写到大写）
            logger.info("🔄 更新数据值...")
            
            # 映射关系
            value_mapping = {
                'new': 'NEW',
                'processing': 'PROCESSING', 
                'completed': 'COMPLETED',
                'failed': 'FAILED',
                'skipped': 'SKIPPED'
            }
            
            for old_value, new_value in value_mapping.items():
                result = session.execute(text("""
                    UPDATE raw_comments 
                    SET processing_status = :new_value 
                    WHERE processing_status = :old_value
                """), {"old_value": old_value, "new_value": new_value})
                
                affected_rows = result.rowcount
                if affected_rows > 0:
                    logger.info(f"  ✅ 更新 '{old_value}' -> '{new_value}': {affected_rows} 条记录")
            
            session.commit()
            logger.info("✅ 数据值更新完成")
            
            # 3. 修改枚举定义
            logger.info("🔧 修改枚举定义...")
            
            # 先添加临时列
            session.execute(text("""
                ALTER TABLE raw_comments 
                ADD COLUMN processing_status_temp ENUM('NEW','PROCESSING','COMPLETED','FAILED','SKIPPED') 
                NOT NULL DEFAULT 'NEW'
            """))
            
            # 复制数据到临时列
            session.execute(text("""
                UPDATE raw_comments 
                SET processing_status_temp = processing_status
            """))
            
            # 删除原列
            session.execute(text("""
                ALTER TABLE raw_comments 
                DROP COLUMN processing_status
            """))
            
            # 重命名临时列
            session.execute(text("""
                ALTER TABLE raw_comments 
                CHANGE COLUMN processing_status_temp processing_status 
                ENUM('NEW','PROCESSING','COMPLETED','FAILED','SKIPPED') 
                NOT NULL DEFAULT 'NEW'
            """))
            
            # 重新添加索引（如果需要）
            try:
                session.execute(text("""
                    CREATE INDEX idx_processing_status ON raw_comments(processing_status)
                """))
                logger.info("✅ 重新创建索引")
            except Exception as e:
                logger.warning(f"⚠️ 创建索引失败（可能已存在）: {e}")
            
            session.commit()
            logger.info("✅ 枚举定义修改完成")
            
            # 4. 验证迁移结果
            logger.info("🔍 验证迁移结果...")
            
            # 检查新的枚举定义
            result = session.execute(text("""
                SHOW COLUMNS FROM raw_comments LIKE 'processing_status'
            """))
            column_info = result.fetchone()
            logger.info(f"新的枚举定义: {column_info[1]}")
            
            # 检查数据分布
            result = session.execute(text("""
                SELECT processing_status, COUNT(*) as count 
                FROM raw_comments 
                GROUP BY processing_status
            """))
            
            new_data = result.fetchall()
            logger.info("迁移后数据分布:")
            for row in new_data:
                logger.info(f"  {row[0]}: {row[1]} 条记录")
            
            logger.info("🎉 枚举值迁移完成！")
            return True
            
    except Exception as e:
        logger.error(f"❌ 枚举值迁移失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    logger.info("🔧 数据库枚举值迁移工具")
    
    # 确认操作
    logger.warning("⚠️ 此操作将修改数据库结构和数据，请确保已备份数据库！")
    
    if migrate_enum_values():
        logger.info("✅ 迁移成功完成！")
        return 0
    else:
        logger.error("❌ 迁移失败！")
        return 1

if __name__ == "__main__":
    exit(main())