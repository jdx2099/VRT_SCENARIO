# VRT 汽车评论数据爬虫系统 - 完整使用指南

## 🎯 系统概述

VRT是一个基于FastAPI + Celery + MySQL的汽车评论数据爬虫和分析系统，支持从汽车之家等渠道自动爬取车型数据和用户评论，并具备定时任务功能。

### ✨ 核心功能
- **车型数据管理**: 自动爬取和更新汽车渠道的车型信息
- **评论数据采集**: 批量爬取车型用户评论，支持增量更新  
- **异步任务处理**: 支持大数据量的非阻塞爬取
- **定时任务系统**: 基于Celery Beat的自动化任务调度
- **数据查询统计**: 提供丰富的数据查询和统计接口

---

## 🚀 快速启动

### 1. 系统要求
- Python 3.8+
- MySQL 8.0+
- Redis 6.0+

### 2. Windows环境启动（推荐）
```bash
# 使用Windows专用启动脚本
scripts/start_windows.bat

# 或使用Python脚本
python scripts/start_celery_windows.py
```

### 3. Linux/Mac环境启动
```bash
# 使用tmux启动脚本
chmod +x scripts/start_all.sh
./scripts/start_all.sh
```

### 4. 手动启动
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库（创建.env文件）
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/vrt_db
REDIS_URL=redis://localhost:6379/0

# 3. 启动FastAPI应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. 启动Celery Worker（Windows兼容）
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=1

# 5. 启动Celery Beat调度器
celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler
```

### 5. 验证启动
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/admin/health

---

## 📡 API接口使用

### 🚗 车型数据管理

#### 获取支持的渠道列表
```bash
GET /api/vehicle-update/channels
```

#### 异步更新车型数据（生产推荐）
```bash
POST /api/vehicle-update/update
{
  "channel_id": 1,
  "force_update": false
}

# 返回: {"task_id": "xxx", "status": "pending", ...}
# 查询状态: GET /api/vehicle-update/sync/{task_id}/status
```

#### 直接更新车型数据（测试用）
```bash
POST /api/vehicle-update/update/direct
{
  "channel_id": 1,
  "force_update": false
}

# 直接返回完整结果
```

### 🕷️ 评论数据爬取

#### 查询车型评论ID列表
```bash
POST /api/raw-comments/query
{
  "channel_id": 1,
  "identifier_on_channel": "s3170"
}
```

#### 统计车型评论数量
```bash
GET /api/raw-comments/vehicle/{channel_id}/{identifier}/count
```

#### 异步爬取评论（生产推荐）
```bash
POST /api/raw-comments/crawl
{
  "channel_id": 1,
  "identifier_on_channel": "s3170",
  "max_pages": 10
}

# 返回: {"task_id": "xxx", "status": "pending", ...}
# 查询状态: GET /api/raw-comments/tasks/{task_id}/status
```

#### 直接爬取评论（测试用）
```bash
POST /api/raw-comments/crawl/direct
{
  "channel_id": 1,
  "identifier_on_channel": "s3170", 
  "max_pages": 2
}

# 直接返回完整结果
```

### ⏰ 定时任务管理

#### 获取定时任务状态
```bash
GET /api/scheduled-tasks/status
```

#### 手动触发车型更新
```bash
POST /api/scheduled-tasks/vehicle-update/trigger
{
  "channel_ids": [1, 2],
  "force_update": false
}
```

#### 查询任务执行状态
```bash
GET /api/scheduled-tasks/tasks/{task_id}/status
```

#### 获取最近执行记录
```bash
GET /api/scheduled-tasks/recent-executions?limit=10
```

#### 触发健康检查
```bash
GET /api/scheduled-tasks/health-check
```

### ⏰ 定时评论爬取任务管理

#### 获取定时评论爬取任务状态
```bash
GET /api/scheduled-comment-tasks/status
```

#### 手动触发评论爬取任务
```bash
POST /api/scheduled-comment-tasks/manual-crawl/trigger
{
  "vehicle_channel_ids": [1, 2, 3],
  "max_pages_per_vehicle": 10
}
```

#### 查询评论爬取任务执行状态
```bash
GET /api/scheduled-comment-tasks/tasks/{task_id}/status
```

#### 获取车型评论爬取统计信息
```bash
GET /api/scheduled-comment-tasks/vehicle-statistics
```

#### 获取未爬取过的车型列表
```bash
GET /api/scheduled-comment-tasks/uncrawled-vehicles?limit=20
```

#### 获取最早爬取过的车型列表
```bash
GET /api/scheduled-comment-tasks/oldest-crawled-vehicles?limit=20
```

#### 获取最近的评论爬取任务执行记录
```bash
GET /api/scheduled-comment-tasks/recent-executions?limit=10
```

---

## ⏰ 定时任务系统

### 📋 功能特性

#### 1. 自动车型数据更新
- **执行频率**: 每天凌晨2点
- **功能**: 自动更新所有渠道的车型数据
- **配置**: 可指定特定渠道或更新所有渠道

#### 2. 系统健康检查
- **执行频率**: 每小时
- **功能**: 检查数据库和Redis连接状态
- **用途**: 监控系统健康状态

### 📊 定时任务配置

#### 当前配置的任务

| 任务名称 | 执行频率 | 功能描述 | 参数 |
|---------|---------|---------|------|
| `daily-vehicle-update` | 每24小时 | 更新所有渠道车型数据 | 所有渠道，不强制更新 |
| `daily-comment-crawl` | 每24小时 | 爬取20个车型的评论 | 20个车型，优先未爬取的 |
| `hourly-health-check` | 每1小时 | 系统健康检查 | 无参数 |

#### 修改定时任务配置

编辑 `app/tasks/celery_app.py` 文件中的 `beat_schedule` 配置：

```python
beat_schedule={
    # 每天凌晨2点执行车型数据更新
    'daily-vehicle-update': {
        'task': 'app.tasks.scheduled_tasks.scheduled_vehicle_update',
        'schedule': 86400.0,  # 24小时 = 86400秒
        'args': (None, False),  # 更新所有渠道，不强制更新
        'options': {'queue': 'default'}
    },
    
    # 每天晚上10点执行评论爬取任务
    'daily-comment-crawl': {
        'task': 'app.tasks.scheduled_comment_tasks.scheduled_comment_crawl',
        'schedule': 86400.0,  # 24小时 = 86400秒
        'args': (20,),  # 爬取20个车型的评论
        'options': {'queue': 'default'}
    },
    
    # 每小时执行一次健康检查
    'hourly-health-check': {
        'task': 'app.tasks.scheduled_tasks.health_check',
        'schedule': 3600.0,  # 1小时 = 3600秒
        'options': {'queue': 'default'}
    },
}
```

---

## 🎭 使用场景指南

### 🔥 生产环境 - 使用异步接口
```bash
# 1. 启动爬取任务
curl -X POST "http://localhost:8000/api/raw-comments/crawl" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": 1, "identifier_on_channel": "s3170", "max_pages": 5}'

# 响应: {"task_id": "abc123", "status": "pending"}

# 2. 轮询任务状态
curl "http://localhost:8000/api/raw-comments/tasks/abc123/status"

# 完成时响应:
{
  "status": "SUCCESS",
  "result": {
    "vehicle_name": "奥迪A3",
    "new_comments_count": 23,
    "crawl_duration": 45.6
  }
}
```

**优势**: 不阻塞、支持进度监控、可处理大数据集

### 🛠️ 开发测试 - 使用直接接口
```bash
# 直接获得完整结果
curl -X POST "http://localhost:8000/api/raw-comments/crawl/direct" \
  -H "Content-Type: application/json" \
  -d '{"channel_id": 1, "identifier_on_channel": "s3170", "max_pages": 1}'

# 立即返回:
{
  "vehicle_channel_info": {...},
  "new_comments_count": 5,
  "crawl_duration": 12.3
}
```

**优势**: 立即查看结果、便于调试、错误信息完整

---

## 🧪 测试和验证

### 快速测试脚本
```bash
# 测试定时任务功能
python test_scheduled_tasks.py

# 测试定时评论爬取任务功能
python test_scheduled_comment_tasks.py
```

### 常用测试车型
| 渠道ID | 车型标识 | 车型名称 | 说明 |
|--------|----------|----------|------|
| 1 | s3170 | 奥迪A3 | 数据较多，适合测试 |
| 1 | s7855 | 奥迪A5L | 数据适中 |
| 1 | s4525 | smart forfour | 历史数据 |

---

## 🔍 故障排查

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查MySQL服务
sudo systemctl status mysql

# 创建数据库
mysql -u root -p -e "CREATE DATABASE vrt_db CHARACTER SET utf8mb4"
```

#### 2. Redis连接失败
```bash
# 启动Redis
redis-server

# 检查连接
redis-cli ping
```

#### 3. 爬取任务失败
- 检查车型标识是否正确
- 确认渠道配置是否完整
- 查看日志: `logs/app.log`

#### 4. Celery任务不执行（Windows环境）
```bash
# 使用Windows兼容配置
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=1

# 检查Worker状态
celery -A app.tasks.celery_app inspect active
```

#### 5. 定时任务不执行
- 检查Celery Beat是否运行
- 检查Redis连接是否正常
- 检查Worker是否运行
- 查看日志文件

### 日志查看
```bash
# 应用日志
tail -f logs/app.log

# Celery日志
celery -A app.tasks.celery_app events

# 查看Celery Worker日志
tail -f logs/celery_worker.log

# 查看Celery Beat日志
tail -f logs/celery_beat.log
```

---

## 📊 数据状态监控

### 检查系统状态
```bash
# 健康检查
curl http://localhost:8000/api/admin/health

# 获取渠道信息
curl http://localhost:8000/api/vehicle-update/channels

# 统计某车型评论数
curl http://localhost:8000/api/raw-comments/vehicle/1/s3170/count

# 获取定时任务状态
curl http://localhost:8000/api/scheduled-tasks/status

# 获取定时评论爬取任务状态
curl http://localhost:8000/api/scheduled-comment-tasks/status

# 获取车型评论爬取统计
curl http://localhost:8000/api/scheduled-comment-tasks/vehicle-statistics
```

### 数据库直接查询
```sql
-- 查看车型数量
SELECT COUNT(*) FROM vehicle_channel_details;

-- 查看评论数量
SELECT COUNT(*) FROM raw_comments;

-- 查看各车型评论分布
SELECT v.name_on_channel, COUNT(r.raw_comment_id) as comment_count
FROM vehicle_channel_details v
LEFT JOIN raw_comments r ON v.vehicle_channel_id = r.vehicle_channel_id_fk
GROUP BY v.vehicle_channel_id
ORDER BY comment_count DESC;

-- 查看最近的定时任务执行记录
SELECT 
    job_id,
    job_type,
    status,
    created_at,
    started_at,
    completed_at,
    result_summary
FROM processing_jobs 
WHERE job_type IN ('scheduled_vehicle_update', 'health_check')
ORDER BY created_at DESC
LIMIT 10;
```

---

## 💡 最佳实践

### 1. 生产环境部署
- 使用异步接口避免界面卡死
- 设置合理的`max_pages`限制
- 定期监控任务执行状态
- 配置日志轮转
- 启用定时任务自动维护

### 2. 开发调试
- 使用直接接口快速验证
- 先用小数据集测试
- 查看详细日志排查问题
- Windows环境使用solo池

### 3. 数据采集策略
- 新车型: 全量爬取建立基线
- 热门车型: 定期增量更新
- 冷门车型: 低频更新

### 4. 性能优化
- 控制并发爬取任务数量
- 设置合理的延迟避免反爬虫
- 监控数据库和Redis性能
- Windows环境使用单进程Worker

### 5. 定时任务管理
- 监控定时任务执行状态
- 定期检查任务执行记录
- 配置合理的执行频率
- 设置任务超时和重试机制

---

## 🏗️ 项目结构

```
vrt_scenario/
├── app/                    # 主应用
│   ├── api/endpoints/      # API接口
│   │   ├── vehicle_update.py      # 车型更新接口
│   │   ├── raw_comment_update.py  # 评论爬取接口
│   │   └── scheduled_tasks.py     # 定时任务接口
│   ├── services/           # 业务逻辑
│   │   ├── vehicle_update_service.py      # 车型更新服务
│   │   └── raw_comment_update_service.py  # 评论爬取服务
│   ├── models/             # 数据模型
│   │   ├── vehicle_update.py      # 车型相关模型
│   │   └── raw_comment_update.py  # 评论相关模型
│   ├── schemas/            # 数据校验
│   ├── tasks/              # 异步任务
│   │   ├── celery_app.py         # Celery配置
│   │   ├── crawler_tasks.py      # 爬虫任务
│   │   └── scheduled_tasks.py    # 定时任务
│   └── utils/              # 工具模块
│       └── channel_parsers/      # 渠道解析器
├── scripts/                # 启动脚本
│   ├── start_all.sh              # Linux/Mac启动脚本
│   ├── start_windows.bat         # Windows启动脚本
│   └── start_celery_windows.py   # Windows Celery启动器
├── logs/                   # 日志文件
├── main.py                 # 应用入口
├── test_scheduled_tasks.py # 定时任务测试脚本
└── requirements.txt        # 依赖文件
```

---

## ⚠️ 注意事项

### 1. 服务依赖
- **Redis**: 必须运行，用于任务队列
- **MySQL**: 必须运行，用于数据存储
- **Celery Worker**: 必须运行，用于执行任务
- **Celery Beat**: 必须运行，用于调度任务

### 2. 时间配置
- 系统使用 `Asia/Shanghai` 时区
- 定时任务基于UTC时间执行
- 建议在服务器上设置正确的时区

### 3. 资源管理
- 定时任务会消耗系统资源
- 建议在低峰期执行大型任务
- 监控系统资源使用情况

### 4. 错误处理
- 任务失败会自动重试（最多3次）
- 失败的任务会记录在数据库中
- 可以通过API查看失败原因

### 5. Windows兼容性
- 使用solo池替代prefork池
- 建议使用单进程Worker
- 使用Windows专用启动脚本

---

## 🎯 总结

VRT系统提供了完整的汽车评论数据采集解决方案：

✅ **双模式接口**: 异步(生产) + 直接(测试)  
✅ **完整功能**: 车型管理 + 评论爬取 + 定时任务  
✅ **易于使用**: 一键启动 + 详细文档  
✅ **生产就绪**: 异步任务 + 错误处理 + 自动调度  
✅ **跨平台**: 支持Windows/Linux/Mac环境

通过本指南，您可以快速上手并充分利用系统的各项功能！

---

**版本**: 2.2.0  
**更新时间**: 2025-01-02  
**维护者**: VRT开发团队 