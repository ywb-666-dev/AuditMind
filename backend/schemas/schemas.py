"""
Pydantic Schemas - 请求和响应数据验证
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ================= 枚举类型 =================

class UserTypeEnum(str, Enum):
    """用户类型枚举"""
    INDIVIDUAL = "individual"
    ENTERPRISE = "enterprise"
    REGULATOR = "regulator"
    AUDITOR = "auditor"


class MembershipLevelEnum(str, Enum):
    """会员等级枚举"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class RiskLevelEnum(str, Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OrderStatusEnum(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethodEnum(str, Enum):
    """支付方式枚举"""
    ALIPAY = "alipay"
    WECHAT = "wechat"
    BANK_TRANSFER = "bank_transfer"


# ================= 用户相关 Schema =================

class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    user_type: UserTypeEnum = UserTypeEnum.INDIVIDUAL


class UserCreate(UserBase):
    """用户创建请求"""
    password: str = Field(..., min_length=6)
    captcha: Optional[str] = None  # 验证码


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """用户更新请求"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    user_type: Optional[UserTypeEnum] = None


class UserProfileCreate(BaseModel):
    """用户资料创建请求"""
    real_name: Optional[str] = Field(None, max_length=50)
    id_card: Optional[str] = Field(None, max_length=18)
    company_name: Optional[str] = Field(None, max_length=200)
    credit_code: Optional[str] = Field(None, max_length=18)


class UserResponse(UserBase):
    """用户响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    membership_level: MembershipLevelEnum
    membership_expire_at: Optional[datetime] = None
    balance: float = 0.0
    free_detections_remaining: Optional[int] = None
    created_at: datetime

    profile: Optional["UserProfileResponse"] = None


class UserProfileResponse(BaseModel):
    """用户资料响应"""
    model_config = ConfigDict(from_attributes=True)

    real_name: Optional[str] = None
    company_name: Optional[str] = None
    certified: bool = False


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ================= 检测相关 Schema =================

class DetectionCreate(BaseModel):
    """检测创建请求"""
    company_name: str
    stock_code: Optional[str] = None
    year: Optional[int] = None
    financial_data: Optional[Dict[str, Any]] = None
    mdna_text: Optional[str] = None
    demo_case_id: Optional[int] = None  # 使用预设案例


class DetectionResponse(BaseModel):
    """检测响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company_name: str
    stock_code: Optional[str]
    year: Optional[int]
    fraud_probability: Optional[float]
    risk_level: Optional[RiskLevelEnum]
    risk_score: Optional[float]
    risk_labels: Optional[List[Dict]]
    status: str
    created_at: datetime


class DetectionDetailResponse(DetectionResponse):
    """检测详情响应（含完整数据）"""
    shap_features: Optional[Dict[str, Any]] = None
    ai_feature_scores: Optional[Dict[str, Any]] = None
    financial_data: Optional[Dict[str, Any]] = None
    risk_evidence_locations: Optional[List[Dict[str, Any]]] = None
    suspicious_segments: Optional[List[Dict[str, Any]]] = None
    mdna_text: Optional[str] = None
    remediation_suggestions: Optional[Dict[str, Any]] = None
    ipo_comparison_results: Optional[List[Dict[str, Any]]] = None


# ================= 报告相关 Schema =================

class ReportResponse(BaseModel):
    """报告响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    report_type: str
    file_url: Optional[str] = None
    is_public: bool = False
    download_count: int = 0
    created_at: datetime


# ================= 订单相关 Schema =================

class OrderCreate(BaseModel):
    """订单创建请求"""
    product_type: str
    product_name: str
    amount: float
    payment_method: PaymentMethodEnum


class OrderResponse(BaseModel):
    """订单响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    product_type: str
    product_name: str
    amount: float
    paid_amount: Optional[float] = None
    status: OrderStatusEnum
    payment_method: Optional[PaymentMethodEnum]
    created_at: datetime


class OrderPaymentResponse(BaseModel):
    """订单支付响应（返回支付参数）"""
    order_no: str
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    alipay_params: Optional[Dict] = None


# ================= 会员相关 Schema =================

class MembershipPlan(BaseModel):
    """会员套餐信息"""
    plan_type: str
    name: str
    price: float
    duration_days: int
    benefits: List[str]


class MembershipResponse(BaseModel):
    """会员状态响应"""
    current_level: str
    expire_at: Optional[datetime] = None
    auto_renew: bool = False
    detections_remaining: int = -1  # -1 表示无限


# ================= AI 问答相关 Schema =================

class QAAskRequest(BaseModel):
    """问答请求"""
    question: str
    category: Optional[str] = None


class QAResponse(BaseModel):
    """问答响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    category: Optional[str]
    created_at: datetime


class QASuggestionResponse(BaseModel):
    """问答推荐响应"""
    category: str
    questions: List[str]


# ================= 预设案例相关 Schema =================

class DemoCaseResponse(BaseModel):
    """预设案例响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_name: str
    case_type: str
    description: Optional[str]
    company_info: Optional[Dict]
    is_featured: bool


class DemoCaseDetailResponse(DemoCaseResponse):
    """预设案例详情响应"""
    financial_data: Optional[Dict]
    mdna_text: Optional[str]
    expected_result: Optional[Dict]


# ================= 通用响应 =================

class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
