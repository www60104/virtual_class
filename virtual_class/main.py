"""
Main Application Entry Point
FastAPI Server + LiveKit Worker Launcher
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, close_db
from api import auth, session, report, livekit_token


# =============================================================================
# Application Lifespan (Startup & Shutdown)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用生命週期管理
    - Startup: 初始化資料庫
    - Shutdown: 關閉資料庫連線
    """
    # Startup
    print("[INFO] Starting Virtual Class Voice AI System...")
    await init_db()
    print("[INFO] Database initialized")
    
    yield
    
    # Shutdown
    print("[INFO] Shutting down...")
    await close_db()
    print("[INFO] Database connections closed")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Virtual Class Voice AI API",
    description="雙路徑語音 AI 系統：快速 Speech-to-Speech + 慢速轉錄記錄",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware（開發環境允許所有來源，生產環境應限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境改為具體的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(auth.router)
app.include_router(session.router)
app.include_router(report.router)
app.include_router(livekit_token.router)


@app.get("/")
async def root():
    """根路由 - API 健康檢查"""
    return {
        "message": "Virtual Class Voice AI API",
        "status": "running",
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy"}


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # 從環境變數讀取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("ENV", "development") == "development"
    
    print(f"""
    ╔════════════════════════════════════════════════════════╗
    ║   Virtual Class Voice AI System - FastAPI Server      ║
    ╠════════════════════════════════════════════════════════╣
    ║   URL: http://{host}:{port}                       ║
    ║   Docs: http://{host}:{port}/docs                 ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
