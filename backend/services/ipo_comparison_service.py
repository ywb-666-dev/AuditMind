"""
过会风险对标服务
- 与近三年被否IPO案例库进行特征匹配
- 告诉用户这个风险曾经否决过哪些公司
"""
import numpy as np
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.models.database import IPORejectedCase, DetectionRecord


class IPOComparisonService:
    """IPO风险对标服务"""

    # 特征权重配置
    FEATURE_WEIGHTS = {
        "CON_SEM_AI": 1.0,
        "COV_RISK_AI": 1.0,
        "TONE_ABN_AI": 1.2,
        "FIT_TD_AI": 1.5,  # 文本-数据一致性权重最高
        "HIDE_REL_AI": 1.3,
        "DEN_ABN_AI": 0.8,
        "STR_EVA_AI": 1.0
    }

    def __init__(self, db: Session):
        self.db = db

    def _calculate_similarity(
        self,
        features1: Dict[str, float],
        features2: Dict[str, float]
    ) -> float:
        """
        计算两个特征向量的余弦相似度
        """
        if not features1 or not features2:
            return 0.0

        # 获取所有特征键
        all_features = set(features1.keys()) | set(features2.keys())

        # 构建向量
        vec1 = []
        vec2 = []
        weights = []

        for feature in all_features:
            v1 = features1.get(feature, 0.0)
            v2 = features2.get(feature, 0.0)

            # 确保是数值
            try:
                v1 = float(v1) if v1 is not None else 0.0
                v2 = float(v2) if v2 is not None else 0.0
            except (ValueError, TypeError):
                continue

            weight = self.FEATURE_WEIGHTS.get(feature, 1.0)

            vec1.append(v1 * weight)
            vec2.append(v2 * weight)
            weights.append(weight)

        if not vec1 or not vec2:
            return 0.0

        # 计算加权余弦相似度
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(vec1, vec2) / (norm1 * norm2)

        # 归一化到0-1
        return max(0.0, min(1.0, similarity))

    def _get_matched_features(
        self,
        detection_features: Dict[str, float],
        case_features: Dict[str, float],
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        获取匹配的特征列表
        """
        matched = []

        feature_names = {
            "CON_SEM_AI": "语义矛盾度",
            "COV_RISK_AI": "风险披露完整性",
            "TONE_ABN_AI": "异常乐观语调",
            "FIT_TD_AI": "文本-数据一致性",
            "HIDE_REL_AI": "关联隐藏指数",
            "DEN_ABN_AI": "信息密度异常",
            "STR_EVA_AI": "回避表述强度"
        }

        for feature in self.FEATURE_WEIGHTS.keys():
            d_score = detection_features.get(feature, 0.0)
            c_score = case_features.get(feature, 0.0)

            try:
                d_score = float(d_score) if d_score is not None else 0.0
                c_score = float(c_score) if c_score is not None else 0.0
            except (ValueError, TypeError):
                continue

            # 如果两者都超过阈值，认为匹配
            if d_score >= threshold and c_score >= threshold:
                matched.append({
                    "feature": feature,
                    "feature_name": feature_names.get(feature, feature),
                    "detection_score": round(d_score, 2),
                    "case_score": round(c_score, 2),
                    "match_strength": min(d_score, c_score)
                })

        return sorted(matched, key=lambda x: x["match_strength"], reverse=True)

    def compare_with_rejected_cases(
        self,
        ai_features: Dict[str, float],
        industry: Optional[str] = None,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        与被否IPO案例进行特征匹配

        Args:
            ai_features: 检测的AI特征
            industry: 行业筛选（可选）
            top_n: 返回最相似的N个案例

        Returns:
            相似案例列表
        """
        # 查询近三年被否案例
        three_years_ago = datetime.now() - timedelta(days=3*365)

        query = self.db.query(IPORejectedCase).filter(
            IPORejectedCase.is_active == True,
            IPORejectedCase.rejected_date >= three_years_ago.date()
        )

        if industry:
            query = query.filter(IPORejectedCase.industry == industry)

        cases = query.all()

        if not cases:
            return []

        # 计算相似度
        similarities = []
        for case in cases:
            case_features = case.risk_features or {}

            similarity = self._calculate_similarity(ai_features, case_features)
            matched_features = self._get_matched_features(ai_features, case_features)

            # 只保留相似度超过阈值的案例
            if similarity >= 0.5 or len(matched_features) >= 2:
                similarities.append({
                    "case_id": case.id,
                    "company_name": case.company_name,
                    "stock_code": case.stock_code,
                    "industry": case.industry,
                    "rejected_date": case.rejected_date.isoformat() if case.rejected_date else None,
                    "rejection_reason": case.rejection_reason,
                    "similarity": round(similarity, 3),
                    "matched_features": matched_features,
                    "case_summary": case.case_summary,
                    "key_risk_points": case.key_risk_points
                })

        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return similarities[:top_n]

    def get_risk_industry_analysis(
        self,
        industry: str
    ) -> Dict[str, Any]:
        """
        获取特定行业的IPO被否风险分析
        """
        three_years_ago = datetime.now() - timedelta(days=3*365)

        cases = self.db.query(IPORejectedCase).filter(
            IPORejectedCase.industry == industry,
            IPORejectedCase.is_active == True,
            IPORejectedCase.rejected_date >= three_years_ago.date()
        ).all()

        if not cases:
            return {
                "industry": industry,
                "total_rejected": 0,
                "common_risk_features": [],
                "rejection_reasons": []
            }

        # 统计常见风险特征
        feature_scores = {}
        rejection_reasons = []

        for case in cases:
            # 聚合风险特征
            if case.risk_features:
                for feature, score in case.risk_features.items():
                    try:
                        score = float(score) if score is not None else 0.0
                    except (ValueError, TypeError):
                        continue

                    if feature not in feature_scores:
                        feature_scores[feature] = []
                    feature_scores[feature].append(score)

            # 收集被否原因
            if case.rejection_reason:
                rejection_reasons.append(case.rejection_reason)

        # 计算平均风险分数
        avg_features = {
            k: round(sum(v) / len(v), 2) if v else 0.0
            for k, v in feature_scores.items()
        }

        # 排序获取最常见的风险特征
        common_features = sorted(
            [{"feature": k, "avg_score": v} for k, v in avg_features.items()],
            key=lambda x: x["avg_score"],
            reverse=True
        )[:5]

        return {
            "industry": industry,
            "total_rejected": len(cases),
            "rejection_rate": f"{len(cases)}家",
            "common_risk_features": common_features,
            "rejection_reasons": rejection_reasons[:3],
            "sample_cases": [
                {
                    "name": c.company_name,
                    "date": c.rejected_date.isoformat() if c.rejected_date else None
                }
                for c in cases[:3]
            ]
        }

    def generate_comparison_report(
        self,
        detection_record: DetectionRecord
    ) -> Dict[str, Any]:
        """
        生成完整的对标报告
        """
        ai_features = detection_record.ai_feature_scores or {}
        industry = None

        # 尝试从公司信息获取行业
        if detection_record.financial_data:
            industry = detection_record.financial_data.get("industry")

        # 1. 匹配相似案例
        similar_cases = self.compare_with_rejected_cases(ai_features, industry)

        # 2. 获取行业分析
        industry_analysis = None
        if industry:
            industry_analysis = self.get_risk_industry_analysis(industry)

        # 3. 生成风险提示
        risk_warnings = []
        if similar_cases:
            top_case = similar_cases[0]
            if top_case["similarity"] >= 0.8:
                risk_warnings.append({
                    "level": "high",
                    "message": f"⚠️ 高度警告：您公司与{top_case['company_name']}高度相似（相似度{top_case['similarity']:.1%}），该公司IPO被否"
                })
            elif top_case["similarity"] >= 0.6:
                risk_warnings.append({
                    "level": "medium",
                    "message": f"⚠️ 中度警告：与{top_case['company_name']}存在相似风险特征"
                })

        # 4. 汇总匹配特征
        all_matched = set()
        for case in similar_cases:
            for mf in case["matched_features"]:
                all_matched.add(mf["feature_name"])

        return {
            "comparison_summary": {
                "total_compared": len(similar_cases),
                "high_similarity_count": sum(1 for c in similar_cases if c["similarity"] >= 0.7),
                "common_risk_features": list(all_matched)[:5]
            },
            "similar_cases": similar_cases,
            "industry_analysis": industry_analysis,
            "risk_warnings": risk_warnings,
            "recommendations": self._generate_recommendations(similar_cases)
        }

    def _generate_recommendations(
        self,
        similar_cases: List[Dict]
    ) -> List[str]:
        """基于对标结果生成建议"""
        recommendations = []

        if not similar_cases:
            recommendations.append("✅ 未发现与近期IPO被否案例的显著相似性")
            return recommendations

        # 根据最相似的案例生成建议
        top_case = similar_cases[0]

        if top_case["similarity"] >= 0.7:
            recommendations.append(
                f"🚨 您公司与{top_case['company_name']}（IPO被否）高度相似，"
                f"建议重点关注：{', '.join([f['feature_name'] for f in top_case['matched_features'][:2]])}"
            )

        # 汇总共性风险
        common_features = {}
        for case in similar_cases:
            for mf in case["matched_features"]:
                fname = mf["feature_name"]
                if fname not in common_features:
                    common_features[fname] = 0
                common_features[fname] += 1

        # 找出高频风险
        high_freq = [k for k, v in common_features.items() if v >= 2]
        if high_freq:
            recommendations.append(
                f"📊 在与{len(similar_cases)}家被否案例比对中，"
                f"发现共性风险：{', '.join(high_freq[:3])}"
            )

        recommendations.append(
            "💡 建议参考上述被否案例的整改经验，提前完善信息披露和财务规范"
        )

        return recommendations


def get_ipo_comparison_service(db: Session) -> IPOComparisonService:
    """获取IPO对标服务实例"""
    return IPOComparisonService(db)
