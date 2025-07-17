#!/usr/bin/env python3
"""
数据库结构检查脚本：对比create_tables_current.sql与实际数据库结构
"""
import sys
import os
import asyncio
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.core.logging import app_logger
from sqlalchemy import text


def parse_sql_file():
    """
    解析create_tables_current.sql文件，提取表结构信息
    """
    sql_file_path = "db/create_tables_current.sql"
    app_logger.info(f"📖 解析SQL文件: {sql_file_path}")
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有CREATE TABLE语句
        create_table_pattern = r'CREATE TABLE `(\w+)`\s*\(([\s\S]*?)\)\s*ENGINE='
        tables = {}
        
        for match in re.finditer(create_table_pattern, content):
            table_name = match.group(1)
            table_body = match.group(2)
            
            # 提取字段定义
            field_pattern = r'`(\w+)`\s+([^,\n]+?)(?:,|$)'
            fields = {}
            
            for field_match in re.finditer(field_pattern, table_body):
                field_name = field_match.group(1)
                field_definition = field_match.group(2).strip()
                fields[field_name] = field_definition
            
            tables[table_name] = fields
            app_logger.info(f"  📋 解析表 {table_name}: {len(fields)} 个字段")
        
        return tables
        
    except Exception as e:
        app_logger.error(f"❌ 解析SQL文件失败: {e}")
        raise


async def get_database_schema():
    """
    获取数据库实际结构
    """
    app_logger.info("🔍 获取数据库实际结构")
    
    try:
        async with AsyncSessionLocal() as db:
            # 获取所有表名
            result = await db.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'vrt_db' 
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """))
            
            tables = {}
            table_names = [row[0] for row in result.fetchall()]
            
            for table_name in table_names:
                # 获取表结构
                result = await db.execute(text(f"""
                    DESCRIBE {table_name}
                """))
                
                fields = {}
                for row in result.fetchall():
                    field_name = row[0]
                    field_type = row[1]
                    nullable = row[2]
                    key = row[3]
                    default = row[4]
                    extra = row[5]
                    
                    fields[field_name] = {
                        'type': field_type,
                        'nullable': nullable,
                        'key': key,
                        'default': default,
                        'extra': extra
                    }
                
                tables[table_name] = fields
                app_logger.info(f"  📋 获取表 {table_name}: {len(fields)} 个字段")
            
            return tables
            
    except Exception as e:
        app_logger.error(f"❌ 获取数据库结构失败: {e}")
        raise


def compare_schemas(sql_tables, db_tables):
    """
    对比SQL文件和数据库结构
    """
    app_logger.info("🔍 开始对比结构")
    
    all_tables = set(sql_tables.keys()) | set(db_tables.keys())
    
    for table_name in sorted(all_tables):
        app_logger.info(f"\n📊 检查表: {table_name}")
        
        if table_name not in sql_tables:
            app_logger.warning(f"  ⚠️ 表 {table_name} 在SQL文件中不存在，但数据库中存在")
            continue
            
        if table_name not in db_tables:
            app_logger.warning(f"  ⚠️ 表 {table_name} 在SQL文件中存在，但数据库中不存在")
            continue
        
        sql_fields = sql_tables[table_name]
        db_fields = db_tables[table_name]
        
        all_fields = set(sql_fields.keys()) | set(db_fields.keys())
        
        for field_name in sorted(all_fields):
            if field_name not in sql_fields:
                app_logger.warning(f"    ⚠️ 字段 {field_name} 在SQL文件中不存在，但数据库中存在")
                continue
                
            if field_name not in db_fields:
                app_logger.warning(f"    ⚠️ 字段 {field_name} 在SQL文件中存在，但数据库中不存在")
                continue
            
            # 检查字段类型是否匹配
            sql_def = sql_fields[field_name]
            db_def = db_fields[field_name]
            
            # 简化类型比较（去掉长度信息等）
            sql_type = re.sub(r'\(\d+\)', '', sql_def.split()[0].upper())
            db_type = re.sub(r'\(\d+\)', '', db_def['type'].upper())
            
            if sql_type != db_type:
                app_logger.warning(f"    ⚠️ 字段 {field_name} 类型不匹配:")
                app_logger.warning(f"      SQL文件: {sql_def}")
                app_logger.warning(f"      数据库: {db_def['type']}")
            else:
                app_logger.info(f"    ✅ 字段 {field_name}: {db_def['type']}")


async def main():
    """主函数"""
    app_logger.info("🚀 开始检查数据库结构一致性")
    
    try:
        # 1. 解析SQL文件
        sql_tables = parse_sql_file()
        
        # 2. 获取数据库结构
        db_tables = await get_database_schema()
        
        # 3. 对比结构
        compare_schemas(sql_tables, db_tables)
        
        app_logger.info("\n🎉 数据库结构检查完成")
        
    except Exception as e:
        app_logger.error(f"❌ 检查失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 