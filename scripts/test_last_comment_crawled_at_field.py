#!/usr/bin/env python3
"""
测试脚本：验证last_comment_crawled_at字段是否正常工作
"""
import sys
import os
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.core.logging import app_logger
from app.models.vehicle_update import VehicleChannelDetail
from sqlalchemy import select


async def test_last_comment_crawled_at_field():
    """
    测试last_comment_crawled_at字段
    """
    app_logger.info("🧪 开始测试last_comment_crawled_at字段")
    
    try:
        async with AsyncSessionLocal() as db:
            # 1. 查询所有车型记录
            result = await db.execute(
                select(VehicleChannelDetail).limit(5)
            )
            vehicles = result.scalars().all()
            
            app_logger.info(f"📊 查询到 {len(vehicles)} 条车型记录")
            
            # 2. 检查字段是否存在
            for vehicle in vehicles:
                app_logger.info(f"车型ID: {vehicle.vehicle_channel_id}")
                app_logger.info(f"  名称: {vehicle.name_on_channel}")
                app_logger.info(f"  last_comment_crawled_at: {vehicle.last_comment_crawled_at}")
                app_logger.info("  ---")
            
            # 3. 测试更新字段
            if vehicles:
                test_vehicle = vehicles[0]
                old_value = test_vehicle.last_comment_crawled_at
                
                # 更新为当前时间
                test_vehicle.last_comment_crawled_at = datetime.utcnow()
                await db.commit()
                
                app_logger.info(f"✅ 成功更新车型 {test_vehicle.vehicle_channel_id} 的last_comment_crawled_at字段")
                app_logger.info(f"  原值: {old_value}")
                app_logger.info(f"  新值: {test_vehicle.last_comment_crawled_at}")
                
                # 恢复原值
                test_vehicle.last_comment_crawled_at = old_value
                await db.commit()
                app_logger.info(f"🔄 已恢复原值: {test_vehicle.last_comment_crawled_at}")
            
            # 4. 统计字段状态
            null_count = await db.execute(
                select(VehicleChannelDetail).where(
                    VehicleChannelDetail.last_comment_crawled_at.is_(None)
                )
            )
            null_vehicles = null_count.scalars().all()
            
            app_logger.info(f"📈 统计信息:")
            app_logger.info(f"  总车型数: {len(vehicles)}")
            app_logger.info(f"  从未爬取过评论的车型数: {len(null_vehicles)}")
            
    except Exception as e:
        app_logger.error(f"❌ 测试失败: {e}")
        raise


async def main():
    """主函数"""
    app_logger.info("🚀 开始测试last_comment_crawled_at字段")
    
    try:
        await test_last_comment_crawled_at_field()
        app_logger.info("🎉 测试完成")
    except Exception as e:
        app_logger.error(f"❌ 测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 