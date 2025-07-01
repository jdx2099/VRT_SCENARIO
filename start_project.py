#!/usr/bin/env python3
"""
VRT项目启动脚本 - 专业版 (uvicorn + Celery + Redis)
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def check_requirements():
    """检查系统要求"""
    print("🔍 检查系统要求...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 8:
        print("❌ Python版本需要3.8+")
        return False
    print(f"✅ Python版本: {python_version.major}.{python_version.minor}")
    
    # 检查必要的文件
    required_files = [
        "requirements.txt",
        "main.py",
        "app/core/config.py",
        "app/core/database.py",
        "app/tasks/celery_app.py"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ 缺少必要文件: {file_path}")
            return False
    print("✅ 项目文件完整")
    
    return True

def create_env_file():
    """创建.env配置文件"""
    env_path = Path(".env")
    if env_path.exists():
        print("✅ .env文件已存在")
        return True
    
    print("📝 创建.env配置文件...")
    env_content = """# VRT系统环境变量配置文件

# 应用配置
PROJECT_NAME=VRT用户反馈解析系统
VERSION=2.0.0
DEBUG=True

# 数据库配置 (请修改为您的实际配置)
DATABASE_URL=mysql+asyncmy://root:password@localhost:3306/vrt_db

# Redis配置 (Celery必需)
REDIS_URL=redis://localhost:6379/0

# Celery配置 (异步任务队列)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 本地大模型配置 (可选)
LOCAL_LLM_MODEL_PATH=/path/to/your/local/model
LOCAL_LLM_MODEL_TYPE=llama
EMBEDDING_MODEL_PATH=

# 向量数据库配置
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=19530

# 爬虫配置
SCRAPER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
REQUEST_DELAY=1
MAX_RETRY=3

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log

# 安全配置 (生产环境请修改SECRET_KEY)
SECRET_KEY=development-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 跨域配置
ALLOWED_ORIGINS=["*"]
"""
    
    try:
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✅ .env文件创建成功")
        return True
    except Exception as e:
        print(f"❌ .env文件创建失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    print("📁 创建必要目录...")
    directories = ["logs", "models"]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ 目录创建完成")

def check_services():
    """检查外部服务状态"""
    print("🔍 检查外部服务状态...")
    
    print("⚠️  【重要】请确保以下服务已启动:")
    print("  1. MySQL服务 - 数据存储")
    print("  2. Redis服务 - Celery消息队列和结果存储")
    
    print("\n💡 启动服务命令:")
    print("  MySQL: sudo systemctl start mysql (Linux) 或 brew services start mysql (Mac)")
    print("  Redis:  sudo systemctl start redis (Linux) 或 brew services start redis (Mac)")
    print("  Windows: 通过服务管理器启动")

def install_dependencies():
    """安装依赖"""
    print("📦 安装项目依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def run_tests():
    """运行测试"""
    print("🧪 运行项目测试...")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 测试通过")
        else:
            print("⚠️  部分测试失败，但可以继续启动")
        return True
    except FileNotFoundError:
        print("⚠️  pytest未安装，跳过测试")
        return True

def show_startup_guide():
    """显示启动指南"""
    print("\n🚀 VRT系统启动指南")
    print("=" * 60)
    
    print("\n📋 【必须】按顺序启动以下服务:")
    
    print("\n1️⃣ 启动FastAPI主应用 (uvicorn):")
    print("   开发环境:")
    print("   uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    print("   生产环境:")
    print("   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4")
    
    print("\n2️⃣ 启动Celery Worker (异步任务处理) - 新终端:")
    print("   celery -A app.tasks.celery_app worker --loglevel=info")
    print("   📝 这个进程处理爬虫、文本处理、LLM解析等耗时任务")
    
    print("\n3️⃣ 启动Celery Beat (定时任务调度) - 新终端 [可选]:")
    print("   celery -A app.tasks.celery_app beat --loglevel=info")
    
    print("\n4️⃣ 启动Celery Flower (任务监控) - 新终端 [可选]:")
    print("   celery -A app.tasks.celery_app flower --port=5555")
    print("   访问: http://localhost:5555")
    
    print("\n🌐 访问地址:")
    print("   - API文档: http://localhost:8000/docs")
    print("   - 健康检查: http://localhost:8000/api/admin/health")
    print("   - 任务监控: http://localhost:5555 (如果启动了Flower)")
    
    print("\n💡 启动方式对比:")
    print("   uvicorn命令行: 专业推荐，便于调试和配置")
    print("   python main.py: 已移除，不建议使用")

def start_services_interactive():
    """交互式启动服务"""
    print("\n" + "=" * 60)
    print("🎯 快速启动选项")
    print("=" * 60)
    
    choices = {
        "1": "启动uvicorn开发服务器 (推荐)",
        "2": "仅显示启动命令 (手动执行)",
        "3": "运行数据库初始化",
        "4": "退出"
    }
    
    for key, value in choices.items():
        print(f"{key}. {value}")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == "1":
        print("\n🚀 启动uvicorn开发服务器...")
        print("💡 请在其他终端窗口启动Celery Worker和Beat")
        print("   Celery Worker: celery -A app.tasks.celery_app worker --loglevel=info")
        print("   Celery Beat:   celery -A app.tasks.celery_app beat --loglevel=info")
        print("\n按Ctrl+C停止服务...")
        
        try:
            subprocess.run([
                "uvicorn", "main:app", 
                "--reload", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ])
        except KeyboardInterrupt:
            print("\n👋 应用已停止")
        except FileNotFoundError:
            print("❌ uvicorn未安装，请先安装: pip install uvicorn")
    
    elif choice == "2":
        show_startup_guide()
    
    elif choice == "3":
        print("\n🗄️ 启动数据库初始化...")
        try:
            subprocess.run([sys.executable, "init_database.py"])
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    elif choice == "4":
        print("👋 退出启动向导")
    
    else:
        print("❌ 无效选择")

def main():
    """主函数"""
    print("🎯 VRT用户反馈解析系统启动向导 (Professional Edition)")
    print("=" * 70)
    
    # 检查系统要求
    if not check_requirements():
        print("❌ 系统要求检查失败，请解决后重试")
        return
    
    # 创建配置文件
    if not create_env_file():
        print("❌ 配置文件创建失败")
        return
    
    # 创建目录
    create_directories()
    
    # 检查服务
    check_services()
    
    # 安装依赖
    if not install_dependencies():
        print("❌ 依赖安装失败")
        return
    
    # 运行测试
    run_tests()
    
    # 显示启动指南
    show_startup_guide()
    
    # 交互式启动
    start_services_interactive()

if __name__ == "__main__":
    main() 