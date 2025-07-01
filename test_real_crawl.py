"""
测试真实的汽车之家车型数据爬取
"""
import asyncio
import json
from app.utils.channel_parsers.autohome_parser import AutoHomeParser

async def test_autohome_crawl():
    """测试汽车之家数据爬取"""
    print("开始测试汽车之家真实数据爬取...")
    
    parser = AutoHomeParser()
    
    try:
        # 测试渠道ID 1（汽车之家）
        vehicles = await parser.extract_vehicles(channel_id=1)
        
        print(f"✅ 爬取完成！共获取 {len(vehicles)} 个车型")
        
        # 显示前5个车型的详细信息
        print("\n前5个车型详情：")
        for i, vehicle in enumerate(vehicles[:5]):
            print(f"{i+1}. {vehicle}")
            
        # 统计信息
        stats = parser.get_statistics()
        print(f"\n统计信息：")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # 按品牌统计
        brand_stats = {}
        for vehicle in vehicles:
            brand = vehicle.get('brand_name', '未知')
            brand_stats[brand] = brand_stats.get(brand, 0) + 1
            
        print(f"\n品牌统计（前10个）：")
        sorted_brands = sorted(brand_stats.items(), key=lambda x: x[1], reverse=True)
        for brand, count in sorted_brands[:10]:
            print(f"  {brand}: {count} 个车型")
        
    except Exception as e:
        print(f"❌ 爬取失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_autohome_crawl()) 