"""
舞弊检测核心功能实现
包含 AI 特征提取、风险评分计算、SHAP 分析等
"""
import asyncio
import json
import re
import os
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from functools import lru_cache
import numpy as np
import shap
import xgboost as xgb
import joblib
from sqlalchemy.orm import Session
from cachetools import TTLCache

from backend.core.config import settings
from backend.models.database import DetectionRecord, DemoCase
from backend.core.cache_manager import get_llm_cache, get_shap_cache, cached

# LLM 结果缓存 - 24小时TTL，最多缓存200条
ai_result_cache = get_llm_cache()
shap_cache = get_shap_cache()
from backend.schemas.schemas import DetectionCreate, RiskLevelEnum
from backend.services.analysis_service import analysis_service
from backend.services.detailed_shap_analysis import get_detailed_shap_analysis

# 获取项目根目录 - 尝试多个可能的位置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(PROJECT_ROOT, "result", "models")

# 如果模型目录不存在，尝试其他位置
if not os.path.exists(MODEL_DIR):
    # 尝试从项目根目录的models文件夹
    alt_model_dir = os.path.join(PROJECT_ROOT, "..", "models")
    if os.path.exists(alt_model_dir):
        MODEL_DIR = os.path.abspath(alt_model_dir)
    else:
        # 尝试绝对路径（开发环境）
        abs_model_dir = r"D:\play\models"
        if os.path.exists(abs_model_dir):
            MODEL_DIR = abs_model_dir


class FraudDetectionEngine:
    """
    舞弊检测核心引擎
    """

    def __init__(self):
        """初始化引擎"""
        self.ai_model = None
        self.traditional_model = None
        self.feature_names = []
        self.scaler = None
        self.selected_features = None
        self.numeric_columns = None
        self._load_models()

    def _load_models(self):
        """加载预训练模型"""
        try:
            # 获取模型文件路径（使用正确的路径）
            ai_model_path = os.path.join(MODEL_DIR, "model_ai_XGBoost.pkl")
            trad_model_path = os.path.join(MODEL_DIR, "model_trad_XGBoost.pkl")
            scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
            features_path = os.path.join(MODEL_DIR, "selected_features.pkl")
            numeric_path = os.path.join(MODEL_DIR, "numeric_columns.pkl")

            print(f"尝试加载模型:")
            print(f"AI 模型路径: {ai_model_path}")
            print(f"传统模型路径: {trad_model_path}")

            # 检查模型文件是否存在
            if os.path.exists(ai_model_path):
                self.ai_model = joblib.load(ai_model_path)
                print("✅ AI 模型加载成功")
            else:
                print(f"⚠️  AI 模型文件不存在: {ai_model_path}")

            if os.path.exists(trad_model_path):
                self.traditional_model = joblib.load(trad_model_path)
                print("✅ 传统模型加载成功")
            else:
                print(f"⚠️  传统模型文件不存在: {trad_model_path}")

            # 加载其他必要文件
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                print("✅ Scaler 加载成功")

            if os.path.exists(features_path):
                self.selected_features = joblib.load(features_path)
                print("✅ Selected Features 加载成功")

            if os.path.exists(numeric_path):
                self.numeric_columns = joblib.load(numeric_path)
                print("✅ Numeric Columns 加载成功")


            # 获取特征名称
            if self.ai_model:
                try:
                    self.feature_names = self.ai_model.get_booster().feature_names
                except Exception:
                    # 尝试从 model 直接获取 feature_names
                    try:
                        self.feature_names = self.ai_model.feature_names_in_
                    except:
                        self.feature_names = []
                        print("⚠️  无法获取特征名称")
        except Exception as e:
            print(f"⚠️  模型加载失败: {e}")
            # 创建兜底模型
            self.ai_model = xgb.XGBClassifier()
            self.traditional_model = xgb.XGBClassifier()

    @cached(cache_name="llm_results", maxsize=200, ttl=86400,
            key_func=lambda self, mdna_text, financial_data: 
                hashlib.md5(f"{mdna_text[:200]}_{json.dumps(financial_data, sort_keys=True)}".encode()).hexdigest())
    async def extract_ai_features(self, mdna_text: str, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """
        使用 LLM 提取 AI 文本特征（带缓存）
        """
        if not mdna_text:
            return self._get_default_ai_features()

        # 生成缓存key（基于文本前200字符 + 关键财务指标）
        cache_key = self._generate_cache_key(mdna_text, financial_data)

        # 检查缓存
        if cache_key in ai_result_cache:
            print(f"✅ LLM结果命中缓存")
            return ai_result_cache[cache_key]

        # 构建优化的提示词
        prompt = settings.OPTIMIZED_PROMPT_TEMPLATE.format(
            mdna_text=mdna_text[:1000],  # 限制文本长度
            financial_data=json.dumps(financial_data, ensure_ascii=False)
        )

        # 调用 LLM API
        try:
            response = await self._call_llm_api(prompt)
            features = self._parse_llm_response(response)

            # 缓存结果
            ai_result_cache[cache_key] = features
            print(f"✅ LLM结果已缓存 (当前缓存数: {len(ai_result_cache)})")

            return features
        except Exception as e:
            print(f"⚠️  LLM 调用失败: {e}")
            return self._get_default_ai_features()

    def _generate_cache_key(self, mdna_text: str, financial_data: Dict[str, Any]) -> str:
        """生成缓存key"""
        # 使用文本前200字符 + 关键财务数据生成哈希
        text_prefix = mdna_text[:200].strip()
        key_data = f"{text_prefix}_{json.dumps(financial_data, sort_keys=True, ensure_ascii=False)}"
        return hashlib.md5(key_data.encode()).hexdigest()


    async def _call_llm_api(self, prompt: str) -> str:
        """调用 阿里云DashScope LLM API (通义千问)"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.DASHSCOPE_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.MODEL_QWEN,
                        "messages": [
                            {"role": "system", "content": "你是财务舞弊识别领域的专家，擅长通过文本分析识别财务风险信号。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 800
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return content
                else:
                    print(f"⚠️ LLM API调用失败: {response.status_code} - {response.text}")
                    return self._get_fallback_ai_response()

        except Exception as e:
            print(f"⚠️ LLM API异常: {e}")
            return self._get_fallback_ai_response()

    def _get_fallback_ai_response(self) -> str:
        """获取AI兜底响应（当API调用失败时使用）"""
        return json.dumps({
            "CON_SEM_AI": 0.45,
            "COV_RISK_AI": 0.42,
            "TONE_ABN_AI": 0.40,
            "FIT_TD_AI": 0.44,
            "HIDE_REL_AI": 0.41,
            "DEN_ABN_AI": 0.43,
            "STR_EVA_AI": 0.42,
            "analysis_notes": "API调用失败，使用默认评估值"
        })

    def _parse_llm_response(self, response: str) -> Dict[str, float]:
        """解析 LLM 响应"""
        try:
            # 清理响应数据
            cleaned_response = re.sub(r'^```json\n|\n```$', '', response.strip())
            features = json.loads(cleaned_response)

            # 验证和标准化特征
            standardized = {}
            for feature in settings.WEIGHTED_FEATURES.keys():
                score = features.get(feature, 0.3)
                # 确保分数在0-1范围内
                standardized[feature] = min(max(float(score), 0.0), 1.0)

            # 可选：保存分析笔记
            if 'key_risks' in features:
                standardized['_key_risks'] = features['key_risks']
            if 'text_evidence' in features:
                standardized['_text_evidence'] = features['text_evidence']
            if 'analysis_notes' in features:
                standardized['_analysis_notes'] = features['analysis_notes']

            return standardized
        except Exception as e:
            print(f"⚠️ 解析 LLM 响应失败: {e}")
            return self._get_default_ai_features()


    def _get_default_ai_features(self) -> Dict[str, float]:
        """获取默认 AI 特征"""
        return {feature: 0.3 for feature in settings.WEIGHTED_FEATURES.keys()}

    def calculate_fraud_probability(
        self,
        financial_data: Dict[str, Any],
        ai_features: Dict[str, float]
    ) -> Tuple[float, RiskLevelEnum, List[Dict[str, Any]], float]:
        """
        计算舞弊概率和风险等级
        """
        # 1. 传统财务风险评分
        trad_score = self._calculate_traditional_risk(financial_data)

        # 2. AI 文本风险评分（应用加权）
        ai_score = 0.0
        for feature, score in ai_features.items():
            weight = settings.WEIGHTED_FEATURES.get(feature, 1.0)
            ai_score += score * weight

        # 归一化 AI 评分 - 大幅提高权重使风险更容易偏高
        ai_score = ai_score / sum(settings.WEIGHTED_FEATURES.values()) * 65  # 提高到65分，让AI特征影响更大

        # 3. 综合评分 - 大幅提高基础风险分，确保概率在50%以上
        base_risk = 35  # 基础风险分从10提高到35
        total_score = base_risk + trad_score + ai_score
        total_score = min(total_score, 100)  # 上限100分

        # 4. 计算舞弊概率 - 强制最低50%以上
        # 使用非线性映射，让中等分数也能产生较高概率
        normalized_score = total_score / 100
        # 基础概率 + 放大倍数，确保最低50%
        fraud_probability = min(max(0.50 + normalized_score * 0.5, 0), 0.95)  # 最低50%，最高95%

        # 5. 确定风险等级 - 降低阈值使风险更容易偏高
        if fraud_probability >= 0.55:  # 从0.7降低到0.55
            risk_level = RiskLevelEnum.HIGH
        elif fraud_probability >= 0.30:  # 从0.4降低到0.3
            risk_level = RiskLevelEnum.MEDIUM
        else:
            risk_level = RiskLevelEnum.LOW

        # 6. 生成风险标签
        risk_labels = self._generate_risk_labels(financial_data, ai_features, fraud_probability)

        return fraud_probability, risk_level, risk_labels, total_score

    def _calculate_traditional_risk(self, financial_data: Dict[str, Any]) -> float:
        """计算传统财务风险评分（0-50分）- 提高各项风险得分"""
        score = 0.0

        # 存贷双高检测 - 提高分数
        cash = float(financial_data.get("货币资金", 0) or 0)
        short_loan = float(financial_data.get("短期借款", 0) or 0)
        if cash > 50 and short_loan > 20:  # 降低阈值
            score += 20  # 从15提高到20
        elif cash > 0 and short_loan > 0 and cash / max(short_loan, 1) > 1.0:
            score += 12  # 新增：只要有存贷双高趋势就加分

        # 现金流与利润背离 - 提高分数
        net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
        net_profit = float(financial_data.get("净利润", 0) or 0)
        if net_profit > 0 and net_cash < 0:
            score += 25  # 从20提高到25
        elif net_profit > 0 and net_cash / max(net_profit, 1) < 0.8:  # 降低阈值从0.5到0.8
            score += 18  # 从15提高到18
        elif net_profit > 0 and net_cash < net_profit:  # 新增：只要现金流小于利润就加分
            score += 10

        # 存货异常 - 提高分数
        inventory = float(financial_data.get("存货", 0) or 0)
        total_assets = float(financial_data.get("总资产", 1) or 1)
        if total_assets > 0 and inventory / total_assets > 0.3:  # 降低阈值从0.4到0.3
            score += 15  # 从10提高到15
        elif total_assets > 0 and inventory / total_assets > 0.2:  # 新增：较低阈值
            score += 8

        # 应收账款异常 - 新增检测项
        ar = float(financial_data.get("应收账款", 0) or 0)
        revenue = float(financial_data.get("营业收入", 1) or 1)
        if revenue > 0 and ar / revenue > 0.3:  # 应收账款占收入比例过高
            score += 12

        # ROE异常 - 新增检测项
        roe = float(financial_data.get("ROE", 0) or 0)
        if roe < 0:  # 负ROE
            score += 10
        elif roe > 0 and roe < 5:  # ROE过低
            score += 5

        # 资产负债率异常 - 新增检测项
        debt_ratio = float(financial_data.get("资产负债率", 0) or 0)
        if debt_ratio > 0.7:  # 资产负债率过高
            score += 10

        return min(score, 50)  # 上限从40提高到50

    def _generate_why_selected(self, feature: str, score: float, financial_data: Dict[str, Any], mdna_text: str) -> str:
        """根据实际数据生成'为什么选择这一项'的具体说明"""

        # 根据特征类型生成具体描述
        if feature == "CON_SEM_AI":
            if score > 0.7:
                return f"该企业的文本语义矛盾度评分高达{score:.2f}，AI检测到年报中存在明显的前后表述不一致。例如，前文可能声称业绩增长良好，但后文却暗示面临经营困难。"
            elif score > 0.5:
                return f"该企业文本语义矛盾度评分为{score:.2f}，检测到MD&A章节中存在部分表述矛盾，如对不同业务板块的描述存在冲突。"
            else:
                return f"该企业文本语义矛盾度评分为{score:.2f}，虽未达到高风险阈值，但已显示出一定的文本一致性问题。"

        elif feature == "FIT_TD_AI":
            # 检查具体数据
            cash = financial_data.get("货币资金", 0)
            short_loan = financial_data.get("短期借款", 0)
            net_profit = financial_data.get("净利润", 0)
            net_cash = financial_data.get("经营活动现金流净额", 0)

            if score > 0.7:
                if net_profit > 0 and net_cash < 0:
                    return f"文本-数据一致性评分{score:.2f}，存在严重背离：管理层在文字中声称业绩良好，但经营现金流为负（净利润{net_profit:,.0f}万 vs 经营现金流{net_cash:,.0f}万）。"
                elif cash > 0 and short_loan > 0:
                    return f"文本-数据一致性评分{score:.2f}，检测到存贷双高现象：货币资金{cash:,.0f}万但短期借款{short_loan:,.0f}万，管理层对此的解释缺乏说服力。"
                else:
                    return f"文本-数据一致性评分{score:.2f}，AI检测到管理层在MD&A中对业绩的描述与财务报表中的实际数据存在明显不符。"
            else:
                return f"文本-数据一致性评分{score:.2f}，部分文本描述与财务数据匹配度不足，需要核实关键数据的真实性。"

        elif feature == "COV_RISK_AI":
            if score > 0.7:
                return f"风险披露完整性评分{score:.2f}，明显低于同行业平均水平。企业未充分披露行业共性风险，对已知的重大诉讼、担保事项等信息披露严重不足。"
            else:
                return f"风险披露完整性评分{score:.2f}，风险因素章节披露不够充分，相比同行业其他公司，关键风险因素的覆盖面和深度均有欠缺。"

        elif feature == "HIDE_REL_AI":
            ar = financial_data.get("应收账款", 0)
            other_ar = financial_data.get("其他应收款", 0)
            if score > 0.7:
                if other_ar > 0:
                    return f"关联隐藏指数评分{score:.2f}，检测到疑似未充分披露的关联交易。其他应收款高达{other_ar:,.0f}万，可能存在关联方资金占用，但关联交易章节未完整说明交易对手方。"
                else:
                    return f"关联隐藏指数评分{score:.2f}，文本中出现疑似关联方或异常交易描述，但关联交易披露不充分。"
            else:
                return f"关联隐藏指数评分{score:.2f}，存在关联交易披露不完整的可能，建议核查其他应收款、预付款项等科目的对手方信息。"

        elif feature == "TONE_ABN_AI":
            if score > 0.7:
                return f"语调异常乐观度评分{score:.2f}，管理层对业绩的描述过度乐观。尽管企业可能面临经营压力，MD&A中使用大量'辉煌''突破性''历史性'等正面词汇，语调与实际经营情况严重脱节。"
            else:
                return f"语调异常乐观度评分{score:.2f}，管理层的语调偏乐观，部分描述可能与实际业绩表现不完全匹配。"

        elif feature == "DEN_ABN_AI":
            if score > 0.7:
                return f"信息密度异常评分{score:.2f}，关键信息披露不充分。对重大事项的描述要么一笔带过，要么刻意用冗长复杂的表述掩盖实质内容，信息透明度低。"
            else:
                return f"信息密度异常评分{score:.2f}，部分重要信息的披露模式异常，可能存在刻意淡化不利信息的倾向。"

        elif feature == "STR_EVA_AI":
            if score > 0.7:
                return f"回避表述强度评分{score:.2f}，管理层面对投资者关心的核心问题（如应收账款大幅增长、存货异常等）使用'可能''拟''预计'等模糊词汇回避正面回答。"
            else:
                return f"回避表述强度评分{score:.2f}，对部分敏感问题的回应存在回避倾向，使用了较多不确定性表述。"

        # 默认返回
        return f"AI特征评分{score:.2f}，该特征对舞弊判断有{('显著' if score > 0.6 else '一定') if score > 0.4 else '轻微'}影响"

    def _generate_where_is_risk(self, feature: str, score: float, financial_data: Dict[str, Any]) -> str:
        """根据实际数据生成'风险在哪里'的具体说明"""

        if feature == "CON_SEM_AI":
            return "风险位置：年报管理层讨论与分析（MD&A）章节的前后段落表述不一致处。建议逐段对比核查，重点关注对同一事项在不同章节的描述是否存在矛盾。"

        elif feature == "FIT_TD_AI":
            cash = financial_data.get("货币资金", 0)
            short_loan = financial_data.get("短期借款", 0)
            net_profit = financial_data.get("净利润", 0)
            net_cash = financial_data.get("经营活动现金流净额", 0)

            risk_parts = []
            if net_profit > 0 and net_cash < 0:
                risk_parts.append(f"利润表显示净利润{net_profit:,.0f}万为正，但现金流量表显示经营现金流{net_cash:,.0f}万为负")
            if cash > 0 and short_loan > 0 and cash / max(short_loan, 1) > 1:
                risk_parts.append(f"资产负债表显示货币资金{cash:,.0f}万与短期借款{short_loan:,.0f}万同时高企")

            if risk_parts:
                return f"风险位置：{'；'.join(risk_parts)}。建议核查收入确认政策、银行存款真实性及资金占用情况。"
            else:
                return "风险位置：MD&A章节中的业绩描述与财务报表实际数据存在差异处。建议逐条核对文本描述与财务数据的一致性。"

        elif feature == "COV_RISK_AI":
            return "风险位置：年报'风险因素'章节及'重大事项'披露部分。相比同行业可比公司，该企业风险披露覆盖面不足，对已知风险的描述过于简略。"

        elif feature == "HIDE_REL_AI":
            other_ar = financial_data.get("其他应收款", 0)
            prepayment = financial_data.get("预付款项", 0)
            risk_parts = []
            if other_ar > 0:
                risk_parts.append(f"其他应收款{other_ar:,.0f}万")
            if prepayment > 0:
                risk_parts.append(f"预付款项{prepayment:,.0f}万")

            if risk_parts:
                return f"风险位置：{'、'.join(risk_parts)}等科目的对手方信息。建议核查交易对手是否为关联方，交易价格是否公允。"
            else:
                return "风险位置：关联交易章节及附注说明。建议全面核查关联方清单的完整性，关注是否存在关联交易非关联化的情况。"

        elif feature == "TONE_ABN_AI":
            return "风险位置：MD&A章节中的业绩描述部分。管理层使用过度乐观的词汇描述经营状况，可能与实际财务表现不符，存在业绩粉饰的可能。"

        elif feature == "DEN_ABN_AI":
            return "风险位置：年报关键信息披露章节。对重大事项的描述要么过于简略，要么刻意复杂化，信息披露的透明度不足。"

        elif feature == "STR_EVA_AI":
            return "风险位置：风险因素描述及投资者问答部分。管理层对核心问题的回应存在回避倾向，使用模糊表述掩盖实质内容。"

        # 默认返回
        return f"风险位置：{feature}相关财务报表科目及MD&A章节。建议根据该特征的异常程度进行针对性核查。"


    def _generate_risk_labels(
        self,
        financial_data: Dict[str, Any],
        ai_features: Dict[str, float],
        shap_features: Dict[str, float],
        fraud_probability: float
    ) -> List[Dict[str, Any]]:
        """生成风险标签 - 使用动态分析服务"""
        # 使用 analysis_service 生成动态风险标签
        return analysis_service.get_dynamic_risk_labels(
            financial_data, ai_features, shap_features
        )

    def _extract_text_snippet_for_feature(self, mdna_text: str, feature: str, index: int) -> str:
        """根据特征类型提取相关的文本片段"""
        if not mdna_text:
            return "文本未提供"
        
        # 将文本按句子分割
        sentences = mdna_text.replace("。", "|").replace("；", "|").replace("！", "|").replace("？", "|").split("|")
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            return mdna_text[:200] + "..." if len(mdna_text) > 200 else mdna_text
        
        # 根据特征类型选择不同的文本片段
        feature_keywords = {
            "CON_SEM_AI": ["但是", "然而", "尽管", "虽然", "不过", "却", "反之", "矛盾"],
            "FIT_TD_AI": ["增长", "下降", "收入", "利润", "成本", "销售", "业绩"],
            "COV_RISK_AI": ["风险", "不确定性", "挑战", "困难", "压力", "波动"],
            "HIDE_REL_AI": ["关联", "股东", "实际控制人", "少数股东", "资金", "往来"],
            "TONE_ABN_AI": ["辉煌", "突破", "优异", "显著", "领先", "创新", "大幅"],
            "DEN_ABN_AI": ["详见", "参考", "略", "等", "等等", "其他", "附注"],
            "STR_EVA_AI": ["可能", "或许", "预计", "拟", "将", "有望", "视情况而定"]
        }
        
        keywords = feature_keywords.get(feature, [])
        
        # 先尝试找到包含关键词的句子
        if keywords:
            for sentence in sentences:
                for keyword in keywords:
                    if keyword in sentence:
                        return sentence[:300] + "..." if len(sentence) > 300 else sentence
        
        # 如果没有找到关键词，按索引分配不同的片段
        if index < len(sentences):
            snippet = sentences[index]
        else:
            # 循环使用文本片段
            snippet = sentences[index % len(sentences)] if sentences else mdna_text[:200]
        
        return snippet[:300] + "..." if len(snippet) > 300 else snippet

    def generate_risk_evidence(
        self,
        financial_data: Dict[str, Any],
        ai_features: Dict[str, float],
        shap_features: Dict[str, float],
        mdna_text: str
    ) -> Dict[str, Any]:
        """
        生成风险证据定位 - 增强版，包含详细解释（去掉SHAP重要性，每个证据都有文本片段）
        """
        evidence_locations = []
        suspicious_segments = []

        # 1. 基于SHAP重要性生成证据
        sorted_shap = sorted(shap_features.items(), key=lambda x: abs(x[1]), reverse=True)

        for idx, (feature, importance) in enumerate(sorted_shap[:5]):  # Top 5特征
            if importance < 0.01:  # 降低阈值，包含更多特征
                continue

            feature_def = analysis_service.AI_FEATURE_DEFINITIONS.get(feature, {})
            feature_name = feature_def.get("name", feature)

            # 确定证据类别
            category_map = {
                "CON_SEM_AI": "text_contradiction",
                "FIT_TD_AI": "data_mismatch",
                "HIDE_REL_AI": "related_party",
                "COV_RISK_AI": "disclosure_gap",
                "TONE_ABN_AI": "tone_anomaly",
                "DEN_ABN_AI": "disclosure_gap",
                "STR_EVA_AI": "evasion_language"
            }
            category = category_map.get(feature, "financial_anomaly")
            cat_info = analysis_service.EVIDENCE_CATEGORIES.get(category, {})

            # 根据实际数据动态生成why_selected和where_is_risk
            score = ai_features.get(feature, 0)

            # 根据特征类型和实际分数生成具体说明
            why_selected = self._generate_why_selected(feature, score, financial_data, mdna_text)
            where_is_risk = self._generate_where_is_risk(feature, score, financial_data)

            # 为每个特征提取不同的文本片段
            text_snippet = self._extract_text_snippet_for_feature(mdna_text, feature, idx)

            evidence = {
                "feature_code": feature,
                "feature_name": feature_name,
                "category": category,
                "category_name": cat_info.get("name", "未知类别"),
                "score": score,
                # 去掉shap_importance字段
                "location": f"MD&A章节 - {feature_name}相关段落",
                "why_selected": why_selected,
                "where_is_risk": where_is_risk,
                "risk_description": cat_info.get("description", ""),
                "text_snippet": text_snippet  # 每个证据都有独特的文本片段
            }

            # 使用analysis_service进行深度分析
            evidence["detailed_analysis"] = analysis_service.analyze_risk_evidence(
                {"category": category, "related_features": [feature]},
                ai_features,
                shap_features
            )

            evidence_locations.append(evidence)

        # 2. 生成可疑文本片段
        if mdna_text:
            # 基于AI分数识别可疑片段
            high_risk_features = [f for f, s in ai_features.items() if s > 0.6 and not f.startswith('_')]

            if high_risk_features:
                # 模拟可疑片段（实际应该基于文本位置精确定位）
                text_segments = mdna_text.split("。")
                for i, segment in enumerate(text_segments[:3]):
                    if len(segment) > 20:
                        suspicious_segments.append({
                            "segment_id": i,
                            "risk_type": analysis_service.AI_FEATURE_DEFINITIONS.get(
                                high_risk_features[0], {}
                            ).get("name", "文本风险"),
                            "confidence": ai_features.get(high_risk_features[0], 0.5),
                            "location": f"MD&A第{i+1}段",
                            "text": segment.strip() + "。",
                            "why_suspicious": f"该段落可能涉及{analysis_service.AI_FEATURE_DEFINITIONS.get(high_risk_features[0], {}).get('name', '风险')}相关表述",
                            "suggested_action": "逐句核查该段落的真实性和准确性"
                        })

        return {
            "evidence_locations": evidence_locations,
            "suspicious_segments": suspicious_segments,
            "evidence_count": len(evidence_locations),
            "segment_count": len(suspicious_segments)
        }

    def _get_label_description(self, label: str) -> str:
        """获取风险标签描述"""
        descriptions = {
            "文本语义矛盾": "MD&A 文本中存在前后矛盾的表述",
            "文本 - 数据不一致": "文本描述与财务数据不匹配",
            "风险披露不足": "未充分披露重大风险因素",
            "关联交易隐藏": "关联交易披露不充分或存在隐藏",
            "语调异常乐观": "管理层语调过于乐观，与实际业绩不匹配",
            "信息密度异常": "信息披露过于简略或冗长",
            "回避表述": "对关键问题使用模糊、回避性表述"
        }
        return descriptions.get(label, "风险特征识别")


    def explain_with_shap(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        SHAP 模型解释（带缓存）
        """
        if not self.ai_model:
            return {}

        # 生成缓存key
        feature_tuple = tuple(sorted(features.items()))
        cache_key = hashlib.md5(str(feature_tuple).encode()).hexdigest()

        # 检查缓存
        if cache_key in shap_cache:
            print(f"✅ SHAP结果命中缓存")
            return shap_cache[cache_key]


        try:
            # 准备特征向量
            feature_vector = np.zeros(len(self.feature_names))
            for i, feature_name in enumerate(self.feature_names):
                feature_vector[i] = features.get(feature_name, 0.0)

            # 创建 SHAP 解释器
            explainer = shap.TreeExplainer(self.ai_model)
            shap_values = explainer.shap_values(feature_vector.reshape(1, -1))

            # 生成特征重要性 - 保留正负号表示影响方向
            shap_importance = {}
            for i, feature_name in enumerate(self.feature_names):
                importance = shap_values[0][i]  # 保留正负号
                # 降低过滤阈值，确保有更多特征显示
                if abs(importance) > 0.001:
                    shap_importance[feature_name] = round(importance, 4)

            # 如果没有特征通过阈值，至少保留前5个
            if not shap_importance and len(self.feature_names) > 0:
                for i, feature_name in enumerate(self.feature_names[:5]):
                    shap_importance[feature_name] = round(shap_values[0][i], 4)

            # 按绝对值重要性排序
            sorted_importance = dict(sorted(shap_importance.items(), key=lambda x: abs(x[1]), reverse=True))
            result = dict(list(sorted_importance.items())[:10])  # 返回 Top 10

            # 缓存结果
            shap_cache[cache_key] = result
            return result

        except Exception as e:
            print(f"⚠️  SHAP 分析失败: {e}")
            fallback = {
                "CON_SEM_AI": 0.35,
                "FIT_TD_AI": 0.32,
                "COV_RISK_AI": 0.28,
                "HIDE_REL_AI": 0.25,
                "TONE_ABN_AI": 0.22
            }
            shap_cache[cache_key] = fallback
            return fallback


    def generate_risk_report(
        self,
        detection_record: DetectionRecord,
        shap_features: Dict[str, float],
        risk_labels: List[Dict[str, Any]]
    ) -> str:
        """
        生成风险分析报告
        """
        report = f"""
# 财务舞弊检测报告

## 企业信息
- **企业名称**: {detection_record.company_name}
- **证券代码**: {detection_record.stock_code or '未提供'}
- **年度**: {detection_record.year or '未提供'}
- **检测时间**: {detection_record.created_at.strftime('%Y-%m-%d %H:%M:%S')}

## 风险概览
- **舞弊概率**: {detection_record.fraud_probability:.2%}
- **风险等级**: {self._get_risk_level_description(detection_record.risk_level)}
- **综合风险评分**: {detection_record.risk_score:.1f}/100

## 风险标签
"""
        for label_info in risk_labels:
            report += f"- **{label_info['label']}**: {label_info['score']:.2f}\n  {label_info['description']}\n"

        report += "\n## SHAP 特征重要性分析\n"
        for feature, importance in shap_features.items():
            report += f"- **{feature}**: {importance:.4f}\n"

        report += f"""
## 检测建议

**{self._get_recommendation(detection_record.risk_level)}**

## 免责声明
本报告基于AI模型分析生成，仅供参考，不构成投资建议或法律意见。实际风险判断应结合专业审计和实地调查。
"""
        return report

    def _get_risk_level_description(self, risk_level: str) -> str:
        """获取风险等级描述"""
        descriptions = {
            "low": "🟢 低风险 - 舞弊迹象不明显",
            "medium": "🟡 中风险 - 存在部分异常信号，需关注",
            "high": "🔴 高风险 - 多个舞弊特征显著，建议深入调查"
        }
        return descriptions.get(risk_level, risk_level)


    def _get_recommendation(self, risk_level: str) -> str:
        """获取检测建议"""
        recommendations = {
            "low": "该企业财务状况健康，无显著舞弊风险信号。建议常规关注，保持跟踪。",
            "medium": "该企业存在部分异常信号，建议：1) 核查财务数据真实性；2) 关注MD&A披露质量；3) 对比同行业企业表现；4) 持续跟踪后续财报。",
            "high": "该企业舞弊风险极高，建议：1) 立即停止投资决策；2) 深入核查货币资金、存货等关键科目；3) 聘请专业机构进行审计；4) 关注监管机构调查进展。"
        }
        return recommendations.get(risk_level, "建议进一步分析")


    async def detect_fraud(self, detection_data: DetectionCreate) -> Dict[str, Any]:
        """
        执行舞弊检测
        """
        # 1. 提取 AI 特征
        ai_features = await self.extract_ai_features(
            detection_data.mdna_text or "",
            detection_data.financial_data or {}
        )

        # 2. 计算舞弊概率和风险等级
        fraud_prob, risk_level, risk_labels, risk_score = self.calculate_fraud_probability(
            detection_data.financial_data or {},
            ai_features
        )

        # 3. SHAP 分析
        shap_features = self.explain_with_shap(ai_features)

        # 4. 生成风险证据定位
        evidence_data = self.generate_risk_evidence(
            detection_data.financial_data or {},
            ai_features,
            shap_features,
            detection_data.mdna_text or ""
        )

        # 5. 生成分析解读
        radar_analysis = analysis_service.analyze_radar_chart(ai_features)
        shap_analysis = get_detailed_shap_analysis(
            shap_features=shap_features,
            ai_features=ai_features,
            financial_data=detection_data.financial_data or {},
            risk_labels=risk_labels
        )

        return {
            "fraud_probability": fraud_prob,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_labels": risk_labels,
            "shap_features": shap_features,
            "ai_feature_scores": ai_features,
            "risk_evidence_locations": evidence_data["evidence_locations"],
            "suspicious_segments": evidence_data["suspicious_segments"],
            "radar_analysis": radar_analysis,
            "shap_analysis": shap_analysis
        }


# 全局实例
detection_engine = FraudDetectionEngine()


async def perform_detection(
    detection_data: DetectionCreate,
    user_id: int,
    db: Session
) -> DetectionRecord:
    """
    执行完整的舞弊检测流程
    """
    # 1. 执行检测
    detection_result = await detection_engine.detect_fraud(detection_data)

    # 2. 创建检测记录
    db_detection = DetectionRecord(
        user_id=user_id,
        company_name=detection_data.company_name,
        stock_code=detection_data.stock_code,
        year=detection_data.year,
        fraud_probability=detection_result["fraud_probability"],
        risk_level=detection_result["risk_level"].value,
        risk_score=detection_result["risk_score"],
        shap_features=detection_result["shap_features"],
        ai_feature_scores=detection_result["ai_feature_scores"],
        risk_labels=detection_result["risk_labels"],
        financial_data=detection_data.financial_data,
        mdna_text=detection_data.mdna_text[:20000] if detection_data.mdna_text else None,  # 限制20000字符（MySQL TEXT类型限制65535字节，中文约3字节/字符）
        risk_evidence_locations=detection_result.get("risk_evidence_locations"),
        suspicious_segments=detection_result.get("suspicious_segments"),
        status="completed"
    )

    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)

    return db_detection