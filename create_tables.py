#!/usr/bin/env python3
"""
简化的数据库表创建脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

async def create_tables():
    """创建数据库表"""
    try:
        print("🗄️ 开始创建数据库表...")
        
        # 导入所有模型
        from app.core.database import engine, Base
        from app.models import crawler, text_processing, llm_parsing, base
        from app.core.logging import app_logger
        
        # 测试数据库连接
        print("📡 测试数据库连接...")
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
            print("✅ 数据库连接成功")
        
        # 创建所有表
        print("🔨 创建数据库表...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ 数据库表创建成功!")
        
        # 显示创建的表
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            
            print("\n📋 已创建的表:")
            for table in tables:
                print(f"  - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🎯 VRT数据库表创建工具")
    print("=" * 40)
    
    success = await create_tables()
    
    if success:
        print("\n🎉 数据库初始化完成!")
        print("现在可以启动应用了:")
        print("uvicorn main:app --reload")
    else:
        print("\n❌ 数据库初始化失败!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        sys.exit(1) 