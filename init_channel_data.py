#!/usr/bin/env python3
"""
初始化渠道数据脚本
向channels表中插入汽车之家等渠道的基础数据
"""
import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings
import asyncmy


async def get_db_connection():
    """获取数据库连接"""
    try:
        # 解析数据库连接信息
        import re
        db_url = settings.DATABASE_URL
        match = re.match(r'mysql\+asyncmy://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if not match:
            raise ValueError(f"无法解析数据库URL: {db_url}")
        
        user, password, host, port, database = match.groups()
        
        conn = await asyncmy.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            autocommit=True
        )
        
        return conn
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


def prepare_autohome_data():
    """准备汽车之家渠道数据"""
    
    # 定义汽车之家的URL配置
    autohome_urls = {
        "brand_overview": {
            "url": "http://www.autohome.com.cn/grade/carhtml/{}.html",
            "description": "品牌-制造商-车型总览页面",
            "method": "GET",
            "params": ["brand_letter"],  # A到Z的品牌字母
            "usage": "获取品牌下的所有车型列表"
        },
        "koubei_series": {
            "url": "https://koubei.app.autohome.com.cn/autov8.3.5/alibi/seriesalibiinfos-pm2-s{}-st0-p{}-s20-isstruct0-o0.json",
            "description": "车系口碑信息API",
            "method": "GET", 
            "params": ["series_id", "page_number"],
            "usage": "根据车系ID获取总页数和收集所有页面的koubei数据"
        },
        "koubei_detail": {
            "url": "https://koubei.app.autohome.com.cn/autov8.3.5/alibi/alibiinfobase-pm2-k{}.json",
            "description": "口碑详情信息API", 
            "method": "GET",
            "params": ["koubei_id"],
            "usage": "使用koubei ID获取具体的koubei信息JSON数据"
        }
    }
    
    channel_data = {
        "channel_name": "汽车之家",
        "channel_base_url": json.dumps(autohome_urls, ensure_ascii=False, indent=2),
        "channel_description": "汽车之家-口碑模块"
    }
    
    return channel_data


async def insert_channel_data(conn, channel_data):
    """插入渠道数据"""
    try:
        cursor = conn.cursor()
        
        # 检查是否已存在
        check_sql = "SELECT channel_id FROM channels WHERE channel_name = %s"
        await cursor.execute(check_sql, (channel_data["channel_name"],))
        existing = await cursor.fetchone()
        
        if existing:
            print(f"⚠️  渠道 '{channel_data['channel_name']}' 已存在 (ID: {existing[0]})")
            
            # 询问是否更新
            update_choice = input("是否更新现有数据? (y/n): ")
            if update_choice.lower() == 'y':
                update_sql = """
                UPDATE channels 
                SET channel_base_url = %s, channel_description = %s 
                WHERE channel_name = %s
                """
                await cursor.execute(update_sql, (
                    channel_data["channel_base_url"],
                    channel_data["channel_description"], 
                    channel_data["channel_name"]
                ))
                print(f"✅ 渠道 '{channel_data['channel_name']}' 数据已更新")
            else:
                print("跳过更新")
        else:
            # 插入新数据
            insert_sql = """
            INSERT INTO channels (channel_name, channel_base_url, channel_description) 
            VALUES (%s, %s, %s)
            """
            await cursor.execute(insert_sql, (
                channel_data["channel_name"],
                channel_data["channel_base_url"],
                channel_data["channel_description"]
            ))
            
            # 获取插入的ID
            channel_id = cursor.lastrowid
            print(f"✅ 成功插入渠道 '{channel_data['channel_name']}' (ID: {channel_id})")
        
        cursor.close()
        return True
        
    except Exception as e:
        print(f"❌ 插入渠道数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def show_channel_data(conn):
    """显示当前的渠道数据"""
    try:
        cursor = conn.cursor()
        
        select_sql = "SELECT channel_id, channel_name, channel_description, created_at FROM channels ORDER BY channel_id"
        await cursor.execute(select_sql)
        channels = await cursor.fetchall()
        
        print(f"\n📋 当前数据库中的渠道 (共{len(channels)}个):")
        if channels:
            print("-" * 80)
            print(f"{'ID':<4} {'渠道名称':<15} {'描述':<25} {'创建时间':<20}")
            print("-" * 80)
            for channel in channels:
                channel_id, name, desc, created_at = channel
                print(f"{channel_id:<4} {name:<15} {desc:<25} {created_at}")
        else:
            print("  (没有找到任何渠道)")
        
        cursor.close()
        
    except Exception as e:
        print(f"❌ 查询渠道数据失败: {e}")


async def show_channel_urls(conn, channel_name="汽车之家"):
    """显示指定渠道的URL配置"""
    try:
        cursor = conn.cursor()
        
        select_sql = "SELECT channel_base_url FROM channels WHERE channel_name = %s"
        await cursor.execute(select_sql, (channel_name,))
        result = await cursor.fetchone()
        
        if result:
            url_config = result[0]
            print(f"\n🔗 {channel_name} 的URL配置:")
            print("-" * 60)
            
            try:
                urls = json.loads(url_config)
                for key, config in urls.items():
                    print(f"\n📍 {key}:")
                    print(f"   URL: {config['url']}")
                    print(f"   描述: {config['description']}")
                    print(f"   用途: {config['usage']}")
                    print(f"   参数: {', '.join(config['params'])}")
            except json.JSONDecodeError:
                print(f"   原始数据: {url_config}")
        else:
            print(f"❌ 未找到渠道 '{channel_name}'")
        
        cursor.close()
        
    except Exception as e:
        print(f"❌ 查询URL配置失败: {e}")


async def main():
    """主函数"""
    print("🏪 VRT渠道数据初始化工具")
    print("=" * 50)
    
    # 获取数据库连接
    conn = await get_db_connection()
    if not conn:
        return
    
    try:
        # 准备汽车之家数据
        print("📝 准备汽车之家渠道数据...")
        autohome_data = prepare_autohome_data()
        
        print(f"   渠道名称: {autohome_data['channel_name']}")
        print(f"   渠道描述: {autohome_data['channel_description']}")
        print(f"   URL配置: 包含3个API端点")
        
        # 插入数据
        print(f"\n🔄 插入渠道数据...")
        success = await insert_channel_data(conn, autohome_data)
        
        if success:
            # 显示所有渠道数据
            await show_channel_data(conn)
            
            # 显示汽车之家的URL配置
            await show_channel_urls(conn, "汽车之家")
            
            print(f"\n🎉 渠道数据初始化完成!")
            print(f"\n💡 下一步:")
            print(f"1. 可以开始配置vehicle_channel_details表")
            print(f"2. 启动爬虫任务收集数据")
            print(f"3. 使用这些URL模板进行数据爬取")
        
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 