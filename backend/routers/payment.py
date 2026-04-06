"""
支付和订单路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import hashlib
import json
from urllib.parse import quote

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.database import User, Order, Transaction, Subscription
from backend.schemas.schemas import (
    OrderCreate, OrderResponse, OrderPaymentResponse,
    OrderStatusEnum, PaymentMethodEnum, MembershipLevelEnum
)

router = APIRouter(prefix="/order", tags=["支付中心"])


def generate_order_no() -> str:
    """
    生成订单号（时间戳 + 随机数）
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_str = str(uuid.uuid4())[:8].replace("-", "")
    return f"FD{timestamp}{random_str}"


def create_alipay_qr(order_no: str, amount: float, subject: str) -> dict:
    """
    创建支付宝扫码支付参数
    （简化版本，实际需使用官方 SDK）
    """
    # 构造业务参数
    biz_content = {
        "out_trade_no": order_no,
        "total_amount": str(amount),
        "subject": subject,
        "product_code": "FACE_TO_FACE_PAYMENT"
    }

    # 支付宝网关参数（模拟）
    alipay_params = {
        "app_id": settings.ALIPAY_APP_ID or "sandbox_app_id",
        "method": "alipay.trade.precreate",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(biz_content, ensure_ascii=False)
    }

    # 模拟返回（实际需调用支付宝 API）
    return {
        "qr_code": f"https://qr.alipay.com/sandbox_{order_no}",
        "out_trade_no": order_no
    }


@router.get("/membership/plans")
def get_membership_plans():
    """
    获取会员套餐列表
    """
    plans = [
        {
            "plan_type": "monthly",
            "name": "专业版月度会员",
            "price": settings.MEMBERSHIP_PRICES["monthly"],
            "duration_days": 30,
            "benefits": [
                "无限次舞弊检测",
                "每日 50 次 AI 问答",
                "PDF/HTML 报告导出",
                "SHAP 特征分析",
                "检测历史永久保存"
            ]
        },
        {
            "plan_type": "quarterly",
            "name": "专业版季度会员",
            "price": settings.MEMBERSHIP_PRICES["quarterly"],
            "duration_days": 90,
            "benefits": [
                "月度会员全部权益",
                "85 折优惠",
                "优先客服支持"
            ]
        },
        {
            "plan_type": "yearly",
            "name": "企业版年度会员",
            "price": settings.MEMBERSHIP_PRICES["yearly"],
            "duration_days": 365,
            "benefits": [
                "专业版全部权益",
                "批量检测（100 家/次）",
                "API 接口调用",
                "专属客服",
                "定制报告模板"
            ]
        }
    ]
    return plans


@router.post("/create", response_model=OrderPaymentResponse)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建订单
    """
    # 生成订单号
    order_no = generate_order_no()

    # 创建订单
    db_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        product_type=order_data.product_type,
        product_name=order_data.product_name,
        product_detail={"plan": order_data.product_type},
        amount=order_data.amount,
        payment_method=order_data.payment_method.value,
        status="pending"
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 根据支付方式生成支付参数
    if order_data.payment_method == PaymentMethodEnum.ALIPAY:
        alipay_result = create_alipay_qr(
            order_no=order_no,
            amount=order_data.amount,
            subject=order_data.product_name
        )
        return {
            "order_no": order_no,
            "qr_code": alipay_result.get("qr_code"),
            "alipay_params": alipay_result
        }
    elif order_data.payment_method == PaymentMethodEnum.WECHAT:
        # TODO: 实现微信支付
        return {
            "order_no": order_no,
            "qr_code": f"wxpay://sandbox_{order_no}"
        }
    else:
        return {
            "order_no": order_no
        }


@router.get("/{order_no}", response_model=OrderResponse)
def get_order(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取订单详情
    """
    order = db.query(Order).filter(
        Order.order_no == order_no,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    return order


@router.get("/list", response_model=list)
def get_order_list(
    page: int = 1,
    page_size: int = 10,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取订单列表
    """
    query = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc())

    if status_filter:
        query = query.filter(Order.status == status_filter)

    offset = (page - 1) * page_size
    orders = query.offset(offset).limit(page_size).all()

    return orders


@router.post("/pay/{order_no}")
def pay_order(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    确认支付（模拟支付成功回调）
    实际场景应由支付平台回调通知
    """
    order = db.query(Order).filter(
        Order.order_no == order_no,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许支付：{order.status}"
        )

    # 更新订单状态
    order.status = "paid"
    order.paid_amount = order.amount
    order.payment_time = datetime.utcnow()

    # 根据商品类型开通权益
    if order.product_type == "subscription":
        # 会员订阅
        plan_type = order.product_detail.get("plan", "monthly")
        duration_map = {
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365
        }
        duration_days = duration_map.get(plan_type, 30)

        # 获取或创建订阅
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()

        if subscription and subscription.status == "active":
            # 续费：在原有效期基础上延长
            if subscription.end_at > datetime.utcnow():
                subscription.end_at += timedelta(days=duration_days)
            else:
                # 已过期：从当前时间开始
                subscription.start_at = datetime.utcnow()
                subscription.end_at = datetime.utcnow() + timedelta(days=duration_days)
        else:
            # 新订阅
            if not subscription:
                subscription = Subscription(user_id=current_user.id)
            subscription.plan_type = plan_type
            subscription.start_at = datetime.utcnow()
            subscription.end_at = datetime.utcnow() + timedelta(days=duration_days)
            subscription.status = "active"

        db.add(subscription)

        # 更新用户会员等级
        if plan_type == "yearly":
            current_user.membership_level = "enterprise"
        else:
            current_user.membership_level = "pro"
        current_user.membership_expire_at = subscription.end_at
        current_user.free_detections_remaining = -1  # 无限检测

    elif order.product_type == "one_time":
        # 单次检测：增加检测次数
        if current_user.free_detections_remaining is None or current_user.free_detections_remaining == -1:
            current_user.free_detections_remaining = 10  # 专业版用户购买单次
        else:
            current_user.free_detections_remaining += 1

    elif order.product_type == "topup":
        # 充值：增加账户余额
        current_user.balance += order.amount

    # 创建交易流水
    transaction = Transaction(
        user_id=current_user.id,
        order_id=order.id,
        type="payment",
        amount=order.amount,
        balance_after=current_user.balance,
        description=f"支付订单 {order_no}"
    )
    db.add(transaction)

    db.commit()

    return {"message": "支付成功", "order_no": order_no}


@router.post("/topup")
def topup_balance(
    amount: float,
    payment_method: PaymentMethodEnum = PaymentMethodEnum.ALIPAY,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    账户充值
    """
    # 计算优惠金额
    bonus = 0
    for threshold, bonus_amount in settings.TOPUP_BONUS.items():
        if amount >= threshold:
            bonus = bonus_amount
            break

    total_amount = amount + bonus

    # 创建充值订单
    order_no = generate_order_no()
    db_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        product_type="topup",
        product_name="账户充值",
        product_detail={"amount": amount, "bonus": bonus},
        amount=amount,
        payment_method=payment_method.value,
        status="pending"
    )

    db.add(db_order)
    db.commit()

    return {
        "order_no": order_no,
        "amount": amount,
        "bonus": bonus,
        "total_amount": total_amount
    }


@router.post("/subscribe/{plan_type}")
def subscribe(
    plan_type: str,
    auto_renew: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    订阅会员套餐
    """
    if plan_type not in settings.MEMBERSHIP_PRICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的套餐类型"
        )

    price = settings.MEMBERSHIP_PRICES[plan_type]
    duration_map = {"monthly": 30, "quarterly": 90, "yearly": 365}
    duration_days = duration_map.get(plan_type, 30)

    # 创建订阅订单
    order_no = generate_order_no()
    db_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        product_type="subscription",
        product_name=f"{plan_type}会员套餐",
        product_detail={"plan": plan_type, "duration": duration_days, "auto_renew": auto_renew},
        amount=price,
        status="pending"
    )

    db.add(db_order)
    db.commit()

    return {
        "order_no": order_no,
        "plan_type": plan_type,
        "price": price,
        "duration_days": duration_days
    }
