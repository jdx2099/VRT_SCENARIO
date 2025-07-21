#!/usr/bin/env python3
"""
Windows环境下的Celery启动脚本
解决Windows兼容性问题
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def start_celery_worker():
    """启动Celery Worker（Windows兼容）"""
    print("🚀 启动Celery Worker (Windows兼容模式)...")
    
    # Windows下的Celery Worker启动命令
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.tasks.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo",  # Windows兼容池
        "--concurrency=1"  # Windows下建议使用单进程
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=Path.cwd())
        print(f"✅ Celery Worker已启动 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ 启动Celery Worker失败: {e}")
        return None

def start_celery_beat():
    """启动Celery Beat调度器"""
    print("⏰ 启动Celery Beat调度器...")
    
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

def main():
    """主函数"""
    print("🪟 Windows环境Celery启动器")
    print("=" * 50)
    
    # 检查环境
    if os.name != 'nt':
        print("⚠️  此脚本专为Windows环境设计")
        return
    
    # 启动Worker
    worker_process = start_celery_worker()
    if not worker_process:
        return
    
    # 等待一下再启动Beat
    time.sleep(2)
    
    # 启动Beat
    beat_process = start_celery_beat()
    if not beat_process:
        worker_process.terminate()
        return
    
    print("\n🎉 所有服务已启动!")
    print("💡 提示:")
    print("   - 按 Ctrl+C 停止所有服务")
    print("   - 访问 http://localhost:8000/docs 查看API文档")
    print("   - 访问 http://localhost:8000/api/v1/scheduled-comment-tasks/status 查看任务状态")
    
    try:
        # 等待进程结束
        worker_process.wait()
        beat_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        worker_process.terminate()
        beat_process.terminate()
        print("✅ 服务已停止")

if __name__ == "__main__":
    main() 