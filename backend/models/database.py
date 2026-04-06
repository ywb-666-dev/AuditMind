"""
数据库模型定义
财务舞弊识别 SaaS 平台 - 核心数据表结构
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Date
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


# ==================== 用户相关模型 ====================

class User(Base):
    """用户表 - 核心用户信息"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)

    # 用户类型：individual(个人), enterprise(企业), regulator(监管机构), auditor(审计师)
    user_type = Column(String(20), default="individual")

    # 会员等级：free(免费), pro(专业), enterprise(企业)
    membership_level = Column(String(20), default="free")
    membership_expire_at = Column(DateTime)

    # 账户余额（用于单次检测支付）
    balance = Column(Float, default=0.0)

    # 检测额度
    free_detections_remaining = Column(Integer, default=3)  # 免费版每月 3 次
    detection_reset_date = Column(Date)  # 额度重置日期

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    detections = relationship("DetectionRecord", back_populates="user")
    orders = relationship("Order", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    qa_history = relationship("QAHistory", back_populates="user")


class UserProfile(Base):
    """用户详情表 - 实名认证信息"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 个人信息
    real_name = Column(String(50))
    id_card = Column(String(18))  # 加密存储
    id_card_verified = Column(Boolean, default=False)

    # 企业信息
    company_name = Column(String(200))
    credit_code = Column(String(18))  # 统一社会信用代码
    company_verified = Column(Boolean, default=False)

    # 认证状态
    certified = Column(Boolean, default=False)
    certified_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


# ==================== 检测相关模型 ====================

class DetectionRecord(Base):
    """检测记录表 - 核心舞弊检测数据"""
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 企业信息
    company_name = Column(String(200), nullable=False)
    stock_code = Column(String(10), index=True)  # 证券代码
    year = Column(Integer)  # 年度

    # 检测结果
    fraud_probability = Column(Float)  # 舞弊概率 (0-1)
    risk_level = Column(String(20))  # low/medium/high
    risk_score = Column(Float)  # 综合风险评分 (0-100)

    # AI 特征分析结果
    shap_features = Column(JSON)  # SHAP 特征重要性 {feature: importance}
    ai_feature_scores = Column(JSON)  # 7 个 AI 文本特征得分
    risk_labels = Column(JSON)  # 风险标签列表 [{label, score}]

    # 新增：智能解析引擎结果
    risk_evidence_locations = Column(JSON)  # 风险证据定位 [{feature, location, text_snippet, page_num}]
    suspicious_segments = Column(JSON)  # 可疑文本片段 [{location, text, risk_type, confidence}]

    # 新增：过会风险对标结果
    ipo_comparison_results = Column(JSON)  # IPO对标结果 [{case_id, similarity, matched_features}]

    # 新增：整改建议
    remediation_suggestions = Column(JSON)  # 整改建议 [{risk_type, suggestions, priority}]

    # 原始数据
    financial_data = Column(JSON)  # 财务数据
    mdna_text = Column(LONGTEXT)  # MD&A 文本（或文件路径），使用LONGTEXT支持大文本

    # 计费信息
    cost = Column(Float, default=0.0)  # 消耗金额
    detection_type = Column(String(20), default="single")  # single/batch/demo

    # 状态
    status = Column(String(20), default="completed")  # pending/processing/completed/failed

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="detections")
    reports = relationship("Report", back_populates="detection")


class Report(Base):
    """检测报告表"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("detection_records.id"))

    # 报告类型
    report_type = Column(String(20), default="basic")  # basic/professional/enterprise

    # 文件信息
    file_path = Column(String(500))  # PDF/HTML 文件路径
    file_url = Column(String(500))  # 公开访问 URL

    # 分享功能
    is_public = Column(Boolean, default=False)
    share_token = Column(String(64), unique=True)
    share_expire_at = Column(DateTime)

    # 统计
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    detection = relationship("DetectionRecord", back_populates="reports")


# ==================== 支付相关模型 ====================

class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 商品信息
    product_type = Column(String(20))  # subscription/one_time/topup
    product_name = Column(String(100))
    product_detail = Column(JSON)  # 商品详情 {plan: 'monthly', duration: 1}

    # 金额
    amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    paid_amount = Column(Float)  # 实付金额

    # 状态
    status = Column(String(20), default="pending")  # pending/paid/cancelled/refunded

    # 支付信息
    payment_method = Column(String(20))  # alipay/wechat/bank_transfer
    payment_time = Column(DateTime)
    payer_info = Column(JSON)  # 支付平台返回的付款人信息

    # 退款信息
    refund_time = Column(DateTime)
    refund_amount = Column(Float)
    refund_reason = Column(String(200))

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    transaction = relationship("Transaction", back_populates="order", uselist=False)


class Transaction(Base):
    """交易流水表"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))

    # 交易类型
    type = Column(String(20), nullable=False)  # payment/refund/topup/consumption

    # 金额
    amount = Column(Float, nullable=False)  # +收入/-支出
    balance_after = Column(Float)  # 交易后余额

    description = Column(String(200))

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")
    order = relationship("Order", back_populates="transaction")


class Subscription(Base):
    """订阅表"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 套餐类型
    plan_type = Column(String(20))  # monthly/yearly

    # 有效期
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)

    # 自动续费
    auto_renew = Column(Boolean, default=False)

    # 状态
    status = Column(String(20), default="active")  # active/expired/cancelled

    # 续费信息
    renewal_order_id = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="subscription")


# ==================== 案例相关模型 ====================

class DemoCase(Base):
    """预设案例表 - 用于演示和测试"""
    __tablename__ = "demo_cases"

    id = Column(Integer, primary_key=True, index=True)

    # 案例信息
    case_name = Column(String(100), nullable=False)  # 如"康美药业"
    case_type = Column(String(20))  # fraud(舞弊)/healthy(健康)
    description = Column(Text)  # 案例描述

    # 预设数据
    company_info = Column(JSON)  # {name, stock_code, year, industry}
    financial_data = Column(JSON)  # 财务数据
    mdna_text = Column(LONGTEXT)  # MD&A 文本，使用LONGTEXT支持大文本

    # 预期结果（用于验证）
    expected_result = Column(JSON)  # {fraud_probability, risk_level, risk_labels}

    # 排序和推荐
    is_featured = Column(Boolean, default=False)  # 是否推荐案例
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 问答相关模型 ====================

class QAHistory(Base):
    """问答历史表"""
    __tablename__ = "qa_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # 问答内容
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(20))  # theory/practice/policy/case/platform

    # 用户反馈
    is_favorite = Column(Boolean, default=False)
    feedback_score = Column(Integer)  # 1-5 评分

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="qa_history")


# ==================== IPO被否案例库 ====================

class IPORejectedCase(Base):
    """IPO被否案例库 - 用于风险对标"""
    __tablename__ = "ipo_rejected_cases"

    id = Column(Integer, primary_key=True, index=True)

    # 企业信息
    company_name = Column(String(200), nullable=False)
    stock_code = Column(String(20), index=True)
    industry = Column(String(100))  # 所属行业
    application_date = Column(Date)  # 申报日期
    rejected_date = Column(Date)  # 被否日期

    # 被否原因
    rejection_reason = Column(Text)  # 官方披露的被否原因
    risk_features = Column(JSON)  # 风险特征 {CON_SEM_AI: 0.8, FIT_TD_AI: 0.7, ...}
    financial_issues = Column(JSON)  # 财务问题列表

    # 案例详情
    case_summary = Column(Text)  # 案例摘要
    mdna_analysis = Column(Text)  # MD&A分析要点
    key_risk_points = Column(JSON)  # 关键风险点 [{point, description}]

    # 相似度计算用
    feature_vector = Column(JSON)  # 特征向量用于相似度匹配

    # 元数据
    data_source = Column(String(100))  # 数据来源
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RemediationSuggestion(Base):
    """整改建议库 - 基于风险类型的整改指引"""
    __tablename__ = "remediation_suggestions"

    id = Column(Integer, primary_key=True, index=True)

    # 风险类型
    risk_type = Column(String(50), nullable=False, index=True)  # 存贷双高/现金流背离/文本语义矛盾...
    risk_level = Column(String(20))  # low/medium/high

    # 整改建议
    title = Column(String(200), nullable=False)
    description = Column(Text)  # 问题描述
    suggestions = Column(JSON)  # 整改建议列表 [{step, action, responsible, timeline}]

    # 参考依据
    regulations = Column(JSON)  # 相关法规 [{name, article, content}]
    case_references = Column(JSON)  # 参考案例 [{case_name, lesson}]

    # 执行指引
    priority = Column(Integer, default=1)  # 优先级 1-5
    estimated_days = Column(Integer)  # 预计完成天数
    department = Column(String(50))  # 责任部门：财务/法务/审计/董秘

    # 模板配置
    is_template = Column(Boolean, default=True)
    template_variables = Column(JSON)  # 模板变量 [{name, description}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 系统配置相关模型 ====================

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(50), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    description = Column(String(200))

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
