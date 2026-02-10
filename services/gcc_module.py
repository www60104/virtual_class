"""
Services Layer - GCC Module (Generate, Collect, Context)
提供 Agent 所需的上下文管理與事件記錄功能
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from services.db_manager import DBManager


class GCCModule:
    """
    GCC 模組 (Generate, Collect, Context)
    - context(): 獲取簡化上下文（最近 N 輪對話）
    - context_full(): 獲取完整上下文（所有對話與轉錄）
    - log_ota(): 記錄 Agent 事件到資料庫
    """

    def __init__(self, db_session: AsyncSession):
        self.db = DBManager(db_session)

    async def context(
        self,
        session_id: int,
        max_turns: int = 5
    ) -> Dict[str, Any]:
        """
        獲取簡化上下文（最近 N 輪對話）

        Args:
            session_id: Session ID
            max_turns: 最大對話輪數（預設 5）

        Returns:
            包含 recent_conversations 的字典
        """
        try:
            conversations = await self.db.get_session_conversations(
                session_id, limit=max_turns
            )

            recent = []
            for conv in conversations:
                recent.append({
                    "user": conv.user_message or "",
                    "agent": conv.agent_response or "",
                    "agent_type": conv.agent_type.value if conv.agent_type else "student",
                    "created_at": conv.created_at.isoformat() if conv.created_at else None
                })

            return {
                "session_id": session_id,
                "recent_conversations": recent,
                "total_turns": len(recent)
            }

        except Exception as e:
            print(f"[GCCModule] Error in context(): {e}")
            return {
                "session_id": session_id,
                "recent_conversations": [],
                "total_turns": 0,
                "error": str(e)
            }

    async def context_full(
        self,
        session_id: int
    ) -> Dict[str, Any]:
        """
        獲取完整上下文（所有對話與轉錄記錄）

        Args:
            session_id: Session ID

        Returns:
            包含 conversations 和 transcripts 的完整上下文字典
        """
        try:
            history = await self.db.get_session_history(session_id)

            conversations = []
            for conv in history.get("conversations", []):
                conversations.append({
                    "user_message": conv.user_message or "",
                    "agent_response": conv.agent_response or "",
                    "agent_type": conv.agent_type.value if conv.agent_type else "student",
                    "gcc_context": conv.gcc_context,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None
                })

            transcripts = []
            for t in history.get("transcripts", []):
                transcripts.append({
                    "speaker": t.speaker,
                    "text": t.text,
                    "source": t.source,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None
                })

            return {
                "session_id": session_id,
                "conversations": conversations,
                "transcripts": transcripts,
                "total_conversations": len(conversations),
                "total_transcripts": len(transcripts)
            }

        except Exception as e:
            print(f"[GCCModule] Error in context_full(): {e}")
            return {
                "session_id": session_id,
                "conversations": [],
                "transcripts": [],
                "error": str(e)
            }

    async def log_ota(
        self,
        session_id: int,
        event_type: str,
        data: Dict[str, Any],
        agent_type: str = "student"
    ) -> None:
        """
        記錄 Agent 事件到資料庫 (OTA = Over-The-Air logging)

        Args:
            session_id: Session ID
            event_type: 事件類型（如 'student_response', 'expert_evaluation'）
            data: 事件資料
            agent_type: Agent 類型（'student' 或 'expert'）
        """
        try:
            await self.db.create_conversation(
                session_id=session_id,
                agent_type=agent_type,
                user_message=data.get("user_input"),
                agent_response=data.get("agent_response") or data.get("evaluation"),
                gcc_context={"event_type": event_type, "data": data}
            )
            print(f"[GCCModule] Logged OTA event: {event_type} for session {session_id}")

        except Exception as e:
            print(f"[GCCModule] Error in log_ota(): {e}")
