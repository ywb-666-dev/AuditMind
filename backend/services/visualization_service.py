"""
数据可视化和 SHAP 分析服务
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import os

from core.config import settings


class VisualizationService:
    """
    数据可视化服务
    """

    def __init__(self):
        """初始化可视化服务"""
        self.output_dir = "result/visualization"
        os.makedirs(self.output_dir, exist_ok=True)

    def create_fraud_probability_gauge(self, fraud_probability: float) -> go.Figure:
        """
        创建舞弊概率仪表盘
        """
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=fraud_probability * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "舞弊概率 (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': self._get_risk_color(fraud_probability)},
                'steps': [
                    {'range': [0, 30], 'color': "rgba(0,255,0,0.2)"},
                    {'range': [30, 60], 'color': "rgba(255,165,0,0.2)"},
                    {'range': [60, 100], 'color': "rgba(255,0,0,0.2)"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': fraud_probability * 100
                }
            }
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return fig

    def _get_risk_color(self, fraud_probability: float) -> str:
        """获取风险颜色"""
        if fraud_probability >= 0.7:
            return "red"
        elif fraud_probability >= 0.4:
            return "orange"
        else:
            return "green"

    def create_shap_feature_importance(self, shap_features: Dict[str, float]) -> go.Figure:
        """
        创建 SHAP 特征重要性柱状图
        """
        if not shap_features:
            return go.Figure()

        # 排序并取 Top 10
        sorted_features = sorted(shap_features.items(), key=lambda x: x[1], reverse=True)[:10]
        features = [f[0] for f in sorted_features]
        importance = [f[1] for f in sorted_features]

        fig = go.Figure(go.Bar(
            x=importance,
            y=features,
            orientation='h',
            marker_color='red'
        ))

        fig.update_layout(
            title="SHAP 特征重要性分析",
            xaxis_title="重要性",
            yaxis_title="特征",
            height=400,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return fig

    def create_ai_feature_radar(self, ai_features: Dict[str, float]) -> go.Figure:
        """
        创建 AI 特征雷达图
        """
        if not ai_features:
            return go.Figure()

        # 特征名称映射
        feature_names = {
            "CON_SEM_AI": "语义矛盾度",
            "COV_RISK_AI": "风险披露完整性",
            "TONE_ABN_AI": "异常乐观语调",
            "FIT_TD_AI": "文本-数据一致性",
            "HIDE_REL_AI": "关联隐藏指数",
            "DEN_ABN_AI": "信息密度异常",
            "STR_EVA_AI": "回避表述强度"
        }

        categories = [feature_names.get(k, k) for k in ai_features.keys()]
        values = list(ai_features.values())

        # 闭合雷达图
        categories.append(categories[0])
        values.append(values[0])

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='AI 文本特征'
        ))

        fig.update_layout(
            title="AI 文本特征雷达图",
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            height=400
        )

        return fig

    def create_risk_labels_cloud(self, risk_labels: List[Dict[str, Any]]) -> go.Figure:
        """
        创建风险标签云
        """
        if not risk_labels:
            return go.Figure()

        labels = []
        scores = []
        colors = []

        for label_info in risk_labels:
            label = label_info.get("label", "")
            score = label_info.get("score", 0.5)

            labels.append(label)
            scores.append(score)

            # 根据分数设置颜色
            if score >= 0.7:
                colors.append("red")
            elif score >= 0.5:
                colors.append("orange")
            else:
                colors.append("green")

        # 创建散点图模拟标签云
        x = np.random.uniform(0, 10, len(labels))
        y = np.random.uniform(0, 10, len(labels))
        sizes = [s * 30 + 10 for s in scores]  # 调整大小

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='markers+text',
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.7
            ),
            text=labels,
            textposition="middle center",
            textfont=dict(size=[s * 12 + 8 for s in scores])
        ))

        fig.update_layout(
            title="风险标签云",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return fig

    def create_financial_trends(self, financial_data: Dict[str, Any]) -> go.Figure:
        """
        创建财务指标趋势图
        """
        # 这里需要历史数据，简化版使用当前数据
        metrics = ["ROE", "营业收入增长率", "资产负债率"]
        values = []

        for metric in metrics:
            value = financial_data.get(metric, 0)
            if isinstance(value, (int, float)):
                values.append(value)
            else:
                values.append(0)

        fig = go.Figure(data=[
            go.Bar(x=metrics, y=values, marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ])

        fig.update_layout(
            title="关键财务指标",
            yaxis_title="数值",
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )

        return fig

    def create_comparison_radar(self, target_company: Dict[str, Any], peer_companies: List[Dict[str, Any]]) -> go.Figure:
        """
        创建与同行对比的雷达图
        """
        # 简化版：只对比风险评分
        categories = ["目标企业"] + [f"同行{i+1}" for i in range(len(peer_companies))]
        values = [target_company.get("risk_score", 50)] + [p.get("risk_score", 50) for p in peer_companies]

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='风险评分对比'
        ))

        fig.update_layout(
            title="同业风险评分对比",
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=False,
            height=400
        )

        return fig

    def save_visualization(self, fig: go.Figure, filename: str) -> str:
        """
        保存可视化图表
        """
        filepath = os.path.join(self.output_dir, filename)
        fig.write_html(filepath)
        return filepath

    def generate_all_visualizations(
        self,
        detection_result: Dict[str, Any],
        output_prefix: str = "detection"
    ) -> Dict[str, str]:
        """
        生成所有可视化图表
        """
        visualizations = {}

        # 1. 舞弊概率仪表盘
        if "fraud_probability" in detection_result:
            gauge_fig = self.create_fraud_probability_gauge(detection_result["fraud_probability"])
            visualizations["gauge"] = self.save_visualization(gauge_fig, f"{output_prefix}_gauge.html")

        # 2. SHAP 特征重要性
        if "shap_features" in detection_result:
            shap_fig = self.create_shap_feature_importance(detection_result["shap_features"])
            visualizations["shap"] = self.save_visualization(shap_fig, f"{output_prefix}_shap.html")

        # 3. AI 特征雷达图
        if "ai_feature_scores" in detection_result:
            radar_fig = self.create_ai_feature_radar(detection_result["ai_feature_scores"])
            visualizations["radar"] = self.save_visualization(radar_fig, f"{output_prefix}_radar.html")

        # 4. 风险标签云
        if "risk_labels" in detection_result:
            cloud_fig = self.create_risk_labels_cloud(detection_result["risk_labels"])
            visualizations["cloud"] = self.save_visualization(cloud_fig, f"{output_prefix}_cloud.html")

        # 5. 财务指标
        if "financial_data" in detection_result:
            trends_fig = self.create_financial_trends(detection_result["financial_data"])
            visualizations["trends"] = self.save_visualization(trends_fig, f"{output_prefix}_trends.html")

        return visualizations

# 全局实例
visualization_service = VisualizationService()