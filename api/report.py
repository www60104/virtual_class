"""
API Layer - Report Endpoints
處理對話記錄匯出（無需登入驗證）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.db_manager import DBManager
from utils.logger import ConversationLogger


router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{session_uuid}/transcript")
async def get_session_transcript(
    session_uuid: str,
    format: str = "markdown",  # "markdown" 或 "txt"
    db: AsyncSession = Depends(get_db)
):
    """
    下載 Session 的完整轉錄文字檔

    Query Parameters:
        - format: "markdown" 或 "txt"（預設 "markdown"）
    """
    db_manager = DBManager(db)

    # 獲取 Session
    session = await db_manager.get_session_by_uuid(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # 獲取轉錄記錄
    transcripts = await db_manager.get_session_transcripts(session.id)

    if not transcripts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcripts found for this session"
        )

    # 格式化轉錄資料
    transcript_data = [
        {
            "speaker": t.speaker,
            "text": t.text,
            "timestamp": t.timestamp.isoformat() if t.timestamp else "",
            "source": t.source
        }
        for t in transcripts
    ]

    # 匯出文字檔
    logger = ConversationLogger()
    file_path = logger.export_session_transcript(
        session_uuid=session_uuid,
        transcripts=transcript_data,
        format=format
    )

    # 返回檔案下載
    return FileResponse(
        path=file_path,
        filename=file_path.split("/")[-1],
        media_type="text/markdown" if format == "markdown" else "text/plain"
    )


@router.get("/{session_uuid}/summary")
async def get_session_summary(
    session_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """
    獲取 Session 的摘要資訊
    包含對話輪數、總時長等統計
    """
    db_manager = DBManager(db)

    # 獲取 Session
    session = await db_manager.get_session_by_uuid(session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # 獲取對話和轉錄記錄
    history = await db_manager.get_session_history(session.id)

    conversations = history.get("conversations", [])
    transcripts = history.get("transcripts", [])

    return {
        "session_uuid": session_uuid,
        "title": session.title,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "is_active": session.is_active,
        "total_conversations": len(conversations),
        "total_transcripts": len(transcripts),
        "user_messages": len([t for t in transcripts if t.speaker == "user"]),
        "agent_messages": len([t for t in transcripts if t.speaker == "agent"])
    }
