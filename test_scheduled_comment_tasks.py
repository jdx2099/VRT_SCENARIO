#!/usr/bin/env python3
"""
定时评论爬取任务测试脚本
用于测试定时评论爬取功能的各个组件
"""
import asyncio
import time
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.logging import app_logger
from app.tasks.celery_app import celery_app
from app.tasks.scheduled_comment_tasks import scheduled_comment_crawl, manual_comment_crawl


def test_scheduled_comment_crawl():
    """测试定时评论爬取任务"""
    print("🧪 测试定时评论爬取任务")
    print("=" * 50)
    
    try:
        # 启动任务
        task = scheduled_comment_crawl.delay(max_vehicles=5)  # 只爬取5个车型进行测试
        print(f"✅ 定时评论爬取任务已启动: task_id={task.id}")
        
        # 轮询任务状态
        while True:
            result = celery_app.AsyncResult(task.id)
            if result.ready():
                if result.successful():
                    print("🎉 定时评论爬取任务完成!")
                    print(f"📊 结果: {result.result}")
                else:
                    print(f"❌ 定时评论爬取任务失败: {result.info}")
                break
            else:
                print(f"⏳ 任务状态: {result.status}")
                if hasattr(result, 'info') and result.info:
                    print(f"   进度: {result.info.get('progress', 0)}%")
                    print(f"   状态: {result.info.get('status', '')}")
                time.sleep(5)
                
    except Exception as e:
        print(f"❌ 测试定时评论爬取任务失败: {e}")


def test_manual_comment_crawl():
    """测试手动评论爬取任务"""
    print("\n🧪 测试手动评论爬取任务")
    print("=" * 50)
    
    try:
        # 启动任务（不指定车型ID，让系统自动选择）
        task = manual_comment_crawl.delay(
            vehicle_channel_ids=None,  # 自动选择
            max_pages_per_vehicle=3    # 每个车型最多爬取3页
        )
        print(f"✅ 手动评论爬取任务已启动: task_id={task.id}")
        
        # 轮询任务状态
        while True:
            result = celery_app.AsyncResult(task.id)
            if result.ready():
                if result.successful():
                    print("🎉 手动评论爬取任务完成!")
                    print(f"📊 结果: {result.result}")
                else:
                    print(f"❌ 手动评论爬取任务失败: {result.info}")
                break
            else:
                print(f"⏳ 任务状态: {result.status}")
                if hasattr(result, 'info') and result.info:
                    print(f"   进度: {result.info.get('progress', 0)}%")
                    print(f"   状态: {result.info.get('status', '')}")
                time.sleep(5)
                
    except Exception as e:
        print(f"❌ 测试手动评论爬取任务失败: {e}")


def test_celery_connection():
    """测试Celery连接"""
    print("🔌 测试Celery连接")
    print("=" * 30)
    
    try:
        # 测试Celery连接
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✅ Celery连接正常")
            print(f"📊 活跃Worker数量: {len(stats)}")
            for worker_name, worker_stats in stats.items():
                print(f"   - {worker_name}: {worker_stats.get('pool', {}).get('processes', 'N/A')} 进程")
        else:
            print("⚠️ 没有找到活跃的Celery Worker")
            print("💡 请确保已启动Celery Worker:")
            print("   celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=1")
            
    except Exception as e:
        print(f"❌ Celery连接测试失败: {e}")
        print("💡 请检查Redis服务是否运行")


def test_beat_schedule():
    """测试定时任务配置"""
    print("\n⏰ 测试定时任务配置")
    print("=" * 30)
    
    try:
        beat_schedule = celery_app.conf.beat_schedule
        print(f"📅 配置的定时任务数量: {len(beat_schedule)}")
        
        for task_name, task_config in beat_schedule.items():
            schedule_seconds = task_config['schedule']
            if schedule_seconds < 60:
                schedule_str = f"{schedule_seconds}秒"
            elif schedule_seconds < 3600:
                schedule_str = f"{schedule_seconds/60:.1f}分钟"
            elif schedule_seconds < 86400:
                schedule_str = f"{schedule_seconds/3600:.1f}小时"
            else:
                schedule_str = f"{schedule_seconds/86400:.1f}天"
            
            print(f"  - {task_name}: {task_config['task']} (每{schedule_str})")
            
            # 检查评论爬取任务
            if 'comment' in task_name.lower() or 'comment' in task_config['task'].lower():
                print(f"    ✅ 找到评论爬取任务: {task_name}")
                
    except Exception as e:
        print(f"❌ 定时任务配置测试失败: {e}")


async def test_api_endpoints():
    """测试API端点（需要FastAPI服务运行）"""
    print("\n🌐 测试API端点")
    print("=" * 30)
    
    try:
        import httpx
        
        # 测试API端点
        async with httpx.AsyncClient() as client:
            # 测试定时评论爬取任务状态
            response = await client.get("http://localhost:8000/api/scheduled-comment-tasks/status")
            if response.status_code == 200:
                print("✅ 定时评论爬取任务状态API正常")
                data = response.json()
                print(f"📊 定时任务数量: {data.get('total_scheduled_comment_tasks', 0)}")
            else:
                print(f"❌ 定时评论爬取任务状态API失败: {response.status_code}")
            
            # 测试车型统计API
            response = await client.get("http://localhost:8000/api/scheduled-comment-tasks/vehicle-statistics")
            if response.status_code == 200:
                print("✅ 车型统计API正常")
                data = response.json()
                print(f"📊 总车型数: {data.get('total_vehicles', 0)}")
                print(f"📊 已爬取车型数: {data.get('crawled_vehicles', 0)}")
                print(f"📊 未爬取车型数: {data.get('uncrawled_vehicles', 0)}")
            else:
                print(f"❌ 车型统计API失败: {response.status_code}")
                
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        print("💡 请确保FastAPI服务正在运行: uvicorn main:app --reload")


def main():
    """主测试函数"""
    print("🚀 定时评论爬取任务测试脚本")
    print("=" * 60)
    
    # 测试Celery连接
    test_celery_connection()
    
    # 测试定时任务配置
    test_beat_schedule()
    
    # 测试API端点
    try:
        asyncio.run(test_api_endpoints())
    except Exception as e:
        print(f"⚠️ API端点测试跳过: {e}")
    
    # 询问是否执行实际任务测试
    print("\n" + "=" * 60)
    choice = input("是否执行实际的评论爬取任务测试? (y/N): ").strip().lower()
    
    if choice in ['y', 'yes']:
        print("\n⚠️ 注意: 这将执行实际的评论爬取任务，可能需要较长时间")
        confirm = input("确认继续? (y/N): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            # 测试手动评论爬取任务
            test_manual_comment_crawl()
            
            # 测试定时评论爬取任务
            test_scheduled_comment_crawl()
        else:
            print("❌ 用户取消测试")
    else:
        print("✅ 跳过实际任务测试")
    
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    main() 