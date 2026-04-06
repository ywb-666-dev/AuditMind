"""
会员中心路由 - 会员权益和计费系统
"""
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.core.database import get_db
from backend.core.security import get_current_user, get_user_membership_level
from backend.core.config import settings
from backend.models.database import User, Subscription, Order, DetectionRecord
from backend.schemas.schemas import MembershipResponse, MessageResponse, MembershipPlan

router = APIRouter(prefix="/membership", tags=["会员中心"])


@router.get("/current", response_model=MembershipResponse)
def get_current_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取当前会员状态
    """
    membership_level = get_user_membership_level(current_user)

    # 获取订阅信息
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()

    # 计算剩余额度
    detections_remaining = -1  # -1 表示无限
    if membership_level == "free":
        detections_remaining = current_user.free_detections_remaining or 0

    return {
        "current_level": membership_level,
        "expire_at": subscription.end_at if subscription else None,
        "auto_renew": subscription.auto_renew if subscription else False,
        "detections_remaining": detections_remaining
    }


@router.get("/plans", response_model=list[MembershipPlan])
def get_membership_plans():
    """
    获取会员套餐列表（详细版）
    """
    plans = [
        MembershipPlan(
            plan_type="free",
            name="免费版",
            price=0.0,
            duration_days=30,
            benefits=[
                "每月 3 次基础检测",
                "每日 5 次 AI 问答",
                "简易报告查看",
                "舞弊概率和风险等级"
            ]
        ),
        MembershipPlan(
            plan_type="monthly",
            name="专业版（月度）",
            price=settings.MEMBERSHIP_PRICES["monthly"],
            duration_days=30,
            benefits=[
                "无限次舞弊检测",
                "每日 50 次 AI 问答",
                "PDF/HTML 报告导出",
                "SHAP 特征重要性分析",
                "检测历史永久保存",
                "风险标签详细解读",
                "优先客服支持"
            ]
        ),
        MembershipPlan(
            plan_type="yearly",
            name="企业版（年度）",
            price=settings.MEMBERSHIP_PRICES["yearly"],
            duration_days=365,
            benefits=[
                "专业版全部权益",
                "批量检测（100 家/次）",
                "API 接口调用",
                "定制报告模板",
                "专属客服经理",
                "私有化部署支持（另议）",
                "企业级数据安全"
            ]
        )
    ]

    return plans


@router.post("/upgrade")
def upgrade_membership(
    plan_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    升级会员等级
    """
    if plan_type not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的套餐类型"
        )

    # 检查是否已经是该等级
    current_level = get_user_membership_level(current_user)
    if (current_level == "pro" and plan_type == "monthly") or \
       (current_level == "enterprise" and plan_type == "yearly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经是该等级会员"
        )

    # 生成订单
    price = settings.MEMBERSHIP_PRICES.get(plan_type, 0)
    order_no = f"FD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(100000, 999999)}"

    db_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        product_type="subscription",
        product_name=f"{plan_type}会员套餐",
        product_detail={"plan": plan_type, "upgrade": True},
        amount=price,
        status="pending"
    )

    db.add(db_order)
    db.commit()

    return {
        "order_no": order_no,
        "plan_type": plan_type,
        "price": price,
        "upgrade": True
    }


@router.post("/cancel-auto-renew")
def cancel_auto_renew(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    取消自动续费
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="没有有效的订阅"
        )

    subscription.auto_renew = False
    db.commit()

    return {"message": "自动续费已取消"}


@router.get("/usage")
def get_usage_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取使用统计
    """
    membership_level = get_user_membership_level(current_user)

    # 今日检测次数
    today = datetime.utcnow().date()
    today_detections = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user.id,
        DetectionRecord.created_at >= today
    ).count()

    # 本月检测次数
    first_day_of_month = today.replace(day=1)
    month_detections = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user.id,
        DetectionRecord.created_at >= first_day_of_month
    ).count()

    # AI 问答次数
    today_qa_count = 0  # TODO: 实现问答次数统计
    month_qa_count = 0

    # 检测额度
    detections_remaining = -1
    if membership_level == "free":
        detections_remaining = current_user.free_detections_remaining or 0

    return {
        "membership_level": membership_level,
        "today_detections": today_detections,
        "month_detections": month_detections,
        "today_qa_count": today_qa_count,
        "month_qa_count": month_qa_count,
        "detections_remaining": detections_remaining,
        "max_monthly_detections": settings.FREE_USER_MONTHLY_DETECTIONS if membership_level == "free" else "无限"
    }


@router.post("/apply-coupon")
def apply_coupon(
    coupon_code: str,
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    应用优惠券
    """
    # TODO: 实现优惠券系统
    valid_coupons = {
        "WELCOME50": {"discount": 50, "min_amount": 299, "description": "新用户立减50元"},
        "NEWYEAR2026": {"discount": 100, "min_amount": 500, "description": "新年特惠100元"},
        "INVITE": {"discount": 30, "min_amount": 100, "description": "邀请好友优惠"}
    }

    if coupon_code not in valid_coupons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的优惠券代码"
        )

    coupon = valid_coupons[coupon_code]
    order = db.query(Order).filter(
        Order.order_no == order_no,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.amount < coupon["min_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单金额需满{coupon['min_amount']}元才能使用此优惠券"
        )

    # 应用优惠
    discount_amount = min(coupon["discount"], order.amount)
    order.discount_amount = discount_amount
    order.amount = order.paid_amount = order.amount - discount_amount

    db.commit()

    return {
        "message": f"优惠券 {coupon_code} 已应用",
        "discount_amount": discount_amount,
        "new_amount": order.amount
    }
