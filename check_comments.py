"""
检查数据库中保存的评论数据
"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def check_saved_comments():
    """检查已保存的评论数据"""
    async with AsyncSessionLocal() as db:
        # 查询奥迪A3的最新评论
        result = await db.execute(text("""
            SELECT 
                rc.identifier_on_channel,
                rc.comment_content,
                rc.posted_at_on_channel,
                rc.comment_source_url,
                vcd.name_on_channel
            FROM raw_comments rc
            JOIN vehicle_channel_details vcd ON rc.vehicle_channel_id_fk = vcd.vehicle_channel_id
            WHERE vcd.identifier_on_channel = 's3170'
            ORDER BY rc.raw_comment_id DESC
            LIMIT 5
        """))
        
        comments = result.fetchall()
        
        print(f"📊 奥迪A3 最新 {len(comments)} 条评论:")
        print("=" * 80)
        
        for i, comment in enumerate(comments):
            koubei_id, content, posted_at, source_url, vehicle_name = comment
            print(f"[{i+1}] KoubeiID: {koubei_id}")
            print(f"    车型: {vehicle_name}")
            print(f"    时间: {posted_at}")
            if content:
                display_content = content[:100] + "..." if len(content) > 100 else content
                print(f"    内容: {display_content}")
            else:
                print(f"    内容: [空]")
            print(f"    来源: {source_url}")
            print()


async def check_total_comments():
    """检查评论总数统计"""
    async with AsyncSessionLocal() as db:
        # 统计各车型的评论数量
        result = await db.execute(text("""
            SELECT 
                vcd.name_on_channel,
                vcd.identifier_on_channel,
                COUNT(rc.raw_comment_id) as comment_count,
                COUNT(CASE WHEN rc.comment_content != '' THEN 1 END) as content_count
            FROM vehicle_channel_details vcd
            LEFT JOIN raw_comments rc ON vcd.vehicle_channel_id = rc.vehicle_channel_id_fk
            WHERE vcd.channel_id_fk = 1
            GROUP BY vcd.vehicle_channel_id, vcd.name_on_channel, vcd.identifier_on_channel
            HAVING comment_count > 0
            ORDER BY comment_count DESC
            LIMIT 10
        """))
        
        stats = result.fetchall()
        
        print(f"\n📈 评论统计 (前10名):")
        print("=" * 80)
        print(f"{'车型':<20} {'标识':<10} {'评论数':<8} {'有内容':<8} {'内容率':<8}")
        print("-" * 80)
        
        for name, identifier, total, with_content, in stats:
            content_rate = f"{(with_content/total*100):.1f}%" if total > 0 else "0%"
            print(f"{name:<20} {identifier:<10} {total:<8} {with_content:<8} {content_rate:<8}")


if __name__ == "__main__":
    asyncio.run(check_saved_comments())
    asyncio.run(check_total_comments()) 