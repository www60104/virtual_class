"""
Core Layer - Auth Module
僅保留 LiveKit Token 生成功能（已移除 JWT 登入驗證）
"""
import os
from typing import Optional

# LiveKit import (可選，離線測試時不需要)
try:
    from livekit import api
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    api = None


# LiveKit 配置
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")


class AuthModule:
    """認證模組：處理 LiveKit Token 生成"""

    @staticmethod
    def generate_livekit_token(
        room_name: str,
        participant_identity: str,
        participant_name: Optional[str] = None
    ) -> str:
        """
        生成 LiveKit Access Token

        Args:
            room_name: LiveKit 房間名稱
            participant_identity: 參與者唯一識別（通常是 user_id）
            participant_name: 參與者顯示名稱（選填）

        Returns:
            LiveKit token 字串
        """
        if not LIVEKIT_AVAILABLE:
            raise ImportError("LiveKit 未安裝，離線測試時不需要此功能")

        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(participant_identity) \
            .with_name(participant_name or participant_identity) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            ))

        return token.to_jwt()
