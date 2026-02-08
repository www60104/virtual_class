"""
API Layer - Authentication Endpoints
處理使用者註冊、登入
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from database import get_db
from services.db_manager import DBManager
from core.auth_module import AuthModule


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Pydantic Models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    註冊新使用者
    """
    db_manager = DBManager(db)
    
    # 檢查使用者是否已存在
    existing_user = await db_manager.get_user_by_username(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = await db_manager.get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 創建新使用者
    hashed_password = AuthModule.hash_password(user.password)
    new_user = await db_manager.create_user(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    
    # 生成 JWT token
    access_token = AuthModule.create_access_token(
        data={"sub": user.username, "user_id": new_user.id}
    )
    
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    使用者登入
    """
    db_manager = DBManager(db)
    
    # 查詢使用者
    user = await db_manager.get_user_by_username(credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # 驗證密碼
    if not AuthModule.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # 生成 JWT token
    access_token = AuthModule.create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return TokenResponse(access_token=access_token)
