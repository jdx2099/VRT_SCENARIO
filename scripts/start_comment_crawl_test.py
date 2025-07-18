#!/usr/bin/env python3
"""
评论爬取功能测试启动脚本
用于快速测试评论爬取功能
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_services():
    """检查必要服务是否运行"""
    print("🔍 检查必要服务...")
    
    # 检查Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis服务正常")
    except Exception as e:
        print(f"❌ Redis服务异常: {e}")
        return False
    
    # 检查MySQL（通过Python连接测试）
    try:
        from app.core.database import sync_engine
        with sync_engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ MySQL服务正常")
    except Exception as e:
        print(f"❌ MySQL服务异常: {e}")
        return False
    
    return True

def start_celery_worker():
    """启动Celery Worker"""
    print("🚀 启动Celery Worker...")
    
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.tasks.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo",
        "--concurrency=1"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=Path.cwd())
        print(f"✅ Celery Worker已启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ 启动Celery Worker失败: {e}")
        return None

def start_celery_beat():
    """启动Celery Beat"""
    print("⏰ 启动Celery Beat...")
    
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.tasks.celery_app",
        "beat",
        "--loglevel=info",
        "--scheduler=celery.beat.PersistentScheduler"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=Path.cwd())
        print(f"✅ Celery Beat已启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ 启动Celery Beat失败: {e}")
        return None

def start_fastapi():
    """启动FastAPI服务"""
    print("🌐 启动FastAPI服务...")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=Path.cwd())
        print(f"✅ FastAPI服务已启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ 启动FastAPI服务失败: {e}")
        return None

def test_comment_crawl():
    """测试评论爬取功能"""
    print("\n🧪 测试评论爬取功能...")
    
    try:
        from app.tasks.scheduled_comment_tasks import manual_comment_crawl
        from app.tasks.celery_app import celery_app
        
        # 启动一个简单的测试任务
        task = manual_comment_crawl.delay(
            vehicle_channel_ids=None,
            max_pages_per_vehicle=2  # 只爬取2页进行测试
        )
        
        print(f"✅ 测试任务已启动: {task.id}")
        
        # 等待任务完成
        while True:
            result = celery_app.AsyncResult(task.id)
            if result.ready():
                if result.successful():
                    print("🎉 测试任务完成!")
                    print(f"📊 结果: {result.result}")
                else:
                    print(f"❌ 测试任务失败: {result.info}")
                break
            else:
                print(f"⏳ 任务状态: {result.status}")
                time.sleep(3)
                
    except Exception as e:
        print(f"❌ 测试评论爬取功能失败: {e}")

def main():
    """主函数"""
    print("🚀 评论爬取功能测试启动脚本")
    print("=" * 50)
    
    # 检查服务
    if not check_services():
        print("❌ 服务检查失败，请确保Redis和MySQL服务正在运行")
        return
    
    # 启动服务
    worker_process = start_celery_worker()
    if not worker_process:
        return
    
    time.sleep(3)  # 等待Worker启动
    
    beat_process = start_celery_beat()
    if not beat_process:
        worker_process.terminate()
        return
    
    time.sleep(2)  # 等待Beat启动
    
    fastapi_process = start_fastapi()
    if not fastapi_process:
        worker_process.terminate()
        beat_process.terminate()
        return
    
    print("\n🎉 所有服务已启动!")
    print("💡 提示:")
    print("   - API文档: http://localhost:8000/docs")
    print("   - 评论爬取API: http://localhost:8000/api/scheduled-comment-tasks/")
    print("   - 按 Ctrl+C 停止所有服务")
    
    # 询问是否进行测试
    try:
        choice = input("\n是否进行评论爬取功能测试? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            test_comment_crawl()
    except KeyboardInterrupt:
        pass
    
    # 等待用户中断
    try:
        print("\n🛑 按 Ctrl+C 停止所有服务...")
        worker_process.wait()
        beat_process.wait()
        fastapi_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        worker_process.terminate()
        beat_process.terminate()
        fastapi_process.terminate()
        print("✅ 服务已停止")

if __name__ == "__main__":
    main() 