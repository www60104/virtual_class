import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.db_manager import DBManager
from core.auth_module import AuthModule
from api.session import get_current_user


router = APIRouter(prefix="/livekit", tags=["LiveKit"])


class LiveKitTokenRequest(BaseModel):
    session_uuid: str


class LiveKitTokenResponse(BaseModel):
    token: str
    url: str
    room_name: str

class QuickTokenResponse(BaseModel):
    token: str
    url: str
    session_uuid: str


@router.post("/token", response_model=LiveKitTokenResponse)
async def generate_livekit_token(
    request: LiveKitTokenRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    生成 LiveKit Access Token
    
    使用者需要提供 session_uuid，系統會：
    1. 驗證 session 存在
    2. 獲取 LiveKit 房間名稱
    3. 生成 Access Token
    """
    db_manager = DBManager(db)
    
    # 獲取 Session
    session = await db_manager.get_session_by_uuid(request.session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # 檢查 Session 是否屬於當前使用者
    if session.user_id != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # 生成 LiveKit Token
    user_id = current_user.get("user_id")
    username = current_user.get("sub")
    
    token = AuthModule.generate_livekit_token(
        room_name=session.livekit_room_name,
        participant_identity=str(user_id),
        participant_name=username
    )
    
    import os
    livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    
    return LiveKitTokenResponse(
        token=token,
        url=livekit_url,
        room_name=session.livekit_room_name
    )


@router.post("/quick_token", response_model=QuickTokenResponse)
async def quick_token(db: AsyncSession = Depends(get_db)):
    """
    [Testing only] 快速獲取 Token，無需登入
    自動使用 guest_student 帳號
    """
    db_manager = DBManager(db)
    
    # 1. 檢查或創建 Guest User
    username = "guest_student"
    user = await db_manager.get_user_by_username(username)
    if not user:
        # 密碼隨便給，因為不會用到登入
        user = await db_manager.create_user(
            username=username,
            email="guest@example.com",
            hashed_password="dummy_hash_password_for_testing"
        )
    
    # 2. 創建 Session
    # Fix: 使用固定房間名稱以便於本地測試 (Agent 可持續連線)
    room_name = "quick-test-room"
    session = await db_manager.create_session(
        user_id=user.id,
        title="Quick Test Session",
        livekit_room_name=room_name
    )
    
    # 3. 生成 Token
    token = AuthModule.generate_livekit_token(
        room_name=session.livekit_room_name,
        participant_identity=str(user.id),
        participant_name=username
    )
    
    import os
    livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    
    return QuickTokenResponse(
        token=token,
        url=livekit_url,
        session_uuid=session.session_uuid
    )
