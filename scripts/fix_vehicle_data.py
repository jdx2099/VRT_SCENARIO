#!/usr/bin/env python3
"""
数据修复脚本
修复vehicle_channel_details表中的空字段问题
"""
import sys
import os
import asyncio
import re
from sqlalchemy import text
from sqlalchemy.orm import Session

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.core.logging import app_logger
from app.models.vehicle_update import VehicleChannelDetail


async def fix_empty_brand_names():
    """
    修复temp_brand_name字段为空的记录
    尝试从name_on_channel中提取品牌信息
    """
    app_logger.info("🔧 开始修复vehicle_channel_details表中的空品牌名称")
    
    try:
        with next(get_db()) as db:
            # 查询temp_brand_name为空的记录
            empty_brand_records = db.query(VehicleChannelDetail).filter(
                (VehicleChannelDetail.temp_brand_name.is_(None)) |
                (VehicleChannelDetail.temp_brand_name == '')
            ).all()
            
            app_logger.info(f"找到 {len(empty_brand_records)} 条需要修复的记录")
            
            fixed_count = 0
            for record in empty_brand_records:
                # 尝试从车型名称中提取品牌
                brand_name = extract_brand_from_vehicle_name(record.name_on_channel)
                
                if brand_name:
                    record.temp_brand_name = brand_name
                    if not record.temp_series_name:
                        record.temp_series_name = record.name_on_channel
                    fixed_count += 1
                    app_logger.debug(f"修复记录 {record.vehicle_channel_id}: {record.name_on_channel} -> 品牌: {brand_name}")
            
            if fixed_count > 0:
                db.commit()
                app_logger.info(f"✅ 成功修复 {fixed_count} 条记录")
            else:
                app_logger.info("ℹ️ 没有需要修复的记录")
                
    except Exception as e:
        app_logger.error(f"❌ 修复品牌名称失败: {e}")
        raise


def extract_brand_from_vehicle_name(vehicle_name: str) -> str:
    """
    从车型名称中提取品牌名称
    
    Args:
        vehicle_name: 车型名称
        
    Returns:
        提取的品牌名称
    """
    if not vehicle_name:
        return ""
    
    # 常见品牌名称映射
    brand_patterns = {
        # 德系品牌
        r'^(奔驰|Mercedes|梅赛德斯)': '奔驰',
        r'^(宝马|BMW)': '宝马',
        r'^(奥迪|Audi)': '奥迪',
        r'^(大众|Volkswagen)': '大众',
        r'^(保时捷|Porsche)': '保时捷',
        
        # 日系品牌
        r'^(丰田|Toyota)': '丰田',
        r'^(本田|Honda)': '本田',
        r'^(日产|Nissan)': '日产',
        r'^(马自达|Mazda)': '马自达',
        r'^(三菱|Mitsubishi)': '三菱',
        r'^(斯巴鲁|Subaru)': '斯巴鲁',
        r'^(雷克萨斯|Lexus)': '雷克萨斯',
        r'^(英菲尼迪|Infiniti)': '英菲尼迪',
        r'^(讴歌|Acura)': '讴歌',
        
        # 美系品牌
        r'^(福特|Ford)': '福特',
        r'^(别克|Buick)': '别克',
        r'^(雪佛兰|Chevrolet)': '雪佛兰',
        r'^(凯迪拉克|Cadillac)': '凯迪拉克',
        r'^(林肯|Lincoln)': '林肯',
        r'^(Jeep|吉普)': 'Jeep',
        
        # 法系品牌
        r'^(标致|Peugeot)': '标致',
        r'^(雪铁龙|Citroen)': '雪铁龙',
        r'^(雷诺|Renault)': '雷诺',
        
        # 英系品牌
        r'^(路虎|Land Rover)': '路虎',
        r'^(捷豹|Jaguar)': '捷豹',
        r'^(劳斯莱斯|Rolls-Royce)': '劳斯莱斯',
        r'^(宾利|Bentley)': '宾利',
        r'^(MINI)': 'MINI',
        
        # 意大利品牌
        r'^(法拉利|Ferrari)': '法拉利',
        r'^(兰博基尼|Lamborghini)': '兰博基尼',
        r'^(玛莎拉蒂|Maserati)': '玛莎拉蒂',
        r'^(阿尔法·罗密欧|Alfa Romeo)': '阿尔法·罗密欧',
        r'^(菲亚特|Fiat)': '菲亚特',
        
        # 韩系品牌
        r'^(现代|Hyundai)': '现代',
        r'^(起亚|Kia)': '起亚',
        r'^(捷尼赛思|Genesis)': '捷尼赛思',
        
        # 国产品牌
        r'^(比亚迪|BYD)': '比亚迪',
        r'^(吉利|Geely)': '吉利',
        r'^(长城|Great Wall)': '长城',
        r'^(哈弗|Haval)': '哈弗',
        r'^(奇瑞|Chery)': '奇瑞',
        r'^(长安|Changan)': '长安',
        r'^(红旗|Hongqi)': '红旗',
        r'^(蔚来|NIO)': '蔚来',
        r'^(小鹏|XPeng)': '小鹏',
        r'^(理想|Li Auto)': '理想',
        r'^(特斯拉|Tesla)': '特斯拉',
    }
    
    # 尝试匹配品牌
    for pattern, brand in brand_patterns.items():
        if re.match(pattern, vehicle_name, re.IGNORECASE):
            return brand
    
    # 如果没有匹配到，尝试提取第一个词作为品牌
    words = vehicle_name.split()
    if words:
        first_word = words[0]
        # 过滤掉一些明显不是品牌的词
        if first_word not in ['新', '全新', '改款', '国产', '进口', '电动']:
            return first_word
    
    return "未知品牌"


async def fix_empty_series_names():
    """
    修复temp_series_name字段为空的记录
    """
    app_logger.info("🔧 开始修复vehicle_channel_details表中的空车系名称")
    
    try:
        with next(get_db()) as db:
            # 查询temp_series_name为空的记录
            empty_series_records = db.query(VehicleChannelDetail).filter(
                (VehicleChannelDetail.temp_series_name.is_(None)) |
                (VehicleChannelDetail.temp_series_name == '')
            ).all()
            
            app_logger.info(f"找到 {len(empty_series_records)} 条需要修复的记录")
            
            fixed_count = 0
            for record in empty_series_records:
                # 暂时使用车型名称作为车系名称
                if record.name_on_channel:
                    record.temp_series_name = record.name_on_channel
                    fixed_count += 1
                    app_logger.debug(f"修复记录 {record.vehicle_channel_id}: 车系名称设为 {record.name_on_channel}")
            
            if fixed_count > 0:
                db.commit()
                app_logger.info(f"✅ 成功修复 {fixed_count} 条记录")
            else:
                app_logger.info("ℹ️ 没有需要修复的记录")
                
    except Exception as e:
        app_logger.error(f"❌ 修复车系名称失败: {e}")
        raise


async def show_data_statistics():
    """
    显示数据统计信息
    """
    try:
        with next(get_db()) as db:
            # 总记录数
            total_count = db.query(VehicleChannelDetail).count()
            
            # 品牌名称为空的记录数
            empty_brand_count = db.query(VehicleChannelDetail).filter(
                (VehicleChannelDetail.temp_brand_name.is_(None)) |
                (VehicleChannelDetail.temp_brand_name == '')
            ).count()
            
            # 车系名称为空的记录数
            empty_series_count = db.query(VehicleChannelDetail).filter(
                (VehicleChannelDetail.temp_series_name.is_(None)) |
                (VehicleChannelDetail.temp_series_name == '')
            ).count()
            
            # 按渠道统计
            channel_stats = db.execute(text("""
                SELECT channel_id_fk, COUNT(*) as count 
                FROM vehicle_channel_details 
                GROUP BY channel_id_fk
            """)).fetchall()
            
            app_logger.info("📊 数据统计信息:")
            app_logger.info(f"  总记录数: {total_count}")
            app_logger.info(f"  品牌名称为空: {empty_brand_count}")
            app_logger.info(f"  车系名称为空: {empty_series_count}")
            app_logger.info("  渠道分布:")
            for channel_id, count in channel_stats:
                app_logger.info(f"    渠道 {channel_id}: {count} 条记录")
                
    except Exception as e:
        app_logger.error(f"❌ 获取统计信息失败: {e}")


async def main():
    """主函数"""
    app_logger.info("🚀 开始执行数据修复脚本")
    
    try:
        # 显示修复前的统计信息
        await show_data_statistics()
        
        # 修复品牌名称
        await fix_empty_brand_names()
        
        # 修复车系名称
        await fix_empty_series_names()
        
        # 显示修复后的统计信息
        app_logger.info("\n📊 修复后的统计信息:")
        await show_data_statistics()
        
        app_logger.info("✅ 数据修复脚本执行完成")
        
    except Exception as e:
        app_logger.error(f"❌ 数据修复脚本执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 