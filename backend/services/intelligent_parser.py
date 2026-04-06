"""
智能解析引擎
- 提取AI特征并定位可疑文本位置
- 从材料中找出最可疑的地方（标明在文章中的位置）
"""
import re
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import httpx

from backend.core.config import settings


@dataclass
class RiskEvidence:
    """风险证据"""
    feature: str  # 特征名称
    feature_name: str  # 特征中文名
    score: float  # 风险得分
    location: str  # 位置描述
    page_num: Optional[int]  # 页码
    paragraph_num: Optional[int]  # 段落号
    text_snippet: str  # 文本片段
    explanation: str  # 解释说明


@dataclass
class SuspiciousSegment:
    """可疑文本片段"""
    location: str  # 位置
    page_num: Optional[int]  # 页码
    text: str  # 原文
    risk_type: str  # 风险类型
    confidence: float  # 置信度
    related_features: List[str]  # 相关特征


class IntelligentParser:
    """智能解析引擎"""

    # AI特征映射
    FEATURE_MAP = {
        "CON_SEM_AI": "语义矛盾度",
        "COV_RISK_AI": "风险披露完整性",
        "TONE_ABN_AI": "异常乐观语调",
        "FIT_TD_AI": "文本-数据一致性",
        "HIDE_REL_AI": "关联隐藏指数",
        "DEN_ABN_AI": "信息密度异常",
        "STR_EVA_AI": "回避表述强度"
    }

    # 风险关键词定位
    RISK_KEYWORDS = {
        "CON_SEM_AI": ["但是", "然而", "尽管", "虽然", "不过", "却", "反之", "尽管如此", "虽然如此"],
        "COV_RISK_AI": ["风险", "不确定性", "挑战", "困难", "压力", "波动", "下滑", "下降"],
        "TONE_ABN_AI": ["大幅增长", "突破", "领先", "优异", "显著", "持续向好", "创新高", "历史性"],
        "FIT_TD_AI": ["增长", "提升", "改善", "上升", "增加"],
        "HIDE_REL_AI": ["关联方", "关联交易", "关联关系", "少数股东", "实际控制人", "控股股东", "一致行动人"],
        "DEN_ABN_AI": [],  # 通过文本长度判断
        "STR_EVA_AI": ["可能", "或许", "大概", "预计", "计划", "拟", "将", "有望", "预期", "估计"]
    }

    def __init__(self):
        self.llm_client = None

    def _estimate_page_number(self, text: str, position: int) -> int:
        """估算页码（基于字符位置和平均每页字符数）"""
        # 假设平均每页1500字符（中文）
        chars_per_page = 1500
        return max(1, position // chars_per_page + 1)

    def _find_paragraph_number(self, text: str, position: int) -> int:
        """估算段落号"""
        # 计算前面有多少个换行符
        text_before = text[:position]
        return text_before.count('\n') + 1

    def _locate_keyword_context(self, text: str, keywords: List[str], window: int = 100) -> List[Dict]:
        """定位关键词上下文"""
        locations = []
        text_lower = text.lower()

        for keyword in keywords:
            for match in re.finditer(keyword, text_lower):
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)

                context = text[start:end]
                position = match.start()

                locations.append({
                    "keyword": keyword,
                    "context": context,
                    "position": position,
                    "page_num": self._estimate_page_number(text, position),
                    "paragraph_num": self._find_paragraph_number(text, position)
                })

        return locations

    async def extract_ai_features_with_location(
        self,
        mdna_text: str,
        financial_data: Dict[str, Any]
    ) -> Tuple[Dict[str, float], List[RiskEvidence]]:
        """
        提取AI特征并定位证据
        返回: (特征得分字典, 风险证据列表)
        """
        if not mdna_text:
            return self._get_default_features(), []

        # 构建增强提示词，要求LLM返回证据位置
        prompt = f"""
你是一位专业的财务舞弊识别专家。请分析以下MD&A文本，提取7个AI文本特征，并指出每个特征在原文中的具体位置。

【财务数据】
{json.dumps(financial_data, ensure_ascii=False, indent=2)}

【MD&A文本】（共{len(mdna_text)}字符）
{mdna_text[:8000]}

【分析要求】
请对以下7个维度进行评分（0-1之间，保留2位小数），并找出每个维度对应的原文证据：

1. CON_SEM_AI - 语义矛盾度：文本中是否存在前后矛盾的表述
2. COV_RISK_AI - 风险披露完整性：是否充分披露重大风险
3. TONE_ABN_AI - 异常乐观语调：语调是否过于乐观
4. FIT_TD_AI - 文本-数据一致性：文本描述与财务数据是否匹配
5. HIDE_REL_AI - 关联隐藏指数：是否隐藏关联交易
6. DEN_ABN_AI - 信息密度异常：信息披露密度是否异常
7. STR_EVA_AI - 回避表述强度：是否使用回避性表述

【输出格式】
请以JSON格式输出：
{{
    "CON_SEM_AI": {{
        "score": 0.65,
        "evidence": "具体文本片段",
        "explanation": "为什么给出这个分数",
        "page_hint": "大约在文本的哪个位置"
    }},
    ...其他特征
}}
"""

        try:
            # 调用LLM API
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.DASHSCOPE_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.MODEL_QWEN,
                        "messages": [
                            {"role": "system", "content": "你是财务舞弊识别领域的专家，擅长通过文本分析识别财务风险信号，并能准确定位风险证据。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    return self._parse_llm_response_with_location(content, mdna_text)
                else:
                    print(f"⚠️ LLM API调用失败: {response.status_code}")
                    return self._fallback_extraction(mdna_text, financial_data)

        except Exception as e:
            print(f"⚠️ 智能解析失败: {e}")
            return self._fallback_extraction(mdna_text, financial_data)

    def _parse_llm_response_with_location(
        self,
        response: str,
        original_text: str
    ) -> Tuple[Dict[str, float], List[RiskEvidence]]:
        """解析LLM响应，提取特征得分和证据位置"""
        features = {}
        evidences = []

        try:
            # 清理响应
            cleaned = re.sub(r'^```json\n|\n```$', '', response.strip())
            data = json.loads(cleaned)

            for feature_key, feature_data in data.items():
                if feature_key not in self.FEATURE_MAP:
                    continue

                # 提取分数
                score = feature_data.get("score", 0.3)
                if isinstance(score, str):
                    try:
                        score = float(score)
                    except:
                        score = 0.3

                features[feature_key] = min(max(score, 0.0), 1.0)

                # 提取证据
                evidence_text = feature_data.get("evidence", "")
                explanation = feature_data.get("explanation", "")
                page_hint = feature_data.get("page_hint", "")

                # 在原文中定位证据
                if evidence_text:
                    location = self._find_exact_location(original_text, evidence_text)
                else:
                    location = None

                evidences.append(RiskEvidence(
                    feature=feature_key,
                    feature_name=self.FEATURE_MAP.get(feature_key, feature_key),
                    score=features[feature_key],
                    location=page_hint or location.get("location", "未知位置") if location else "未知位置",
                    page_num=location.get("page_num") if location else None,
                    paragraph_num=location.get("paragraph_num") if location else None,
                    text_snippet=evidence_text or location.get("text", "")[:200] if location else "",
                    explanation=explanation
                ))

        except Exception as e:
            print(f"⚠️ 解析LLM响应失败: {e}")
            return self._fallback_extraction(original_text, {})

        return features, evidences

    def _find_exact_location(self, text: str, snippet: str) -> Optional[Dict]:
        """在原文中精确定位片段"""
        if not snippet or len(snippet) < 5:
            return None

        # 尝试精确匹配
        snippet_clean = snippet.strip()
        if snippet_clean in text:
            pos = text.find(snippet_clean)
            return {
                "location": f"第{self._estimate_page_number(text, pos)}页",
                "page_num": self._estimate_page_number(text, pos),
                "paragraph_num": self._find_paragraph_number(text, pos),
                "text": snippet_clean
            }

        # 尝试模糊匹配（取前20个字符）
        snippet_start = snippet_clean[:min(20, len(snippet_clean))]
        if snippet_start in text:
            pos = text.find(snippet_start)
            return {
                "location": f"第{self._estimate_page_number(text, pos)}页",
                "page_num": self._estimate_page_number(text, pos),
                "paragraph_num": self._find_paragraph_number(text, pos),
                "text": text[pos:pos+len(snippet_clean)]
            }

        return None

    def _fallback_extraction(
        self,
        mdna_text: str,
        financial_data: Dict[str, Any]
    ) -> Tuple[Dict[str, float], List[RiskEvidence]]:
        """备用提取方案（基于规则）"""
        features = {}
        evidences = []

        text_lower = mdna_text.lower()

        # 7个特征的规则提取
        for feature_key, feature_name in self.FEATURE_MAP.items():
            score = 0.35
            evidence_text = ""
            locations = []

            keywords = self.RISK_KEYWORDS.get(feature_key, [])

            if feature_key == "DEN_ABN_AI":
                # 信息密度通过文本长度判断
                text_length = len(mdna_text)
                if text_length < 500:
                    score = 0.65
                    evidence_text = "文本长度过短，信息披露可能不充分"
                elif text_length > 5000:
                    score = 0.55
                    evidence_text = "文本长度过长，可能存在信息冗余"
                else:
                    score = 0.35
                    evidence_text = "文本长度正常"

            elif keywords:
                # 统计关键词出现次数
                count = sum(1 for kw in keywords if kw in text_lower)

                # 定位关键词位置
                locations = self._locate_keyword_context(mdna_text, keywords[:3])

                if feature_key == "CON_SEM_AI":
                    score = min(0.35 + count * 0.1, 0.9) if count >= 2 else 0.35
                elif feature_key == "COV_RISK_AI":
                    score = 0.65 if count < 3 else (0.55 if count > 10 else 0.35)
                elif feature_key == "TONE_ABN_AI":
                    score = min(0.35 + count * 0.08, 0.95) if count > 3 else 0.35
                elif feature_key == "FIT_TD_AI":
                    # 检查文本-数据一致性
                    revenue_growth = financial_data.get("营业收入增长率", 0)
                    profit_growth = financial_data.get("净利润增长率", 0)

                    if ("增长" in text_lower or "提升" in text_lower) and revenue_growth < -0.1:
                        score = 0.85
                        evidence_text = "文本描述增长但实际营收下滑"
                    else:
                        score = 0.35
                elif feature_key == "HIDE_REL_AI":
                    score = 0.55 if count == 0 else min(0.35 + count * 0.05, 0.8)
                elif feature_key == "STR_EVA_AI":
                    score = min(0.35 + count * 0.04, 0.85) if count > 8 else 0.35

            features[feature_key] = round(score, 2)

            # 创建证据
            if locations:
                loc = locations[0]  # 取第一个位置
                evidences.append(RiskEvidence(
                    feature=feature_key,
                    feature_name=feature_name,
                    score=features[feature_key],
                    location=f"第{loc['page_num']}页，第{loc['paragraph_num']}段",
                    page_num=loc['page_num'],
                    paragraph_num=loc['paragraph_num'],
                    text_snippet=loc['context'][:200],
                    explanation=f"检测到关键词: {loc['keyword']}"
                ))
            elif evidence_text:
                evidences.append(RiskEvidence(
                    feature=feature_key,
                    feature_name=feature_name,
                    score=features[feature_key],
                    location="全文分析",
                    page_num=None,
                    paragraph_num=None,
                    text_snippet=evidence_text[:200],
                    explanation="基于规则自动分析"
                ))

        return features, evidences

    def extract_suspicious_segments(
        self,
        mdna_text: str,
        ai_features: Dict[str, float]
    ) -> List[SuspiciousSegment]:
        """
        提取最可疑的文本片段
        返回前5个最可疑的片段
        """
        segments = []
        text_lower = mdna_text.lower()

        # 高风险关键词组合
        high_risk_patterns = [
            {
                "keywords": ["存贷", "借款", "资金"],
                "risk_type": "存贷双高风险",
                "condition": lambda f: f.get("HIDE_REL_AI", 0) > 0.5
            },
            {
                "keywords": ["现金流", "利润", "盈利"],
                "risk_type": "现金流背离风险",
                "condition": lambda f: f.get("FIT_TD_AI", 0) > 0.5
            },
            {
                "keywords": ["关联", "股东", "控制"],
                "risk_type": "关联交易风险",
                "condition": lambda f: f.get("HIDE_REL_AI", 0) > 0.5
            },
            {
                "keywords": ["但是", "然而", "尽管"],
                "risk_type": "语义矛盾风险",
                "condition": lambda f: f.get("CON_SEM_AI", 0) > 0.5
            },
            {
                "keywords": ["大幅增长", "显著改善", "创新高"],
                "risk_type": "异常乐观语调",
                "condition": lambda f: f.get("TONE_ABN_AI", 0) > 0.5
            }
        ]

        for pattern in high_risk_patterns:
            if not pattern["condition"](ai_features):
                continue

            for keyword in pattern["keywords"]:
                for match in re.finditer(keyword, text_lower):
                    # 提取上下文
                    start = max(0, match.start() - 150)
                    end = min(len(mdna_text), match.end() + 150)
                    context = mdna_text[start:end]

                    position = match.start()
                    page_num = self._estimate_page_number(mdna_text, position)
                    para_num = self._find_paragraph_number(mdna_text, position)

                    # 计算置信度
                    confidence = sum(1 for k in pattern["keywords"] if k in context.lower()) / len(pattern["keywords"])
                    confidence = min(confidence * 1.5, 0.95)

                    segments.append(SuspiciousSegment(
                        location=f"第{page_num}页，第{para_num}段",
                        page_num=page_num,
                        text=context.strip(),
                        risk_type=pattern["risk_type"],
                        confidence=round(confidence, 2),
                        related_features=[k for k, v in ai_features.items() if v > 0.5]
                    ))

        # 去重并按置信度排序
        seen_texts = set()
        unique_segments = []
        for seg in sorted(segments, key=lambda x: x.confidence, reverse=True):
            text_hash = seg.text[:50]
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_segments.append(seg)

        return unique_segments[:5]

    def _get_default_features(self) -> Dict[str, float]:
        """获取默认特征值"""
        return {k: 0.35 for k in self.FEATURE_MAP.keys()}


# 全局实例
intelligent_parser = IntelligentParser()
