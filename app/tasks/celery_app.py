"""
Celery应用配置
"""
import logging
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings



# 创建Celery应用
celery_app = Celery(
    "vrt_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks']
)

# 手动导入任务模块以确保任务被注册
try:
    from app.tasks import crawler_tasks, scheduled_vehicle_tasks, scheduled_comment_tasks
    print(f"✅ 任务模块已导入: {len([t for t in celery_app.tasks if not t.startswith('celery.')])} 个任务")
    print(f"   已注册的任务: {[t for t in celery_app.tasks if not t.startswith('celery.')]}")
except ImportError as e:
    print(f"❌ 任务模块导入失败: {e}")

# Celery配置 - Windows兼容版本
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    task_soft_time_limit=25 * 60,  # 25分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Windows兼容性配置
    worker_pool='solo',  # 在Windows上使用solo池而不是prefork
    broker_connection_retry_on_startup=True,
    task_always_eager=False,  # 确保任务异步执行
    
    # 定时任务配置
    beat_schedule={
        # 每周日凌晨2点执行车型数据更新
        'weekly-vehicle-update': {
            'task': 'app.tasks.scheduled_vehicle_tasks.scheduled_vehicle_update',
            # 'schedule': crontab(hour=2, minute=0, day_of_week=0),  # 每周日凌晨2点 (0=周日)
            'schedule': crontab(hour=16, minute=30),  # 每周日凌晨2点 (0=周日)
            'args': (None, False),  # 更新所有渠道，不强制更新
            'options': {'queue': 'celery'}
        },
        
        # 每天晚上11点执行评论爬取任务
        'daily-comment-crawl': {
            'task': 'app.tasks.scheduled_comment_tasks.scheduled_comment_crawl',
            # 'schedule': crontab(hour=23, minute=0),  # 每天晚上11点
            'schedule': crontab(hour=18, minute=24),  # 每天晚上11点
            'args': (1,),  # 爬取20个车型的评论
            'options': {'queue': 'celery'}
        },
        
        # 每小时执行一次健康检查
        'hourly-health-check': {
            'task': 'app.tasks.scheduled_vehicle_tasks.health_check',
            'schedule': 3600.0,  # 1小时 = 3600秒
            'options': {'queue': 'celery'}
        },
    },
    
    # Beat调度器配置
    beat_max_loop_interval=300,  # 最大循环间隔5分钟
    beat_sync_every=1,  # 每次同步的任务数量
) 