"""
支付系统核心路由 - 完整支付流程
包含订单管理、支付回调、退款处理等
"""
import random

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import hashlib
import time
from urllib.parse import parse_qs, unquote

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.database import User, Order, Transaction, Subscription, DetectionRecord
from backend.schemas.schemas import (OrderCreate, OrderResponse, OrderPaymentResponse,
                           OrderStatusEnum, PaymentMethodEnum, MembershipLevelEnum)

router = APIRouter(prefix="/order", tags=["支付系统"])


def verify_alipay_signature(params: dict) -> bool:
    """
    验证支付宝回调签名（简化版）
    实际项目应使用官方 SDK 验证
    """
    # 1. 过滤空值和签名参数
    params_filtered = {k: v for k, v in params.items()
                        if v and k not in ['sign', 'sign_type']}

    # 2. 排序参数
    params_sorted = sorted(params_filtered.items())

    # 3. 拼接字符串
    sign_str = '&'.join([f"{k}={v}" for k, v in params_sorted])

    # 4. 验证签名（简化版，实际应使用 RSA 验证）
    # 这里直接返回True，实际项目需要替换为真正的签名验证
    return True


def handle_payment_success(order_no: str, db: Session):
    """
    处理支付成功逻辑
    """
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        return False

    if order.status != "pending":
        return False

    # 更新订单状态
    order.status = "paid"
    order.paid_amount = order.amount
    order.payment_time = datetime.utcnow()

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        return False

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
            Subscription.user_id == user.id
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
                subscription = Subscription(user_id=user.id)
            subscription.plan_type = plan_type
            subscription.start_at = datetime.utcnow()
            subscription.end_at = datetime.utcnow() + timedelta(days=duration_days)
            subscription.status = "active"
            db.add(subscription)

        # 更新用户会员等级
        if plan_type == "yearly":
            user.membership_level = "enterprise"
        else:
            user.membership_level = "pro"
        user.membership_expire_at = subscription.end_at
        user.free_detections_remaining = -1  # 无限检测

    elif order.product_type == "one_time":
        # 单次检测：增加检测次数
        if user.membership_level == "free":
            if user.free_detections_remaining is None:
                user.free_detections_remaining = 1
            else:
                user.free_detections_remaining += 1
        else:
            # 专业版用户购买单次检测
            if not hasattr(user, 'extra_detections'):
                user.extra_detections = 1
            else:
                user.extra_detections += 1

    elif order.product_type == "topup":
        # 充值：增加账户余额
        bonus = order.product_detail.get("bonus", 0)
        user.balance += order.amount + bonus

    # 创建交易流水
    transaction = Transaction(
        user_id=user.id,
        order_id=order.id,
        type="payment",
        amount=order.amount,
        balance_after=user.balance,
        description=f"支付订单 {order_no}"
    )
    db.add(transaction)

    db.commit()
    return True


@router.post("/create", response_model=OrderPaymentResponse)
def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建订单 - 完整版
    """
    # 检查商品类型
    if order_data.product_type == "subscription":
        if order_data.product_name not in ["monthly", "quarterly", "yearly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的套餐类型"
            )

    # 生成订单号
    order_no = f"FD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{random.randint(100000, 999999)}"

    # 创建订单
    product_detail = {}
    if order_data.product_type == "subscription":
        product_detail = {
            "plan": order_data.product_name,
            "duration": {"monthly": 30, "quarterly": 90, "yearly": 365}.get(order_data.product_name, 30)
        }
    elif order_data.product_type == "topup":
        # 计算充值优惠
        bonus = 0
        for threshold, bonus_amount in settings.TOPUP_BONUS.items():
            if order_data.amount >= threshold:
                bonus = bonus_amount
                break
        product_detail = {"amount": order_data.amount, "bonus": bonus}

    db_order = Order(
        order_no=order_no,
        user_id=current_user.id,
        product_type=order_data.product_type,
        product_name=order_data.product_name,
        product_detail=product_detail,
        amount=order_data.amount,
        payment_method=order_data.payment_method.value,
        status="pending"
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 根据支付方式生成支付参数
    payment_response = {
        "order_no": order_no,
        "product_type": order_data.product_type,
        "amount": order_data.amount
    }

    if order_data.payment_method == PaymentMethodEnum.ALIPAY:
        # 生成支付宝支付参数（简化版）
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        notify_url = f"{settings.ALIPAY_NOTIFY_URL}?order_no={order_no}"

        biz_content = {
            "out_trade_no": order_no,
            "total_amount": str(order_data.amount),
            "subject": order_data.product_name,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "notify_url": notify_url,
            "return_url": f"http://localhost:8501/payment-result?order_no={order_no}"
        }

        # 模拟支付宝参数（实际应使用官方 SDK 生成）
        payment_response.update({
            "alipay_params": {
                "app_id": settings.ALIPAY_APP_ID,
                "method": "alipay.trade.page.pay",
                "charset": "utf-8",
                "sign_type": "RSA2",
                "timestamp": timestamp,
                "version": "1.0",
                "biz_content": json.dumps(biz_content, ensure_ascii=False)
            },
            "payment_url": f"https://openapi.alipay.com/gateway.do?biz_content={json.dumps(biz_content)}"
        })

    elif order_data.payment_method == PaymentMethodEnum.WECHAT:
        # 微信支付（需要企业资质，简化版）
        payment_response.update({
            "qr_code": f"wxpay://sandbox_{order_no}",
            "payment_url": f"https://wxpay.example.com/pay?order_no={order_no}"
        })

    return payment_response


@router.post("/callback/alipay")
async def alipay_callback(request: Request, db: Session = Depends(get_db)):
    """
    支付宝支付回调
    """
    # 获取回调参数
    body = await request.body()
    params = parse_qs(unquote(body.decode('utf-8')))
    params = {k: v[0] for k, v in params.items()}

    # 验证签名
    if not verify_alipay_signature(params):
        raise HTTPException(status_code=400, detail="签名验证失败")

    # 验证交易状态
    trade_status = params.get('trade_status')
    if trade_status not in ['TRADE_SUCCESS', 'TRADE_FINISHED']:
        return {"status": "ignored", "message": "交易状态不成功"}

    order_no = params.get('out_trade_no')
    if not order_no:
        raise HTTPException(status_code=400, detail="缺少订单号")

    # 处理支付成功
    success = handle_payment_success(order_no, db)

    if success:
        return {"status": "success", "message": "支付处理成功"}
    else:
        raise HTTPException(status_code=400, detail="支付处理失败")


@router.post("/refund/{order_no}")
def refund_order(
    order_no: str,
    refund_reason: str = "用户申请退款",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    申请退款
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

    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态不允许退款：{order.status}"
        )

    # 检查退款时间（7天内可退款）
    if order.payment_time and (datetime.utcnow() - order.payment_time).days > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="超过7天退款期限"
        )

    # 更新订单状态
    order.status = "refunded"
    order.refund_time = datetime.utcnow()
    order.refund_amount = order.paid_amount
    order.refund_reason = refund_reason

    # 退款处理
    user = current_user

    # 根据商品类型处理退款
    if order.product_type == "subscription":
        # 会员订阅退款
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()

        if subscription:
            if subscription.start_at > datetime.utcnow():
                # 未开始的订阅，直接取消
                subscription.status = "cancelled"
            else:
                # 已开始的订阅，按比例退款
                used_days = (datetime.utcnow() - subscription.start_at).days
                total_days = (subscription.end_at - subscription.start_at).days
                refund_ratio = max(0, 1 - used_days / total_days)
                order.refund_amount = order.paid_amount * refund_ratio

                # 更新会员状态
                user.membership_level = "free"
                user.membership_expire_at = None

    elif order.product_type == "one_time":
        # 单次检测退款
        if user.free_detections_remaining and user.free_detections_remaining > 0:
            user.free_detections_remaining -= 1

    elif order.product_type == "topup":
        # 充值退款
        if user.balance >= order.refund_amount:
            user.balance -= order.refund_amount

    # 创建退款交易
    refund_transaction = Transaction(
        user_id=user.id,
        order_id=order.id,
        type="refund",
        amount=-order.refund_amount,
        balance_after=user.balance,
        description=f"退款: {refund_reason}"
    )
    db.add(refund_transaction)

    db.commit()

    return {
        "message": "退款申请成功",
        "refund_amount": order.refund_amount,
        "status": "refunded"
    }


@router.get("/payment-status/{order_no}")
def get_payment_status(
    order_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取支付状态
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

    return {
        "order_no": order_no,
        "status": order.status,
        "amount": order.amount,
        "paid_amount": order.paid_amount,
        "payment_time": order.payment_time,
        "product_type": order.product_type,
        "product_name": order.product_name
    }
