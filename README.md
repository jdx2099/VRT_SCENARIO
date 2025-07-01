# VRT 用户反馈结构化解析系统

基于爬虫和大模型的用户反馈结构化解析系统，用于自动爬取汽车评论数据并进行智能分析。

## 项目结构

```
vrt_scenario/
├── app/                        # 主应用目录
│   ├── api/                    # API路由
│   │   └── endpoints/          # API端点
│   ├── core/                   # 核心配置
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic模型
│   ├── services/               # 业务服务
│   ├── utils/                  # 工具模块
│   └── tasks/                  # Celery异步任务
├── db/                         # 数据库相关
├── docs/                       # 文档
├── logs/                       # 日志文件
├── models/                     # 本地大模型存储
├── tests/                      # 测试代码
├── main.py                     # 应用入口
├── requirements.txt            # Python依赖
├── Dockerfile                  # Docker镜像构建
└── README.md                   # 项目说明
```

## 功能模块

- **爬虫模块**: 自动爬取第三方渠道车型用户反馈文本
- **文本处理**: 通过文本拆解与嵌入，结合功能模块语义匹配
- **语义匹配**: 实现精准模块定位
- **大模型解析**: 利用本地大模型对定位后的文本进行结构化信息抽取
- **数据存储**: 存储结构化结果，支持多条件查询和数据统计
- **系统管理**: 支持任务管理、日志管理和系统监控

## 快速开始

### 环境要求

- Python 3.8+
- MySQL 8.0+
- Redis
- 本地大模型 (LLaMA, ChatGLM等)
- 向量数据库 (可选: Milvus)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

```bash
# 创建.env文件，配置以下变量：
DATABASE_URL=mysql+asyncmy://username:password@localhost:3306/vrt_db
LOCAL_LLM_MODEL_PATH=/path/to/your/local/model
LOCAL_LLM_MODEL_TYPE=llama
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 数据库初始化

```sql
-- 创建数据库
CREATE DATABASE vrt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用现有的SQL脚本创建表结构
mysql -u username -p vrt_db < db/create_tables.sql
mysql -u username -p vrt_db < db/init_data.sql
```

### 启动服务

```bash
# 启动主应用
python main.py

# 启动Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# 启动Celery beat (定时任务)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Docker部署

```bash
# 构建镜像
docker build -t vrt-system .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v /path/to/models:/app/models \
  -v /path/to/logs:/app/logs \
  -e DATABASE_URL=mysql+asyncmy://user:pass@host:3306/vrt_db \
  -e LOCAL_LLM_MODEL_PATH=/app/models/your-model \
  --name vrt-system \
  vrt-system
```

## API文档

启动服务后，访问 http://localhost:8000/docs 查看API文档

## 技术栈

- **Web框架**: FastAPI
- **数据库**: MySQL + SQLAlchemy
- **异步任务**: Celery + Redis
- **文本处理**: sentence-transformers
- **大模型**: 本地大模型 + LangChain
- **容器化**: Docker

## 本地大模型支持

系统支持多种本地大模型：

- **LLaMA系列**: LLaMA, LLaMA2, Code Llama
- **ChatGLM系列**: ChatGLM-6B, ChatGLM2-6B, ChatGLM3-6B
- **百川系列**: Baichuan-13B, Baichuan2-13B
- **其他开源模型**: 支持通过LangChain集成

### 模型配置示例

```python
# 在.env文件中配置
LOCAL_LLM_MODEL_PATH=/path/to/chatglm-6b
LOCAL_LLM_MODEL_TYPE=chatglm

# 或者
LOCAL_LLM_MODEL_PATH=/path/to/llama-2-7b-chat
LOCAL_LLM_MODEL_TYPE=llama
```

## 开发指南

### 添加新的爬虫

1. 在 `app/utils/scrapers.py` 中继承 `BaseScraper` 类
2. 实现 `fetch_page` 和 `parse_comments` 方法
3. 在爬虫服务中注册新的爬虫类

### 添加新的本地模型

1. 在 `app/utils/llm_clients.py` 中的 `_load_model` 方法中添加模型加载逻辑
2. 根据模型特性调整提示词格式
3. 测试模型响应质量

### 添加新的功能模块

1. 在数据库中添加功能模块记录
2. 更新向量数据库中的模块描述向量
3. 调整语义匹配算法阈值

## 系统架构

系统采用异步架构，主要组件包括：

- **FastAPI**: Web框架，提供REST API
- **SQLAlchemy**: ORM，数据库操作
- **Celery**: 异步任务队列
- **Redis**: 缓存和消息队列
- **MySQL**: 关系数据库
- **LangChain**: 本地大模型框架
- **向量数据库**: 存储和检索文本向量

## 许可证

MIT License 