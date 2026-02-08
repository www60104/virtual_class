"""
Database Configuration
配置異步 SQLAlchemy 引擎與 Session Factory
"""
import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from models import Base

# 載入 .env 檔案
load_dotenv()

# 從環境變數讀取資料庫 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/virtual_class"
)

# 如果是 Heroku 或其他雲端平台，可能需要轉換
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


# 創建異步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 開發時顯示 SQL，生產環境建議設為 False
    future=True,
    pool_pre_ping=True,  # 檢查連線是否存活
    poolclass=NullPool if os.getenv("TESTING") else None,  # 測試時使用 NullPool
)


# Session Factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes
    提供資料庫 session，用於 FastAPI 的依賴注入
    
    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化資料庫（創建所有表）
    僅在開發環境使用，生產環境建議使用 Alembic 進行遷移
    """
    async with engine.begin() as conn:
        # 刪除所有表（危險！僅用於開發）
        # await conn.run_sync(Base.metadata.drop_all)
        
        # 創建所有表
        await conn.run_sync(Base.metadata.create_all)
    
    print("[INFO] Database tables created successfully!")


async def close_db():
    """
    關閉資料庫連線（應用關閉時調用）
    """
    await engine.dispose()
    print("[INFO] Database connections closed.")
