# Tasks包初始化文件

# 导入所有任务模块以确保任务被注册到Celery
from . import crawler_tasks
from . import scheduled_vehicle_tasks
from . import scheduled_comment_tasks

__all__ = ['crawler_tasks', 'scheduled_vehicle_tasks', 'scheduled_comment_tasks'] 