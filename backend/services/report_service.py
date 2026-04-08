"""
报告管理服务
生成、导出、分享检测报告
"""
import os
import json
import uuid
import hashlib
import datetime
from typing import Dict, List, Optional, Any
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.database import Report, DetectionRecord, User
from backend.schemas.schemas import ReportResponse
from backend.services.detection_service import detection_engine


class ReportService:
    """
    报告管理服务
    """

    def __init__(self):
        """初始化报告服务"""
        self.template_dir = "backend/templates/reports"
        self.output_dir = settings.REPORT_DIR or "result/reports"
        self._ensure_directories()

    def _ensure_directories(self):
        """确保存储目录存在"""
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(
        self,
        detection_id: int,
        report_type: str = "basic",
        user_id: Optional[int] = None
    ) -> Report:
        """
        生成检测报告
        """
        db = SessionLocal()
        try:
            # 获取检测记录
            detection = db.query(DetectionRecord).filter(
                DetectionRecord.id == detection_id
            ).first()

            if not detection:
                raise ValueError("检测记录不存在")

            # 获取用户信息
            user = None
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()

            # 生成报告内容
            report_content = self._render_report_template(
                detection,
                report_type,
                user
            )

            # 生成文件名
            report_filename = self._generate_filename(detection, report_type)
            file_path = os.path.join(self.output_dir, report_filename)

            # 保存报告文件
            self._save_report_file(file_path, report_content, report_type, detection)

            # 创建报告记录
            db_report = Report(
                record_id=detection_id,
                report_type=report_type,
                file_path=file_path,
                file_url=f"/reports/{report_filename}"
            )

            db.add(db_report)
            db.commit()
            db.refresh(db_report)

            return db_report

        finally:
            db.close()

    def _render_report_template(
        self,
        detection: DetectionRecord,
        report_type: str,
        user: Optional[User] = None
    ) -> str:
        """渲染报告模板"""
        # 准备模板数据
        template_data = {
            "company_name": detection.company_name,
            "stock_code": detection.stock_code or "未提供",
            "year": detection.year or "未提供",
            "detection_time": detection.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "report_id": f"FD-{detection.id}-{datetime.datetime.now().strftime('%Y%m%d')}",
            "fraud_probability": f"{detection.fraud_probability:.2%}",
            "risk_level": self._get_risk_level_description(detection.risk_level),
            "risk_score": f"{detection.risk_score:.1f}",
            "risk_labels": detection.risk_labels or [],
            "shap_features": detection.shap_features or {},
            "ai_feature_scores": detection.ai_feature_scores or {},
            "financial_data": detection.financial_data or {},
            "mdna_summary": detection.mdna_text[:200] + "..." if detection.mdna_text else "未提供",
            "user": user,
            "disclaimer": "本报告基于AI模型分析生成，仅供参考，不构成投资建议或法律意见。"
        }

        if report_type == "professional":
            template_data["recommendations"] = self._generate_recommendations(detection)
            template_data["comparison_data"] = self._get_comparison_data(detection)

        elif report_type == "enterprise":
            template_data["detailed_analysis"] = self._generate_detailed_analysis(detection)
            template_data["historical_trends"] = self._get_historical_trends(detection)

        # 选择模板
        template_name = self._get_template_name(report_type, detection.risk_level)

        # 渲染模板
        return self._render_template(template_name, template_data)

    def _get_template_name(self, report_type: str, risk_level: str) -> str:
        """获取模板名称"""
        templates = {
            "basic": "basic_report.html",
            "professional": "professional_report.html",
            "enterprise": "enterprise_report.html"
        }

        # 高风险报告使用特殊模板
        if risk_level == "high" and report_type in ["professional", "enterprise"]:
            return f"high_risk_{report_type}_report.html"

        return templates.get(report_type, "basic_report.html")

    def _render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        # 创建Jinja2环境
        env = Environment(loader=FileSystemLoader(self.template_dir))

        # 加载模板
        template = env.get_template(template_name)

        # 渲染
        return template.render(**data)

    def _generate_filename(self, detection: DetectionRecord, report_type: str) -> str:
        """生成报告文件名"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        company_name = detection.company_name.replace(" ", "_").replace("/", "_")
        return f"{company_name}_{detection.year}_{report_type}_{timestamp}.pdf"

    def _save_report_file(self, file_path: str, content: str, report_type: str, detection: DetectionRecord = None):
        """保存报告文件"""
        if report_type.endswith("pdf"):
            try:
                # 尝试使用 weasyprint 生成 PDF
                html = HTML(string=content)
                html.write_pdf(file_path)
            except Exception as e:
                print(f"[WARN] weasyprint 生成 PDF 失败: {e}，尝试使用 reportlab")
                # 回退到使用 professional_report_service 生成 PDF
                if detection:
                    from backend.services.professional_report_service import generate_professional_report
                    result = generate_professional_report(detection)
                    # 复制生成的文件到目标路径
                    import shutil
                    shutil.copy(result['file_path'], file_path)
                else:
                    # 如果无法使用 reportlab，保存为 HTML
                    html_path = file_path.replace('.pdf', '.html')
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    raise RuntimeError(f"PDF 生成失败，已保存为 HTML: {html_path}")
        else:
            # 保存 HTML
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    def _get_risk_level_description(self, risk_level: str) -> str:
        """获取风险等级描述"""
        descriptions = {
            "low": "🟢 低风险 - 舞弊迹象不明显",
            "medium": "🟡 中风险 - 存在部分异常信号，需关注",
            "high": "🔴 高风险 - 多个舞弊特征显著，建议深入调查"
        }
        return descriptions.get(risk_level, risk_level)

    def _generate_recommendations(self, detection: DetectionRecord) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于风险等级
        if detection.risk_level == "high":
            recommendations.extend([
                "立即停止相关投资决策",
                "聘请专业审计机构进行深入核查",
                "重点关注货币资金、存货、应收账款等关键科目",
                "核查MD&A文本与财务数据的一致性"
            ])
        elif detection.risk_level == "medium":
            recommendations.extend([
                "加强对该企业的财务监控",
                "对比分析同行业可比企业",
                "关注后续财报披露情况",
                "必要时进行专项审计"
            ])
        else:
            recommendations.extend([
                "保持常规关注",
                "定期跟踪财务指标变化",
                "关注行业政策变化影响"
            ])

        # 基于风险标签
        risk_labels = detection.risk_labels or []
        for label_info in risk_labels:
            label = label_info.get("label", "")
            if "存贷双高" in label:
                recommendations.append("核查银行存款真实性和资金使用合理性")
            elif "现金流背离" in label:
                recommendations.append("分析经营活动现金流质量，核查收入确认政策")
            elif "存货异常" in label:
                recommendations.append("实地核查存货，关注存货周转率变化")
            elif "文本语义矛盾" in label:
                recommendations.append("深入分析MD&A披露质量，关注风险披露完整性")

        return recommendations[:8]  # 限制最多8条建议

    def _get_comparison_data(self, detection: DetectionRecord) -> Dict[str, Any]:
        """获取对比数据"""
        # 这里应该是从数据库获取行业平均数据
        # 简化版返回模拟数据
        return {
            "industry_avg": {
                "资产负债率": 0.45,
                "ROE": 0.12,
                "营收增长率": 0.15
            },
            "peer_companies": [
                {"name": "同行企业A", "risk_score": 35.2},
                {"name": "同行企业B", "risk_score": 42.8},
                {"name": "同行企业C", "risk_score": 28.6}
            ]
        }

    def _generate_detailed_analysis(self, detection: DetectionRecord) -> str:
        """生成详细分析"""
        if not detection.shap_features:
            return "SHAP特征分析数据不足"

        analysis = "### 深度特征分析\n\n"
        for feature, importance in detection.shap_features.items():
            analysis += f"**{feature}** (重要性: {importance:.4f}):\n"
            analysis += f"- 该特征对舞弊概率的影响方向: {'正向' if importance > 0 else '负向'}\n"
            analysis += f"- 建议核查重点: {self._get_feature_focus(feature)}\n\n"

        return analysis

    def _get_feature_focus(self, feature: str) -> str:
        """获取特征关注点"""
        focus_map = {
            "CON_SEM_AI": "MD&A文本中是否存在前后矛盾表述",
            "FIT_TD_AI": "文本描述与财务数据是否匹配",
            "COV_RISK_AI": "风险披露是否充分、具体",
            "HIDE_REL_AI": "关联交易披露是否完整",
            "TONE_ABN_AI": "管理层语调是否异常乐观",
            "DEN_ABN_AI": "信息披露密度是否合理",
            "STR_EVA_AI": "是否回避关键问题或使用模糊表述"
        }
        return focus_map.get(feature, "需要进一步分析")

    def _get_historical_trends(self, detection: DetectionRecord) -> List[Dict[str, Any]]:
        """获取历史趋势数据"""
        # 简化版返回模拟数据
        return [
            {"year": 2020, "risk_score": 25.6, "fraud_probability": 0.256},
            {"year": 2021, "risk_score": 32.8, "fraud_probability": 0.328},
            {"year": 2022, "risk_score": 45.2, "fraud_probability": 0.452},
            {"year": 2023, "risk_score": 58.7, "fraud_probability": 0.587}
        ]

    def generate_share_token(self, report_id: int) -> str:
        """生成分享令牌"""
        return hashlib.md5(f"{report_id}_{uuid.uuid4()}".encode()).hexdigest()

    def share_report(
        self,
        report_id: int,
        expire_days: int = 7,
        can_download: bool = False
    ) -> Dict[str, Any]:
        """分享报告"""
        db = SessionLocal()
        try:
            report = db.query(Report).filter(Report.id == report_id).first()
            if not report:
                raise ValueError("报告不存在")

            # 生成分享令牌
            share_token = self.generate_share_token(report_id)

            # 设置过期时间
            expire_at = datetime.datetime.now() + datetime.timedelta(days=expire_days)

            # 更新报告记录
            report.share_token = share_token
            report.is_public = True
            report.share_expire_at = expire_at
            report.can_download = can_download

            db.commit()

            return {
                "share_token": share_token,
                "share_url": f"{settings.FRONTEND_URL}/report/share/{share_token}",
                "expire_at": expire_at.isoformat(),
                "can_download": can_download
            }

        finally:
            db.close()

    def get_shared_report(self, share_token: str) -> Optional[ReportResponse]:
        """获取分享的报告"""
        db = SessionLocal()
        try:
            report = db.query(Report).filter(
                Report.share_token == share_token,
                Report.is_public == True,
                Report.share_expire_at > datetime.datetime.now()
            ).first()

            if not report:
                return None

            # 增加查看次数
            report.view_count = (report.view_count or 0) + 1
            db.commit()

            return ReportResponse.model_validate(report)

        finally:
            db.close()

    def batch_export_reports(
        self,
        report_ids: List[int],
        export_format: str = "pdf",
        user_id: int = None
    ) -> str:
        """批量导出报告"""
        if not report_ids:
            raise ValueError("没有选择要导出的报告")

        # 创建压缩包
        zip_filename = f"reports_batch_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(self.output_dir, zip_filename)

        # TODO: 实现批量导出逻辑
        # 1. 获取所有报告文件
        # 2. 创建ZIP压缩包
        # 3. 返回下载链接

        return zip_path

    def get_report_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取报告统计信息"""
        db = SessionLocal()
        try:
            # 获取用户报告
            reports = db.query(Report).join(Report.detection).filter(
                DetectionRecord.user_id == user_id
            ).all()

            # 统计信息
            total_reports = len(reports)
            download_count = sum(r.download_count for r in reports if r.download_count)
            view_count = sum(r.view_count for r in reports if r.view_count)
            shared_count = sum(1 for r in reports if r.is_public)

            # 风险等级分布
            risk_distribution = {"low": 0, "medium": 0, "high": 0}
            for report in reports:
                if report.detection and report.detection.risk_level:
                    level = report.detection.risk_level
                    if level in risk_distribution:
                        risk_distribution[level] += 1

            return {
                "total_reports": total_reports,
                "download_count": download_count,
                "view_count": view_count,
                "shared_count": shared_count,
                "risk_distribution": risk_distribution,
                "most_recent_report": max(reports, key=lambda r: r.created_at).created_at.isoformat() if reports else None
            }

        finally:
            db.close()

# 全局实例
report_service = ReportService()
