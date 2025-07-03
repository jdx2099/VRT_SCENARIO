"""
Celery应用配置
"""
from celery import Celery
from app.core.config import settings

# 创建Celery应用
celery_app = Celery(
    "vrt_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.crawler_tasks']
)

# 手动导入任务模块以确保任务被注册
try:
    from app.tasks import crawler_tasks
    print(f"✅ 任务模块已导入: {len([t for t in celery_app.tasks if not t.startswith('celery.')])} 个任务")
except ImportError as e:
    print(f"❌ 任务模块导入失败: {e}")

# Celery配置
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
    worker_max_tasks_per_child=1000
) 