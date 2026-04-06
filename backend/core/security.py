"""
用户认证和安全工具
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.database import User

# 🔥 关键修改：替换为无冲突、无长度限制的算法
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（无需截断，支持任意长度）"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希（无需截断，支持任意长度）"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Access Token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码 JWT Access Token
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户（依赖注入用）
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def get_user_membership_level(user: User) -> str:
    """
    获取用户会员等级（考虑过期时间）
    """
    if user.membership_level != "free":
        # 检查会员是否过期
        if user.membership_expire_at and user.membership_expire_at < datetime.utcnow():
            # 会员已过期，降级为免费版
            user.membership_level = "free"
            user.membership_expire_at = None
            return "free"
    return user.membership_level


def check_detection_quota(user: User) -> bool:
    """
    检查用户是否有检测额度
    """
    membership_level = get_user_membership_level(user)

    if membership_level == "free":
        # 检查月度额度
        if user.free_detections_remaining is None or user.free_detections_remaining <= 0:
            return False
        # 检查是否到了重置日期
        if user.detection_reset_date and user.detection_reset_date < datetime.utcnow().date():
            # 重置额度
            user.free_detections_remaining = settings.FREE_USER_MONTHLY_DETECTIONS
            user.detection_reset_date = datetime.utcnow().date() + timedelta(days=30)
        return user.free_detections_remaining > 0
    else:
        # 专业版和企业版无限额度
        return True


def consume_detection_quota(user: User) -> int:
    """
    消耗检测额度，返回剩余额度
    """
    membership_level = get_user_membership_level(user)

    if membership_level == "free":
        if user.free_detections_remaining and user.free_detections_remaining > 0:
            user.free_detections_remaining -= 1
            return user.free_detections_remaining
    # 专业版和企业版不扣减额度
    return -1  # 表示无限


def check_ai_question_quota(user: User) -> bool:
    """
    检查用户是否有 AI 问答额度
    """
    membership_level = get_user_membership_level(user)

    quotas = {
        "free": settings.FREE_USER_DAILY_AI_QUESTIONS,
        "pro": settings.PRO_USER_DAILY_AI_QUESTIONS,
        "enterprise": settings.ENTERPRISE_USER_DAILY_AI_QUESTIONS,
    }

    quota = quotas.get(membership_level, 0)
    return quota <= 0 or (user.free_detections_remaining is None or user.free_detections_remaining < quota)