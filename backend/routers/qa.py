"""
AI 智能问答路由 - 支持流式输出
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, AsyncGenerator
import httpx
import json

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.config import settings
from backend.models.database import User, QAHistory
from backend.schemas.schemas import QAAskRequest, QAResponse, QASuggestionResponse

router = APIRouter(prefix="/qa", tags=["AI 问答"])


# 预设问题推荐
PRESET_QUESTIONS = {
    "theory": [
        "什么是财务舞弊的信号传递理论？",
        "信息不对称如何导致财务舞弊？",
        "舞弊三角理论的核心要素是什么？",
        "GONE 理论如何解释财务舞弊？"
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


# 预设答案库（简化版本，实际应调用 LLM）
PRESET_ANSWERS = {
    "存贷双高": """
**存贷双高**是指企业同时存在高货币资金和高有息负债的异常财务现象。

**识别特征：**
1. 货币资金占总资产比例超过 30%
2. 短期借款/长期借款金额巨大
3. 财务费用率高（利息支出大）

**舞弊风险：**
- 货币资金可能是虚构的（如康美药业 342 亿"不翼而飞"）
- 存贷双高违反商业常识：有钱为什么不还借款省利息？

**核查建议：**
1. 查看货币资金明细和存放地点
2. 函证银行存款余额
3. 分析利息收入与存款规模是否匹配
""",

    "康美药业": """
**康美药业（600518）舞弊案**是中国版"安然事件"，2019 年曝光的 300 亿货币资金"不翼而飞"。

**关键识别点：**

1. **存贷双高**
   - 货币资金：342 亿元
   - 短期借款：147 亿元
   - 典型"有钱却借钱"的异常现象

2. **现金流与利润背离**
   - 账面净利润：41 亿元
   - 经营现金流净额：-56 亿元
   - 利润没有现金支撑

3. **存货异常增长**
   - 存货余额激增 85%
   - 以"战略性备货"为由解释

4. **大股东高比例质押**
   - 大股东质押超 90% 持股
   - 资金链紧张信号

**结局：** 2021 年康美药业被判赔偿投资者 24.59 亿元，实控人获刑 12 年
""",

    "SHAP 分析": """
**SHAP (SHapley Additive exPlanations)** 是一种基于博弈论的机器学习可解释性方法。

**核心原理：**
1. 来自博弈论的 Shapley 值概念
2. 计算每个特征对预测结果的"边际贡献"
3. 满足效率性、对称性、线性等公理

**在舞弊识别中的应用：**
- 展示哪些财务指标/文本特征最影响舞弊判断
- 解决 AI"黑箱"问题，满足监管可解释性要求
- 帮助审计师定位重点核查方向

**示例解读：**
如果 SHAP 分析显示"FIT_TD_AI"（文本 - 数据一致性）是最重要的特征，
说明 MD&A 文本描述与财务数据的匹配程度是判断舞弊的关键依据。
""",

    "舞弊概率": """
**舞弊概率**是模型对企业财务报告存在舞弊可能性的量化评估（0-100%）。

**解读指南：**

| 概率区间 | 风险等级 | 含义 | 建议 |
|---------|---------|------|-----|
| 0-30% | 🟢 低风险 | 舞弊迹象不明显 | 常规关注 |
| 30-60% | 🟡 中风险 | 存在部分异常信号 | 重点核查 |
| 60-100% | 🔴 高风险 | 多个舞弊特征显著 | 深入调查 |

**注意事项：**
1. 舞弊概率≠确定舞弊，仅是风险提示
2. 需结合专业判断和实地核查
3. 关注具体风险标签和 SHAP 特征分析
4. 建议与健康企业对比分析

**使用建议：**
- 高风险企业：建议深入分析各项风险指标
- 中风险企业：关注具体风险标签指向
- 低风险企业：可作为投资/审计的参考依据
"""
}


def match_preset_answer(question: str) -> Optional[str]:
    """
    匹配预设答案（简化版本）
    """
    question_lower = question.lower()

    # 检查是否匹配预设问题
    for key, answer in PRESET_ANSWERS.items():
        if key.lower() in question_lower:
            return answer

    return None


# 系统提示词
SYSTEM_PROMPT = """你是一位财务舞弊识别领域的专家助手。请用专业、准确但通俗易懂的语言回答用户问题。

回答要求：
1. 回答要准确、专业，符合中国会计准则和监管实践
2. 适当使用表格、列表等形式增强可读性
3. 涉及案例时要准确引用真实数据
4. 对于不确定的内容要诚实说明"""


async def call_llm_api(question: str, context: str = "") -> str:
    """
    调用 LLM API 获取回答（同步版本 - 用于非流式）
    """
    user_prompt = f"{context}\n\n问题：{question}" if context else question

    # 调用 阿里云DashScope API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.DASHSCOPE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.MODEL_QWEN,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                # API 调用失败，返回预设答案
                print(f"⚠️ QA API调用失败: {response.status_code} - {response.text}")
                return f"（API 调用失败，使用预设答案）\n\n{match_preset_answer(question) or '抱歉，暂时无法回答该问题。'}"

    except Exception as e:
        # 异常时返回预设答案
        print(f"⚠️ QA API异常: {e}")
        preset = match_preset_answer(question)
        if preset:
            return f"（使用预设答案）\n\n{preset}"
        return f"抱歉，回答失败：{str(e)[:100]}"


async def call_llm_api_streaming(question: str, context: str = "") -> AsyncGenerator[str, None]:
    """
    调用 LLM API 获取流式回答
    """
    user_prompt = f"{context}\n\n问题：{question}" if context else question

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{settings.DASHSCOPE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.MODEL_QWEN,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500,
                    "stream": True  # 启用流式输出
                }
            ) as response:
                if response.status_code != 200:
                    error_msg = f"API调用失败: {response.status_code}"
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    return

                # 处理流式响应
                async for line in response.aiter_lines():
                    if not line or line.strip() == "":
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]  # 去掉 "data: " 前缀

                        if data_str == "[DONE]":
                            yield f"data: {json.dumps({'done': True})}\n\n"
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    content = delta["content"]
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        print(f"⚠️ 流式API异常: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    question_data: QAAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    向 AI 提问（非流式版本）
    """
    # 获取回答
    if question_data.category and question_data.category in ["theory", "practice", "policy", "case", "platform"]:
        context = f"问题类别：{question_data.category}"
    else:
        context = ""

    answer = await call_llm_api(question_data.question, context)

    # 保存问答历史
    db_qa = QAHistory(
        user_id=current_user.id,
        question=question_data.question,
        answer=answer,
        category=question_data.category
    )

    db.add(db_qa)
    db.commit()
    db.refresh(db_qa)

    return db_qa


@router.post("/ask-stream")
async def ask_question_stream(
    question_data: QAAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    向 AI 提问（流式输出版本）

    返回 Server-Sent Events (SSE) 格式的流式响应
    """
    # 获取上下文
    if question_data.category and question_data.category in ["theory", "practice", "policy", "case", "platform"]:
        context = f"问题类别：{question_data.category}"
    else:
        context = ""

    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        full_answer = ""

        # 发送开始标记
        yield f"data: {json.dumps({'start': True})}\n\n"

        # 流式获取回答
        async for chunk in call_llm_api_streaming(question_data.question, context):
            yield chunk

            # 收集完整回答用于保存
            try:
                if chunk.startswith("data: "):
                    data = json.loads(chunk[6:])
                    if "content" in data:
                        full_answer += data["content"]
            except:
                pass

        # 发送结束标记
        yield f"data: {json.dumps({'done': True})}\n\n"

        # 保存问答历史（异步保存）
        try:
            db_qa = QAHistory(
                user_id=current_user.id,
                question=question_data.question,
                answer=full_answer or "（流式输出内容）",
                category=question_data.category
            )
            db.add(db_qa)
            db.commit()
        except Exception as e:
            print(f"保存问答历史失败: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )


@router.get("/history", response_model=List[QAResponse])
def get_qa_history(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取问答历史
    """
    query = db.query(QAHistory).filter(
        QAHistory.user_id == current_user.id
    ).order_by(QAHistory.created_at.desc())

    offset = (page - 1) * page_size
    history = query.offset(offset).limit(page_size).all()

    return history


@router.get("/suggestions", response_model=List[QASuggestionResponse])
def get_suggestions(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取预设问题推荐
    """
    if category and category in PRESET_QUESTIONS:
        return [
            QASuggestionResponse(
                category=category,
                questions=PRESET_QUESTIONS[category]
            )
        ]

    # 返回所有类别
    return [
        QASuggestionResponse(category=cat, questions=questions)
        for cat, questions in PRESET_QUESTIONS.items()
    ]


@router.post("/favorite/{qa_id}")
def toggle_favorite(
    qa_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    收藏/取消收藏问答
    """
    qa = db.query(QAHistory).filter(
        QAHistory.id == qa_id,
        QAHistory.user_id == current_user.id
    ).first()

    if not qa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="问答记录不存在"
        )

    qa.is_favorite = not qa.is_favorite
    db.commit()

    return {"message": f"已{'收藏' if qa.is_favorite else '取消收藏'}"}
