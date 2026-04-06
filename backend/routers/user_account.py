"""
用户账户管理路由 - 扩展功能
包含实名认证、密码管理、设备管理等
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string

from backend.core.database import get_db
from backend.core.security import get_current_user, verify_password, get_password_hash
from backend.core.config import settings
from backend.models.database import User, UserProfile
from backend.schemas.schemas import UserResponse, MessageResponse

router = APIRouter(prefix="/user", tags=["用户账户管理"])


def generate_verification_code(length=6) -> str:
    """生成验证码"""
    return ''.join(random.choice(string.digits) for _ in range(length))


@router.post("/verify-email")
def verify_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    验证邮箱（发送验证码）
    """
    # 检查邮箱是否已被其他用户使用
    existing = db.query(User).filter(
        User.email == email,
        User.id != current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被其他用户使用"
        )

    # 生成验证码
    verification_code = generate_verification_code()
    expiration = datetime.utcnow() + timedelta(minutes=15)

    # TODO: 实际发送邮件
    print(f"📧 验证码已发送到 {email}: {verification_code} (仅用于开发)")

    # 保存到 session 或缓存
    # 实际项目应使用 Redis 缓存验证码
    current_user.verification_code = verification_code
    current_user.verification_expires = expiration
    current_user.email = email

    db.commit()

    return {"message": "验证码已发送，请查收邮件"}


@router.post("/reset-password")
def reset_password(
    email: str,
    new_password: str,
    verification_code: str,
    db: Session = Depends(get_db)
):
    """
    重置密码
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 验证验证码
    if not user.verification_code or user.verification_code != verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )

    if user.verification_expires and user.verification_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期"
        )

    # 更新密码
    user.password_hash = get_password_hash(new_password)
    user.verification_code = None
    user.verification_expires = None

    db.commit()

    return {"message": "密码重置成功"}


@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改密码
    """
    # 验证旧密码
    if not verify_password(old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="原密码错误"
        )

    # 更新密码
    current_user.password_hash = get_password_hash(new_password)
    db.commit()

    return {"message": "密码修改成功"}


@router.get("/devices")
def get_login_devices(
    current_user: User = Depends(get_current_user)
):
    """
    获取登录设备列表
    """
    # TODO: 实际应记录用户登录设备信息
    # 这里返回模拟数据
    return {
        "devices": [
            {
                "device_id": "device1",
                "device_name": "Windows PC",
                "ip_address": "192.168.1.100",
                "last_login": "2026-03-30T10:30:00",
                "is_current": True
            },
            {
                "device_id": "device2",
                "device_name": "iPhone 13",
                "ip_address": "192.168.1.101",
                "last_login": "2026-03-29T15:20:00",
                "is_current": False
            }
        ]
    }


@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    撤销设备登录
    """
    # TODO: 实际应从 token 黑名单中移除该设备的 token
    if device_id == "current":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能撤销当前设备"
        )

    # 模拟成功
    return {"message": f"设备 {device_id} 已撤销登录权限"}


@router.get("/activity-log")
def get_activity_log(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user)
):
    """
    获取操作日志
    """
    # TODO: 实际应记录用户操作日志
    # 这里返回模拟数据
    total = 5
    has_next = page * page_size < total

    return {
        "items": [
            {
                "action": "login",
                "description": "用户登录",
                "ip_address": "192.168.1.100",
                "timestamp": "2026-03-30T10:30:00"
            },
            {
                "action": "detection",
                "description": "执行康美药业舞弊检测",
                "ip_address": "192.168.1.100",
                "timestamp": "2026-03-30T10:35:00"
            },
            {
                "action": "qa_ask",
                "description": "提问：什么是存贷双高？",
                "ip_address": "192.168.1.100",
                "timestamp": "2026-03-30T10:40:00"
            }
        ][(page-1)*page_size:page*page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": has_next
    }
