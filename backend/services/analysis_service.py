"""
智能分析服务 - 为雷达图、SHAP、风险证据提供自动分析解读
"""
from typing import Dict, List, Any, Optional
import json


class AnalysisService:
    """智能分析服务"""

    # AI特征定义和解读模板
    AI_FEATURE_DEFINITIONS = {
        "CON_SEM_AI": {
            "name": "语义矛盾度",
            "description": "检测文本中前后矛盾的表述",
            "high_risk_indicators": [
                "先说'业绩大幅增长'后说'面临严峻挑战'",
                "财务数据与业务描述不符",
                "本期表述与前期报告矛盾"
            ],
            "interpretation": {
                "high": "文本中存在明显的语义矛盾，管理层可能试图掩盖真实情况或误导投资者",
                "medium": "存在部分表述不一致，需进一步核实",
                "low": "文本表述一致性良好，无明显矛盾"
            }
        },
        "COV_RISK_AI": {
            "name": "风险披露完整性",
            "description": "评估风险因素披露的充分性",
            "high_risk_indicators": [
                "对重大风险轻描淡写",
                "遗漏行业共性风险",
                "风险提示流于形式"
            ],
            "interpretation": {
                "high": "风险披露不完整，可能刻意回避关键风险因素",
                "medium": "风险披露基本完整但不够深入",
                "low": "风险披露充分透明"
            }
        },
        "TONE_ABN_AI": {
            "name": "异常乐观语调",
            "description": "检测语调是否过度乐观",
            "high_risk_indicators": [
                "过多使用积极词汇",
                "对困难一笔带过",
                "业绩下滑仍强调机遇"
            ],
            "interpretation": {
                "high": "语调异常乐观，与财务表现不匹配，存在粉饰嫌疑",
                "medium": "语调偏乐观，需关注实质内容",
                "low": "语调客观理性，与实际业绩匹配"
            }
        },
        "FIT_TD_AI": {
            "name": "文本-数据一致性",
            "description": "验证文本描述与财务数据是否一致",
            "high_risk_indicators": [
                "文本说'销量大增'但营收下降",
                "强调市场份额提升但毛利率下滑",
                "描述业务扩张但现金流恶化"
            ],
            "interpretation": {
                "high": "文本描述与财务数据存在重大不一致，高度可疑",
                "medium": "部分指标存在不一致，需要核查",
                "low": "文本与财务数据高度一致"
            }
        },
        "HIDE_REL_AI": {
            "name": "关联隐藏指数",
            "description": "识别隐藏的关联交易",
            "high_risk_indicators": [
                "疑似关联方名称出现",
                "交易价格异常但对手方信息模糊",
                "担保事项披露不充分"
            ],
            "interpretation": {
                "high": "发现疑似隐藏关联交易的线索，需重点核查",
                "medium": "存在关联交易披露不充分的可能",
                "low": "关联交易披露充分透明"
            }
        },
        "DEN_ABN_AI": {
            "name": "信息密度异常",
            "description": "检测信息披露的异常模式",
            "high_risk_indicators": [
                "关键信息一带而过",
                "重要科目描述过于简略",
                "用套话填充篇幅"
            ],
            "interpretation": {
                "high": "信息密度异常，关键信息披露不充分",
                "medium": "部分信息披露不够详细",
                "low": "信息披露密度适中，详略得当"
            }
        },
        "STR_EVA_AI": {
            "name": "回避表述强度",
            "description": "识别对敏感问题的回避性表述",
            "high_risk_indicators": [
                "过度使用'可能''拟''预计'",
                "对关键问题模糊其词",
                "承诺事项缺乏具体时间表"
            ],
            "interpretation": {
                "high": "大量使用回避性表述，对关键问题避重就轻",
                "medium": "存在部分回避性表述",
                "low": "表述直接明确，不回避关键问题"
            }
        }
    }

    # SHAP特征解读模板
    SHAP_FEATURE_INTERPRETATIONS = {
        "CON_SEM_AI": {
            "name": "语义矛盾度",
            "impact_high": "文本语义矛盾是主要风险信号，建议逐段核查MD&A表述",
            "impact_medium": "存在一定语义不一致，需关注",
            "impact_low": "文本一致性良好"
        },
        "FIT_TD_AI": {
            "name": "文本-数据一致性",
            "impact_high": "文本描述与财务数据严重背离，这是重要的舞弊预警信号",
            "impact_medium": "部分指标存在不一致",
            "impact_low": "文本与数据匹配度良好"
        },
        "COV_RISK_AI": {
            "name": "风险披露完整性",
            "impact_high": "风险披露不足大幅推高舞弊概率",
            "impact_medium": "风险披露有改进空间",
            "impact_low": "风险披露充分"
        },
        "HIDE_REL_AI": {
            "name": "关联隐藏指数",
            "impact_high": "疑似隐藏关联交易，建议全面核查关联方",
            "impact_medium": "存在关联交易披露疑点",
            "impact_low": "关联交易披露透明"
        },
        "TONE_ABN_AI": {
            "name": "异常乐观语调",
            "impact_high": "过度乐观的语调可能是业绩粉饰的信号",
            "impact_medium": "语调偏乐观",
            "impact_low": "语调客观"
        },
        "DEN_ABN_AI": {
            "name": "信息密度异常",
            "impact_high": "信息披露不充分，关键内容被刻意淡化",
            "impact_medium": "信息密度偏低",
            "impact_low": "信息披露充分"
        },
        "STR_EVA_AI": {
            "name": "回避表述强度",
            "impact_high": "大量使用模糊表述回避敏感问题",
            "impact_medium": "存在回避性表述",
            "impact_low": "表述明确直接"
        }
    }

    # 动态风险证据分类
    EVIDENCE_CATEGORIES = {
        "financial_anomaly": {
            "name": "财务数据异常",
            "description": "财务指标偏离正常范围或存在异常变动",
            "why_selected": "该财务指标与行业平均水平或企业历史数据存在显著偏离，偏离度超过正常波动范围",
            "risk_location": "资产负债表或利润表相关科目"
        },
        "text_contradiction": {
            "name": "文本矛盾",
            "description": "MD&A文本中存在前后矛盾的表述",
            "why_selected": "AI模型在同一文档的不同段落中检测到相互矛盾的表述：前文声称业绩增长良好，后文却提到经营面临重大挑战",
            "risk_location": "管理层讨论与分析(MD&A)章节的前后段落"
        },
        "data_mismatch": {
            "name": "数据不匹配",
            "description": "文本描述与财务数据不一致",
            "why_selected": "管理层在文字中声称'销量大增''成本控制良好'，但财务数据显示营业收入下降、毛利率下滑，文字与数据明显矛盾",
            "risk_location": "MD&A章节中的业绩描述与财务报表数据对比"
        },
        "disclosure_gap": {
            "name": "披露缺陷",
            "description": "重要信息披露不充分或缺失",
            "why_selected": "相比同行业其他公司，该企业未充分披露行业共性风险，且对已知重大事项的说明过于简略",
            "risk_location": "年报'风险因素'章节及'重大事项'披露部分"
        },
        "related_party": {
            "name": "关联交易疑点",
            "description": "疑似隐藏或未充分披露的关联交易",
            "why_selected": "文本中出现'其他应收款大幅增加''与某关联方进行交易'等描述，但关联交易披露章节未完整说明交易对手方及交易价格公允性",
            "risk_location": "关联交易章节、其他应收款附注说明"
        },
        "tone_anomaly": {
            "name": "语调异常",
            "description": "管理层语调与业绩表现不匹配",
            "why_selected": "尽管企业营收下滑、利润下降，管理层在MD&A中使用'辉煌''突破性''历史性'等大量正面词汇，语调与实际业绩严重脱节",
            "risk_location": "管理层讨论与分析(MD&A)章节的业绩描述部分"
        },
        "evasion_language": {
            "name": "回避性语言",
            "description": "对关键问题使用模糊、回避性表述",
            "why_selected": "面对投资者关心的核心问题(如应收账款大幅增长的原因)，管理层使用'可能''拟''预计''视情况而定'等模糊词汇回避正面回答",
            "risk_location": "风险因素描述及投资者问答部分"
        },
        "consistency_issue": {
            "name": "一致性issue",
            "description": "本期报告与前期报告存在重大不一致",
            "why_selected": "对比本期与前期年报发现：本期对同一业务的描述与前期存在重大差异，且未说明原因或进行追溯调整",
            "risk_location": "本期报告与上期报告的对比分析"
        },
        "industry_deviation": {
            "name": "行业偏离",
            "description": "指标显著偏离同行业平均水平",
            "why_selected": "该企业的毛利率/应收账款周转率等关键指标与同行业可比公司平均值偏离超过20%，且缺乏合理的商业解释",
            "risk_location": "财务指标与行业均值对比分析"
        },
        "trend_abnormality": {
            "name": "趋势异常",
            "description": "指标变动趋势与业务逻辑不符",
            "why_selected": "企业声称业务稳步增长，但核心财务指标(如经营性现金流)连续多个季度下滑，趋势与描述不符",
            "risk_location": "多期财务报表的趋势分析"
        }
    }

    @staticmethod
    def analyze_radar_chart(ai_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        分析AI风险特征雷达图，生成解读报告
        """
        if not ai_scores:
            return {"summary": "暂无数据", "details": []}

        # 计算平均分和高风险特征
        valid_scores = {k: v for k, v in ai_scores.items() if not k.startswith('_')}
        avg_score = sum(valid_scores.values()) / len(valid_scores) if valid_scores else 0

        high_risk_features = []
        medium_risk_features = []
        low_risk_features = []

        for feature, score in valid_scores.items():
            if score >= 0.6:
                high_risk_features.append((feature, score))
            elif score >= 0.4:
                medium_risk_features.append((feature, score))
            else:
                low_risk_features.append((feature, score))

        # 按风险程度排序
        high_risk_features.sort(key=lambda x: x[1], reverse=True)
        medium_risk_features.sort(key=lambda x: x[1], reverse=True)

        # 生成综合分析
        analysis_parts = []

        # 整体评价
        if avg_score >= 0.5:
            overall = f"⚠️ **整体风险评估：高风险** (平均分: {avg_score:.2f})\n\n该企业在多个维度显示出明显的文本风险信号，建议进行深入调查。"
        elif avg_score >= 0.35:
            overall = f"⚡ **整体风险评估：中等风险** (平均分: {avg_score:.2f})\n\n该企业在部分维度存在可疑信号，需要重点关注。"
        else:
            overall = f"✅ **整体风险评估：低风险** (平均分: {avg_score:.2f})\n\n该企业文本风险指标整体良好。"
        analysis_parts.append(overall)

        # 详细分析
        details = []

        if high_risk_features:
            details.append("\n**🔴 高风险维度（需立即关注）：**")
            for feature, score in high_risk_features:
                def_info = AnalysisService.AI_FEATURE_DEFINITIONS.get(feature, {})
                name = def_info.get("name", feature)
                interp = def_info.get("interpretation", {}).get("high", "")
                indicators = def_info.get("high_risk_indicators", [])

                detail = f"\n**{name}** ({score:.2f})\n"
                detail += f"> {interp}\n"
                if indicators:
                    detail += f"> 典型表现：{indicators[0]}\n"
                details.append(detail)

        if medium_risk_features:
            details.append("\n**🟡 中等风险维度（需关注）：**")
            for feature, score in medium_risk_features:
                def_info = AnalysisService.AI_FEATURE_DEFINITIONS.get(feature, {})
                name = def_info.get("name", feature)
                interp = def_info.get("interpretation", {}).get("medium", "")
                detail = f"\n**{name}** ({score:.2f})\n> {interp}\n"
                details.append(detail)

        if low_risk_features:
            # 只显示表现最好的2个维度
            low_risk_features.sort(key=lambda x: x[1])
            if low_risk_features:
                details.append("\n**🟢 表现良好维度：**")
                for feature, score in low_risk_features[:2]:
                    def_info = AnalysisService.AI_FEATURE_DEFINITIONS.get(feature, {})
                    name = def_info.get("name", feature)
                    detail = f"✓ **{name}** ({score:.2f}) - 风险可控\n"
                    details.append(detail)

        # 生成建议
        recommendations = []
        if high_risk_features:
            top_risk = high_risk_features[0][0]
            def_info = AnalysisService.AI_FEATURE_DEFINITIONS.get(top_risk, {})
            rec = f"\n**💡 优先建议：**\n重点核查**{def_info.get('name', '')}**相关披露，"
            if top_risk == "CON_SEM_AI":
                rec += "建议逐段对比MD&A文本，识别矛盾表述"
            elif top_risk == "FIT_TD_AI":
                rec += "建议将文本描述与财务数据逐项核对"
            elif top_risk == "HIDE_REL_AI":
                rec += "建议全面核查关联方清单及交易定价"
            else:
                rec += "建议深入分析相关披露内容"
            recommendations.append(rec)

        return {
            "summary": overall,
            "average_score": avg_score,
            "high_risk_count": len(high_risk_features),
            "medium_risk_count": len(medium_risk_features),
            "details": "\n".join(details),
            "recommendations": "\n".join(recommendations)
        }

    @staticmethod
    def analyze_shap_features(shap_features: Dict[str, float]) -> Dict[str, Any]:
        """
        分析SHAP特征重要性，生成具体解读报告
        """
        if not shap_features:
            return {"summary": "暂无数据", "details": []}

        # 按绝对值重要性排序
        sorted_features = sorted(shap_features.items(), key=lambda x: abs(x[1]), reverse=True)

        # 分离正向和负向影响
        positive_impact = [(f, v) for f, v in sorted_features if v > 0]
        negative_impact = [(f, v) for f, v in sorted_features if v < 0]

        # 总体分析 - 使用最具体的描述
        top_feature = sorted_features[0]
        top_code = top_feature[0]
        top_value = top_feature[1]

        # 获取特征的具体解释
        interp = AnalysisService.SHAP_FEATURE_INTERPRETATIONS.get(top_code, {})
        feature_name = interp.get("name", top_code)

        # 生成具体的影响描述
        if abs(top_value) < 0.01:
            impact_desc = "影响微弱"
        elif abs(top_value) < 0.05:
            impact_desc = "影响较小"
        elif abs(top_value) < 0.1:
            impact_desc = "有一定影响"
        elif abs(top_value) < 0.2:
            impact_desc = "影响显著"
        else:
            impact_desc = "影响重大"

        summary = f"**SHAP特征重要性分析**\n\n"
        summary += f"对舞弊判断影响最大的是 **{feature_name}** (SHAP值: {top_value:+.4f})。\n\n"

        if top_value > 0:
            summary += f"该特征**{impact_desc}地推高了**舞弊概率判断。"
            # 添加具体解释
            if top_code == "CON_SEM_AI":
                summary += "具体表现为年报文本中存在前后表述不一致的情况，如前文声称业绩增长良好，后文却暗示经营困难。"
            elif top_code == "FIT_TD_AI":
                summary += "具体表现为管理层在文字中描述的业绩情况与财务报表中的实际数据存在明显出入。"
            elif top_code == "COV_RISK_AI":
                summary += "具体表现为企业对重大风险因素的披露不够充分，可能刻意回避了投资者关心的关键问题。"
            elif top_code == "HIDE_REL_AI":
                summary += "具体表现为年报中存在疑似未充分披露的关联交易，或关联方资金往来异常。"
            elif top_code == "TONE_ABN_AI":
                summary += "具体表现为管理层对业绩的描述过于乐观，使用大量夸张形容词，与实际情况不符。"
            elif top_code == "DEN_ABN_AI":
                summary += "具体表现为关键信息要么过于简略一笔带过，要么刻意用复杂表述掩盖实质内容。"
            elif top_code == "STR_EVA_AI":
                summary += "具体表现为面对投资者关心的核心问题，管理层使用模糊表述回避正面回答。"
        else:
            summary += f"该特征**{impact_desc}地降低了**舞弊概率判断，说明企业在该方面表现正常，起到风险缓释作用。"

        analysis_parts.append(summary)

        # 详细解读 - 每个特征给出具体分析
        details = []

        if positive_impact:
            details.append("\n**📈 推高风险判断的具体因素：**")
            for feature, value in positive_impact[:5]:
                interp = AnalysisService.SHAP_FEATURE_INTERPRETATIONS.get(feature, {})
                name = interp.get("name", feature)

                # 根据特征代码生成具体分析
                specific_analysis = AnalysisService._get_specific_shap_analysis(feature, value)
                details.append(f"\n**{name}** (贡献度: +{value:.4f})\n> {specific_analysis}")

        if negative_impact:
            details.append("\n**📉 降低风险判断的缓和因素：**")
            for feature, value in negative_impact[:3]:
                interp = AnalysisService.SHAP_FEATURE_INTERPRETATIONS.get(feature, {})
                name = interp.get("name", feature)

                # 根据SHAP值大小给出具体描述
                if abs(value) > 0.1:
                    desc = f"该因素显著降低了舞弊概率判断（贡献度: {value:.4f}），表明企业在该维度表现良好"
                elif abs(value) > 0.05:
                    desc = f"该因素一定程度上降低了舞弊概率判断（贡献度: {value:.4f}）"
                else:
                    desc = f"该因素轻微降低了舞弊概率判断（贡献度: {value:.4f}）"
                details.append(f"\n**{name}**\n> {desc}")

        # 综合结论 - 基于具体数据
        total_positive = sum(v for _, v in positive_impact)
        total_negative = sum(abs(v) for _, v in negative_impact)
        net_effect = total_positive - total_negative

        conclusion = f"\n**综合评估：**\n"

        if net_effect > 0.3:
            conclusion += f"综合来看，风险推高因素明显占优（净效应: +{net_effect:.4f}）。"
            conclusion += f"共识别出{len(positive_impact)}个推高风险的特征，总贡献度为{total_positive:.4f}；"
            conclusion += f"而{len(negative_impact)}个降低风险的特征总贡献度为{total_negative:.4f}。"
            conclusion += "建议对该企业进行深入调查后再做投资决策。"
        elif net_effect > 0.1:
            conclusion += f"综合来看，风险推高因素略占优势（净效应: +{net_effect:.4f}）。"
            conclusion += f"推高因素贡献度{total_positive:.4f}，缓和因素贡献度{total_negative:.4f}。"
            conclusion += "建议保持关注，持续监测后续变化。"
        elif net_effect > -0.1:
            conclusion += f"综合来看，正负因素基本平衡（净效应: {net_effect:+.4f}）。"
            conclusion += "建议结合其他定性因素综合判断。"
        else:
            conclusion += f"综合来看，风险缓和因素占优（净效应: {net_effect:.4f}）。"
            conclusion += "当前评估显示风险可控，但仍建议保持常规关注。"

        return {
            "summary": summary,
            "top_feature": feature_name,
            "top_contribution": top_value,
            "positive_count": len(positive_impact),
            "negative_count": len(negative_impact),
            "details": "\n".join(details),
            "conclusion": conclusion,
            "net_effect": round(net_effect, 4)
        }

    @staticmethod
    def _get_specific_shap_analysis(feature_code: str, value: float) -> str:
        """根据特征代码和SHAP值生成具体分析"""
        # 根据SHAP值大小确定严重程度
        if value > 0.2:
            severity = "严重"
            level = "极高"
        elif value > 0.1:
            severity = "显著"
            level = "较高"
        elif value > 0.05:
            severity = "一定"
            level = "中等"
        else:
            severity = "轻微"
            level = "较低"

        analysis_map = {
            "CON_SEM_AI": f"文本中存在{severity}的前后矛盾。该指标贡献度为{value:.4f}，表明企业在不同段落对同一事项的表述不一致，可能试图掩盖真实情况。",
            "FIT_TD_AI": f"文本描述与财务数据存在{severity}背离（贡献度: {value:.4f}）。管理层的说辞与实际数据不匹配，这是最直接的舞弊预警信号。",
            "COV_RISK_AI": f"风险披露存在{severity}不足（贡献度: {value:.4f}）。企业对重大风险要么轻描淡写，要么刻意隐瞒。",
            "HIDE_REL_AI": f"发现{severity}的关联交易隐藏迹象（贡献度: {value:.4f}）。存在未充分披露的关联方或异常资金往来。",
            "TONE_ABN_AI": f"语调存在{severity}异常乐观（贡献度: {value:.4f}）。管理层使用大量正面词汇描述业绩，与实际经营情况脱节。",
            "DEN_ABN_AI": f"信息披露存在{severity}异常（贡献度: {value:.4f}）。关键内容要么过于简略，要么用复杂表述刻意掩盖。",
            "STR_EVA_AI": f"存在{severity}的回避性表述（贡献度: {value:.4f}）。面对投资者关心的核心问题，管理层选择模糊处理或避而不答。"
        }

        return analysis_map.get(feature_code, f"该因素对舞弊判断有{level}程度的影响（贡献度: {value:.4f}）")

    @staticmethod
    def analyze_risk_evidence(
        evidence: Dict[str, Any],
        ai_scores: Dict[str, float],
        shap_features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        分析单个风险证据，生成详细解读
        """
        category = evidence.get("category", "unknown")
        cat_info = AnalysisService.EVIDENCE_CATEGORIES.get(
            category, AnalysisService.EVIDENCE_CATEGORIES.get("financial_anomaly")
        )

        # 获取相关特征分数
        related_features = evidence.get("related_features", [])
        feature_scores = {f: ai_scores.get(f, 0) for f in related_features}

        analysis = {
            "category_name": cat_info["name"],
            "category_description": cat_info["description"],
            "why_selected": cat_info["why_selected"],
            "risk_location": cat_info["risk_location"],
            "detailed_explanation": "",
            "related_features_analysis": []
        }

        # 生成详细解释
        if category == "text_contradiction":
            analysis["detailed_explanation"] = (
                "AI模型通过自然语言处理技术识别出文本中存在语义矛盾。"
                "这种矛盾可能是有意为之（试图掩盖真实情况）或无意遗漏，"
                "无论哪种情况都表明内部控制或信息披露存在问题。"
            )
        elif category == "data_mismatch":
            analysis["detailed_explanation"] = (
                "文本描述与财务数据之间存在不一致。例如文本声称'销量大增'但营收下降，"
                "或强调'成本控制良好'但毛利率下滑。这种不一致是业绩粉饰的典型信号。"
            )
        elif category == "related_party":
            analysis["detailed_explanation"] = (
                "检测到疑似关联交易线索。可能表现为：交易对手方名称疑似关联方、"
                "交易价格明显偏离市场价格、担保事项披露不充分等。"
                "关联交易是财务舞弊的高发区，需重点核查。"
            )
        elif category == "disclosure_gap":
            analysis["detailed_explanation"] = (
                "重要风险因素未被充分披露。根据信息披露规则，"
                "上市公司应当充分披露可能影响投资者决策的重大风险。"
                "披露不充分可能导致投资者无法准确评估企业风险。"
            )
        else:
            analysis["detailed_explanation"] = (
                f"该证据属于{cat_info['name']}类别，"
                f"表明在{cat_info['risk_location']}方面存在可疑信号。"
            )

        # 分析相关特征
        for feature, score in feature_scores.items():
            def_info = AnalysisService.AI_FEATURE_DEFINITIONS.get(feature, {})
            if score > 0.6:
                level = "高风险"
            elif score > 0.4:
                level = "中等风险"
            else:
                level = "低风险"

            analysis["related_features_analysis"].append({
                "feature": def_info.get("name", feature),
                "score": score,
                "risk_level": level
            })

        return analysis

    @staticmethod
    def get_dynamic_risk_labels(
        financial_data: Dict[str, Any],
        ai_scores: Dict[str, float],
        shap_features: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        生成动态风险标签（支持更多分类）
        """
        labels = []

        # 财务指标标签
        cash = float(financial_data.get("货币资金", 0) or 0)
        short_loan = float(financial_data.get("短期借款", 0) or 0)
        total_assets = float(financial_data.get("总资产", 1) or 1)
        net_cash = float(financial_data.get("经营活动现金流净额", 0) or 0)
        net_profit = float(financial_data.get("净利润", 0) or 0)
        inventory = float(financial_data.get("存货", 0) or 0)
        revenue = float(financial_data.get("营业收入", 0) or 0)
        ar = float(financial_data.get("应收账款", 0) or 0)

        # 1. 存贷双高
        if cash > 100 and short_loan > 50:
            severity = "high" if cash / max(short_loan, 1) > 2 else "medium"
            labels.append({
                "label": "存贷双高",
                "category": "资金异常",
                "severity": severity,
                "score": 0.85 if severity == "high" else 0.65,
                "description": "货币资金和短期借款同时处于高位，可能存在资金真实性问题或资金被占用",
                "why_selected": "货币资金" + ("远高于" if severity == "high" else "高于") + "短期借款，违反商业常识",
                "where_is_risk": "资产负债表-货币资金、短期借款科目；需函证银行存款真实性"
            })

        # 2. 现金流背离
        if net_profit > 0 and net_cash < 0:
            deviation_ratio = abs(net_cash) / max(net_profit, 1)
            severity = "high" if deviation_ratio > 1 else "medium"
            labels.append({
                "label": "现金流背离",
                "category": "盈利质量",
                "severity": severity,
                "score": 0.90 if severity == "high" else 0.70,
                "description": "净利润为正但经营现金流为负，利润缺乏现金支撑",
                "why_selected": f"净利润{net_profit:.0f}万但经营现金流{net_cash:.0f}万，背离度{deviation_ratio:.1f}倍",
                "where_is_risk": "现金流量表-经营活动现金流；利润表-净利润；关注收入确认政策"
            })
        elif net_profit > 0 and net_cash / max(net_profit, 1) < 0.5:
            labels.append({
                "label": "现金流质量差",
                "category": "盈利质量",
                "severity": "medium",
                "score": 0.65,
                "description": "经营现金流远低于净利润，盈利质量存疑",
                "why_selected": f"经营现金流/净利润={net_cash/max(net_profit,1):.1%}，低于健康水平",
                "where_is_risk": "应收账款、存货增加导致的资金占用"
            })

        # 3. 存货异常
        if total_assets > 0 and inventory / total_assets > 0.3:
            severity = "high" if inventory / total_assets > 0.5 else "medium"
            labels.append({
                "label": "存货占比高",
                "category": "资产异常",
                "severity": severity,
                "score": 0.75 if severity == "high" else 0.60,
                "description": "存货占总资产比例过高，可能存在减值风险或虚增资产",
                "why_selected": f"存货占比{inventory/total_assets:.1%}，" + ("远超" if severity == "high" else "高于") + "行业平均水平",
                "where_is_risk": "资产负债表-存货科目；需实地盘点并核查跌价准备计提"
            })

        # 4. 应收账款异常
        if revenue > 0 and ar / revenue > 0.4:
            severity = "high" if ar / revenue > 0.6 else "medium"
            labels.append({
                "label": "应收账款高企",
                "category": "资产异常",
                "severity": severity,
                "score": 0.70 if severity == "high" else 0.55,
                "description": "应收账款占营收比例过高，可能存在收入确认激进或坏账风险",
                "why_selected": f"应收账款/营收={ar/revenue:.1%}，回款压力大",
                "where_is_risk": "应收账款周转天数、账龄分析、坏账准备计提政策"
            })

        # 5. AI文本风险标签（动态生成）
        for feature, score in ai_scores.items():
            if feature.startswith('_'):
                continue
            if score >= 0.5:
                feature_def = AnalysisService.AI_FEATURE_DEFINITIONS.get(feature, {})
                severity = "high" if score >= 0.7 else "medium"
                label_name = feature_def.get("name", feature)

                labels.append({
                    "label": label_name,
                    "category": "文本风险",
                    "severity": severity,
                    "score": round(score, 2),
                    "description": feature_def.get("description", "AI检测到的文本风险"),
                    "why_selected": f"AI模型评分{score:.2f}，" + ("显著高于" if severity == "high" else "高于") + "阈值0.5",
                    "where_is_risk": "MD&A章节；建议逐句核查相关披露"
                })

        # 6. 综合风险标签
        avg_ai_score = sum(v for k, v in ai_scores.items() if not k.startswith('_')) / max(len([k for k in ai_scores if not k.startswith('_')]), 1)
        if avg_ai_score > 0.6:
            labels.append({
                "label": "综合文本高风险",
                "category": "综合评估",
                "severity": "high",
                "score": round(avg_ai_score, 2),
                "description": "多个AI文本风险指标同时偏高，存在系统性披露问题",
                "why_selected": f"7项AI特征平均分{avg_ai_score:.2f}，多个维度同时异常",
                "where_is_risk": "整体信息披露质量；建议全面复核年报披露"
            })

        # 按严重程度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        labels.sort(key=lambda x: (severity_order.get(x["severity"], 3), -x["score"]))

        return labels[:12]  # 最多返回12个标签


# 全局分析服务实例
analysis_service = AnalysisService()
