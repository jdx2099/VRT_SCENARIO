# 🚀 VRT项目快速启动指南

## 📋 系统要求

- **Python**: 3.8+
- **MySQL**: 8.0+
- **Redis**: 6.0+
- **Chrome**: 最新版本（用于Selenium爬虫，可选）

## ⚡ 快速启动 (推荐)

### 1. 使用启动脚本（一键启动）
```bash
# 运行启动向导，自动完成环境检查、依赖安装等
python start_project.py
```

这个脚本会自动完成：
- ✅ 检查系统要求
- ✅ 创建.env配置文件
- ✅ 安装Python依赖
- ✅ 创建必要目录
- ✅ 运行测试
- ✅ 启动应用

## 🔧 手动启动

### 1. 环境准备
```bash
# 克隆项目后进入目录
cd vrt_scenario

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件
创建 `.env` 文件并配置以下内容：
```env
# 数据库配置（请修改为实际配置）
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/vrt_db

# Redis配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 安全配置
SECRET_KEY=your-secret-key-change-in-production

# 其他配置保持默认即可...
```

### 3. 数据库初始化
```bash
# 首先在MySQL中创建数据库
mysql -u root -p -e "CREATE DATABASE vrt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 运行数据库初始化脚本
python init_database.py
```

### 4. 启动服务

#### 主应用 (终端1)
```bash
python main.py
```

#### Celery Worker (终端2)
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

#### Celery Beat定时任务 (终端3，可选)
```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

## 🌐 访问应用

启动成功后，可以访问：

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/admin/health

## 🧪 测试项目

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_text_processing.py -v

# 查看测试覆盖率
pytest tests/ --cov=app
```

## 🐳 Docker启动 (可选)

```bash
# 构建镜像
docker build -t vrt-system .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  -e DATABASE_URL=mysql+asyncmy://user:pass@host:3306/vrt_db \
  --name vrt-system \
  vrt-system
```

## 🔍 常见问题

### 1. 数据库连接失败
- 检查MySQL服务是否启动
- 确认数据库已创建：`CREATE DATABASE vrt_db;`
- 检查.env文件中的DATABASE_URL配置

### 2. Redis连接失败
- 确认Redis服务已启动：`redis-server`
- 检查Redis端口是否被占用

### 3. 依赖安装失败
```bash
# 升级pip
pip install --upgrade pip

# 使用清华源安装
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 4. Selenium相关错误
```bash
# Ubuntu/Debian安装ChromeDriver
sudo apt-get install chromium-browser chromium-chromedriver

# 或手动下载ChromeDriver并添加到PATH
```

### 5. 端口占用
```bash
# 查看端口占用
netstat -an | grep 8000

# 修改main.py中的端口号
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

## 📁 项目结构说明

```
vrt_scenario/
├── app/                    # 主应用目录
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── schemas/           # Pydantic模型
│   ├── services/          # 业务服务
│   ├── tasks/             # Celery任务
│   └── utils/             # 工具模块
├── tests/                 # 测试文件
├── logs/                  # 日志文件
├── main.py               # 应用入口
├── start_project.py      # 启动脚本
├── init_database.py      # 数据库初始化
└── requirements.txt      # 依赖文件
```

## 🎯 功能模块

- **爬虫管理**: `/api/crawler/*` - 管理爬虫任务
- **文本处理**: `/api/text/*` - 文本分割和嵌入
- **语义匹配**: `/api/semantic/*` - 功能模块匹配
- **大模型解析**: `/api/llm/*` - 结构化信息抽取
- **查询统计**: `/api/query/*` - 数据查询和统计
- **系统管理**: `/api/admin/*` - 系统监控和管理

## 💡 开发建议

1. **日志查看**: 日志文件保存在 `logs/app.log`
2. **配置修改**: 修改 `.env` 文件后需重启应用
3. **数据库变更**: 修改模型后运行 `python init_database.py`
4. **测试驱动**: 新功能开发前先编写测试用例

## 🆘 获取帮助

如果遇到问题，请检查：
1. `logs/app.log` 中的错误日志
2. 终端中的错误输出
3. 系统资源使用情况
4. 网络连接状态

---

🎉 **恭喜！您的VRT系统已经成功启动！** 