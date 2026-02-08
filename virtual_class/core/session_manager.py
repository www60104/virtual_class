"""
Core Layer - Session Manager
管理使用者 Session 狀態，與 LangGraph 同步
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from services.db_manager import DBManager


class SessionManager:
    """
    Session 管理器
    - 創建、查詢、更新 Session
    - 管理 Session 狀態（active, paused, ended）
    - 與 LangGraph 狀態同步
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = DBManager(db_session)
        self._active_sessions: Dict[str, Dict[str, Any]] = {}  # 記憶體快取
    
    async def create_session(
        self,
        user_id: int,
        title: Optional[str] = None,
        livekit_room_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        創建新的 Session
        
        Returns:
            包含 session_uuid 和其他資訊的字典
        """
        session = await self.db.create_session(
            user_id=user_id,
            title=title,
            livekit_room_name=livekit_room_name
        )
        
        # 加入記憶體快取
        session_data = {
            "session_id": session.id,
            "session_uuid": session.session_uuid,
            "user_id": session.user_id,
            "title": session.title,
            "livekit_room_name": session.livekit_room_name,
            "is_active": session.is_active,
            "started_at": session.started_at,
            "state": {}  # LangGraph 狀態初始化
        }
        
        self._active_sessions[session.session_uuid] = session_data
        
        print(f"[SessionManager] Created session: {session.session_uuid}")
        return session_data
    
    async def get_session(self, session_uuid: str) -> Optional[Dict[str, Any]]:
        """
        獲取 Session 資訊（優先從快取讀取）
        """
        # 先查快取
        if session_uuid in self._active_sessions:
            return self._active_sessions[session_uuid]
        
        # 快取未命中，從資料庫讀取
        session = await self.db.get_session_by_uuid(session_uuid)
        if not session:
            return None
        
        session_data = {
            "session_id": session.id,
            "session_uuid": session.session_uuid,
            "user_id": session.user_id,
            "title": session.title,
            "livekit_room_name": session.livekit_room_name,
            "is_active": session.is_active,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "state": session.session_metadata or {}
        }
        
        # 加入快取
        if session.is_active:
            self._active_sessions[session_uuid] = session_data
        
        return session_data
    
    async def update_session_state(
        self,
        session_uuid: str,
        langgraph_state: Dict[str, Any]
    ) -> None:
        """
        更新 Session 的 LangGraph 狀態
        
        Args:
            session_uuid: Session UUID
            langgraph_state: LangGraph 狀態字典
        """
        if session_uuid in self._active_sessions:
            self._active_sessions[session_uuid]["state"] = langgraph_state
        
        # 同步到資料庫（可選，根據性能需求決定）
        # 這裡簡化處理，實際應該更新 session.session_metadata
        print(f"[SessionManager] Updated state for session: {session_uuid}")
    
    async def end_session(self, session_uuid: str) -> None:
        """結束 Session"""
        session_data = await self.get_session(session_uuid)
        if not session_data:
            return
        
        await self.db.end_session(session_data["session_id"])
        
        # 從快取移除
        self._active_sessions.pop(session_uuid, None)
        
        print(f"[SessionManager] Ended session: {session_uuid}")
    
    def get_active_sessions_count(self) -> int:
        """獲取活躍 Session 數量"""
        return len(self._active_sessions)
