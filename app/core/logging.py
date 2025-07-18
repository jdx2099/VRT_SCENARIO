"""
日志配置管理
"""
import sys
from loguru import logger
from app.core.config import settings

def setup_logging():
    """
    配置应用日志
    """
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL
    )
    
    # 添加文件处理器
    logger.add(
        settings.LOG_FILE_PATH,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="100 MB",
        retention="30 days",
        compression="zip"
    )
    
    return logger

# 初始化日志
app_logger = setup_logging() 