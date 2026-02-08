"""
API Layer - Session Endpoints
處理 Session 創建、查詢
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.db_manager import DBManager
from core.auth_module import AuthModule
from core.session_manager import SessionManager


router = APIRouter(prefix="/session", tags=["Session"])


# Pydantic Models
class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: int
    session_uuid: str
    title: Optional[str]
    livekit_room_name: Optional[str]
    is_active: bool
    started_at: str


# Helper function: Get current user from JWT
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    從 JWT Token 獲取當前使用者
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = AuthModule.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload


@router.post("/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    創建新的 Session
    """
    user_id = current_user.get("user_id")
    
    session_manager = SessionManager(db)
    
    # 生成 LiveKit 房間名稱
    import uuid
    livekit_room_name = f"room_{uuid.uuid4().hex[:8]}"
    
    session = await session_manager.create_session(
        user_id=user_id,
        title=session_data.title,
        livekit_room_name=livekit_room_name
    )
    
    return SessionResponse(
        session_id=session["session_id"],
        session_uuid=session["session_uuid"],
        title=session["title"],
        livekit_room_name=session["livekit_room_name"],
        is_active=session["is_active"],
        started_at=session["started_at"].isoformat() if session["started_at"] else ""
    )


@router.get("/{session_uuid}", response_model=SessionResponse)
async def get_session(
    session_uuid: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取 Session 資訊
    """
    session_manager = SessionManager(db)
    session = await session_manager.get_session(session_uuid)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionResponse(
        session_id=session["session_id"],
        session_uuid=session["session_uuid"],
        title=session["title"],
        livekit_room_name=session["livekit_room_name"],
        is_active=session["is_active"],
        started_at=session["started_at"].isoformat() if session.get("started_at") else ""
    )


@router.post("/{session_uuid}/end")
async def end_session(
    session_uuid: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    結束 Session
    """
    session_manager = SessionManager(db)
    await session_manager.end_session(session_uuid)
    
    return {"message": "Session ended successfully"}
