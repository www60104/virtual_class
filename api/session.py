"""
API Layer - Session Endpoints
處理 Session 創建、查詢（無需登入驗證）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from database import get_db
from services.db_manager import DBManager
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


@router.post("/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    創建新的 Session（無需登入）
    自動使用 guest 使用者
    """
    db_manager = DBManager(db)

    # 使用 guest 使用者
    username = "guest_student"
    user = await db_manager.get_user_by_username(username)
    if not user:
        user = await db_manager.create_user(
            username=username,
            email="guest@example.com",
            hashed_password="no_auth_required"
        )

    session_manager = SessionManager(db)

    # 生成 LiveKit 房間名稱
    livekit_room_name = f"room_{uuid.uuid4().hex[:8]}"

    session = await session_manager.create_session(
        user_id=user.id,
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
    db: AsyncSession = Depends(get_db)
):
    """
    結束 Session
    """
    session_manager = SessionManager(db)
    await session_manager.end_session(session_uuid)

    return {"message": "Session ended successfully"}
