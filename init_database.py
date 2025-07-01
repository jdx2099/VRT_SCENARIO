#!/usr/bin/env python3
"""
数据库初始化脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.core.database import engine, Base
from app.core.config import settings
from app.core.logging import app_logger
from app.models import crawler, text_processing, llm_parsing

async def create_database():
    """创建数据库表"""
    try:
        app_logger.info("开始创建数据库表...")
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        app_logger.info("✅ 数据库表创建成功")
        return True
        
    except Exception as e:
        app_logger.error(f"❌ 数据库表创建失败: {e}")
        return False

async def init_basic_data():
    """初始化基础数据"""
    try:
        from app.core.database import AsyncSessionLocal
        
        app_logger.info("开始初始化基础数据...")
        
        async with AsyncSessionLocal() as session:
            # 这里可以添加初始化数据的逻辑
            # 例如：创建默认的功能模块、管理员用户等
            pass
        
        app_logger.info("✅ 基础数据初始化成功")
        return True
        
    except Exception as e:
        app_logger.error(f"❌ 基础数据初始化失败: {e}")
        return False

async def test_database_connection():
    """测试数据库连接"""
    try:
        app_logger.info("测试数据库连接...")
        
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            await result.fetchone()
        
        app_logger.info("✅ 数据库连接正常")
        return True
        
    except Exception as e:
        app_logger.error(f"❌ 数据库连接失败: {e}")
        app_logger.error("请检查以下配置:")
        app_logger.error(f"- 数据库URL: {settings.DATABASE_URL}")
        app_logger.error("- MySQL服务是否已启动")
        app_logger.error("- 数据库用户名密码是否正确")
        app_logger.error("- 数据库是否已创建")
        return False

def print_database_info():
    """打印数据库信息"""
    print("\n📊 数据库配置信息:")
    print(f"- 数据库URL: {settings.DATABASE_URL}")
    print(f"- 数据库类型: MySQL (asyncmy驱动)")
    print("\n📋 数据表结构:")
    
    tables = [
        ("crawler_tasks", "爬虫任务表"),
        ("raw_comments", "原始评论数据表"),
        ("text_segments", "文本片段表"),
        ("function_modules", "功能模块表"),
        ("semantic_matches", "语义匹配结果表"),
        ("structured_feedback", "结构化反馈表"),
        ("llm_parsing_tasks", "LLM解析任务表"),
    ]
    
    for table_name, description in tables:
        print(f"  - {table_name}: {description}")

async def main():
    """主函数"""
    print("🗄️  VRT数据库初始化向导")
    print("=" * 50)
    
    # 打印数据库信息
    print_database_info()
    
    # 测试数据库连接
    if not await test_database_connection():
        print("\n❌ 数据库连接失败，请检查配置后重试")
        print("💡 提示:")
        print("1. 确保MySQL服务已启动")
        print("2. 确保数据库已创建: CREATE DATABASE vrt_db;")
        print("3. 检查.env文件中的DATABASE_URL配置")
        return
    
    # 创建数据库表
    if not await create_database():
        print("❌ 数据库表创建失败")
        return
    
    # 初始化基础数据
    if not await init_basic_data():
        print("❌ 基础数据初始化失败")
        return
    
    print("\n🎉 数据库初始化完成!")
    print("现在可以启动应用了:")
    print("python start_project.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 初始化已取消")
    except Exception as e:
        print(f"❌ 初始化过程出错: {e}")
        sys.exit(1) 