"""
AI 智能问答服务
集成 LLM API，提供财务舞弊领域的专业问答
"""
import json
import re
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from datetime import datetime

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.database import QAHistory, User
from backend.schemas.schemas import QAAskRequest, QAResponse


class QAEngine:
    """
    AI 问答引擎
    """

    def __init__(self):
        """初始化问答引擎"""
        self.context_window = 5  # 上下文窗口大小
        self.max_tokens = 1500
        self.temperature = 0.7

    async def ask_question(
        self,
        question: str,
        user: User,
        category: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, float]:
        """
        向 AI 提问
        返回 (答案, 置信度)
        """
        # 1. 构建系统提示
        system_prompt = self._build_system_prompt(category)

        # 2. 构建上下文
        messages = [{"role": "system", "content": system_prompt}]

        if context:
            for msg in context[-self.context_window:]:
                messages.append(msg)

        messages.append({"role": "user", "content": question})

        # 3. 调用 LLM API
        try:
            response = await self._call_llm_api(messages)
            answer, confidence = self._parse_llm_response(response)
            return answer, confidence
        except Exception as e:
            print(f"⚠️  LLM 调用失败: {e}")
            return self._get_fallback_answer(question), 0.3

    def _build_system_prompt(self, category: Optional[str] = None) -> str:
        """构建系统提示"""
        base_prompt = """
你是一位财务舞弊识别领域的专业助手。请用专业、准确且易懂的语言回答用户问题。

回答要求：
1. 内容准确：确保财务、审计、法律相关内容的准确性
2. 通俗易懂：避免过度专业术语，必要时解释概念
3. 结构清晰：使用标题、列表、表格等格式提高可读性
4. 有理有据：引用法规、准则、案例时注明来源
5. 风险提示：涉及投资建议时，必须包含风险提示

专业领域：
- 财务舞弊识别理论（舞弊三角理论、GONE理论等）
- 财务分析技巧（比率分析、趋势分析、同业对比）
- 审计实务（风险导向审计、分析性程序）
- 监管规则（证监会规定、交易所规则、会计准则）
- 经典案例（康美药业、瑞幸咖啡、獐子岛等）
"""

        category_prompts = {
            "theory": "重点讲解理论基础、研究框架、学术观点",
            "practice": "重点讲解实操技巧、分析方法、工具使用",
            "policy": "重点讲解法律法规、监管政策、合规要求",
            "case": "重点讲解案例细节、舞弊手法、识别要点",
            "platform": "重点讲解平台功能、使用方法、报告解读"
        }

        if category in category_prompts:
            return base_prompt + f"\n\n当前问题类别：{category_prompts[category]}"
        return base_prompt

    async def _call_llm_api(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM API"""
        # 这里是简化版本，实际应集成具体的 LLM API 调用
        # 模拟不同类别的回答
        question = messages[-1]["content"].lower()

        # 预设回答库
        preset_answers = {
            "存贷双高": """
### 什么是存贷双高？

**存贷双高**是指企业同时存在高额货币资金和高额有息负债（短期借款）的异常财务现象。

#### 识别特征：
- 货币资金占总资产比例超过30%
- 短期借款金额巨大，资产负债率高
- 财务费用率高（利息支出大）
- 资金收益率低于借款利率

#### 舞弊风险：
1. **资金真实性存疑**：货币资金可能是虚构的（如康美药业342亿"不翼而飞"）
2. **商业逻辑违背**：有钱为什么不还借款省利息？
3. **资金被占用**：大股东可能通过关联方占用公司资金

#### 核查建议：
1. 查看货币资金明细和存放地点
2. 函证银行存款余额
3. 分析利息收入与存款规模是否匹配
4. 检查受限资金情况
""",
            "康美药业": """
### 康美药业舞弊案关键识别点

**康美药业（600518）** 是中国版"安然事件"，2019年曝光的300亿货币资金"不翼而飞"。

#### 核心识别特征：

**1. 存贷双高异常**
- 货币资金：342亿元
- 短期借款：147亿元
- 财务费用：高达11亿元
- **关键问题**：为什么有钱还要借这么多钱？

**2. 现金流与利润严重背离**
- 账面净利润：41亿元
- 经营活动现金流净额：-56亿元
- **关键问题**：利润没有现金支撑

**3. 存货异常增长**
- 存货余额激增85%
- 以"战略性备货"为由解释
- **关键问题**：存货大幅增长但没有相应收入增长

**4. MD&A 文本风险信号**
- 文本中对资金用途描述模糊
- 风险披露不充分
- 语调过于乐观，回避关键问题

#### 监管处罚：
- 被证监会处以60万元顶格罚款
- 实控人马兴田被判刑12年
- 赔偿投资者24.59亿元

#### 识别启示：
1. **数据+文本双维度分析**：仅看财务数据可能不够，需要结合MD&A文本分析
2. **关注异常财务比率**：存贷双高、现金流背离是重要预警信号
3. **重视文本语调分析**：管理层语调异常乐观往往伴随财务舞弊
""",
            "SHAP分析": """
### SHAP 分析原理与应用

**SHAP (SHapley Additive exPlanations)** 是一种基于博弈论的机器学习可解释性方法。

#### 核心原理：
1. **Shapley 值**：源自合作博弈论，衡量每个特征对预测结果的"边际贡献"
2. **数学性质**：满足效率性、对称性、线性等公理，保证解释的一致性
3. **计算方法**：通过蒙特卡洛采样或树模型专用算法高效计算

#### 在舞弊识别中的应用：

**1. 识别关键风险特征**
- 展示哪些财务指标/文本特征最影响舞弊判断
- 帮助审计师定位重点核查方向

**2. 增强模型可解释性**
- 解决 AI"黑箱"问题，满足监管可解释性要求
- 为审计意见提供量化支持

**3. 优化检测策略**
- 根据特征重要性调整风险阈值
- 为不同行业定制检测模型

#### 示例解读：
如果 SHAP 分析显示：
- "FIT_TD_AI"（文本-数据一致性）重要性：0.32
- "CON_SEM_AI"（语义矛盾）重要性：0.28
- "COV_RISK_AI"（风险披露）重要性：0.21

**解读**：MD&A 文本与财务数据的一致性是判断舞弊的最关键因素，企业经常通过文本描述掩盖财务异常。

#### 实际应用建议：
1. **重点关注 Top 3 特征**：通常它们贡献了80%以上的解释力
2. **结合业务逻辑**：SHAP 值需要结合具体业务场景解读
3. **动态监控**：定期重新计算 SHAP 值，跟踪特征重要性变化
"""
        }

        # 匹配预设问题
        for keyword, answer in preset_answers.items():
            if keyword in question:
                return json.dumps({
                    "choices": [{"message": {"content": answer}}],
                    "confidence": 0.95
                })

        # 模拟通用回答
        return json.dumps({
            "choices": [{"message": {"content": f"关于 '{question[:20]}...' 的专业解答：\n\n在财务舞弊识别中，这是一个重要问题。根据我们的分析，...（详细解答）\n\n建议进一步关注相关财务指标和文本特征。"}}],
            "confidence": 0.85
        })

    def _parse_llm_response(self, response: str) -> Tuple[str, float]:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            answer = data["choices"][0]["message"]["content"]
            confidence = data.get("confidence", 0.8)
            return answer, confidence
        except Exception as e:
            print(f"⚠️  解析 LLM 响应失败: {e}")
            return "抱歉，暂时无法回答该问题。", 0.3

    def _get_fallback_answer(self, question: str) -> str:
        """获取兜底回答"""
        question_lower = question.lower()

        if "存贷双高" in question_lower:
            return "存贷双高是指企业同时存在高额货币资金和高额短期借款的异常现象。这通常表明企业的资金管理存在问题，可能是虚构货币资金或资金被占用。建议核查银行存款真实性、利息收支匹配性等。"
        elif "舞弊" in question_lower or "识别" in question_lower:
            return "财务舞弊识别需要结合财务数据异常分析和非财务信息（如MD&A文本）分析。关键指标包括：存贷双高、现金流与利润背离、存货异常增长等。同时关注文本语调、风险披露完整性等非结构化特征。"
        elif "报告" in question_lower or "解读" in question_lower:
            return "舞弊检测报告包含舞弊概率、风险等级、风险标签、SHAP特征分析等核心内容。舞弊概率超过70%为高风险，40-70%为中风险，低于40%为低风险。重点关注高风险标签和SHAP重要性排名靠前的特征。"
        else:
            return "这是一个关于财务舞弊识别的专业问题。建议您：1) 查阅相关专业文献；2) 咨询专业审计师；3) 使用我们的舞弊检测功能进行实证分析。如需更详细的解答，请提供更具体的问题描述。"

    def get_suggested_questions(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """获取推荐问题"""
        suggestions = {
            "theory": [
                "什么是财务舞弊的信号传递理论？",
                "舞弊三角理论的核心要素是什么？",
                "信息不对称如何导致财务舞弊？",
                "GONE理论如何解释财务舞弊？"
            ],
            "practice": [
                "什么是存贷双高？如何识别？",
                "如何识别 MD&A 中的语义矛盾？",
                "审计中如何使用 AI 工具辅助？",
                "如何通过现金流分析识别舞弊？"
            ],
            "policy": [
                "A 股信息披露规则有哪些核心要求？",
                "证监会财务舞弊处罚标准是什么？",
                "新证券法对舞弊的处罚力度如何？",
                "会计师事务所的审计责任有哪些？"
            ],
            "case": [
                "康美药业舞弊案的关键识别点是什么？",
                "瑞幸咖啡虚增收入的手法是什么？",
                "獐子岛扇贝跑路事件如何识别？",
                "贵州茅台为什么是健康企业典型？"
            ],
            "platform": [
                "如何解读舞弊概率？",
                "SHAP 分析的原理是什么？",
                "如何导出检测报告？",
                "会员版和免费版有什么区别？"
            ]
        }

        if category and category in suggestions:
            return {category: suggestions[category]}
        return suggestions

    async def save_qa_history(
        self,
        user_id: int,
        question: str,
        answer: str,
        category: Optional[str],
        confidence: float
    ) -> QAResponse:
        """保存问答历史"""
        db = SessionLocal()
        try:
            db_qa = QAHistory(
                user_id=user_id,
                question=question,
                answer=answer,
                category=category,
                feedback_score=int(confidence * 5)  # 转换为1-5分
            )
            db.add(db_qa)
            db.commit()
            db.refresh(db_qa)
            return QAResponse.model_validate(db_qa)
        finally:
            db.close()

# 全局实例
qa_engine = QAEngine()
