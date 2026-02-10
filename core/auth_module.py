import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt

# LiveKit import (可選，離線測試時不需要)
try:
    from livekit import api
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    api = None


# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# LiveKit 配置
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")


class AuthModule:
    """認證模組：處理 JWT 與 LiveKit Token"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash 密碼"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """驗證密碼"""
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        創建 JWT Access Token
        
        Args:
            data: 要編碼的資料（通常是 {"sub": username}）
            expires_delta: 過期時間（預設 24 小時）
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        驗證 JWT Token
        
        Returns:
            解碼後的 payload，或 None（如果無效）
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
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
