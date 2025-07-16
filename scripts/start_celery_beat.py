#!/usr/bin/env python3
"""
Celery Beat 调度器启动脚本
用于启动定时任务调度器
"""
import os
import sys
import signal
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.tasks.celery_app import celery_app
from app.core.logging import app_logger
from app.core.config import settings

def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    app_logger.info("🛑 收到关闭信号，正在停止Celery Beat...")
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app_logger.info("⏰ 启动Celery Beat定时任务调度器...")
    app_logger.info(f"📋 项目名称: {settings.PROJECT_NAME}")
    app_logger.info(f"📋 版本: {settings.VERSION}")
    app_logger.info(f"📋 Redis Broker: {settings.CELERY_BROKER_URL}")
    app_logger.info(f"📋 Redis Backend: {settings.CELERY_RESULT_BACKEND}")
    
    # 显示配置的定时任务
    beat_schedule = celery_app.conf.beat_schedule
    app_logger.info(f"📅 配置的定时任务数量: {len(beat_schedule)}")
    
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
        
        app_logger.info(f"  - {task_name}: {task_config['task']} (每{schedule_str})")
    
    try:
        # 启动Celery Beat
        app_logger.info("🚀 正在启动Celery Beat调度器...")
        
        # 这里我们直接使用celery的命令行接口
        # 在实际部署中，应该使用: celery -A app.tasks.celery_app beat
        os.system(f"celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler")
        
    except KeyboardInterrupt:
        app_logger.info("🛑 用户中断，正在关闭...")
    except Exception as e:
        app_logger.error(f"❌ Celery Beat启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 