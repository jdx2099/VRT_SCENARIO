"""
原始评论模块测试脚本
"""
import asyncio
import json
from datetime import datetime
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.vehicle_update import VehicleChannelDetail
from app.models.raw_comment_update import RawComment
from app.services.raw_comment_update_service import raw_comment_update_service
from app.schemas.raw_comment_update import RawCommentQueryRequest
from app.core.logging import app_logger


async def check_vehicle_data():
    """检查车型数据"""
    print("\n🔍 检查车型数据...")
    
    async with AsyncSessionLocal() as db:
        # 查询前5个车型
        result = await db.execute(
            select(VehicleChannelDetail).limit(5)
        )
        vehicles = result.scalars().all()
        
        print(f"📊 数据库中共有 {len(vehicles)} 个车型（显示前5个）:")
        for vehicle in vehicles:
            print(f"  - ID: {vehicle.vehicle_channel_id}, 渠道: {vehicle.channel_id_fk}, "
                  f"标识: {vehicle.identifier_on_channel}, 名称: {vehicle.name_on_channel}")
        
        return vehicles


async def add_test_raw_comments():
    """添加测试原始评论数据"""
    print("\n📝 添加测试原始评论数据...")
    
    async with AsyncSessionLocal() as db:
        # 获取第一个车型用于测试
        result = await db.execute(select(VehicleChannelDetail).limit(1))
        vehicle = result.scalar_one_or_none()
        
        if not vehicle:
            print("❌ 没有找到车型数据，请先运行车型更新")
            return None
        
        print(f"🎯 将为车型添加测试评论: {vehicle.name_on_channel} (ID: {vehicle.vehicle_channel_id})")
        
        # 检查是否已有评论
        existing_result = await db.execute(
            select(func.count()).select_from(RawComment).where(
                RawComment.vehicle_channel_id_fk == vehicle.vehicle_channel_id
            )
        )
        existing_count = existing_result.scalar()
        
        if existing_count > 0:
            print(f"✅ 该车型已有 {existing_count} 条评论，无需重复添加")
            return vehicle
        
        # 添加测试评论数据
        test_comments = [
            {
                "identifier_on_channel": "comment_001",
                "comment_content": "这款车外观很漂亮，动力也不错，值得推荐！",
                "comment_source_url": f"https://www.autohome.com.cn/spec/{vehicle.identifier_on_channel}/comment/1",
                "posted_at_on_channel": datetime(2024, 1, 15, 10, 30, 0)
            },
            {
                "identifier_on_channel": "comment_002", 
                "comment_content": "内饰设计比较满意，但是价格稍微贵了一点。",
                "comment_source_url": f"https://www.autohome.com.cn/spec/{vehicle.identifier_on_channel}/comment/2",
                "posted_at_on_channel": datetime(2024, 1, 16, 14, 20, 0)
            },
            {
                "identifier_on_channel": "comment_003",
                "comment_content": "油耗控制得不错，城市道路大约8个油左右。",
                "comment_source_url": f"https://www.autohome.com.cn/spec/{vehicle.identifier_on_channel}/comment/3",
                "posted_at_on_channel": datetime(2024, 1, 17, 9, 45, 0)
            },
            {
                "identifier_on_channel": "comment_004",
                "comment_content": "空间够用，后排坐三个人不会太挤。",
                "comment_source_url": f"https://www.autohome.com.cn/spec/{vehicle.identifier_on_channel}/comment/4",
                "posted_at_on_channel": datetime(2024, 1, 18, 16, 10, 0)
            },
            {
                "identifier_on_channel": "comment_005",
                "comment_content": "售后服务态度很好，维修也很及时。",
                "comment_source_url": f"https://www.autohome.com.cn/spec/{vehicle.identifier_on_channel}/comment/5",
                "posted_at_on_channel": datetime(2024, 1, 19, 11, 30, 0)
            }
        ]
        
        # 批量插入评论
        for comment_data in test_comments:
            comment = RawComment(
                vehicle_channel_id_fk=vehicle.vehicle_channel_id,
                **comment_data
            )
            db.add(comment)
        
        await db.commit()
        print(f"✅ 成功添加 {len(test_comments)} 条测试评论")
        
        return vehicle


async def test_query_raw_comment_ids():
    """测试查询原始评论ID功能"""
    print("\n🧪 测试查询原始评论ID功能...")
    
    # 先确保有测试数据
    vehicle = await add_test_raw_comments()
    if not vehicle:
        return
    
    # 创建查询请求
    query_request = RawCommentQueryRequest(
        channel_id=vehicle.channel_id_fk,
        identifier_on_channel=vehicle.identifier_on_channel
    )
    
    print(f"🔍 查询参数:")
    print(f"  - 渠道ID: {query_request.channel_id}")
    print(f"  - 车型标识: {query_request.identifier_on_channel}")
    
    try:
        # 调用服务层方法
        result = await raw_comment_update_service.get_vehicle_raw_comment_ids(query_request)
        
        print(f"\n✅ 查询成功!")
        print(f"📊 车型信息:")
        print(f"  - 车型渠道ID: {result.vehicle_channel_info.vehicle_channel_id}")
        print(f"  - 渠道ID: {result.vehicle_channel_info.channel_id}")
        print(f"  - 车型标识: {result.vehicle_channel_info.identifier_on_channel}")
        print(f"  - 车型名称: {result.vehicle_channel_info.name_on_channel}")
        print(f"  - 品牌: {result.vehicle_channel_info.temp_brand_name}")
        print(f"  - 车系: {result.vehicle_channel_info.temp_series_name}")
        
        print(f"\n📝 评论信息:")
        print(f"  - 评论总数: {result.total_comments}")
        print(f"  - 评论ID列表: {result.raw_comment_ids}")
        
        return result
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return None


async def test_invalid_query():
    """测试无效查询参数"""
    print("\n🧪 测试无效查询参数...")
    
    # 使用不存在的车型数据
    query_request = RawCommentQueryRequest(
        channel_id=999,
        identifier_on_channel="nonexistent_vehicle"
    )
    
    try:
        result = await raw_comment_update_service.get_vehicle_raw_comment_ids(query_request)
        print("❌ 应该抛出异常但没有抛出")
    except ValueError as e:
        print(f"✅ 正确处理了无效参数: {e}")
    except Exception as e:
        print(f"❌ 意外的异常类型: {e}")


async def test_comment_count():
    """测试评论数量统计功能"""  
    print("\n🧪 测试评论数量统计功能...")
    
    async with AsyncSessionLocal() as db:
        # 获取第一个车型
        result = await db.execute(select(VehicleChannelDetail).limit(1))
        vehicle = result.scalar_one_or_none()
        
        if not vehicle:
            print("❌ 没有找到车型数据")
            return
        
        try:
            # 测试统计功能
            count = await raw_comment_update_service.count_raw_comments_by_vehicle_channel_id(
                vehicle.vehicle_channel_id
            )
            print(f"✅ 车型 {vehicle.name_on_channel} 共有 {count} 条评论")
            
        except Exception as e:
            print(f"❌ 统计失败: {e}")


async def main():
    """主测试函数"""
    try:
        print("🚀 开始测试原始评论模块...")
        
        # 1. 检查车型数据
        await check_vehicle_data()
        
        # 2. 添加测试数据并查询
        await test_query_raw_comment_ids()
        
        # 3. 测试无效查询
        await test_invalid_query()
        
        # 4. 测试评论数量统计
        await test_comment_count()
        
        print("\n🎉 所有测试完成!")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 