"""
数据库初始化脚本 - 导入预设案例数据
财务舞弊识别 SaaS 平台 - 经典案例库
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
# 🔥 强制导入 表基类 + 引擎 + 模型
from backend.models.database import Base, DemoCase, User, UserProfile
from backend.core.database import engine, SessionLocal
from backend.core.security import get_password_hash


def init_demo_cases(db: Session):
    """
    初始化预设案例数据
    """
    # 检查是否已存在案例
    existing = db.query(DemoCase).first()
    if existing:
        print("✅ 案例数据已存在，跳过初始化")
        return

    # ================= 案例 1: 康美药业 - 存贷双高典型 =================
    case_kangmei = DemoCase(
        case_name="康美药业",
        case_type="fraud",
        description="中国版'安然事件'，300 亿货币资金'不翼而飞'，存贷双高典型",
        company_info={
            "name": "康美药业股份有限公司",
            "stock_code": "600518",
            "year": 2017,
            "industry": "医药制造业"
        },
        financial_data={
            "货币资金": 34200000000,  # 342 亿元
            "短期借款": 14700000000,  # 147 亿元
            "营业收入": 26470000000,  # 265 亿元
            "净利润": 4100000000,    # 41 亿元
            "经营活动现金流净额": -5600000000,  # -56 亿元
            "存货": 12000000000,     # 存货激增
            "ROE": 0.158,
            "资产负债率": 0.47,
            "营业收入增长率": 0.22
        },
        mdna_text="""
报告期内，公司取得了卓越的经营业绩。营业收入大幅增长至265亿元，同比增长22%，
体现了公司在医药行业的领先地位和强大的市场竞争力。管理层对公司的未来发展充满信心，
预计市场需求将持续向好，公司业绩将保持高速增长态势。

然而，公司也面临一定的经营挑战。虽然账面净利润达到41亿元，表现优异，
但经营活动产生的现金流量净额为-56亿元，与账面利润存在背离。对此，
管理层解释称，这主要是由于公司为应对未来订单增长进行了战略性备货，导致存货余额激增85%。

关于货币资金情况，公司期末余额为342亿元，资金充裕。但为了维护与银行的良好合作关系，
公司同时维持着147亿元的短期借款。公司认为这种存贷双高的现象在行业内较为普遍，
属于正常的财务管理安排。部分货币资金可能受到一定的使用限制，但总体上不影响公司的正常经营。

在风险披露方面，公司充分认识到市场竞争加剧、原材料价格波动等风险因素，
并已制定相应的应对措施。公司将继续加强与主要供应商的合作关系，确保原材料供应稳定。
同时，公司将持续优化产品结构，提升核心竞争力。

展望未来，管理层预计公司将继续保持高速增长，为股东创造更大价值。虽然可能面临
一些不确定性和挑战，但公司有信心克服困难，实现既定目标。
""",
        expected_result={
            "fraud_probability": 0.968,
            "risk_level": "high",
            "risk_labels": ["存贷双高", "现金流背离", "存货异常", "财务费用异常"]
        },
        is_featured=True,
        sort_order=1
    )

    # ================= 案例 2: 瑞幸咖啡 - 虚增收入典型 =================
    case_luckin = DemoCase(
        case_name="瑞幸咖啡",
        case_type="fraud",
        description="中概股造假丑闻，虚增收入和费用，单店销售数据造假",
        company_info={
            "name": "瑞幸咖啡（Luckin Coffee）",
            "stock_code": "LK",
            "year": 2019,
            "industry": "餐饮业"
        },
        financial_data={
            "营业收入": 4290000000,    # 42.9 亿元
            "净利润": -320000000,      # -3.2 亿元
            "销售费用率": 0.58,        # 58% 异常高
            "营业收入增长率": 2.22,    # 222% 异常增长
            "经营活动现金流净额": -1500000000
        },
        mdna_text="""
报告期内，公司实现了爆发式增长，营业收入达到42.9亿元，同比增长222%，远超行业平均水平。
这一卓越表现主要得益于公司创新的商业模式和强大的执行力。管理层对未来充满信心，
预计公司将在不久的将来实现盈利，成为行业标杆。

在单店运营方面，公司表现突出。单店日均销售额达到行业均值的3倍以上，
部分核心门店甚至达到5倍以上。客户复购率超过50%，体现了强大的品牌黏性。
管理层表示，通过大数据驱动的精细化运营和精准营销，公司实现了远超传统餐饮企业的增长效率。

然而，公司销售费用较高，达到24.8亿元，占收入的58%，主要用于用户补贴和市场推广。
公司解释称，这是互联网模式快速扩张的必要投入，随着规模效应显现和品牌知名度提升，
未来费用率有望逐步下降。部分支出可能涉及关联方交易，但已按照相关规定进行披露。

关于现金流情况，由于大规模扩张和市场投入，经营活动现金流暂时为负。
管理层预计这一情况将在未来6-12个月内得到改善。公司将密切关注资金状况，
确保业务健康可持续发展。整体而言，公司基本面良好，未来发展前景广阔。
""",
        expected_result={
            "fraud_probability": 0.942,
            "risk_level": "high",
            "risk_labels": ["收入异常增长", "费用率异常", "经营数据矛盾"]
        },
        is_featured=True,
        sort_order=2
    )

    # ================= 案例 3: 獐子岛 - 存货异常典型 =================
    case_zhangzidao = DemoCase(
        case_name="獐子岛",
        case_type="fraud",
        description="'扇贝跑路'事件，存货盘点困难，资产减值异常",
        company_info={
            "name": "獐子岛集团股份有限公司",
            "stock_code": "002069",
            "year": 2014,
            "industry": "渔业"
        },
        financial_data={
            "存货": 2800000000,        # 28 亿元
            "存货占总资产比": 0.52,    # 52% 异常高
            "资产减值损失": 820000000, # 8.2 亿元
            "净利润": -1180000000,     # -11.8 亿元
            "经营活动现金流净额": -1200000000
        },
        mdna_text="""
报告期内，公司业绩出现大幅波动。经初步核查，底播虾夷扇贝发生大规模死亡，
预计造成存货损失。由于公司养殖海域位于深海区域，环境复杂多变，
传统盘点手段难以准确核实存货状况。这可能与近期海域水温变化、洋流异常等
自然因素有关，但具体原因尚需进一步调查分析。

基于谨慎性原则，公司计提资产减值损失约8.2亿元，导致当期净利润亏损11.8亿元。
管理层表示，虽然本次事件对公司短期业绩造成冲击，但公司已采取积极措施应对，
包括调整养殖结构、加强海域监测等。公司相信通过这些措施，未来经营状况将逐步改善。

在关联交易方面，公司与部分供应商和客户存在正常业务往来，均已按照规定进行披露。
部分交易可能涉及关联方，但交易价格公允，不存在利益输送情形。

审计机构在审计过程中注意到存货监盘存在一定困难，已就此与公司管理层进行充分沟通。
公司承诺将进一步完善存货管理制度，提高信息披露质量。管理层预计，
随着行业周期好转，公司业绩有望回升。
""",
        expected_result={
            "fraud_probability": 0.925,
            "risk_level": "high",
            "risk_labels": ["存货异常", "资产减值异常", "现金流恶化"]
        },
        is_featured=True,
        sort_order=3
    )

    # ================= 案例 4: 贵州茅台 - 健康企业对照 =================
    case_moutai = DemoCase(
        case_name="贵州茅台",
        case_type="healthy",
        description="A 股价值投资标杆，财务状况健康，无显著风险信号",
        company_info={
            "name": "贵州茅台酒股份有限公司",
            "stock_code": "600519",
            "year": 2022,
            "industry": "酒类制造业"
        },
        financial_data={
            "营业收入": 127500000000,   # 1275 亿元
            "净利润": 62700000000,      # 627 亿元
            "经营活动现金流净额": 72400000000,  # 724 亿元，与利润匹配
            "货币资金": 188900000000,   # 1889 亿元
            "短期借款": 0,              # 无短期借款
            "资产负债率": 0.22,         # 22% 健康水平
            "ROE": 0.30,
            "营业收入增长率": 0.16
        },
        mdna_text="""
报告期内，公司实现营业收入1275亿元，同比增长16%；净利润627亿元，同比增长20%。
经营活动产生的现金流量净额为724亿元，与净利润高度匹配，盈利质量优良。

公司严格执行会计准则，财务数据真实可靠。期末货币资金余额为1889亿元，
无短期借款和长期借款，资产负债率维持在22%的健康水平，财务状况稳健。
公司与主要供应商和客户均不存在关联关系，所有交易均按照市场化原则进行。

在风险披露方面，公司充分识别并披露了市场竞争、政策变化、原材料供应等
潜在风险因素，并制定了相应的应对措施。公司定期发布业绩预告和快报，
及时回应投资者关切，信息披露透明规范。

审计机构对公司的财务报表发表了标准无保留意见，肯定了公司财务数据的真实性和
完整性。公司将继续坚持高质量发展战略，稳步提升经营业绩，为股东创造持续稳定的回报。
""",
        expected_result={
            "fraud_probability": 0.032,
            "risk_level": "low",
            "risk_labels": []
        },
        is_featured=True,
        sort_order=4
    )

    # 添加案例到数据库
    db.add(case_kangmei)
    db.add(case_luckin)
    db.add(case_zhangzidao)
    db.add(case_moutai)

    db.commit()

    print(f"✅ 成功导入 {db.query(DemoCase).count()} 个预设案例")


def init_default_user(db: Session):
    """
    初始化默认用户账号 - AuditMind（演示账号，拥有全部功能）
    """
    # 检查默认账号是否已存在
    existing = db.query(User).filter(User.username == "AuditMind").first()
    if existing:
        print("✅ 默认账号 AuditMind 已存在，跳过创建")
        # 确保账号有企业版权限
        if existing.membership_level != "enterprise":
            existing.membership_level = "enterprise"
            existing.free_detections_remaining = -1  # 无限次检测
            db.commit()
            print("✅ 已更新 AuditMind 为 Enterprise 会员")
        return

    # 创建默认账号
    default_user = User(
        username="AuditMind",
        email="admin@auditmind.com",
        phone="13800000000",
        password_hash=get_password_hash("123"),
        user_type="enterprise",
        membership_level="enterprise",  # 企业版，拥有全部功能
        membership_expire_at=datetime.utcnow() + timedelta(days=3650),  # 10年有效期
        balance=999999.0,  # 充足余额
        free_detections_remaining=-1,  # -1 表示无限次检测
        detection_reset_date=datetime.utcnow().date() + timedelta(days=3650)
    )

    db.add(default_user)
    db.commit()
    db.refresh(default_user)

    # 创建用户资料
    default_profile = UserProfile(
        user_id=default_user.id,
        real_name="审计专家",
        company_name="AuditMind 智能审计",
        certified=True,
        certified_at=datetime.utcnow()
    )

    db.add(default_profile)
    db.commit()

    print("✅ 默认账号创建成功！")
    print("=" * 50)
    print("📋 账号信息:")
    print("   用户名: AuditMind")
    print("   密  码: 123")
    print("   邮  箱: admin@auditmind.com")
    print("   手  机: 13800000000")
    print("   权  限: Enterprise（全部功能）")
    print("=" * 50)


if __name__ == "__main__":
    # 🔥 🔥 🔥 核心修复：直接强制创建所有表（100%生效）
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功！")

    # 创建会话并导入案例
    db = SessionLocal()
    try:
        init_demo_cases(db)
        init_default_user(db)  # 创建默认账号
    finally:
        db.close()