"""
Services Layer - Database Manager
封裝所有資料庫 CRUD 操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import User, Session, Conversation, Transcript, AgentType


class DBManager:
    """
    資料庫管理器
    - 封裝所有與 PostgreSQL 的互動
    - 提供 User, Session, Conversation, Transcript 的 CRUD
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # =========================================================================
    # User CRUD
    # =========================================================================

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根據使用者名稱查詢"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根據 Email 查詢"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根據 ID 查詢"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str
    ) -> User:
        """建立新使用者"""
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # =========================================================================
    # Session CRUD
    # =========================================================================

    async def create_session(
        self,
        user_id: int,
        title: Optional[str] = None,
        livekit_room_name: Optional[str] = None
    ) -> Session:
        """建立新的 Session"""
        session = Session(
            session_uuid=str(uuid.uuid4()),
            user_id=user_id,
            title=title or "Untitled Session",
            livekit_room_name=livekit_room_name,
            is_active=True,
            started_at=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session_by_uuid(self, session_uuid: str) -> Optional[Session]:
        """根據 UUID 查詢 Session"""
        result = await self.db.execute(
            select(Session).where(Session.session_uuid == session_uuid)
        )
        return result.scalar_one_or_none()

    async def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """根據 ID 查詢 Session"""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def end_session(self, session_id: int) -> None:
        """結束 Session"""
        await self.db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(is_active=False, ended_at=datetime.utcnow())
        )
        await self.db.flush()

    # =========================================================================
    # Conversation CRUD
    # =========================================================================

    async def create_conversation(
        self,
        session_id: int,
        agent_type: str,
        user_message: Optional[str] = None,
        agent_response: Optional[str] = None,
        langgraph_state: Optional[dict] = None,
        gcc_context: Optional[dict] = None
    ) -> Conversation:
        """建立新的對話記錄"""
        conversation = Conversation(
            session_id=session_id,
            agent_type=AgentType(agent_type),
            user_message=user_message,
            agent_response=agent_response,
            langgraph_state=langgraph_state,
            gcc_context=gcc_context
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def get_session_conversations(
        self,
        session_id: int,
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """獲取 Session 的所有對話記錄"""
        query = (
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.created_at.asc())
        )
        if limit:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Transcript CRUD
    # =========================================================================

    async def create_transcript(
        self,
        session_id: int,
        speaker: str,
        text: str,
        source: str = "slow_path",
        duration_ms: Optional[int] = None,
        audio_url: Optional[str] = None
    ) -> Transcript:
        """建立新的轉錄記錄"""
        transcript = Transcript(
            session_id=session_id,
            speaker=speaker,
            text=text,
            source=source,
            duration_ms=duration_ms,
            audio_url=audio_url
        )
        self.db.add(transcript)
        await self.db.flush()
        await self.db.refresh(transcript)
        return transcript

    async def get_session_transcripts(
        self,
        session_id: int
    ) -> List[Transcript]:
        """獲取 Session 的所有轉錄記錄"""
        result = await self.db.execute(
            select(Transcript)
            .where(Transcript.session_id == session_id)
            .order_by(Transcript.timestamp.asc())
        )
        return list(result.scalars().all())

    # =========================================================================
    # Composite Queries
    # =========================================================================

    async def get_session_history(self, session_id: int) -> Dict[str, Any]:
        """
        獲取 Session 的完整歷史記錄（對話 + 轉錄）
        """
        conversations = await self.get_session_conversations(session_id)
        transcripts = await self.get_session_transcripts(session_id)

        return {
            "conversations": conversations,
            "transcripts": transcripts
        }
