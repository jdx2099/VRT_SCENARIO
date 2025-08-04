# 评论语义处理模块使用说明

## 概述

评论语义处理模块是一个基于Celery的定时任务系统，用于对原始评论进行结构化提取和语义相似度检索。该模块能够：

1. 从`raw_comments`表中提取待处理的评论
2. 对评论内容进行文本分块
3. 使用语义搜索匹配相关的产品功能模块
4. 将处理结果存储到`processed_comments`表

## 系统架构

```
评论语义处理模块
├── 模型层 (Models)
│   ├── ProductFeature - 产品功能模块模型
│   └── ProcessedComment - 处理后评论模型
├── 服务层 (Services)
│   ├── SemanticSearchService - 语义搜索服务
│   └── CommentProcessingService - 评论处理服务
├── 任务层 (Tasks)
│   └── ScheduledCommentProcessingTasks - 定时任务
└── API层 (API)
    └── CommentProcessingAPI - REST API接口
```

## 配置要求

### 1. 环境配置

在 `app/core/config.py` 中添加以下配置：

```python
# 语义搜索配置
EMBEDDING_API_BASE = "http://localhost:11434/v1"
EMBEDDING_API_KEY = "ollama"
EMBEDDING_MODEL_NAME = "Qwen3-Embedding-8B-local"
SEMANTIC_SIMILARITY_THRESHOLD = 0.7
```

### 2. 数据库表

确保数据库中存在以下表：
- `product_features` - 产品功能模块表
- `processed_comments` - 处理后评论表
- `raw_comments` - 原始评论表（需要有`processing_status`字段）

## 安装和部署

### 1. 安装依赖

```bash
pip install langchain langchain-openai chromadb pandas
```

### 2. 导入产品功能模块数据

```bash
# 运行数据导入脚本
python scripts/import_product_features.py
```

### 3. 启动Celery服务

```bash
# 启动Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo --concurrency=1

# 启动Celery Beat调度器
celery -A app.tasks.celery_app beat --loglevel=info --scheduler=celery.beat.PersistentScheduler
```

### 4. 启动FastAPI应用

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 使用方法

### 1. API接口使用

#### 启动语义处理任务

```bash
curl -X POST "http://localhost:8000/api/comment-processing/start-semantic-processing" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 20}'
```

#### 获取处理状态

```bash
curl -X GET "http://localhost:8000/api/comment-processing/status"
```

#### 获取特定任务状态

```bash
curl -X GET "http://localhost:8000/api/comment-processing/task-status/{task_id}"
```

#### 手动处理（测试用）

```bash
curl -X POST "http://localhost:8000/api/comment-processing/manual-processing" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 5}'
```

### 2. 直接调用服务

```python
from app.services.comment_processing_service import comment_processing_service

# 处理单条评论
result = comment_processing_service.process_single_comment(comment_id=123)

# 批量处理评论
result = comment_processing_service.process_batch_comments(limit=20)

# 获取处理统计
stats = comment_processing_service.get_processing_statistics()
```

### 3. 定时任务配置

定时任务默认每5分钟执行一次，可以在 `app/tasks/scheduled_comment_processing_tasks.py` 中修改：

```python
@celery_app.task(bind=True)
@periodic_task(run_every=crontab(minute='*/5'))  # 每5分钟执行一次
def scheduled_comment_semantic_processing(self, batch_size: int = 20):
    # 任务逻辑
```

## 测试和验证

### 1. 运行测试脚本

```bash
python test_comment_processing.py
```

测试脚本会验证：
- 数据库连接
- 产品功能模块数据
- 原始评论数据
- 语义搜索服务
- 评论处理服务
- 批量处理功能
- 处理统计功能

### 2. 查看日志

```bash
# 查看Celery Worker日志
tail -f celery_worker.log

# 查看应用日志
tail -f app.log
```

## 数据流程

```
1. 原始评论 (raw_comments)
   ↓ processing_status = 'new'
2. 语义搜索服务
   ↓ 文本分块 + 向量搜索
3. 功能模块匹配 (product_features)
   ↓ 相似度计算
4. 处理结果存储 (processed_comments)
   ↓ 包含匹配结果和向量
5. 状态更新
   ↓ processing_status = 'completed'
```

## 性能优化

### 1. 批处理大小

- 默认批处理大小：20条评论
- 可根据服务器性能调整：1-100条
- 建议在测试环境先小批量测试

### 2. 向量存储

- 使用Chroma向量数据库
- 支持持久化存储
- 自动索引优化

### 3. 并发控制

- Celery Worker使用solo池（Windows兼容）
- 可根据需要调整并发数
- 避免数据库连接池耗尽

## 故障排除

### 1. 常见问题

**问题：嵌入模型连接失败**
```
解决：检查EMBEDDING_API_BASE配置，确保本地模型服务正在运行
```

**问题：没有待处理评论**
```
解决：检查raw_comments表中是否有processing_status='new'的记录
```

**问题：向量搜索结果为空**
```
解决：检查product_features表是否有数据，运行import_product_features.py导入
```

### 2. 调试模式

在配置文件中启用调试模式：

```python
DEBUG = True
LOG_LEVEL = "DEBUG"
```

### 3. 监控指标

- 处理成功率
- 平均处理时间
- 语义匹配准确率
- 系统资源使用情况

## API文档

启动应用后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持基本的语义搜索和评论处理
- 提供REST API接口
- 支持定时任务调度

## 联系支持

如有问题或建议，请联系开发团队。