"""
Data Layer - SQLAlchemy Models
定義資料庫表結構：User, Session, Conversation, Transcript
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class UserRole(str, enum.Enum):
    """使用者角色"""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class AgentType(str, enum.Enum):
    """Agent 類型"""
    STUDENT = "student"
    EXPERT = "expert"


class User(Base):
    """使用者表"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """對話 Session 表"""
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    title: Mapped[Optional[str]] = mapped_column(String(200))
    livekit_room_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Status tracking
    is_active: Mapped[bool] = mapped_column(default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Session metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    session_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    transcripts: Mapped[list["Transcript"]] = relationship("Transcript", back_populates="session", cascade="all, delete-orphan")


class Conversation(Base):
    """對話記錄表（LangGraph 狀態相關）"""
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    
    # Agent information
    agent_type: Mapped[AgentType] = mapped_column(SQLEnum(AgentType), nullable=False)
    
    # Message content
    user_message: Mapped[Optional[str]] = mapped_column(Text)
    agent_response: Mapped[Optional[str]] = mapped_column(Text)
    
    # LangGraph state snapshot
    langgraph_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # GCC memory context
    gcc_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="conversations")


class Transcript(Base):
    """完整轉錄記錄表（慢速路徑輸出）"""
    __tablename__ = "transcripts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    
    # Speaker identification
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "agent"
    
    # Transcript content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timing information
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # audio duration in milliseconds
    
    # Source tracking (fast path vs slow path)
    source: Mapped[str] = mapped_column(String(20), default="slow_path")  # "fast_path" or "slow_path"
    
    # Audio metadata
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # if audio is stored
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="transcripts")
