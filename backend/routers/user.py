"""
用户认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.core.database import get_db
from backend.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from backend.core.config import settings
from backend.models.database import User, UserProfile
from backend.schemas.schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    UserUpdate, UserProfileCreate, UserProfileResponse,
    MembershipLevelEnum
)

router = APIRouter(prefix="/user", tags=["用户认证"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )

    # 检查手机号是否已存在
    if user_data.phone:
        existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )

    # 创建新用户
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password),
        user_type=user_data.user_type.value,
        membership_level="free",
        free_detections_remaining=settings.FREE_USER_MONTHLY_DETECTIONS,
        detection_reset_date=datetime.utcnow().date() + timedelta(days=30)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 创建用户资料
    db_profile = UserProfile(user_id=db_user.id)
    db.add(db_profile)
    db.commit()

    return db_user


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    """
    # 查找用户
    user = db.query(User).filter(
        (User.username == login_data.username) |
        (User.email == login_data.username) |
        (User.phone == login_data.username)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 生成 Token
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户信息
    """
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户信息
    """
    update_data = user_data.model_dump(exclude_unset=True)

    # 检查邮箱是否已被其他用户使用
    if user_data.email and user_data.email != current_user.email:
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )

    # 检查手机号是否已被其他用户使用
    if user_data.phone and user_data.phone != current_user.phone:
        existing = db.query(User).filter(
            User.phone == user_data.phone,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被其他用户使用"
            )

    # 更新用户信息
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/profile", response_model=UserProfileResponse)
def update_user_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户资料（实名认证）
    """
    # 获取或创建用户资料
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # 更新资料
    if profile_data.real_name:
        profile.real_name = profile_data.real_name
    if profile_data.id_card:
        profile.id_card = profile_data.id_card  # TODO: 加密存储
    if profile_data.company_name:
        profile.company_name = profile_data.company_name
    if profile_data.credit_code:
        profile.credit_code = profile_data.credit_code

    # 检查是否已认证
    if profile.real_name and profile.id_card:
        profile.certified = True
        profile.certified_at = datetime.utcnow()
    elif profile.company_name and profile.credit_code:
        profile.certified = True
        profile.certified_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)

    return profile


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出（客户端删除 token 即可）
    """
    return {"message": "登出成功"}
