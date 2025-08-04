"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量文件
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "VRT用户反馈解析系统"
    VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # 数据库配置 (使用asyncmy驱动)
    DATABASE_URL: str = "mysql+asyncmy://root:Pass1234@localhost:3306/vrt_db"
    
    # 同步数据库配置 (使用pymysql驱动，用于Celery任务)
    SYNC_DATABASE_URL: str = "mysql+pymysql://root:Pass1234@localhost:3306/vrt_db"
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # 本地大模型配置
    LOCAL_LLM_MODEL_PATH: str = "/path/to/local/model"
    LOCAL_LLM_MODEL_TYPE: str = "llama"  # llama, chatglm, baichuan, etc.
    EMBEDDING_MODEL_PATH: Optional[str] = None
    
    # 向量数据库配置
    VECTOR_DB_HOST: str = "localhost"
    VECTOR_DB_PORT: int = 19530
    
    # 爬虫配置
    SCRAPER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_DELAY: int = 1
    MAX_RETRY: int = 3
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/app.log"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 跨域配置
    ALLOWED_ORIGINS: list = ["*"]
    
    model_config = {"env_file": ".env"}

settings = Settings() 