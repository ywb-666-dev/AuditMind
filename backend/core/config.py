"""
核心配置模块
财务舞弊识别 SaaS 平台 - 环境变量和配置管理
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional
from datetime import timedelta


class Settings(BaseSettings):
    """应用配置"""

    # ================= 应用基础配置 =================
    APP_NAME: str = "财务舞弊识别 SaaS 平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # ================= 数据库配置 =================
    DATABASE_URL: str = "mysql+pymysql://root:712693@localhost:3306/fraud_detection?charset=utf8mb4"

    # ================= 安全配置 =================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # ================= LLM API 配置 =================
    # 阿里云 DashScope (通义千问)
    DASHSCOPE_API_KEY: str = "sk-49dfdf1df5c245febf3254741c8aa381"  # 阿里云DashScope API Key
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MODEL_QWEN: str = "deepseek-v3.2"  # 使用DeepSeek-V3.2模型

    # 其他备选 LLM 配置
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    MODEL_DEEPSEEK: str = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"  # 用于深度推理

    # ================= AI 提示词优化配置 =================
    # 专业的财务舞弊文本分析提示词
    OPTIMIZED_PROMPT_TEMPLATE: str = """作为财务舞弊识别专家，请对以下企业年报中的MD&A（管理层讨论与分析）文本进行深度风险分析。

【分析任务】
评估以下7个维度的风险信号强度，每个维度给出0.00-1.00的评分（保留两位小数）：

1. CON_SEM_AI (语义矛盾度): 检测文本中前后矛盾的表述，如先说"业绩大幅增长"后又说"面临严峻挑战"
2. COV_RISK_AI (风险披露完整性): 评估风险因素披露的充分性，是否回避了关键风险
3. TONE_ABN_AI (异常乐观语调): 检测语调是否过度乐观，与财务数据是否匹配
4. FIT_TD_AI (文本-数据一致性): 验证文本描述与财务数据是否一致，如文本说"销量大增"但营收下降
5. HIDE_REL_AI (关联隐藏指数): 识别关联交易披露不充分或刻意隐藏关联方信息
6. DEN_ABN_AI (信息密度异常): 检测关键信息披露过于简略或故意冗长模糊
7. STR_EVA_AI (回避表述强度): 识别对敏感问题使用"可能""拟""预计"等模糊回避性表述

【输入数据】
MD&A文本（前1500字）:
{mdna_text}

财务数据摘要:
{financial_data}

【输出要求】
严格按以下JSON格式输出，不要有任何其他说明文字：
{{
    "CON_SEM_AI": 0.XX,
    "COV_RISK_AI": 0.XX,
    "TONE_ABN_AI": 0.XX,
    "FIT_TD_AI": 0.XX,
    "HIDE_REL_AI": 0.XX,
    "DEN_ABN_AI": 0.XX,
    "STR_EVA_AI": 0.XX,
    "key_risks": ["风险点1", "风险点2"],
    "text_evidence": "关键文本片段引用"
}}

【评分标准】
- 0.00-0.30: 低风险，无明显异常
- 0.30-0.60: 中等风险，存在可疑信号
- 0.60-1.00: 高风险，存在明显舞弊嫌疑

请确保评分客观准确，能够区分健康企业和高风险企业。"""

    # 风险评分加权配置（提高权重使风险更容易偏高）
    WEIGHTED_FEATURES: dict = {
        "CON_SEM_AI": 2.0,      # 语义矛盾 - 重点突出（提高）
        "FIT_TD_AI": 2.0,       # 文本 - 数据一致性 - 重点突出（提高）
        "COV_RISK_AI": 1.8,     # 风险披露（提高）
        "HIDE_REL_AI": 1.8,     # 关联隐藏（提高）
        "TONE_ABN_AI": 1.5,     # 提高
        "DEN_ABN_AI": 1.5,      # 提高
        "STR_EVA_AI": 1.5,      # 提高
    }

    # 风险标签阈值优化（降低阈值使风险更容易被标记）
    RISK_LABEL_THRESHOLDS: dict = {
        "存贷双高": 0.3,        # 降低
        "现金流背离": 0.3,      # 降低
        "文本粉饰": 0.3,        # 降低
        "关联交易": 0.4,        # 降低
        "存货异常": 0.3,        # 降低
        "收入异常": 0.3,        # 降低
        "费用率异常": 0.3,      # 降低
        "资产减值异常": 0.3,    # 降低
    }

    # ================= 支付配置 =================
    # 支付宝配置
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_GATEWAY: str = "https://openapi.alipay.com/gateway.do"
    ALIPAY_NOTIFY_URL: str = "https://your-domain.com/api/order/callback"

    # 微信支付配置（需要企业资质）
    WECHAT_PAY_MCH_ID: str = ""
    WECHAT_PAY_APP_ID: str = ""
    WECHAT_PAY_API_KEY: str = ""
    WECHAT_PAY_NOTIFY_URL: str = "https://your-domain.com/api/order/callback"

    # ================= 价格配置 =================
    # 会员套餐价格
    MEMBERSHIP_PRICES: dict = {
        "monthly": 299.0,
        "quarterly": 799.0,
        "yearly": 2999.0,
    }

    # 单次检测价格
    ONE_TIME_DETECTION_PRICE: float = 99.0

    # 充值优惠
    TOPUP_BONUS: dict = {
        500: 50,    # 充 500 送 50
        1000: 150,  # 充 1000 送 150
        5000: 1000, # 充 5000 送 1000
    }

    # ================= 额度配置 =================
    # 免费版额度
    FREE_USER_DAILY_AI_QUESTIONS: int = 5
    FREE_USER_MONTHLY_DETECTIONS: int = 3

    # 专业版额度
    PRO_USER_DAILY_AI_QUESTIONS: int = 50
    PRO_USER_MONTHLY_DETECTIONS: int = -1  # 无限

    # 企业版额度
    ENTERPRISE_USER_DAILY_AI_QUESTIONS: int = -1  # 无限
    ENTERPRISE_USER_MONTHLY_DETECTIONS: int = -1  # 无限

    # ================= 文件存储配置 =================
    UPLOAD_FOLDER: str = "data/uploads"

    # ================= 报告存储配置 =================
    REPORT_DIR: str = "result/reports"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {"pdf", "png", "jpg", "jpeg", "csv", "xlsx", "xls", "txt"}

    # ================= 邮件配置（可选） =================
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@frauddetection.com"

    # ================= 短信配置（可选） =================
    SMS_PROVIDER: str = "aliyun"  # aliyun/tencent
    SMS_ACCESS_KEY: str = ""
    SMS_SECRET_KEY: str = ""
    SMS_SIGN_NAME: str = "财务舞弊识别平台"

    # ================= 限流配置 =================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ================= 开发测试配置 =================
    # 设置为 True 可绕过免费用户检测额度限制（仅开发测试使用）
    BYPASS_DETECTION_QUOTA: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（依赖注入用）"""
    return settings
