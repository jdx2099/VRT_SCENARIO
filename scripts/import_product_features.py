#!/usr/bin/env python3
"""
产品功能模块数据导入脚本
从CSV文件导入功能模块数据到product_features表
"""
import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_sync_session
from app.models.comment_processing import ProductFeature
from app.core.logging import app_logger


def import_product_features_from_csv(csv_file_path: str):
    """
    从CSV文件导入产品功能模块数据
    
    Args:
        csv_file_path: CSV文件路径
    """
    try:
        print(f"📂 读取CSV文件: {csv_file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            print(f"❌ CSV文件不存在: {csv_file_path}")
            return False
        
        # 读取CSV文件
        df = pd.read_csv(csv_file_path, encoding='utf-8')
        print(f"📊 CSV文件包含 {len(df)} 行数据")
        
        # 检查必要的列
        required_columns = ['id', '功能模块名称', '功能模块描述']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ CSV文件缺少必要的列: {missing_columns}")
            print(f"📋 可用列: {list(df.columns)}")
            return False
        
        # 数据库操作
        with get_sync_session() as session:
            print("🔄 开始导入数据...")
            
            # 检查是否已有数据
            existing_count = session.query(ProductFeature).count()
            if existing_count > 0:
                print(f"⚠️ 数据库中已有 {existing_count} 条功能模块数据")
                response = input("是否清空现有数据重新导入？(y/N): ")
                if response.lower() == 'y':
                    session.query(ProductFeature).delete()
                    session.commit()
                    print("🗑️ 已清空现有数据")
                else:
                    print("❌ 取消导入")
                    return False
            
            # 批量导入数据
            imported_count = 0
            failed_count = 0
            
            for index, row in df.iterrows():
                try:
                    # 创建ProductFeature对象
                    feature = ProductFeature(
                        feature_code=str(row['id']).strip(),
                        feature_name=str(row['功能模块名称']).strip(),
                        feature_description=str(row['功能模块描述']).strip(),
                        hierarchy_level=1,  # 默认层级
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    session.add(feature)
                    imported_count += 1
                    
                    # 每100条提交一次
                    if imported_count % 100 == 0:
                        session.commit()
                        print(f"✅ 已导入 {imported_count} 条数据...")
                        
                except Exception as e:
                    failed_count += 1
                    print(f"❌ 导入第 {index+1} 行失败: {e}")
                    continue
            
            # 最终提交
            session.commit()
            
            print(f"🎉 数据导入完成!")
            print(f"✅ 成功导入: {imported_count} 条")
            print(f"❌ 失败: {failed_count} 条")
            
            # 验证导入结果
            total_count = session.query(ProductFeature).count()
            print(f"📊 数据库中总计: {total_count} 条功能模块数据")
            
            return True
            
    except Exception as e:
        print(f"❌ 导入过程中发生错误: {e}")
        return False


def show_sample_data():
    """显示示例数据"""
    try:
        with get_sync_session() as session:
            features = session.query(ProductFeature).limit(10).all()
            
            if features:
                print("\n📋 示例数据 (前10条):")
                print("-" * 80)
                for feature in features:
                    print(f"代码: {feature.feature_code}")
                    print(f"名称: {feature.feature_name}")
                    print(f"描述: {feature.feature_description[:100]}...")
                    print("-" * 80)
            else:
                print("📭 数据库中没有功能模块数据")
                
    except Exception as e:
        print(f"❌ 查询示例数据失败: {e}")


def main():
    """主函数"""
    print("🚀 产品功能模块数据导入工具")
    print("=" * 60)
    
    # 默认CSV文件路径
    default_csv_path = "c:/Dev/PYSeries/vrt_scenario/temp/functional_modules_output_v2.csv"
    
    # 获取CSV文件路径
    csv_path = input(f"请输入CSV文件路径 (默认: {default_csv_path}): ").strip()
    if not csv_path:
        csv_path = default_csv_path
    
    # 导入数据
    if import_product_features_from_csv(csv_path):
        print("\n🎉 导入成功!")
        show_sample_data()
    else:
        print("\n❌ 导入失败!")
    
    print("\n" + "=" * 60)
    print("导入完成")


if __name__ == "__main__":
    main()