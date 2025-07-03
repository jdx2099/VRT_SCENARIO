# VRT 汽车评论数据爬虫系统 - 使用指南

## 🎯 系统概述

VRT是一个基于FastAPI + Celery + MySQL的汽车评论数据爬虫和分析系统，支持从汽车之家等渠道自动爬取车型数据和用户评论。

### ✨ 核心功能
- **车型数据管理**: 自动爬取和更新汽车渠道的车型信息
- **评论数据采集**: 批量爬取车型用户评论，支持增量更新  
- **异步任务处理**: 支持大数据量的非阻塞爬取
- **数据查询统计**: 提供丰富的数据查询和统计接口

---

## 🚀 快速启动

### 1. 系统要求
- Python 3.8+
- MySQL 8.0+
- Redis 6.0+

### 2. 一键启动（推荐）
```bash
python start_project.py
```

### 3. 手动启动
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库（创建.env文件）
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/vrt_db
REDIS_URL=redis://localhost:6379/0

# 3. 初始化数据库
python init_database.py

# 4. 启动服务
python main.py

# 5. 启动异步任务（新终端）
celery -A app.tasks.celery_app worker --loglevel=info
```

### 4. 验证启动
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
# 测试车型更新
python test_api_simple.py

# 测试评论爬取完整流程
python test_full_crawl.py

# 验证数据库数据
python check_comments.py
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

#### 4. Celery任务不执行
```bash
# 检查Worker状态
celery -A app.tasks.celery_app inspect active

# 重启Worker
celery -A app.tasks.celery_app worker --loglevel=info
```

### 日志查看
```bash
# 应用日志
tail -f logs/app.log

# Celery日志
celery -A app.tasks.celery_app events
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
```

---

## 💡 最佳实践

### 1. 生产环境部署
- 使用异步接口避免界面卡死
- 设置合理的`max_pages`限制
- 定期监控任务执行状态
- 配置日志轮转

### 2. 开发调试
- 使用直接接口快速验证
- 先用小数据集测试
- 查看详细日志排查问题

### 3. 数据采集策略
- 新车型: 全量爬取建立基线
- 热门车型: 定期增量更新
- 冷门车型: 低频更新

### 4. 性能优化
- 控制并发爬取任务数量
- 设置合理的延迟避免反爬虫
- 监控数据库和Redis性能

---

## 🏗️ 项目结构

```
vrt_scenario/
├── app/                    # 主应用
│   ├── api/endpoints/      # API接口
│   ├── services/           # 业务逻辑
│   ├── models/             # 数据模型
│   ├── schemas/            # 数据校验
│   ├── tasks/              # 异步任务
│   └── utils/              # 工具模块
├── logs/                   # 日志文件
├── main.py                 # 应用入口
├── start_project.py        # 启动脚本
└── requirements.txt        # 依赖文件
```

---

## 🎯 总结

VRT系统提供了完整的汽车评论数据采集解决方案：

✅ **双模式接口**: 异步(生产) + 直接(测试)  
✅ **完整功能**: 车型管理 + 评论爬取  
✅ **易于使用**: 一键启动 + 详细文档  
✅ **生产就绪**: 异步任务 + 错误处理

通过本指南，您可以快速上手并充分利用系统的各项功能！ 