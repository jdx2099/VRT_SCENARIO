"""
数据库连接管理
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings
from contextlib import contextmanager

# 创建异步数据库引擎 (MySQL with asyncmy)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,  # MySQL连接回收时间
    pool_size=10,        # asyncmy建议较小的连接池
    max_overflow=20,     # 减少溢出连接
    # asyncmy特定配置
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    }
)

# 创建同步数据库引擎（用于Celery任务）
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
    }
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建同步会话工厂（用于Celery任务）
SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False
)

# 创建基础模型类
Base = declarative_base()

# 依赖注入：获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 同步会话上下文管理器（用于Celery任务）
@contextmanager
def get_sync_session():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close() 