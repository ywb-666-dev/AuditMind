"""
详细的SHAP特征分析 - 根据实际数据给出具体解读
"""
from typing import Dict, Any, List, Optional


class DetailedSHAPAnalyzer:
    """SHAP特征详细分析器"""

    # 特征含义和财务数据关联映射
    FEATURE_FINANCIAL_LINKS = {
        "CON_SEM_AI": {
            "name": "文本语义矛盾度",
            "financial_indicators": [],  # 文本特征，不直接关联财务指标
            "interpretations": {
                "high": {
                    "threshold": 0.6,
                    "meaning": "MD&A文本中存在明显的语义矛盾",
                    "possible_causes": [
                        "管理层试图掩盖真实经营情况",
                        "不同章节对同一事项的描述不一致",
                        "本期表述与前期报告存在重大矛盾"
                    ],
                    "verification_steps": [
                        "逐段对比MD&A各章节表述",
                        "核对管理层讨论与财务报表附注的一致性",
                        "对比本期与前期报告的关键表述变化"
                    ]
                },
                "medium": {
                    "threshold": 0.4,
                    "meaning": "文本中存在部分表述不一致",
                    "possible_causes": [
                        "信息披露不够严谨",
                        "对复杂事项的描述存在歧义"
                    ],
                    "verification_steps": [
                        "重点关注业绩变动原因的解释",
                        "核实风险因素的完整性和准确性"
                    ]
                }
            }
        },
        "FIT_TD_AI": {
            "name": "文本-数据一致性",
            "financial_indicators": ["营业收入", "净利润", "毛利率"],
            "interpretations": {
                "high": {
                    "threshold": 0.6,
                    "meaning": "文本描述与财务数据存在重大不一致",
                    "possible_causes": [
                        "文本声称'销量大增'但营收下降",
                        "强调'成本控制良好'但毛利率下滑",
                        "描述'现金流充裕'但经营活动现金流为负"
                    ],
                    "verification_steps": [
                        "将文本中的增长/下降描述与财务数据逐项核对",
                        "验证收入确认政策是否与业务描述一致",
                        "检查非经常性损益是否被包装为经营性收益"
                    ]
                },
                "medium": {
                    "threshold": 0.4,
                    "meaning": "部分指标存在文本与数据不匹配",
                    "possible_causes": [
                        "选择性披露有利信息",
                        "对不利因素的描述过于乐观"
                    ],
                    "verification_steps": [
                        "对比营收增长与销量增长的差异",
                        "分析毛利率变动与成本描述的匹配度"
                    ]
                }
            }
        },
        "COV_RISK_AI": {
            "name": "风险披露完整性",
            "financial_indicators": [],
            "interpretations": {
                "high": {
                    "threshold": 0.6,
                    "meaning": "风险披露严重不足，可能刻意回避关键风险",
                    "possible_causes": [
                        "对行业共性风险轻描淡写",
                        "遗漏重大诉讼或担保事项",
                        "风险提示流于形式，缺乏具体性"
                    ],
                    "verification_steps": [
                        "对照同行业可比公司的风险披露",
                        "核查是否存在未披露的重大事项",
                        "分析风险因素的覆盖面和深度"
                    ]
                }
            }
        },
        "HIDE_REL_AI": {
            "name": "关联隐藏指数",
            "financial_indicators": ["其他应收款", "预付款项"],
            "interpretations": {
                "high": {
                    "threshold": 0.6,
                    "meaning": "存在疑似隐藏关联交易",
                    "possible_causes": [
                        "关联方资金占用未充分披露",
                        "异常交易对手方疑似关联方",
                        "担保事项披露不完整"
                    ],
                    "verification_steps": [
                        "全面核查其他应收款、预付款项的对手方",
                        "对比交易价格与市场价格",
                        "核查关联方清单的完整性"
                    ]
                }
            }
        }
    }

    @staticmethod
    def analyze_with_context(
        shap_features: Dict[str, float],
        ai_features: Dict[str, float],
        financial_data: Dict[str, Any],
        risk_labels: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        根据实际数据生成具体的SHAP分析

        Args:
            shap_features: SHAP特征重要性值
            ai_features: AI特征分数
            financial_data: 财务数据
            risk_labels: 风险标签列表

        Returns:
            详细的SHAP分析报告
        """
        if not shap_features:
            return {"summary": "暂无SHAP分析数据", "details": []}

        # 按绝对值排序
        sorted_features = sorted(
            shap_features.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        # 分离正负影响
        positive_impact = [(f, v) for f, v in sorted_features if v > 0]
        negative_impact = [(f, v) for f, v in sorted_features if v < 0]

        # 生成总体摘要
        summary = DetailedSHAPAnalyzer._generate_summary(
            sorted_features, positive_impact, negative_impact
        )

        # 生成详细分析
        details = []

        # 对每个重要特征进行具体分析
        for feature, importance in sorted_features[:5]:
            if abs(importance) < 0.01:  # 跳过不重要的特征
                continue

            analysis = DetailedSHAPAnalyzer._analyze_single_feature(
                feature=feature,
                shap_value=importance,
                ai_score=ai_features.get(feature, 0),
                financial_data=financial_data,
                risk_labels=risk_labels
            )
            details.append(analysis)

        # 生成风险验证建议
        verification_steps = DetailedSHAPAnalyzer._generate_verification_steps(
            positive_impact, financial_data
        )

        # 生成可操作的建议
        recommendations = DetailedSHAPAnalyzer._generate_recommendations(
            sorted_features[:3], ai_features, financial_data
        )

        # 将 details 列表转换为字符串格式以便前端显示
        details_str = "\n\n".join([
            f"**{d.get('feature_name', d.get('feature_code', '未知特征'))}**\n"
            f"- SHAP值: {d.get('shap_value', 0):+.4f}\n"
            f"- 解读: {d.get('interpretation', '无')}\n"
            f"- 可能原因: {'; '.join(d.get('possible_causes', ['未分析']))}"
            for d in details
        ])

        # 生成结论字符串
        conclusion = f"综合评估: 推高风险的特征共{len(positive_impact)}个，总贡献度{sum(v for _, v in positive_impact):.4f}；"
        conclusion += f"降低风险的特征共{len(negative_impact)}个，总贡献度{sum(abs(v) for _, v in negative_impact):.4f}。"

        return {
            "summary": summary,
            "details": details_str,
            "details_list": details,  # 保留原始列表格式
            "verification_steps": verification_steps,
            "recommendations": recommendations,
            "conclusion": conclusion,
            "positive_impact_count": len(positive_impact),
            "negative_impact_count": len(negative_impact),
            "total_positive_value": round(sum(v for _, v in positive_impact), 4),
            "total_negative_value": round(sum(abs(v) for _, v in negative_impact), 4)
        }

    @staticmethod
    def _generate_summary(
        sorted_features: List[tuple],
        positive_impact: List[tuple],
        negative_impact: List[tuple]
    ) -> str:
        """生成总体摘要"""
        if not sorted_features:
            return "暂无数据"

        top_feature, top_value = sorted_features[0]
        top_name = DetailedSHAPAnalyzer.FEATURE_FINANCIAL_LINKS.get(
            top_feature, {}
        ).get("name", top_feature)

        summary = f"**SHAP模型可解释性分析**\n\n"

        # 根据影响程度给出总体评估
        total_positive = sum(v for _, v in positive_impact)
        total_negative = sum(abs(v) for _, v in negative_impact)

        if total_positive > 0.3:
            risk_level = "高"
            summary += f"⚠️ **风险等级：{risk_level}**\n\n"
            summary += f"AI模型判断该企业存在较高的舞弊风险，主要依据是 **{top_name}** 特征显著异常（贡献度：+{top_value:.3f}）。"
        elif total_positive > 0.15:
            risk_level = "中"
            summary += f"⚡ **风险等级：{risk_level}**\n\n"
            summary += f"AI模型识别出部分异常信号，最显著的是 **{top_name}**（贡献度：+{top_value:.3f}）。"
        else:
            risk_level = "低"
            summary += f"✅ **风险等级：{risk_level}**\n\n"
            summary += f"AI模型判断整体风险可控，但 **{top_name}** 仍值得注意（贡献度：{top_value:.3f}）。"

        summary += f"\n\n本分析基于XGBoost模型的SHAP（SHapley Additive exPlanations）值计算，"
        summary += f"共分析{len(sorted_features)}个特征，其中{len(positive_impact)}个推高风险，{len(negative_impact)}个降低风险。"

        return summary

    @staticmethod
    def _analyze_single_feature(
        feature: str,
        shap_value: float,
        ai_score: float,
        financial_data: Dict[str, Any],
        risk_labels: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析单个特征"""
        feature_info = DetailedSHAPAnalyzer.FEATURE_FINANCIAL_LINKS.get(feature, {})
        name = feature_info.get("name", feature)

        # 判断严重程度
        if abs(shap_value) > 0.15:
            level = "high"
            level_emoji = "🔴"
        elif abs(shap_value) > 0.08:
            level = "medium"
            level_emoji = "🟡"
        else:
            level = "low"
            level_emoji = "🟢"

        result = {
            "feature_code": feature,
            "feature_name": name,
            "shap_value": shap_value,
            "ai_score": ai_score,
            "importance_level": level,
            "direction": "推高" if shap_value > 0 else "抑制",
            "emoji": level_emoji
        }

        # 获取具体解读
        interpretations = feature_info.get("interpretations", {})

        if level == "high" and "high" in interpretations:
            interp = interpretations["high"]
            result["interpretation"] = interp["meaning"]
            result["possible_causes"] = interp.get("possible_causes", [])
            result["verification_steps"] = interp.get("verification_steps", [])
        elif level == "medium" and "medium" in interpretations:
            interp = interpretations["medium"]
            result["interpretation"] = interp["meaning"]
            result["possible_causes"] = interp.get("possible_causes", [])
            result["verification_steps"] = interp.get("verification_steps", [])
        else:
            result["interpretation"] = f"该特征对模型判断的{'推高' if shap_value > 0 else '抑制'}作用较弱"
            result["possible_causes"] = []
            result["verification_steps"] = []

        # 关联财务数据分析
        linked_indicators = feature_info.get("financial_indicators", [])
        if linked_indicators:
            result["linked_financial_data"] = {
                indicator: financial_data.get(indicator, "N/A")
                for indicator in linked_indicators
                if indicator in financial_data
            }

        # 查找相关的风险标签
        related_labels = [
            label for label in risk_labels
            if feature.lower() in label.get("label", "").lower() or
               name in label.get("label", "")
        ]
        if related_labels:
            result["related_risk_labels"] = related_labels

        return result

    @staticmethod
    def _generate_verification_steps(
        positive_impact: List[tuple],
        financial_data: Dict[str, Any]
    ) -> List[str]:
        """生成验证步骤"""
        steps = []

        for feature, value in positive_impact[:3]:
            feature_info = DetailedSHAPAnalyzer.FEATURE_FINANCIAL_LINKS.get(feature, {})
            verification = feature_info.get("interpretations", {}).get("high", {}).get("verification_steps", [])
            steps.extend(verification[:2])  # 每个特征最多2个验证步骤

        return steps[:6]  # 总共最多6个步骤

    @staticmethod
    def _generate_recommendations(
        top_features: List[tuple],
        ai_features: Dict[str, float],
        financial_data: Dict[str, Any]
    ) -> List[str]:
        """生成针对性建议"""
        recommendations = []

        # 根据最重要的特征生成建议
        for feature, shap_value in top_features[:2]:
            if shap_value < 0.05:
                continue

            if feature == "FIT_TD_AI":
                recommendations.append("**优先核查文本-数据一致性**：将MD&A中的业务描述与财务报表逐项核对，重点关注收入增长与销量增长的匹配度")
            elif feature == "CON_SEM_AI":
                recommendations.append("**核查信息披露质量**：逐段对比MD&A各章节，识别前后矛盾的表述，特别关注业绩变动原因的解释")
            elif feature == "HIDE_REL_AI":
                recommendations.append("**全面核查关联方**：重点检查其他应收款、预付款项的对手方信息，对比交易价格公允性")
            elif feature == "COV_RISK_AI":
                recommendations.append("**补充风险披露核查**：对照同行业可比公司，检查是否遗漏重大风险因素，特别是行业共性风险")

        # 根据财务数据添加建议
        cash = financial_data.get("货币资金", 0)
        short_loan = financial_data.get("短期借款", 0)
        if cash and short_loan and cash > 100 and short_loan > 50:
            recommendations.append(f"**存贷双高核查**：货币资金{cash}与短期借款{short_loan}同时处于高位，建议函证银行存款真实性")

        net_cash = financial_data.get("经营活动现金流净额", 0)
        net_profit = financial_data.get("净利润", 0)
        if net_profit and net_cash and net_profit > 0 and net_cash < 0:
            recommendations.append(f"**盈利质量核查**：净利润{net_profit}为正但经营现金流{net_cash}为负，建议核查收入确认政策")

        return recommendations[:5]  # 最多5条建议


# 便捷函数
def get_detailed_shap_analysis(
    shap_features: Dict[str, float],
    ai_features: Dict[str, float],
    financial_data: Dict[str, Any],
    risk_labels: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """获取详细的SHAP分析"""
    return DetailedSHAPAnalyzer.analyze_with_context(
        shap_features, ai_features, financial_data, risk_labels
    )
