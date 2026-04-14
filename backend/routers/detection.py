"""
舞弊检测核心路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Tuple
from functools import lru_cache
import json
import re

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.database import User, DetectionRecord, DemoCase, Report
from backend.schemas.schemas import (
    DetectionCreate, DetectionResponse, DetectionDetailResponse,
    DemoCaseResponse, DemoCaseDetailResponse, RiskLevelEnum
)

# API 响应缓存 - 案例列表缓存（5分钟）
_cases_cache = {}
_cases_cache_time = 0

import time

def get_cached_cases(db: Session, featured_only: bool = False):
    """获取缓存的案例列表"""
    global _cases_cache, _cases_cache_time

    cache_key = f"featured_{featured_only}"
    current_time = time.time()

    # 缓存5分钟
    if cache_key in _cases_cache and (current_time - _cases_cache_time) < 300:
        return _cases_cache[cache_key]

    query = db.query(DemoCase)
    if featured_only:
        query = query.filter(DemoCase.is_featured == True)

    cases = query.order_by(DemoCase.sort_order, DemoCase.id).all()
    _cases_cache[cache_key] = cases
    _cases_cache_time = current_time

    return cases

router = APIRouter(prefix="/detection", tags=["舞弊检测"])


def compute_shap_features(ai_scores: dict, financial_data: dict) -> dict:
    """
    计算 SHAP 特征重要性
    （简化版本，基于规则的重要性排序）
    """
    shap_values = {}

    # AI 特征重要性
    for feature, score in ai_scores.items():
        # ====================== 类型安全修复 ======================
        # 处理列表/元组
        if isinstance(score, (list, tuple)):
            score = score[0]
        # 处理字符串，赋值为0
        if isinstance(score, str):
            safe_score = 0.0
        else:
            # 尝试转浮点数，失败则为0
            try:
                safe_score = float(score)
            except:
                safe_score = 0.0
        # ========================================================
        shap_values[feature] = round(safe_score * 0.3, 4)

    # 财务特征重要性
    if financial_data:
        # 存贷双高特征
        cash = float(financial_data.get("货币资金", 0) or 0)
        short_loan = float(financial_data.get("短期借款", 0) or 0)
        if cash > 50 and short_loan > 20:
            shap_values["存贷双高指标"] = 0.25

        # 现金流背离特征
        net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
        net_profit = float(financial_data.get("净利润", 0) or 0)
        if net_profit > 0 and net_cash < 0:
            shap_values["现金流背离指标"] = 0.22

        # 存货特征
        inventory = float(financial_data.get("存货", 0) or 0)
        total_assets = float(financial_data.get("总资产", 1) or 1)
        if total_assets > 0 and inventory / total_assets > 0.15:
            shap_values["存货占比指标"] = 0.18

    # 归一化
    total = sum(shap_values.values())
    if total > 0:
        shap_values = {k: round(v / total, 4) for k, v in shap_values.items()}

    return shap_values


async def extract_ai_features_from_text(mdna_text: str, financial_data: dict) -> dict:
    """
    使用 LLM 提取 AI 文本特征
    真实调用 SiliconFlow API 进行深度分析
    """
    from backend.services.detection_service import detection_engine

    if not mdna_text:
        return detection_engine._get_default_ai_features()

    # 调用检测引擎中的 LLM 分析
    try:
        ai_features = await detection_engine.extract_ai_features(mdna_text, financial_data)
        return ai_features
    except Exception as e:
        print(f"⚠️ LLM特征提取失败，使用备用方案: {e}")
        # 备用：规则-based 快速评估
        return _fallback_ai_feature_extraction(mdna_text, financial_data)


def _fallback_ai_feature_extraction(mdna_text: str, financial_data: dict) -> dict:
    """备用AI特征提取（规则-based）"""
    ai_scores = {
        "CON_SEM_AI": 0.35,
        "COV_RISK_AI": 0.35,
        "TONE_ABN_AI": 0.35,
        "FIT_TD_AI": 0.35,
        "HIDE_REL_AI": 0.35,
        "DEN_ABN_AI": 0.35,
        "STR_EVA_AI": 0.35
    }

    text_lower = mdna_text.lower()

    # 语义矛盾检测
    contradiction_keywords = ["但是", "然而", "尽管", "虽然", "不过", "却", "反之"]
    contra_count = sum(1 for kw in contradiction_keywords if kw in text_lower)
    if contra_count >= 2:
        ai_scores["CON_SEM_AI"] = min(0.4 + contra_count * 0.08, 0.9)

    # 风险披露完整性
    risk_keywords = ["风险", "不确定性", "挑战", "困难", "压力", "波动", "下滑"]
    risk_count = sum(1 for kw in risk_keywords if kw in text_lower)
    if risk_count < 3:
        ai_scores["COV_RISK_AI"] = 0.65
    elif risk_count > 8:
        ai_scores["COV_RISK_AI"] = 0.55

    # 语调异常乐观
    positive_keywords = ["大幅增长", "突破", "领先", "优异", "显著", "持续向好", "创新高"]
    positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
    if positive_count > 3:
        ai_scores["TONE_ABN_AI"] = min(0.45 + positive_count * 0.1, 0.95)

    # 文本 - 数据一致性检查
    if financial_data:
        revenue_growth = float(financial_data.get("营业收入增长率", 0) or 0)
        profit_growth = float(financial_data.get("净利润增长率", 0) or 0)
        cash_flow = float(financial_data.get("经营活动现金流净额", 0) or 0)
        net_profit = float(financial_data.get("净利润", 0) or 0)

        # 文本说增长但数据下降
        if ("增长" in text_lower or "提升" in text_lower) and revenue_growth < -0.1:
            ai_scores["FIT_TD_AI"] = 0.85
        # 利润为正但现金流为负
        if net_profit > 0 and cash_flow < 0:
            ai_scores["FIT_TD_AI"] = min(ai_scores["FIT_TD_AI"] + 0.25, 0.9)

    # 关联隐藏检测
    related_keywords = ["关联方", "关联交易", "关联关系", "少数股东", "实际控制人", "控股股东"]
    related_count = sum(1 for kw in related_keywords if kw in text_lower)
    if related_count == 0:
        ai_scores["HIDE_REL_AI"] = 0.55
    elif related_count > 5:
        ai_scores["HIDE_REL_AI"] = min(0.45 + related_count * 0.06, 0.8)

    # 信息密度检测
    text_length = len(mdna_text)
    if text_length < 300:
        ai_scores["DEN_ABN_AI"] = 0.6
    elif text_length > 3000:
        ai_scores["DEN_ABN_AI"] = 0.5

    # 回避表述检测
    evade_keywords = ["可能", "或许", "大概", "预计", "计划", "拟", "将", "有望"]
    evade_count = sum(1 for kw in evade_keywords if kw in text_lower)
    if evade_count > 8:
        ai_scores["STR_EVA_AI"] = min(0.4 + evade_count * 0.05, 0.85)

    return ai_scores


def compute_shap_features(ai_scores: dict, financial_data: dict) -> dict:
    """
    计算 SHAP 特征重要性
    （简化版本，基于规则的重要性排序）
    """
    shap_values = {}

    # AI 特征重要性
    for feature, score in ai_scores.items():
        # 跳过非特征键（如分析笔记）
        if feature.startswith('_'):
            continue

        # 类型安全处理
        try:
            score_val = float(score) if score is not None else 0.3
        except (ValueError, TypeError):
            score_val = 0.3

        shap_values[feature] = round(score_val * 0.8, 4)

    # 财务特征重要性
    if financial_data:
        # 存贷双高特征
        cash = float(financial_data.get("货币资金", 0) or 0)
        short_loan = float(financial_data.get("短期借款", 0) or 0)
        if cash > 50 and short_loan > 20:
            shap_values["存贷双高指标"] = 0.25

        # 现金流背离特征
        net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
        net_profit = float(financial_data.get("净利润", 0) or 0)
        if net_profit > 0 and net_cash < 0:
            shap_values["现金流背离指标"] = 0.22

        # 存货特征
        inventory = float(financial_data.get("存货", 0) or 0)
        total_assets = float(financial_data.get("总资产", 1) or 1)
        if total_assets > 0 and inventory / total_assets > 0.15:
            shap_values["存货占比指标"] = 0.18

    # 归一化
    total = sum(shap_values.values())
    if total > 0:
        shap_values = {k: round(v / total, 4) for k, v in shap_values.items()}

    return shap_values


def calculate_fraud_probability(
    financial_data: Dict[str, Any],
    ai_features: Dict[str, float]
) -> Tuple[float, RiskLevelEnum, List[Dict[str, Any]], float]:
    """
    计算舞弊概率和风险等级
    """
    # 1. 传统财务风险评分（40分满分）
    trad_score = 0.0

    # 存贷双高检测
    cash = float(financial_data.get("货币资金", 0) or 0)
    short_loan = float(financial_data.get("短期借款", 0) or 0)
    if cash > 100 and short_loan > 50 and cash / short_loan > 1.5:
        trad_score += 15

    # 现金流与利润背离
    net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
    net_profit = float(financial_data.get("净利润", 0) or 0)
    if net_profit > 0 and net_cash < 0:
        trad_score += 20
    elif net_profit > 0 and net_cash / net_profit < 0.5:
        trad_score += 15

    # 存货异常
    inventory = float(financial_data.get("存货", 0) or 0)
    total_assets = float(financial_data.get("总资产", 1) or 1)
    if total_assets > 0 and inventory / total_assets > 0.4:
        trad_score += 10

    trad_score = min(trad_score, 40)

    # 2. AI 文本风险评分（60分满分）
    ai_score = 0.0
    weighted_features = {
        "CON_SEM_AI": 1.0,
        "COV_RISK_AI": 1.0,
        "TONE_ABN_AI": 1.2,
        "FIT_TD_AI": 1.5,
        "HIDE_REL_AI": 1.3,
        "DEN_ABN_AI": 0.8,
        "STR_EVA_AI": 1.0
    }

    for feature, score in ai_features.items():
        # 跳过非特征键（如分析笔记）
        if feature.startswith('_') or feature not in weighted_features:
            continue

        # 类型安全处理
        try:
            score_val = float(score) if score is not None else 0.3
        except (ValueError, TypeError):
            score_val = 0.3

        weight = weighted_features.get(feature, 1.0)
        ai_score += score_val * weight

    total_weight = sum(weighted_features.values())
    ai_score = (ai_score / total_weight) * 60 if total_weight > 0 else 0

    # 3. 综合评分（0-100分）
    total_score = trad_score + ai_score

    # 4. 计算舞弊概率（0-1）
    fraud_probability = min(max(total_score / 100, 0), 1)

    # 5. 确定风险等级
    if fraud_probability >= 0.7:
        risk_level = RiskLevelEnum.HIGH
    elif fraud_probability >= 0.4:
        risk_level = RiskLevelEnum.MEDIUM
    else:
        risk_level = RiskLevelEnum.LOW

    # 6. 生成风险标签
    risk_labels = generate_risk_labels(financial_data, ai_features, fraud_probability)

    return fraud_probability, risk_level, risk_labels, total_score


def generate_risk_labels(
    financial_data: Dict[str, Any],
    ai_features: Dict[str, float],
    fraud_probability: float
) -> List[Dict[str, Any]]:
    """生成风险标签"""
    risk_labels = []

    # 1. 财务风险标签
    cash = float(financial_data.get("货币资金", 0) or 0)
    short_loan = float(financial_data.get("短期借款", 0) or 0)
    net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
    net_profit = float(financial_data.get("净利润", 0) or 0)
    inventory = float(financial_data.get("存货", 0) or 0)
    total_assets = float(financial_data.get("总资产", 1) or 1)

    if cash > 50 and short_loan > 20:
        risk_labels.append({
            "label": "存贷双高",
            "score": 0.85,
            "description": "货币资金和短期借款同时处于高位，可能存在资金真实性问题"
        })

    if net_profit > 0 and net_cash < 0:
        risk_labels.append({
            "label": "现金流背离",
            "score": 0.90,
            "description": "净利润为正但经营现金流为负，可能存在利润操纵"
        })

    if total_assets > 0 and inventory / total_assets > 0.15:
        risk_labels.append({
            "label": "存货异常",
            "score": 0.75,
            "description": "存货占总资产比例过高，可能存在资产虚增"
        })

    # 2. AI 文本风险标签
    label_map = {
        "CON_SEM_AI": ("文本语义矛盾", "MD&A 文本中存在前后矛盾的表述"),
        "FIT_TD_AI": ("文本-数据不一致", "文本描述与财务数据不匹配"),
        "COV_RISK_AI": ("风险披露不足", "未充分披露重大风险因素"),
        "HIDE_REL_AI": ("关联交易隐藏", "关联交易披露不充分或存在隐藏"),
        "TONE_ABN_AI": ("语调异常乐观", "管理层语调过于乐观，与实际业绩不匹配"),
        "DEN_ABN_AI": ("信息密度异常", "信息披露过于简略或冗长"),
        "STR_EVA_AI": ("回避表述", "对关键问题使用模糊、回避性表述")
    }

    thresholds = {
        "CON_SEM_AI": 0.6,
        "COV_RISK_AI": 0.6,
        "TONE_ABN_AI": 0.55,
        "FIT_TD_AI": 0.6,
        "HIDE_REL_AI": 0.55,
        "DEN_ABN_AI": 0.65,
        "STR_EVA_AI": 0.6
    }

    for feature, score in ai_features.items():
        # 跳过非特征键（如分析笔记）
        if feature.startswith('_') or feature not in label_map:
            continue

        # 类型安全处理
        try:
            score_val = float(score) if score is not None else 0.0
        except (ValueError, TypeError):
            score_val = 0.0

        threshold = thresholds.get(feature, 0.6)
        if score_val >= threshold:
            label, description = label_map.get(feature, (feature, "风险特征识别"))
            risk_labels.append({
                "label": label,
                "score": round(score_val, 2),
                "description": description
            })

    # 3. 根据舞弊概率添加综合标签
    if fraud_probability > 0.8:
        risk_labels.append({
            "label": "高舞弊风险",
            "score": round(fraud_probability, 2),
            "description": "综合多个风险特征，舞弊风险极高"
        })

    return risk_labels[:10]  # 限制最多10个标签


@router.get("/cases", response_model=List[DemoCaseResponse])
def get_demo_cases(
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取预设案例列表（带缓存）
    """
    return get_cached_cases(db, featured_only)


@router.get("/cases/{case_id}", response_model=DemoCaseDetailResponse)
def get_demo_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    获取预设案例详情
    """
    case = db.query(DemoCase).filter(DemoCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案例不存在"
        )
    return case


@router.post("/cases/{case_id}/load", response_model=DetectionCreate)
def load_demo_case(
    case_id: int,
    db: Session = Depends(get_db)
):
    """
    加载预设案例数据到检测表单
    """
    case = db.query(DemoCase).filter(DemoCase.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="案例不存在"
        )

    return {
        "company_name": case.company_info.get("name") if case.company_info else case.case_name,
        "stock_code": case.company_info.get("stock_code") if case.company_info else None,
        "year": case.company_info.get("year") if case.company_info else None,
        "financial_data": case.financial_data,
        "mdna_text": case.mdna_text,
        "demo_case_id": case_id
    }


@router.post("/analyze", response_model=DetectionDetailResponse)
async def analyze_detection(
    detection_data: DetectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    执行舞弊检测分析（真实LLM分析）
    """
    # 检查用户检测额度（可通过配置绕过，仅用于开发测试）
    if not settings.BYPASS_DETECTION_QUOTA:
        if current_user.membership_level == "free":
            if not current_user.free_detections_remaining or current_user.free_detections_remaining <= 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="免费版检测额度已用完，请升级会员或购买单次检测"
                )
    else:
        # 开发模式：自动重置免费用户额度
        if current_user.membership_level == "free":
            if not current_user.free_detections_remaining or current_user.free_detections_remaining <= 0:
                current_user.free_detections_remaining = 3
                print(f"[DEV MODE] 自动重置用户 {current_user.username} 的检测额度为 3")

    # 如果使用预设案例，加载案例数据
    if detection_data.demo_case_id:
        demo_case = db.query(DemoCase).filter(
            DemoCase.id == detection_data.demo_case_id
        ).first()
        if demo_case:
            detection_data.financial_data = demo_case.financial_data
            detection_data.mdna_text = demo_case.mdna_text
            if demo_case.company_info:
                detection_data.company_name = demo_case.company_info.get("name", detection_data.company_name)
                detection_data.stock_code = demo_case.company_info.get("stock_code", detection_data.stock_code)
                detection_data.year = demo_case.company_info.get("year", detection_data.year)

    # 提取 AI 特征（真实调用LLM API）
    ai_scores = await extract_ai_features_from_text(
        detection_data.mdna_text or "",
        detection_data.financial_data or {}
    )

    # 计算舞弊概率和风险等级
    fraud_prob, risk_level, risk_labels, risk_score = calculate_fraud_probability(
        detection_data.financial_data or {},
        ai_scores
    )

    # 计算 SHAP 特征
    shap_features = compute_shap_features(ai_scores, detection_data.financial_data or {})

    # ============ 新增：智能解析引擎 ============
    risk_evidence_locations = []
    suspicious_segments = []

    try:
        from backend.services.intelligent_parser import intelligent_parser

        # 提取AI特征并定位证据
        ai_features_with_location, evidences = await intelligent_parser.extract_ai_features_with_location(
            detection_data.mdna_text or "",
            detection_data.financial_data or {}
        )

        # 更新AI特征（包含更精确的分析）
        ai_scores.update(ai_features_with_location)

        # 转换证据格式
        risk_evidence_locations = [
            {
                "feature": e.feature,
                "feature_name": e.feature_name,
                "score": e.score,
                "location": e.location,
                "page_num": e.page_num,
                "paragraph_num": e.paragraph_num,
                "text_snippet": e.text_snippet,
                "explanation": e.explanation
            }
            for e in evidences
        ]

        # 提取可疑文本片段
        segments = intelligent_parser.extract_suspicious_segments(
            detection_data.mdna_text or "",
            ai_scores
        )
        suspicious_segments = [
            {
                "location": s.location,
                "page_num": s.page_num,
                "text": s.text,
                "risk_type": s.risk_type,
                "confidence": s.confidence,
                "related_features": s.related_features
            }
            for s in segments
        ]

    except Exception as e:
        print(f"⚠️ 智能解析引擎调用失败: {e}")

    # ============ 新增：过会风险对标 ============
    ipo_comparison_results = []
    try:
        from backend.services.ipo_comparison_service import get_ipo_comparison_service

        ipo_service = get_ipo_comparison_service(db)
        industry = detection_data.financial_data.get("industry") if detection_data.financial_data else None

        ipo_comparison_results = ipo_service.compare_with_rejected_cases(
            ai_scores,
            industry=industry,
            top_n=5
        )
    except Exception as e:
        print(f"⚠️ IPO对标服务调用失败: {e}")

    # ============ 新增：整改建议引擎 ============
    remediation_suggestions = []
    try:
        from backend.services.remediation_engine import get_remediation_engine

        remediation_engine = get_remediation_engine(db)

        # 先生成临时检测记录用于整改建议
        temp_record = DetectionRecord(
            risk_labels=risk_labels,
            ai_feature_scores=ai_scores
        )

        remediation_result = remediation_engine.generate_full_remediation_plan(temp_record)
        remediation_suggestions = remediation_result

    except Exception as e:
        print(f"⚠️ 整改建议引擎调用失败: {e}")

    # 创建检测记录 - 包含所有新字段
    db_detection = DetectionRecord(
        user_id=current_user.id,
        company_name=detection_data.company_name,
        stock_code=detection_data.stock_code,
        year=detection_data.year,
        fraud_probability=round(fraud_prob, 4),
        risk_level=risk_level.value,
        risk_score=round(risk_score, 2),
        shap_features=shap_features,
        ai_feature_scores=ai_scores,
        risk_labels=risk_labels,
        # 新增字段
        risk_evidence_locations=risk_evidence_locations,
        suspicious_segments=suspicious_segments,
        ipo_comparison_results=ipo_comparison_results,
        remediation_suggestions=remediation_suggestions,
        # 原始数据
        financial_data=detection_data.financial_data,
        mdna_text=detection_data.mdna_text[:20000] if detection_data.mdna_text else None,  # 限制20000字符（MySQL TEXT类型限制65535字节，中文约3字节/字符）
        status="completed"
    )

    # 扣减免费额度
    if current_user.membership_level == "free":
        if current_user.free_detections_remaining and current_user.free_detections_remaining > 0:
            current_user.free_detections_remaining -= 1

    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)

    return db_detection


@router.get("/history", response_model=List[DetectionResponse])
def get_detection_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取检测历史记录
    """
    query = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user.id
    ).order_by(DetectionRecord.created_at.desc())

    # 分页
    offset = (page - 1) * page_size
    detections = query.offset(offset).limit(page_size).all()

    return detections


@router.get("/ai-prompt")
def get_ai_prompt():
    """
    获取AI分析使用的提示词（用于演示展示）
    """
    from backend.core.config import settings

    prompt_data = {
        "title": "AI文本风险分析提示词",
        "description": "本提示词用于指导大语言模型对MD&A文本进行7维度风险分析",
        "model": settings.MODEL_QWEN,
        "prompt_template": settings.OPTIMIZED_PROMPT_TEMPLATE,
        "features": {
            "CON_SEM_AI": {
                "name": "语义矛盾度",
                "description": "检测文本中前后矛盾的表述",
                "example": "先说'业绩大幅增长'后又说'面临严峻挑战'"
            },
            "COV_RISK_AI": {
                "name": "风险披露完整性",
                "description": "评估风险因素披露的充分性",
                "example": "是否回避了关键风险"
            },
            "TONE_ABN_AI": {
                "name": "异常乐观语调",
                "description": "检测语调是否过度乐观",
                "example": "与财务数据是否匹配"
            },
            "FIT_TD_AI": {
                "name": "文本-数据一致性",
                "description": "验证文本描述与财务数据是否一致",
                "example": "文本说'销量大增'但营收下降"
            },
            "HIDE_REL_AI": {
                "name": "关联隐藏指数",
                "description": "识别关联交易披露不充分",
                "example": "刻意隐藏关联方信息"
            },
            "DEN_ABN_AI": {
                "name": "信息密度异常",
                "description": "检测关键信息披露过于简略或冗长",
                "example": "故意冗长模糊"
            },
            "STR_EVA_AI": {
                "name": "回避表述强度",
                "description": "识别对敏感问题使用模糊表述",
                "example": "使用'可能''拟''预计'等词汇"
            }
        },
        "scoring_criteria": {
            "low": "0.00-0.30: 低风险，无明显异常",
            "medium": "0.30-0.60: 中等风险，存在可疑信号",
            "high": "0.60-1.00: 高风险，存在明显舞弊嫌疑"
        }
    }

    return prompt_data


@router.get("/{detection_id}", response_model=DetectionDetailResponse)
def get_detection_detail(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取检测详情
    """
    detection = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )

    return detection


@router.delete("/{detection_id}")
def delete_detection(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除检测记录
    """
    detection = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )

    db.delete(detection)
    db.commit()

    return {"message": "删除成功"}


@router.get("/{detection_id}/smart-report")
def get_smart_report(
    detection_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取智能增强报告（包含证据定位、IPO对标、整改建议）
    """
    detection = db.query(DetectionRecord).filter(
        DetectionRecord.id == detection_id,
        DetectionRecord.user_id == current_user.id
    ).first()

    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="检测记录不存在"
        )

    # 构建智能报告
    smart_report = {
        "basic_info": {
            "company_name": detection.company_name,
            "stock_code": detection.stock_code,
            "year": detection.year,
            "detection_date": detection.created_at.isoformat() if detection.created_at else None,
            "fraud_probability": detection.fraud_probability,
            "risk_level": detection.risk_level,
            "risk_score": detection.risk_score
        },
        "risk_summary": {
            "risk_labels": detection.risk_labels,
            "shap_features": detection.shap_features,
            "ai_feature_scores": detection.ai_feature_scores
        },
        "evidence_analysis": {
            "risk_evidence_locations": detection.risk_evidence_locations or [],
            "suspicious_segments": detection.suspicious_segments or []
        },
        "ipo_comparison": {
            "similar_cases": detection.ipo_comparison_results or [],
            "comparison_summary": _generate_comparison_summary(detection.ipo_comparison_results)
        },
        "remediation_plan": detection.remediation_suggestions or {}
    }

    return smart_report


def _generate_comparison_summary(ipo_results: list) -> dict:
    """生成IPO对标摘要"""
    if not ipo_results:
        return {
            "has_similar_cases": False,
            "message": "未发现与近三年IPO被否案例的显著相似性"
        }

    top_case = ipo_results[0]
    return {
        "has_similar_cases": True,
        "similar_case_count": len(ipo_results),
        "highest_similarity": top_case.get("similarity", 0),
        "most_similar_case": top_case.get("company_name"),
        "common_risk_features": list(set(
            f["feature_name"]
            for case in ipo_results
            for f in case.get("matched_features", [])
        ))[:5]
    }
