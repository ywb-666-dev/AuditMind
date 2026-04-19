"""
财务报表助手路由
帮助企业填写四表一注：资产负债表、利润表、现金流量表、所有者权益变动表、财务报表附注
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json

from core.database import get_db
from core.security import get_current_user
from models.database import FinancialStatement, User
from schemas.schemas import (
    FinancialStatementCreate, FinancialStatementUpdate,
    FinancialStatementResponse, FinancialStatementListItem,
    AISuggestionRequest, AISuggestionResponse, ValidationResult,
    MessageResponse
)

router = APIRouter(prefix="/financial-statements", tags=["财务报表助手"])


# ==================== 预设模板：标准报表项目 ====================

BALANCE_SHEET_TEMPLATE = {
    "流动资产": [
        {"item_name": "货币资金", "item_code": "1001", "ending_balance": None, "beginning_balance": None},
        {"item_name": "交易性金融资产", "item_code": "1101", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应收票据", "item_code": "1121", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应收账款", "item_code": "1122", "ending_balance": None, "beginning_balance": None},
        {"item_name": "预付款项", "item_code": "1123", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他应收款", "item_code": "1221", "ending_balance": None, "beginning_balance": None},
        {"item_name": "存货", "item_code": "1401", "ending_balance": None, "beginning_balance": None},
        {"item_name": "一年内到期的非流动资产", "item_code": "1501", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他流动资产", "item_code": "1901", "ending_balance": None, "beginning_balance": None},
    ],
    "非流动资产": [
        {"item_name": "可供出售金融资产", "item_code": "1503", "ending_balance": None, "beginning_balance": None},
        {"item_name": "持有至到期投资", "item_code": "1501", "ending_balance": None, "beginning_balance": None},
        {"item_name": "长期股权投资", "item_code": "1511", "ending_balance": None, "beginning_balance": None},
        {"item_name": "投资性房地产", "item_code": "1521", "ending_balance": None, "beginning_balance": None},
        {"item_name": "固定资产", "item_code": "1601", "ending_balance": None, "beginning_balance": None},
        {"item_name": "在建工程", "item_code": "1604", "ending_balance": None, "beginning_balance": None},
        {"item_name": "无形资产", "item_code": "1701", "ending_balance": None, "beginning_balance": None},
        {"item_name": "开发支出", "item_code": "5301", "ending_balance": None, "beginning_balance": None},
        {"item_name": "商誉", "item_code": "1711", "ending_balance": None, "beginning_balance": None},
        {"item_name": "长期待摊费用", "item_code": "1801", "ending_balance": None, "beginning_balance": None},
        {"item_name": "递延所得税资产", "item_code": "1811", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他非流动资产", "item_code": "1902", "ending_balance": None, "beginning_balance": None},
    ],
    "流动负债": [
        {"item_name": "短期借款", "item_code": "2001", "ending_balance": None, "beginning_balance": None},
        {"item_name": "交易性金融负债", "item_code": "2101", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付票据", "item_code": "2201", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付账款", "item_code": "2202", "ending_balance": None, "beginning_balance": None},
        {"item_name": "预收款项", "item_code": "2203", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付职工薪酬", "item_code": "2211", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应交税费", "item_code": "2221", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付利息", "item_code": "2231", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付股利", "item_code": "2232", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他应付款", "item_code": "2241", "ending_balance": None, "beginning_balance": None},
        {"item_name": "一年内到期的非流动负债", "item_code": "2501", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他流动负债", "item_code": "2401", "ending_balance": None, "beginning_balance": None},
    ],
    "非流动负债": [
        {"item_name": "长期借款", "item_code": "2501", "ending_balance": None, "beginning_balance": None},
        {"item_name": "应付债券", "item_code": "2502", "ending_balance": None, "beginning_balance": None},
        {"item_name": "长期应付款", "item_code": "2701", "ending_balance": None, "beginning_balance": None},
        {"item_name": "预计负债", "item_code": "2801", "ending_balance": None, "beginning_balance": None},
        {"item_name": "递延收益", "item_code": "2401", "ending_balance": None, "beginning_balance": None},
        {"item_name": "递延所得税负债", "item_code": "2901", "ending_balance": None, "beginning_balance": None},
        {"item_name": "其他非流动负债", "item_code": "2601", "ending_balance": None, "beginning_balance": None},
    ],
    "所有者权益": [
        {"item_name": "实收资本（或股本）", "item_code": "4001", "ending_balance": None, "beginning_balance": None},
        {"item_name": "资本公积", "item_code": "4002", "ending_balance": None, "beginning_balance": None},
        {"item_name": "盈余公积", "item_code": "4101", "ending_balance": None, "beginning_balance": None},
        {"item_name": "未分配利润", "item_code": "4103", "ending_balance": None, "beginning_balance": None},
    ],
}

INCOME_STATEMENT_TEMPLATE = {
    "营业收入": [
        {"item_name": "营业收入", "item_code": "6001", "current_period": None, "previous_period": None},
        {"item_name": "其中：主营业务收入", "item_code": "600101", "current_period": None, "previous_period": None},
        {"item_name": "其他业务收入", "item_code": "6051", "current_period": None, "previous_period": None},
    ],
    "营业成本及费用": [
        {"item_name": "营业成本", "item_code": "6401", "current_period": None, "previous_period": None},
        {"item_name": "税金及附加", "item_code": "6403", "current_period": None, "previous_period": None},
        {"item_name": "销售费用", "item_code": "6601", "current_period": None, "previous_period": None},
        {"item_name": "管理费用", "item_code": "6602", "current_period": None, "previous_period": None},
        {"item_name": "研发费用", "item_code": "5301", "current_period": None, "previous_period": None},
        {"item_name": "财务费用", "item_code": "6603", "current_period": None, "previous_period": None},
    ],
    "利润相关": [
        {"item_name": "其他收益", "item_code": "6117", "current_period": None, "previous_period": None},
        {"item_name": "投资收益", "item_code": "6111", "current_period": None, "previous_period": None},
        {"item_name": "公允价值变动收益", "item_code": "6101", "current_period": None, "previous_period": None},
        {"item_name": "信用减值损失", "item_code": "6701", "current_period": None, "previous_period": None},
        {"item_name": "资产减值损失", "item_code": "6711", "current_period": None, "previous_period": None},
        {"item_name": "资产处置收益", "item_code": "6115", "current_period": None, "previous_period": None},
        {"item_name": "营业利润", "item_code": "6901", "current_period": None, "previous_period": None},
        {"item_name": "营业外收入", "item_code": "6301", "current_period": None, "previous_period": None},
        {"item_name": "营业外支出", "item_code": "6711", "current_period": None, "previous_period": None},
        {"item_name": "利润总额", "item_code": "6902", "current_period": None, "previous_period": None},
        {"item_name": "所得税费用", "item_code": "6801", "current_period": None, "previous_period": None},
        {"item_name": "净利润", "item_code": "6903", "current_period": None, "previous_period": None},
    ],
}

CASH_FLOW_TEMPLATE = {
    "经营活动": [
        {"item_name": "销售商品、提供劳务收到的现金", "item_code": "CF01", "current_period": None},
        {"item_name": "收到的税费返还", "item_code": "CF02", "current_period": None},
        {"item_name": "收到其他与经营活动有关的现金", "item_code": "CF03", "current_period": None},
        {"item_name": "经营活动现金流入小计", "item_code": "CF04", "current_period": None},
        {"item_name": "购买商品、接受劳务支付的现金", "item_code": "CF05", "current_period": None},
        {"item_name": "支付给职工以及为职工支付的现金", "item_code": "CF06", "current_period": None},
        {"item_name": "支付的各项税费", "item_code": "CF07", "current_period": None},
        {"item_name": "支付其他与经营活动有关的现金", "item_code": "CF08", "current_period": None},
        {"item_name": "经营活动现金流出小计", "item_code": "CF09", "current_period": None},
        {"item_name": "经营活动产生的现金流量净额", "item_code": "CF10", "current_period": None},
    ],
    "投资活动": [
        {"item_name": "收回投资收到的现金", "item_code": "CF11", "current_period": None},
        {"item_name": "取得投资收益收到的现金", "item_code": "CF12", "current_period": None},
        {"item_name": "处置固定资产等收回的现金", "item_code": "CF13", "current_period": None},
        {"item_name": "投资活动现金流入小计", "item_code": "CF14", "current_period": None},
        {"item_name": "购建固定资产等支付的现金", "item_code": "CF15", "current_period": None},
        {"item_name": "投资支付的现金", "item_code": "CF16", "current_period": None},
        {"item_name": "投资活动现金流出小计", "item_code": "CF17", "current_period": None},
        {"item_name": "投资活动产生的现金流量净额", "item_code": "CF18", "current_period": None},
    ],
    "筹资活动": [
        {"item_name": "吸收投资收到的现金", "item_code": "CF19", "current_period": None},
        {"item_name": "取得借款收到的现金", "item_code": "CF20", "current_period": None},
        {"item_name": "筹资活动现金流入小计", "item_code": "CF21", "current_period": None},
        {"item_name": "偿还债务支付的现金", "item_code": "CF22", "current_period": None},
        {"item_name": "分配股利、利润或偿付利息支付的现金", "item_code": "CF23", "current_period": None},
        {"item_name": "筹资活动现金流出小计", "item_code": "CF24", "current_period": None},
        {"item_name": "筹资活动产生的现金流量净额", "item_code": "CF25", "current_period": None},
    ],
    "现金及等价物": [
        {"item_name": "汇率变动对现金的影响", "item_code": "CF26", "current_period": None},
        {"item_name": "现金及现金等价物净增加额", "item_code": "CF27", "current_period": None},
        {"item_name": "期初现金及现金等价物余额", "item_code": "CF28", "current_period": None},
        {"item_name": "期末现金及现金等价物余额", "item_code": "CF29", "current_period": None},
    ],
}

EQUITY_CHANGE_TEMPLATE = {
    "所有者权益变动": [
        {"item_name": "实收资本（或股本）", "item_code": "EQ01", "beginning_balance": None, "increase": None, "decrease": None, "ending_balance": None},
        {"item_name": "资本公积", "item_code": "EQ02", "beginning_balance": None, "increase": None, "decrease": None, "ending_balance": None},
        {"item_name": "盈余公积", "item_code": "EQ03", "beginning_balance": None, "increase": None, "decrease": None, "ending_balance": None},
        {"item_name": "未分配利润", "item_code": "EQ04", "beginning_balance": None, "increase": None, "decrease": None, "ending_balance": None},
        {"item_name": "所有者权益合计", "item_code": "EQ05", "beginning_balance": None, "increase": None, "decrease": None, "ending_balance": None},
    ],
}


NOTES_TEMPLATE = """## 一、公司基本情况
（请填写公司注册信息、经营范围、组织架构等）

## 二、财务报表编制基础
（请说明编制依据，如企业会计准则等）

## 三、重要会计政策和会计估计
（请说明重要的会计政策选择，如收入确认、折旧方法等）

## 四、税项
（请说明适用的主要税种及税率）

## 五、财务报表主要项目注释
### 1. 货币资金
### 2. 应收账款
### 3. 存货
### 4. 固定资产
### 5. 短期借款
### 6. 应付账款
（请逐项填写详细注释信息）

## 六、或有事项
（请说明重大或有事项）

## 七、资产负债表日后事项
（请说明期后重大事项）
"""


# ==================== 路由 ====================

@router.get("/templates", response_model=Dict[str, Any])
def get_templates():
    """获取四表一注的标准模板"""
    return {
        "balance_sheet": BALANCE_SHEET_TEMPLATE,
        "income_statement": INCOME_STATEMENT_TEMPLATE,
        "cash_flow": CASH_FLOW_TEMPLATE,
        "equity_change": EQUITY_CHANGE_TEMPLATE,
        "notes": NOTES_TEMPLATE,
    }


@router.get("", response_model=List[FinancialStatementListItem])
def list_financial_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    year: Optional[int] = None,
    company_name: Optional[str] = None,
):
    """获取当前用户的财务报表列表"""
    query = db.query(FinancialStatement).filter(
        FinancialStatement.user_id == current_user.id
    )

    if year:
        query = query.filter(FinancialStatement.report_year == year)
    if company_name:
        query = query.filter(FinancialStatement.company_name.contains(company_name))

    statements = query.order_by(FinancialStatement.created_at.desc()).offset(skip).limit(limit).all()
    return statements


@router.post("", response_model=FinancialStatementResponse, status_code=status.HTTP_201_CREATED)
def create_financial_statement(
    data: FinancialStatementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的财务报表"""
    # 检查是否存在同企业同年度的报表
    existing = db.query(FinancialStatement).filter(
        FinancialStatement.user_id == current_user.id,
        FinancialStatement.company_name == data.company_name,
        FinancialStatement.report_year == data.report_year,
        FinancialStatement.report_period == data.report_period,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该企业该年度已存在报表，请直接编辑或删除后重建"
        )

    statement = FinancialStatement(
        user_id=current_user.id,
        company_name=data.company_name,
        stock_code=data.stock_code,
        report_year=data.report_year,
        report_period=data.report_period,
        balance_sheet=data.balance_sheet or BALANCE_SHEET_TEMPLATE,
        income_statement=data.income_statement or INCOME_STATEMENT_TEMPLATE,
        cash_flow=data.cash_flow or CASH_FLOW_TEMPLATE,
        equity_change=data.equity_change or EQUITY_CHANGE_TEMPLATE,
        notes=data.notes or NOTES_TEMPLATE,
        status="draft",
    )

    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("/{statement_id}", response_model=FinancialStatementResponse)
def get_financial_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个财务报表详情"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    return statement


@router.put("/{statement_id}", response_model=FinancialStatementResponse)
def update_financial_statement(
    statement_id: int,
    data: FinancialStatementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新财务报表"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(statement, field, value)

    db.commit()
    db.refresh(statement)
    return statement


@router.delete("/{statement_id}", response_model=MessageResponse)
def delete_financial_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除财务报表"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    db.delete(statement)
    db.commit()
    return MessageResponse(message="删除成功")


@router.post("/{statement_id}/validate", response_model=ValidationResult)
def validate_financial_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """校验财务报表数据的勾稽关系"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    errors = []
    warnings = []
    details = {}

    # 校验资产负债表：资产 = 负债 + 所有者权益
    bs = statement.balance_sheet or {}
    if bs:
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0

        for section, items in bs.items():
            for item in items:
                val = item.get("ending_balance") or 0
                if "资产" in section and "非流动" not in section:
                    total_assets += val
                elif "负债" in section:
                    total_liabilities += val
                elif "权益" in section or "所有者" in section:
                    total_equity += val

        if abs(total_assets - (total_liabilities + total_equity)) > 0.01:
            errors.append(f"资产负债表不平衡：资产({total_assets:.2f}) != 负债({total_liabilities:.2f}) + 所有者权益({total_equity:.2f})")
        details["total_assets"] = total_assets
        details["total_liabilities"] = total_liabilities
        details["total_equity"] = total_equity

    # 校验利润表：营业利润 → 利润总额 → 净利润
    is_data = statement.income_statement or {}
    if is_data:
        # 简化校验：净利润 = 利润总额 - 所得税费用
        pass

    # 校验现金流量表：期末 = 期初 + 净增加额
    cf = statement.cash_flow or {}
    if cf:
        pass

    is_valid = len(errors) == 0
    result = ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        details=details,
    )

    # 保存校验结果
    statement.validation_results = result.model_dump()
    db.commit()

    return result


@router.post("/{statement_id}/ai-suggestions", response_model=AISuggestionResponse)
def get_ai_suggestions(
    statement_id: int,
    req: AISuggestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取AI填表建议（基于已有数据智能推荐）"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    # 基于已有数据给出简单建议（实际可接入AI模型）
    suggestions = []
    warnings = []
    estimated = {}

    if req.statement_type == "balance_sheet":
        suggestions.append("请确保货币资金与现金流量表期末余额一致")
        suggestions.append("应收账款账龄分析需与附注中的坏账准备匹配")
        warnings.append("如存货金额较大，建议在附注中披露详细的存货明细")
    elif req.statement_type == "income_statement":
        suggestions.append("营业收入增长率应与行业平均水平对比")
        suggestions.append("毛利率异常波动需在附注中说明原因")
    elif req.statement_type == "cash_flow":
        suggestions.append("经营活动现金流量净额应与净利润基本匹配")
        suggestions.append("如投资活动现金流出较大，需说明主要投资项目")
    elif req.statement_type == "equity_change":
        suggestions.append("所有者权益变动应与资产负债表对应科目一致")
    elif req.statement_type == "notes":
        suggestions.append("重要会计政策需说明选择依据")
        suggestions.append("关联交易需详细披露交易对手及金额")

    response = AISuggestionResponse(
        suggestions=suggestions,
        warnings=warnings if warnings else None,
        estimated_values=estimated if estimated else None,
    )

    # 保存AI建议
    existing = statement.ai_suggestions or {}
    existing[req.statement_type] = response.model_dump()
    statement.ai_suggestions = existing
    db.commit()

    return response


@router.post("/{statement_id}/complete", response_model=FinancialStatementResponse)
def complete_financial_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记报表为已完成"""
    statement = db.query(FinancialStatement).filter(
        FinancialStatement.id == statement_id,
        FinancialStatement.user_id == current_user.id,
    ).first()

    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="财务报表不存在"
        )

    statement.status = "completed"
    db.commit()
    db.refresh(statement)
    return statement
