"""
整改建议引擎
- 基于风险类型，自动生成可执行的整改操作指引
- 财务总监知道下一步该改什么
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from backend.models.database import RemediationSuggestion, DetectionRecord


@dataclass
class RemediationAction:
    """整改行动项"""
    step: int  # 步骤序号
    action: str  # 行动内容
    responsible: str  # 责任部门
    timeline: str  # 时间要求
    deliverable: str  # 交付物
    priority: str  # high/medium/low


@dataclass
class RiskRemediation:
    """风险整改方案"""
    risk_type: str  # 风险类型
    risk_level: str  # high/medium/low
    title: str  # 标题
    description: str  # 问题描述
    actions: List[RemediationAction]  # 行动列表
    regulations: List[Dict]  # 相关法规
    references: List[Dict]  # 参考案例


class RemediationEngine:
    """整改建议引擎"""

    # 内置整改建议模板
    DEFAULT_TEMPLATES = {
        "存贷双高": {
            "title": "货币资金与短期借款同时高企问题整改",
            "description": "公司账面货币资金充裕但同时又存在大额短期借款，可能存在资金真实性存疑或资金被占用的情况。",
            "department": "财务/审计",
            "estimated_days": 60,
            "actions": [
                {
                    "step": 1,
                    "action": "全面梳理银行账户，编制资金明细表",
                    "responsible": "财务部",
                    "timeline": "1周内",
                    "deliverable": "银行账户清单及余额明细",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "核查大额资金流水，确认资金真实性",
                    "responsible": "审计部",
                    "timeline": "2周内",
                    "deliverable": "资金流水核查报告",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "分析借款必要性，制定资金优化方案",
                    "responsible": "财务总监",
                    "timeline": "2周内",
                    "deliverable": "资金优化方案",
                    "priority": "medium"
                },
                {
                    "step": 4,
                    "action": "在年报中补充披露资金存管及使用情况的专项说明",
                    "responsible": "董秘办",
                    "timeline": "1月内",
                    "deliverable": "补充披露公告",
                    "priority": "high"
                }
            ],
            "regulations": [
                {"name": "《企业会计准则》", "article": "货币资金", "content": "货币资金应按实际发生额计量，确保真实完整"},
                {"name": "《上市公司信息披露管理办法》", "article": "第十九条", "content": "公司应真实、准确、完整、及时地披露信息"}
            ],
            "references": [
                {"case_name": "康美药业", "lesson": "虚构货币资金887亿元，暴露资金真实性核查漏洞"}
            ]
        },
        "现金流背离": {
            "title": "净利润与经营现金流背离问题整改",
            "description": "公司账面盈利但经营现金流持续为负或远低于净利润，可能存在收入确认不当或应收账款异常。",
            "department": "财务/审计",
            "estimated_days": 45,
            "actions": [
                {
                    "step": 1,
                    "action": "分析收入确认政策，核查是否符合会计准则",
                    "responsible": "财务部",
                    "timeline": "1周内",
                    "deliverable": "收入确认政策核查报告",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "梳理应收账款账龄，评估坏账风险",
                    "responsible": "财务部",
                    "timeline": "2周内",
                    "deliverable": "应收账款分析报告",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "核查是否存在关联方资金占用",
                    "responsible": "审计部",
                    "timeline": "2周内",
                    "deliverable": "关联方资金往来核查报告",
                    "priority": "high"
                },
                {
                    "step": 4,
                    "action": "制定现金流改善计划，加强应收账款管理",
                    "responsible": "财务总监",
                    "timeline": "1月内",
                    "deliverable": "现金流改善方案",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《企业会计准则第14号》", "article": "收入", "content": "收入应在履行履约义务时确认"},
                {"name": "《企业会计准则第22号》", "article": "金融工具", "content": "应收款项应合理评估信用风险"}
            ],
            "references": [
                {"case_name": "乐视网", "lesson": "持续盈利但现金流恶化，最终导致资金链断裂"}
            ]
        },
        "文本语义矛盾": {
            "title": "MD&A文本表述前后矛盾问题整改",
            "description": "管理层讨论与分析中存在前后矛盾的表述，影响信息披露的准确性和可信度。",
            "department": "董秘办/法务",
            "estimated_days": 30,
            "actions": [
                {
                    "step": 1,
                    "action": "全面梳理MD&A文本，标注矛盾之处",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "矛盾点梳理清单",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "核实矛盾表述的事实依据",
                    "responsible": "各业务部门",
                    "timeline": "1周内",
                    "deliverable": "事实核查报告",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "统一表述口径，修订MD&A文本",
                    "responsible": "董秘办",
                    "timeline": "2周内",
                    "deliverable": "修订后的MD&A文本",
                    "priority": "high"
                },
                {
                    "step": 4,
                    "action": "建立MD&A文本审核机制",
                    "responsible": "法务部",
                    "timeline": "1月内",
                    "deliverable": "MD&A审核制度",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《公开发行证券的公司信息披露内容与格式准则》", "article": "第2号", "content": "年度报告的内容与格式要求"}
            ],
            "references": [
                {"case_name": "多家IPO被否案例", "lesson": "信息披露前后矛盾是发审委关注的重点问题"}
            ]
        },
        "关联交易隐藏": {
            "title": "关联交易披露不充分问题整改",
            "description": "存在关联交易披露不完整或关联方识别不充分的情况，可能涉及利益输送。",
            "department": "法务/审计",
            "estimated_days": 90,
            "actions": [
                {
                    "step": 1,
                    "action": "全面梳理关联方清单，核查完整性",
                    "responsible": "法务部",
                    "timeline": "2周内",
                    "deliverable": "完整关联方清单",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "核查近三年所有关联交易，补充披露",
                    "responsible": "审计部",
                    "timeline": "1月内",
                    "deliverable": "关联交易核查报告",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "评估关联交易的必要性和定价公允性",
                    "responsible": "独立董事",
                    "timeline": "2周内",
                    "deliverable": "关联交易公允性意见",
                    "priority": "high"
                },
                {
                    "step": 4,
                    "action": "建立关联交易管理制度和审批流程",
                    "responsible": "法务部",
                    "timeline": "1月内",
                    "deliverable": "关联交易管理制度",
                    "priority": "high"
                }
            ],
            "regulations": [
                {"name": "《企业会计准则第36号》", "article": "关联方披露", "content": "应披露关联方关系及交易"},
                {"name": "《上市公司治理准则》", "article": "关联交易", "content": "关联交易应遵循公允、合规原则"}
            ],
            "references": [
                {"case_name": "多家IPO被否", "lesson": "关联交易披露不完整、定价不公允是常见被否原因"}
            ]
        },
        "文本-数据不一致": {
            "title": "文本描述与财务数据不一致问题整改",
            "description": "MD&A中的描述与财务报表数据存在不一致，影响信息披露的准确性。",
            "department": "财务/董秘办",
            "estimated_days": 21,
            "actions": [
                {
                    "step": 1,
                    "action": "逐条核对MD&A描述与财务报表数据",
                    "responsible": "财务部",
                    "timeline": "1周内",
                    "deliverable": "数据核对清单",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "修正文本描述或核实数据准确性",
                    "responsible": "财务部",
                    "timeline": "1周内",
                    "deliverable": "修正后的文本/数据说明",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "建立文本与数据的交叉核对机制",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "核对流程文档",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《上市公司信息披露管理办法》", "article": "信息披露原则", "content": "信息披露应当真实、准确、完整"}
            ],
            "references": [
                {"case_name": "IPO被否案例", "lesson": "文本与数据不一致会被质疑信息披露质量"}
            ]
        },
        "异常乐观语调": {
            "title": "管理层语调异常乐观问题整改",
            "description": "管理层讨论与分析中语调过于乐观，与实际业绩和行业趋势不符。",
            "department": "董秘办",
            "estimated_days": 14,
            "actions": [
                {
                    "step": 1,
                    "action": "梳理过于乐观的表述，与实际情况对比",
                    "responsible": "董秘办",
                    "timeline": "3天内",
                    "deliverable": "表述梳理清单",
                    "priority": "medium"
                },
                {
                    "step": 2,
                    "action": "调整MD&A语调，确保客观审慎",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "修订后的MD&A",
                    "priority": "medium"
                },
                {
                    "step": 3,
                    "action": "建立MD&A语调审核机制",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "审核指引",
                    "priority": "low"
                }
            ],
            "regulations": [
                {"name": "《上市公司信息披露管理办法》", "article": "信息披露原则", "content": "信息披露应当客观、公正"}
            ],
            "references": [
                {"case_name": "乐视", "lesson": "过度乐观表述掩盖经营风险"}
            ]
        },
        "风险披露不足": {
            "title": "风险因素披露不充分问题整改",
            "description": "未充分披露公司面临的重大风险因素，影响投资者判断。",
            "department": "董秘办/法务",
            "estimated_days": 30,
            "actions": [
                {
                    "step": 1,
                    "action": "对照同行业公司，梳理遗漏的风险因素",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "风险因素梳理清单",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "补充完善风险因素披露",
                    "responsible": "董秘办",
                    "timeline": "2周内",
                    "deliverable": "风险因素补充披露",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "建立风险因素定期更新机制",
                    "responsible": "法务部",
                    "timeline": "1周内",
                    "deliverable": "风险更新制度",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《公开发行证券的公司信息披露内容与格式准则》", "article": "风险因素", "content": "应充分披露可能对公司产生不利影响的风险因素"}
            ],
            "references": [
                {"case_name": "IPO被否案例", "lesson": "风险披露不充分是常见被否原因"}
            ]
        },
        "回避表述": {
            "title": "关键问题回避性表述问题整改",
            "description": "对关键问题使用模糊、回避性表述，未能清晰回应投资者关切。",
            "department": "董秘办",
            "estimated_days": 21,
            "actions": [
                {
                    "step": 1,
                    "action": "梳理回避性表述，明确核心问题",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "问题梳理清单",
                    "priority": "medium"
                },
                {
                    "step": 2,
                    "action": "针对核心问题补充明确表述",
                    "responsible": "相关部门",
                    "timeline": "1周内",
                    "deliverable": "补充说明",
                    "priority": "medium"
                },
                {
                    "step": 3,
                    "action": "统一对外表述口径",
                    "responsible": "董秘办",
                    "timeline": "1周内",
                    "deliverable": "统一口径文件",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《上市公司信息披露管理办法》", "article": "信息披露原则", "content": "信息披露应当清晰、明了"}
            ],
            "references": []
        },
        "存货异常": {
            "title": "存货占比异常问题整改",
            "description": "存货占总资产比例过高，可能存在存货跌价风险或虚增资产。",
            "department": "财务/审计",
            "estimated_days": 60,
            "actions": [
                {
                    "step": 1,
                    "action": "全面盘点存货，核实存货真实性",
                    "responsible": "审计部",
                    "timeline": "2周内",
                    "deliverable": "存货盘点报告",
                    "priority": "high"
                },
                {
                    "step": 2,
                    "action": "评估存货跌价准备计提的充分性",
                    "responsible": "财务部",
                    "timeline": "2周内",
                    "deliverable": "跌价准备评估报告",
                    "priority": "high"
                },
                {
                    "step": 3,
                    "action": "分析存货周转情况，制定去库存方案",
                    "responsible": "运营部",
                    "timeline": "1月内",
                    "deliverable": "去库存方案",
                    "priority": "medium"
                },
                {
                    "step": 4,
                    "action": "在年报中补充披露存货相关情况",
                    "responsible": "董秘办",
                    "timeline": "1月内",
                    "deliverable": "补充披露公告",
                    "priority": "medium"
                }
            ],
            "regulations": [
                {"name": "《企业会计准则第1号》", "article": "存货", "content": "存货应按成本与可变现净值孰低计量"}
            ],
            "references": [
                {"case_name": "獐子岛", "lesson": "存货异常是财务造假的典型信号"}
            ]
        }
    }

    def __init__(self, db: Session):
        self.db = db

    def get_remediation_plan(
        self,
        risk_type: str,
        risk_level: str = "medium"
    ) -> Optional[RiskRemediation]:
        """
        获取风险整改方案
        """
        # 1. 从数据库查询
        suggestion = self.db.query(RemediationSuggestion).filter(
            RemediationSuggestion.risk_type == risk_type,
            RemediationSuggestion.is_active == True
        ).first()

        if suggestion:
            return self._build_from_db(suggestion, risk_level)

        # 2. 使用默认模板
        template = self.DEFAULT_TEMPLATES.get(risk_type)
        if template:
            return self._build_from_template(risk_type, risk_level, template)

        # 3. 生成通用整改方案
        return self._build_generic_plan(risk_type, risk_level)

    def _build_from_db(
        self,
        suggestion: RemediationSuggestion,
        risk_level: str
    ) -> RiskRemediation:
        """从数据库构建整改方案"""
        actions_data = suggestion.suggestions or []
        regulations = suggestion.regulations or []
        references = suggestion.case_references or []

        actions = [
            RemediationAction(
                step=i+1,
                action=a.get("action", ""),
                responsible=a.get("responsible", "相关部门"),
                timeline=a.get("timeline", "待定"),
                deliverable=a.get("deliverable", ""),
                priority=a.get("priority", "medium")
            )
            for i, a in enumerate(actions_data)
        ]

        return RiskRemediation(
            risk_type=suggestion.risk_type,
            risk_level=risk_level,
            title=suggestion.title,
            description=suggestion.description,
            actions=actions,
            regulations=regulations,
            references=references
        )

    def _build_from_template(
        self,
        risk_type: str,
        risk_level: str,
        template: Dict
    ) -> RiskRemediation:
        """从模板构建整改方案"""
        actions = [
            RemediationAction(
                step=a["step"],
                action=a["action"],
                responsible=a["responsible"],
                timeline=a["timeline"],
                deliverable=a["deliverable"],
                priority=a["priority"]
            )
            for a in template["actions"]
        ]

        return RiskRemediation(
            risk_type=risk_type,
            risk_level=risk_level,
            title=template["title"],
            description=template["description"],
            actions=actions,
            regulations=template.get("regulations", []),
            references=template.get("references", [])
        )

    def _build_generic_plan(
        self,
        risk_type: str,
        risk_level: str
    ) -> RiskRemediation:
        """构建通用整改方案"""
        return RiskRemediation(
            risk_type=risk_type,
            risk_level=risk_level,
            title=f"{risk_type}问题整改",
            description=f"检测到{risk_type}风险，建议尽快排查整改。",
            actions=[
                RemediationAction(
                    step=1,
                    action="排查风险原因，收集相关证据",
                    responsible="相关部门",
                    timeline="1周内",
                    deliverable="风险排查报告",
                    priority="high"
                ),
                RemediationAction(
                    step=2,
                    action="制定整改方案并实施",
                    responsible="相关部门",
                    timeline="1月内",
                    deliverable="整改完成报告",
                    priority="high"
                )
            ],
            regulations=[],
            references=[]
        )

    def generate_full_remediation_plan(
        self,
        detection_record: DetectionRecord
    ) -> Dict[str, Any]:
        """
        生成完整整改方案
        """
        risk_labels = detection_record.risk_labels or []
        ai_features = detection_record.ai_feature_scores or {}

        # 风险标签映射到整改类型
        label_to_type = {
            "存贷双高": "存贷双高",
            "现金流背离": "现金流背离",
            "存货异常": "存货异常",
            "文本语义矛盾": "文本语义矛盾",
            "文本-数据不一致": "文本-数据不一致",
            "关联交易隐藏": "关联交易隐藏",
            "语调异常乐观": "异常乐观语调",
            "风险披露不足": "风险披露不足",
            "回避表述": "回避表述"
        }

        # 特征映射到整改类型
        feature_to_type = {
            "CON_SEM_AI": "文本语义矛盾",
            "FIT_TD_AI": "文本-数据不一致",
            "COV_RISK_AI": "风险披露不足",
            "HIDE_REL_AI": "关联交易隐藏",
            "TONE_ABN_AI": "异常乐观语调",
            "STR_EVA_AI": "回避表述"
        }

        # 收集需要整改的风险
        remediation_plans = []
        processed_types = set()

        # 从风险标签获取
        for label_info in risk_labels:
            label = label_info.get("label", "") if isinstance(label_info, dict) else str(label_info)
            risk_level = label_info.get("level", "medium") if isinstance(label_info, dict) else "medium"

            for key, rtype in label_to_type.items():
                if key in label and rtype not in processed_types:
                    plan = self.get_remediation_plan(rtype, risk_level)
                    if plan:
                        remediation_plans.append(plan)
                        processed_types.add(rtype)
                    break

        # 从高AI特征值补充
        for feature, score in ai_features.items():
            try:
                score_val = float(score) if score is not None else 0.0
            except (ValueError, TypeError):
                continue

            if score_val >= 0.6 and feature in feature_to_type:
                rtype = feature_to_type[feature]
                if rtype not in processed_types:
                    risk_level = "high" if score_val >= 0.7 else "medium"
                    plan = self.get_remediation_plan(rtype, risk_level)
                    if plan:
                        remediation_plans.append(plan)
                        processed_types.add(rtype)

        # 生成汇总报告
        return {
            "summary": {
                "total_risks": len(remediation_plans),
                "high_priority": sum(1 for p in remediation_plans if p.risk_level == "high"),
                "medium_priority": sum(1 for p in remediation_plans if p.risk_level == "medium"),
                "total_estimated_days": max([sum(
                    int(a.timeline.replace("天", "").replace("周内", "7").replace("月内", "30").replace("待定", "0").split("-")[0])
                    for a in p.actions
                ) for p in remediation_plans]) if remediation_plans else 0
            },
            "remediation_plans": [
                {
                    "risk_type": p.risk_type,
                    "risk_level": p.risk_level,
                    "title": p.title,
                    "description": p.description,
                    "department": self._get_department_from_actions(p.actions),
                    "actions": [
                        {
                            "step": a.step,
                            "action": a.action,
                            "responsible": a.responsible,
                            "timeline": a.timeline,
                            "deliverable": a.deliverable,
                            "priority": a.priority
                        }
                        for a in p.actions
                    ],
                    "regulations": p.regulations,
                    "references": p.references
                }
                for p in remediation_plans
            ],
            "prioritized_actions": self._generate_priority_list(remediation_plans)
        }

    def _get_department_from_actions(self, actions: List[RemediationAction]) -> str:
        """从行动中获取主要责任部门"""
        departments = set()
        for a in actions:
            if "/" in a.responsible:
                departments.update(a.responsible.split("/"))
            else:
                departments.add(a.responsible)
        return "/".join(sorted(departments))[:50]

    def _generate_priority_list(
        self,
        plans: List[RiskRemediation]
    ) -> List[Dict]:
        """生成优先行动清单"""
        all_actions = []

        for plan in plans:
            for action in plan.actions:
                all_actions.append({
                    "risk_type": plan.risk_type,
                    "title": plan.title,
                    "action": action.action,
                    "responsible": action.responsible,
                    "timeline": action.timeline,
                    "priority": action.priority,
                    "priority_score": self._calculate_priority_score(plan.risk_level, action)
                })

        # 按优先级排序
        all_actions.sort(key=lambda x: x["priority_score"], reverse=True)

        return all_actions[:10]  # 返回前10个优先事项

    def _calculate_priority_score(
        self,
        risk_level: str,
        action: RemediationAction
    ) -> int:
        """计算优先级分数"""
        score = 0

        # 风险等级权重
        if risk_level == "high":
            score += 100
        elif risk_level == "medium":
            score += 50
        else:
            score += 20

        # 行动优先级权重
        if action.priority == "high":
            score += 30
        elif action.priority == "medium":
            score += 15

        # 步骤越靠前权重越高
        score += max(0, 20 - action.step * 5)

        return score


def get_remediation_engine(db: Session) -> RemediationEngine:
    """获取整改建议引擎实例"""
    return RemediationEngine(db)
