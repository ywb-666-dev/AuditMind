"""
通俗易懂的PDF报告生成服务 - 让普通人也能看懂
"""
import os
import datetime
from typing import Dict, List, Optional, Any
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, HRFlowable
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError as e:
    REPORTLAB_AVAILABLE = False
    print(f"[WARN] reportlab 未安装: {e}")

from backend.core.config import settings
from backend.models.database import DetectionRecord, User


class ProfessionalReportService:
    """通俗易懂的报告生成服务"""

    # 特征通俗解释
    FEATURE_EXPLANATIONS = {
        "CON_SEM_AI": {
            "name": "报告前后矛盾",
            "simple_name": "报告表述矛盾",
            "explanation": "企业在年报不同的地方对同一件事情的描述互相矛盾，比如前面说业绩很好，后面又说面临困难",
            "why_it_matters": "正常的企业报告应该前后一致，如果自相矛盾，可能是在掩盖真实情况"
        },
        "FIT_TD_AI": {
            "name": "数据和说法不匹配",
            "simple_name": "言行不一致",
            "explanation": "企业在文字里说业务很好，但财务数据却显示收入下降，文字和数据对不上",
            "why_it_matters": "文本描述与财务数据脱节，是财务信息失真的典型特征，需重点核查数据真实性"
        },
        "COV_RISK_AI": {
            "name": "风险披露不充分",
            "simple_name": "风险披露不充分",
            "explanation": "企业对该说的风险轻描淡写，或者故意隐瞒重要风险信息",
            "why_it_matters": "坦诚的公司会如实告知风险，刻意隐瞒往往意味着问题严重"
        },
        "HIDE_REL_AI": {
            "name": "关联交易隐藏",
            "simple_name": "关联交易异常",
            "explanation": "企业与关联方（如大股东、子公司）之间有不透明的资金往来，可能存在利益输送",
            "why_it_matters": "关联交易不透明可能导致利益输送，损害中小股东权益"
        },
        "TONE_ABN_AI": {
            "name": "语气过于乐观",
            "simple_name": "表述过度乐观",
            "explanation": "企业对业绩的描述过于乐观，使用大量夸张的形容词，脱离实际情况",
            "why_it_matters": "过度乐观往往是为了掩盖业绩下滑或财务问题"
        },
        "DEN_ABN_AI": {
            "name": "信息披露异常",
            "simple_name": "信息披露不完整",
            "explanation": "年报中某些部分写得特别简略或特别复杂，信息披露的模式异常",
            "why_it_matters": "信息异常通常意味着企业在刻意掩盖某些不利信息"
        },
        "STR_EVA_AI": {
            "name": "回避关键问题",
            "simple_name": "关键问题回避",
            "explanation": "面对投资者关心的关键问题，企业使用模棱两可的话术回避正面回答",
            "why_it_matters": "对关键问题避而不答往往暗示存在不愿披露的信息"
        }
    }

    # 风险等级样式
    RISK_STYLES = {
        "high": {"color": colors.HexColor('#dc3545'), "text": "高风险", "emoji": "⚠️", "hex": "#dc3545",
                 "advice": "建议谨慎对待，深入调查后再做决策"},
        "medium": {"color": colors.HexColor('#ffc107'), "text": "中风险", "emoji": "⚡", "hex": "#ffc107",
                   "advice": "存在一定异常，建议保持关注"},
        "low": {"color": colors.HexColor('#28a745'), "text": "低风险", "emoji": "✓", "hex": "#28a745",
                "advice": "暂未发现明显异常，保持正常关注即可"}
    }

    def __init__(self):
        self.output_dir = settings.REPORT_DIR or "result/reports"
        self._ensure_directories()
        self._register_fonts()

    def _ensure_directories(self):
        """确保存储目录存在"""
        os.makedirs(self.output_dir, exist_ok=True)

    def _register_fonts(self):
        """注册中文字体 - 支持 Windows 和 Linux"""
        font_registered = False
        try:
            # 尝试多种字体路径（Windows + Linux）
            font_paths = [
                # Windows 字体
                ('C:/Windows/Fonts/msyh.ttc', 'MicrosoftYaHei'),
                ('C:/Windows/Fonts/simhei.ttf', 'SimHei'),
                ('C:/Windows/Fonts/simsun.ttc', 'SimSun'),
                ('C:/Windows/Fonts/msyhbd.ttc', 'MicrosoftYaHeiBold'),
                # Linux 中文字体
                ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 'WenQuanYiZenHei'),
                ('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 'WenQuanYiMicroHei'),
                ('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 'NotoSansCJK'),
                ('/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc', 'NotoSansCJKBold'),
                ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'NotoSansCJK'),
                ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVu'),
                ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 'Liberation'),
            ]

            chinese_font_path = None
            for path, name in font_paths:
                if os.path.exists(path):
                    try:
                        if 'Bold' in name or 'bd' in path.lower():
                            pdfmetrics.registerFont(TTFont('ChineseFontBold', path))
                        else:
                            pdfmetrics.registerFont(TTFont('ChineseFont', path))
                            chinese_font_path = path
                        print(f"[OK] 注册字体: {name} from {path}")
                        font_registered = True
                    except Exception as e:
                        print(f"[WARN] 注册字体失败 {name}: {e}")
                        continue

            # 如果没有粗体字体，用常规字体代替
            if chinese_font_path:
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFontBold', chinese_font_path))
                except:
                    pass

            if not font_registered:
                print("[WARN] 未找到任何中文字体，PDF生成可能显示乱码")

        except Exception as e:
            print(f"[WARN] 字体注册失败: {e}")

    def generate_pdf(self, detection: DetectionRecord, user: Optional[User] = None) -> Dict[str, Any]:
        """生成通俗易懂的PDF报告"""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab 未安装")

        filename = f"{detection.company_name}_{detection.year}_财务风险检测报告_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        file_path = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=60,
            leftMargin=60,
            topMargin=60,
            bottomMargin=40
        )

        # 定义样式
        styles = self._create_styles()
        story = []

        # 封面
        self._add_cover_page(story, detection, styles)
        story.append(PageBreak())

        # 核心结论（最重要，放在最前面）
        self._add_core_findings(story, detection, styles)

        # 风险详情解释
        self._add_risk_explanations(story, detection, styles)

        # 重点关注的问题
        self._add_key_concerns(story, detection, styles)

        # 建议怎么做
        self._add_action_plan(story, detection, styles)

        # 免责声明
        self._add_simple_disclaimer(story, styles)

        doc.build(story)

        return {
            "file_path": file_path,
            "filename": filename,
            "file_type": "pdf",
            "file_size": os.path.getsize(file_path)
        }

    def _get_font_name(self, bold=False) -> str:
        """获取可用字体名称"""
        try:
            # 检查字体是否已注册
            from reportlab.pdfbase import pdfmetrics
            if bold:
                if 'ChineseFontBold' in pdfmetrics._fonts:
                    return 'ChineseFontBold'
            if 'ChineseFont' in pdfmetrics._fonts:
                return 'ChineseFont'
        except:
            pass
        # 回退到 Helvetica（英文）或默认字体
        return 'Helvetica-Bold' if bold else 'Helvetica'

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """创建文档样式"""
        styles = {}

        # 获取可用字体
        font_name = self._get_font_name(bold=False)
        font_name_bold = self._get_font_name(bold=True)

        # 标题样式
        styles['title'] = ParagraphStyle(
            'CustomTitle',
            fontName=font_name,
            fontSize=26,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a1a2e')
        )

        styles['subtitle'] = ParagraphStyle(
            'CustomSubtitle',
            fontName=font_name,
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        )

        styles['heading1'] = ParagraphStyle(
            'CustomHeading1',
            fontName=font_name,
            fontSize=16,
            leading=22,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1a1a2e'),
            borderPadding=5
        )

        styles['heading2'] = ParagraphStyle(
            'CustomHeading2',
            fontName=font_name,
            fontSize=13,
            leading=17,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#333333')
        )

        styles['normal'] = ParagraphStyle(
            'CustomNormal',
            fontName=font_name,
            fontSize=10,
            leading=15,
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=4
        )

        styles['highlight'] = ParagraphStyle(
            'CustomHighlight',
            fontName=font_name,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#333333'),
            backColor=colors.HexColor('#fff3cd'),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=8
        )

        styles['alert'] = ParagraphStyle(
            'CustomAlert',
            fontName=font_name,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#721c24'),
            backColor=colors.HexColor('#f8d7da'),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=8
        )

        styles['success'] = ParagraphStyle(
            'CustomSuccess',
            fontName=font_name,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#155724'),
            backColor=colors.HexColor('#d4edda'),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=8
        )

        styles['quote'] = ParagraphStyle(
            'CustomQuote',
            fontName=font_name,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#555555'),
            leftIndent=20,
            rightIndent=20,
            spaceBefore=6,
            spaceAfter=6,
            borderColor=colors.HexColor('#dddddd'),
            borderWidth=1,
            borderPadding=8
        )

        return styles

    def _add_cover_page(self, story: List, detection: DetectionRecord, styles: Dict):
        """添加封面"""
        story.append(Spacer(1, 60))

        # 主标题
        story.append(Paragraph("财务风险检测报告", styles['title']))
        story.append(Spacer(1, 30))

        # 企业信息
        story.append(Paragraph(f"<b>{detection.company_name}</b>", styles['subtitle']))
        if detection.stock_code:
            story.append(Paragraph(f"股票代码：{detection.stock_code}", styles['subtitle']))
        if detection.year:
            story.append(Paragraph(f"报告年度：{detection.year}年", styles['subtitle']))
        story.append(Spacer(1, 50))

        # 风险等级大图标
        risk_style = self.RISK_STYLES.get(detection.risk_level, self.RISK_STYLES['low'])

        # 获取可用字体
        font_name = self._get_font_name(bold=False)

        # 风险等级框
        risk_box_style = ParagraphStyle(
            'RiskBox',
            fontName=font_name,
            fontSize=20,
            alignment=TA_CENTER,
            textColor=risk_style['color'],
            spaceBefore=10,
            spaceAfter=10
        )

        story.append(Paragraph(f"{risk_style['emoji']} 检测结论：{risk_style['text']}", risk_box_style))
        story.append(Spacer(1, 10))

        # 舞弊概率
        prob_style = ParagraphStyle(
            'ProbStyle',
            fontName=font_name,
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#333333')
        )
        story.append(Paragraph(f"舞弊风险概率：<b>{detection.fraud_probability:.1%}</b>", prob_style))
        story.append(Spacer(1, 10))

        # 简要建议
        advice_style = ParagraphStyle(
            'AdviceStyle',
            fontName=font_name,
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666'),
            leading=16
        )
        story.append(Paragraph(risk_style['advice'], advice_style))

        story.append(Spacer(1, 60))

        # 生成日期
        story.append(Paragraph(
            f"报告生成日期：{detection.created_at.strftime('%Y年%m月%d日')}",
            styles['subtitle']
        ))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dddddd')))

    def _add_core_findings(self, story: List, detection: DetectionRecord, styles: Dict):
        """添加核心发现 - 用大白话解释"""
        story.append(Paragraph("一、核心发现", styles['heading1']))

        risk_style = self.RISK_STYLES.get(detection.risk_level, self.RISK_STYLES['low'])

        # 根据风险等级给出简洁结论
        if detection.risk_level == "high":
            conclusion = f"""
            <b>主要结论：</b>经过AI分析，<b>{detection.company_name}</b>的财务报告存在
            <font color="{risk_style['hex']}"><b>较高风险</b></font>。
            系统检测到多项异常信号，建议投资者在做出决策前谨慎评估。
            """
            story.append(Paragraph(conclusion, styles['alert']))
        elif detection.risk_level == "medium":
            conclusion = f"""
            <b>主要结论：</b>经过AI分析，<b>{detection.company_name}</b>的财务报告存在
            <font color="{risk_style['hex']}"><b>一定风险信号</b></font>。
            虽然尚未达到高风险级别，但已发现一些值得关注的问题，建议保持关注。
            """
            story.append(Paragraph(conclusion, styles['highlight']))
        else:
            conclusion = f"""
            <b>主要结论：</b>经过AI分析，<b>{detection.company_name}</b>的财务报告
            <font color="{risk_style['hex']}"><b>风险较低</b></font>。
            暂未发现明显的异常信号，但仍建议持续关注后续财报变化。
            """
            story.append(Paragraph(conclusion, styles['success']))

        story.append(Spacer(1, 10))

        # 关键数据
        story.append(Paragraph("<b>关键数据一览：</b>", styles['heading2']))

        info_data = [
            ['评估项目', '结果', '说明'],
            ['舞弊风险概率', f"{detection.fraud_probability:.1%}", 'AI模型预测的财务造假可能性'],
            ['综合风险评分', f"{detection.risk_score:.1f}/100", '满分100分，分数越高风险越大'],
            ['发现问题数量', f"{len(detection.risk_labels or [])}项", '系统自动识别出的风险点数量'],
        ]

        info_table = Table(info_data, colWidths=[100, 100, 270])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#dddddd')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self._get_font_name()),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)

    def _add_risk_explanations(self, story: List, detection: DetectionRecord, styles: Dict):
        """添加风险解释 - 用通俗语言解释发现了什么问题，引用原文"""
        if not detection.ai_feature_scores:
            return

        story.append(PageBreak())
        story.append(Paragraph("二、发现了什么问题？", styles['heading1']))

        # 计算有多少个特征满足显示条件
        significant_issues = [(k, v) for k, v in detection.ai_feature_scores.items()
                              if not k.startswith('_') and v >= 0.4]

        total_issues = len([k for k, v in detection.ai_feature_scores.items() if not k.startswith('_')])

        if len(significant_issues) < total_issues:
            story.append(Paragraph(
                f"我们使用人工智能技术分析了企业的年报文本，共检测到 {total_issues} 项风险特征。"
                f"其中 {len(significant_issues)} 项风险程度较高（评分≥0.4），以下为您详细说明：",
                styles['normal']
            ))
        else:
            story.append(Paragraph(
                "我们使用人工智能技术分析了企业的年报文本，发现了以下值得关注的问题：",
                styles['normal']
            ))
        story.append(Spacer(1, 10))

        # 找出得分最高的3个风险特征
        sorted_features = sorted(
            [(k, v) for k, v in detection.ai_feature_scores.items() if not k.startswith('_')],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # 获取可疑文本片段
        suspicious_segments = detection.suspicious_segments or []

        displayed_count = 0
        for i, (feature, score) in enumerate(sorted_features, 1):
            feature_info = self.FEATURE_EXPLANATIONS.get(feature, {
                "simple_name": feature,
                "explanation": "",
                "why_it_matters": ""
            })

            # 只展示有明显问题的（分数>0.4），最多显示3个
            if score < 0.4 or displayed_count >= 3:
                continue
            displayed_count += 1

            story.append(Paragraph(f"{i}. {feature_info['simple_name']}", styles['heading2']))

            # 风险程度
            if score > 0.6:
                level = "严重"
                color = "#dc3545"
            elif score > 0.4:
                level = "中等"
                color = "#ffc107"
            else:
                level = "轻微"
                color = "#28a745"

            story.append(Paragraph(
                f"<b>风险程度：</b><font color='{color}'>{level}</font>（评分：{score:.2f}）",
                styles['normal']
            ))

            story.append(Paragraph(f"<b>问题说明：</b>{feature_info['explanation']}", styles['normal']))
            story.append(Paragraph(f"<b>风险提示：</b>{feature_info['why_it_matters']}", styles['normal']))

            # 查找并显示相关的可疑文本片段
            related_segments = [
                seg for seg in suspicious_segments
                if seg.get('risk_type') == feature or feature in str(seg.get('risk_type', ''))
            ]

            # 如果找不到精确匹配，显示前几个可疑片段
            if not related_segments and suspicious_segments:
                related_segments = suspicious_segments[:1]

            if related_segments:
                story.append(Paragraph("<b>原文引用：</b>", styles['normal']))
                for seg in related_segments[:2]:  # 最多显示2个片段
                    text_content = seg.get('text', '')
                    if text_content and len(text_content) > 10:  # 确保有实质内容
                        # 截断过长的文本
                        display_text = text_content[:300] + "..." if len(text_content) > 300 else text_content
                        story.append(Paragraph(f"「{display_text}」", styles['quote']))

            story.append(Spacer(1, 15))

    def _add_key_concerns(self, story: List, detection: DetectionRecord, styles: Dict):
        """添加重点关注的问题 - 基于SHAP分析"""
        if not detection.shap_features:
            return

        story.append(Paragraph("三、哪些因素影响了风险评估？", styles['heading1']))

        story.append(Paragraph(
            "以下因素对本次风险评估结果影响最大（按影响程度排序）：",
            styles['normal']
        ))
        story.append(Spacer(1, 10))

        # 取影响最大的5个特征
        sorted_shap = sorted(
            detection.shap_features.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]

        concern_data = [['问题类型', '影响程度', '说明']]

        for feature, importance in sorted_shap:
            feature_info = self.FEATURE_EXPLANATIONS.get(feature, {
                "simple_name": feature,
                "name": feature
            })

            # 影响程度描述
            abs_imp = abs(importance)
            if abs_imp > 0.15:
                impact_level = "影响很大"
            elif abs_imp > 0.08:
                impact_level = "影响中等"
            else:
                impact_level = "影响较小"

            # 影响方向
            if importance > 0:
                direction = "推高风险"
            else:
                direction = "降低风险"

            concern_data.append([
                feature_info['simple_name'],
                f"{impact_level}\n（{direction}）",
                feature_info.get('explanation', '')[:40] + "..." if len(feature_info.get('explanation', '')) > 40 else feature_info.get('explanation', '')
            ])

        if len(concern_data) > 1:
            concern_table = Table(concern_data, colWidths=[100, 80, 310])
            concern_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#dddddd')),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), self._get_font_name()),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(concern_table)

        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "<b>说明：</b>正值表示该因素推高了风险评估，负值表示降低了风险评估。",
            styles['normal']
        ))

    def _add_action_plan(self, story: List, detection: DetectionRecord, styles: Dict):
        """添加行动建议 - 详细版本"""
        story.append(PageBreak())
        story.append(Paragraph("四、建议怎么做？", styles['heading1']))

        if detection.risk_level == "high":
            story.append(Paragraph("<b>鉴于检测到较高风险，建议您采取以下措施：</b>", styles['normal']))
            story.append(Spacer(1, 10))

            actions = [
                ("🚨 谨慎投资", """
                在当前风险水平下，建议您暂缓投资计划，优先进行更深入的风险排查。
                首先，咨询专业财务顾问或注册会计师，获取独立第三方意见；
                其次，查阅近期是否有研究机构发布关于该公司的风险提示报告；
                最后，关注市场反应，观察是否存在其他投资者也对该公司的财务数据提出质疑。
                投资安全应优先于投资收益，切勿被表面的高成长性所迷惑。
                """),
                ("📊 核实关键财务数据", """
                重点核查以下科目：货币资金的真实性（是否存在虚假存款）、
                存货的准确性（是否存在虚增库存）、应收账款的回收可能性（是否存在虚构收入）。
                特别关注"存贷双高"现象——即企业账面上有大量现金却同时借入大量贷款，
                这种情况往往暗示资金被挪用或存款不存在。
                此外，对比经营活动现金流与净利润的差异，若长期背离需高度警惕。
                """),
                ("📖 仔细阅读年报原文", """
                重点阅读"管理层讨论与分析"（MD&A）章节，这是企业解释经营情况的核心部分。
                首先，关注业绩变动原因的解释是否充分、合理；
                其次，检查是否存在避重就轻的情况，如对亏损业务一笔带过，对盈利业务大书特书；
                最后，对比前后年度的表述，看是否存在自相矛盾之处。
                正常的企业报告应该前后一致、逻辑自洽。
                """),
                ("🔍 关注监管动态", """
                定期查看证监会、证券交易所官网，确认该公司是否收到过监管问询函或关注函。
                问询函通常意味着监管机构发现了某些可疑之处需要企业解释。
                同时，关注财经媒体报道，搜索该公司名称加"财务造假"、"违规"等关键词，
                了解是否有 whistleblower（举报人）或其他线索。
                监管动态是判断企业风险的重要风向标。
                """),
            ]
        elif detection.risk_level == "medium":
            story.append(Paragraph("<b>检测到一定风险信号，建议您采取以下措施：</b>", styles['normal']))
            story.append(Spacer(1, 10))

            actions = [
                ("👀 保持观望", """
                在当前风险水平下，不建议立即做出投资决策，但也不急于完全否定。
                建议设置观察期（如3-6个月），在此期间持续关注该公司的后续动态。
                重点关注下一季度或下一年度的财报披露，观察本次发现的风险信号是否仍然存在，
                是有所缓解还是进一步加重。风险信号的变化趋势往往比单一时间点的风险水平更具参考价值。
                """),
                ("📈 对比同行业公司", """
                将该公司的关键财务指标与同行业其他可比公司进行横向对比。
                对比维度包括：毛利率水平、应收账款周转率、存货周转率、资产负债率等。
                如果该公司多项指标明显偏离行业平均水平，而又缺乏合理的商业解释，
                则风险程度可能高于当前评估。行业对比是识别财务异常的有效方法。
                """),
                ("📝 建立跟踪档案", """
                建议您为该公司建立专门的信息跟踪档案，定期记录以下内容：
                每季度财报发布后的关键数据变化、监管机构的问询情况、
                高管人员的变动信息、重大合同或关联交易的披露情况。
                通过长期跟踪，可以更准确地判断风险发展趋势，避免因短期数据波动而做出错误决策。
                """),
            ]
        else:
            story.append(Paragraph("<b>风险较低，但仍建议您采取以下预防措施：</b>", styles['normal']))
            story.append(Spacer(1, 10))

            actions = [
                ("✓ 定期复检", """
                虽然当前评估显示风险较低，但财务风险是动态变化的。
                建议每季度更新一次风险评估，特别是在该公司发布新的财报后。
                建立定期复检机制可以及时发现风险的早期信号，避免在风险积累后才被动应对。
                即使是看似稳健的企业，也可能因为行业环境变化或内部管理问题而出现财务恶化。
                """),
                ("📊 分散投资组合", """
                无论单一股票的风险评估结果如何，都不建议将过多资金集中在单一标的上。
                建议采用投资组合的方式分散风险，将资金配置在不同行业、不同风险特征的资产上。
                即使某一家公司出现问题，也不会对整个投资组合造成致命打击。
                分散投资是控制风险的基本原则。
                """),
                ("📚 持续学习财务知识", """
                提升自身的财务分析能力是识别风险的根本途径。
                建议学习基础的财务报表分析方法，了解常见的财务造假手法，
                如虚增收入、隐瞒负债、关联交易非关联化等。
                掌握这些知识后，您可以更独立地判断企业的财务健康状况，
                而不是完全依赖外部评级或他人推荐。
                """),
            ]

        for title, desc in actions:
            story.append(Paragraph(f"<b>{title}</b>", styles['heading2']))
            story.append(Paragraph(desc.strip(), styles['normal']))
            story.append(Spacer(1, 8))

        # 风险证据定位 - 直接输出原文
        if detection.risk_evidence_locations or detection.suspicious_segments:
            story.append(Spacer(1, 15))
            story.append(Paragraph("<b>📍 系统检测到的可疑文本片段</b>", styles['heading2']))
            story.append(Paragraph("以下是人工智能系统在年报中识别出的可疑表述：", styles['normal']))
            story.append(Spacer(1, 5))

            # 优先使用 suspicious_segments，因为它包含原文
            segments = detection.suspicious_segments or []
            if not segments and detection.risk_evidence_locations:
                # 如果没有 suspicious_segments，尝试从 risk_evidence_locations 获取
                segments = [
                    {
                        'text': e.get('where_is_risk', ''),
                        'risk_type': e.get('feature_name', ''),
                        'location': e.get('location', '')
                    }
                    for e in detection.risk_evidence_locations
                    if e.get('where_is_risk') or e.get('why_selected')
                ]

            displayed_segments = 0
            for i, seg in enumerate(segments[:10], 1):  # 检查更多片段
                feature_name = seg.get('risk_type', '')
                feature_info = self.FEATURE_EXPLANATIONS.get(feature_name, {"simple_name": feature_name})

                # 尝试多个可能的字段名获取文本
                text_content = seg.get('text', '') or seg.get('content', '') or seg.get('segment', '')

                # 如果还是没有，尝试拼接其他信息
                if not text_content or len(text_content) < 5:
                    why = seg.get('why_selected', '')
                    where = seg.get('where_is_risk', '')
                    text_content = why or where or ''

                if text_content and len(text_content) > 5:
                    displayed_segments += 1
                    story.append(Paragraph(f"片段 {displayed_segments}：{feature_info['simple_name']}", styles['heading2']))

                    # 显示原文
                    display_text = text_content[:500] + "..." if len(text_content) > 500 else text_content
                    story.append(Paragraph(f"「{display_text}」", styles['quote']))

                    # 显示位置信息（如果有）
                    location = seg.get('location', '') or seg.get('segment_id', '')
                    if location and location not in ['未指定', '', '未知', None]:
                        story.append(Paragraph(f"<i>位置：第{location}段</i>", styles['normal']))

                    story.append(Spacer(1, 8))

            # 如果没有显示任何片段，给出说明
            if displayed_segments == 0:
                story.append(Paragraph(
                    "系统已识别出风险特征，但未能提取到具体的原文片段。这可能是由于文本解析问题或风险特征来源于整体数据模式而非具体段落。",
                    styles['normal']
                ))

    def _add_simple_disclaimer(self, story: List, styles: Dict):
        """添加简化的免责声明"""
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#eeeeee')))
        story.append(Spacer(1, 10))

        disclaimer = """
        <b>免责声明：</b>本报告由AI系统自动生成，仅供参考，不构成任何投资建议。
        报告分析基于公开的年报数据，可能存在误判。投资有风险，决策需谨慎。
        建议结合专业审计意见和实地调研做出投资决策。
        """
        story.append(Paragraph(disclaimer, styles['normal']))


# 便捷函数
def generate_professional_report(detection: DetectionRecord, user: Optional[User] = None) -> Dict[str, Any]:
    """生成通俗易懂的专业报告"""
    service = ProfessionalReportService()
    return service.generate_pdf(detection, user)
