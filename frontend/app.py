"""
财务舞弊识别 SaaS 平台
"""
import streamlit as st
import requests
import pandas as pd
import io
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import base64
import extra_streamlit_components as stx
from utils import cached_api_request, clear_api_cache, api_cache, batch_load_data
from download_helper import download_file_with_auth, create_download_button

# 持久化存储 - 使用 Cookie (通过 extra-streamlit-components)

# ================= 页面配置 =================
st.set_page_config(
    page_title="财务舞弊识别 SaaS 平台",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= API 配置 =================
API_BASE_URL = "http://localhost:8000/api"

# ================= 持久化登录管理 =================
class AuthManager:
    """登录状态管理器 - 使用 Cookie 持久化"""

    COOKIE_NAME = "fraud_detection_auth"
    COOKIE_EXPIRY_DAYS = 7  # Cookie 有效期7天

    @staticmethod
    def _get_cookie_manager():
        """获取 Cookie Manager 实例"""
        return stx.CookieManager()

    @staticmethod
    def save_auth(token: str, user_info: dict):
        """保存登录信息到 Cookie"""
        try:
            auth_data = {
                "token": token,
                "user_info": user_info,
                "saved_at": datetime.now().isoformat()
            }
            auth_json = json.dumps(auth_data, ensure_ascii=False)

            # 使用 CookieManager 保存
            cookie_manager = AuthManager._get_cookie_manager()
            cookie_manager.set(
                AuthManager.COOKIE_NAME,
                auth_json,
                expires_at=datetime.now() + timedelta(days=AuthManager.COOKIE_EXPIRY_DAYS)
            )

            # 同时保存到 session_state
            st.session_state.token = token
            st.session_state.user_info = user_info
            st.session_state.logged_in = True
            st.session_state.persisted_token = token
            st.session_state.persisted_user_info = user_info

            print("[AuthManager] 登录信息已保存到 Cookie")

        except Exception as e:
            print(f"[AuthManager] 保存登录状态失败: {e}")

    @staticmethod
    def clear_auth():
        """清除登录信息"""
        try:
            # 清除 Cookie
            cookie_manager = AuthManager._get_cookie_manager()
            cookie_manager.delete(AuthManager.COOKIE_NAME)

            # 清除 session_state
            keys_to_clear = ['token', 'user_info', 'logged_in', 'persisted_token', 'persisted_user_info']
            for key in keys_to_clear:
                if key in st.session_state:
                    st.session_state[key] = None

            print("[AuthManager] 登录信息已清除")

        except Exception as e:
            print(f"[AuthManager] 清除登录状态失败: {e}")

    @staticmethod
    def try_auto_login():
        """尝试自动登录 - 从 Cookie 恢复"""
        # 如果已经登录，直接返回
        if st.session_state.get('logged_in'):
            return True

        try:
            # 从 Cookie 读取登录信息
            cookie_manager = AuthManager._get_cookie_manager()
            auth_json = cookie_manager.get(AuthManager.COOKIE_NAME)

            if not auth_json:
                print("[AuthManager] 未找到 Cookie 中的登录信息")
                return False

            auth_data = json.loads(auth_json)
            token = auth_data.get('token')
            user_info = auth_data.get('user_info')

            if not token or not user_info:
                print("[AuthManager] Cookie 中的登录信息不完整")
                return False

            # 验证 token 是否有效
            url = f"{API_BASE_URL}/user/profile"
            response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)

            if response.status_code == 200:
                # 更新用户信息(从服务器获取最新数据)
                fresh_user_info = response.json()
                # 合并原有信息和新信息
                user_info.update(fresh_user_info)

                st.session_state.token = token
                st.session_state.user_info = user_info
                st.session_state.logged_in = True
                st.session_state.persisted_token = token
                st.session_state.persisted_user_info = user_info

                # 刷新 Cookie 过期时间
                cookie_manager.set(
                    AuthManager.COOKIE_NAME,
                    auth_json,
                    expires_at=datetime.now() + timedelta(days=AuthManager.COOKIE_EXPIRY_DAYS)
                )

                print("[AuthManager] 已从 Cookie 恢复登录状态")
                return True
            else:
                print(f"[AuthManager] Token 已失效: {response.status_code}")
                # Token 失效，清除 Cookie
                cookie_manager.delete(AuthManager.COOKIE_NAME)
                return False

        except Exception as e:
            print(f"[AuthManager] 自动登录失败: {e}")
            return False

    @staticmethod
    def get_cookie_manager_instance():
        """获取并初始化 Cookie Manager (需要在页面开始处调用)"""
        return stx.CookieManager()


# ================= 会话状态初始化 =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "token" not in st.session_state:
    st.session_state.token = None
if "current_detection" not in st.session_state:
    st.session_state.current_detection = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "auth_initialized" not in st.session_state:
    st.session_state.auth_initialized = False

# ================= 辅助函数 =================
def make_api_request(endpoint, method="GET", data=None, headers=None, timeout=30):
    """发送 API 请求"""
    url = f"{API_BASE_URL}{endpoint}"

    if headers is None:
        headers = {}

    # 添加认证 token
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)

        if response.status_code == 401:
            st.session_state.logged_in = False
            st.session_state.token = None
            st.session_state.user_info = None
            st.error("登录已过期，请重新登录")
            return None

        if response.status_code >= 400:
            st.error(f"请求失败：{response.status_code} - {response.text}")
            return None

        return response.json()
    except Exception as e:
        st.error(f"请求失败：{str(e)}")
        return None




def run_detection_with_progress(detection_data, timeout=120):
    """
    执行检测并显示步骤进度动画
    返回检测结果或None
    """
    import time

    # 定义检测步骤
    steps = [
        ("📊 数据验证", "验证财务数据完整性和一致性..."),
        ("🔍 AI文本分析", "使用大模型提取7维风险特征..."),
        ("📈 财务指标计算", "计算传统财务舞弊指标..."),
        ("🤖 模型推理", "执行XGBoost模型预测..."),
        ("📊 SHAP可解释性", "计算特征重要性分析..."),
        ("⚖️ IPO对标分析", "对比历史IPO被否案例..."),
        ("💡 生成整改建议", "基于风险标签生成建议..."),
    ]

    result = None
    error_msg = None

    # 使用 st.status 创建进度容器
    with st.status("🔍 正在执行AI舞弊检测分析...", expanded=True) as status:
        progress_bar = st.progress(0)
        step_text = st.empty()

        # 步骤1-2: 数据验证和AI分析(在实际API调用前)
        for i, (step_name, step_desc) in enumerate(steps[:2]):
            progress = (i + 1) / len(steps)
            progress_bar.progress(progress)
            step_text.markdown(f"**{step_name}**\n{step_desc}")
            time.sleep(0.5)  # 短暂延迟显示动画效果

        # 步骤3-7: 实际API调用(在后端完成)
        step_text.markdown(f"**{steps[2][0]}**\n{steps[2][1]}")
        progress_bar.progress(0.4)

        try:
            # 执行实际API调用
            result = make_api_request(
                "/detection/analyze",
                method="POST",
                data=detection_data,
                timeout=timeout
            )

            if result:
                # API调用成功，快速完成后几个步骤的展示
                for i, (step_name, step_desc) in enumerate(steps[3:], start=3):
                    progress = (i + 1) / len(steps)
                    progress_bar.progress(min(progress, 1.0))
                    step_text.markdown(f"**{step_name}**\n{step_desc}")
                    time.sleep(0.2)

                status.update(label="✅ 检测完成！", state="complete", expanded=False)
            else:
                error_msg = "检测请求失败"
                status.update(label=f"❌ {error_msg}", state="error")

        except Exception as e:
            error_msg = str(e)
            status.update(label=f"❌ 检测失败: {error_msg}", state="error")

        progress_bar.empty()
        step_text.empty()

    if error_msg:
        st.error(f"检测失败: {error_msg}")

    return result


# ================= Streamlit 缓存装饰器 =================

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_detection_history(_token=None):
    """缓存检测历史数据(1小时)"""
    url = f"{API_BASE_URL}/detection/history"
    headers = {}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_cached_demo_cases(featured_only=False, _token=None):
    """缓存案例列表数据(30分钟)"""
    url = f"{API_BASE_URL}/detection/cases?featured_only={featured_only}"
    headers = {}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_membership_plans(_token=None):
    """缓存会员套餐数据(1小时)"""
    url = f"{API_BASE_URL}/order/membership/plans"
    headers = {}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


@st.cache_resource
def get_chart_config():
    """缓存图表配置资源"""
    return {
        "gauge": {
            "colors": ["rgba(0,255,0,0.2)", "rgba(255,165,0,0.2)", "rgba(255,0,0,0.2)"],
            "thresholds": [30, 60, 100]
        },
        "chart_theme": "plotly_white"
    }


def show_risk_level_badge(risk_level):
    """显示风险等级徽章"""
    if risk_level == "high":
        return "🔴 高风险"
    elif risk_level == "medium":
        return "🟡 中风险"
    else:
        return "🟢 低风险"


def create_fraud_probability_gauge(fraud_prob):
    """创建舞弊概率仪表盘"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fraud_prob * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "舞弊概率 (%)"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "red" if fraud_prob > 0.6 else "orange" if fraud_prob > 0.3 else "green"},
            'steps': [
                {'range': [0, 30], 'color': "rgba(0,255,0,0.2)"},
                {'range': [30, 60], 'color': "rgba(255,165,0,0.2)"},
                {'range': [60, 100], 'color': "rgba(255,0,0,0.2)"}
            ]
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def create_shap_bar_chart(shap_features):
    """创建 SHAP 特征重要性柱状图"""
    if not shap_features:
        return None

    # 排序并取 Top 10
    sorted_features = sorted(shap_features.items(), key=lambda x: x[1], reverse=True)[:10]
    features = [f[0] for f in sorted_features]
    importance = [f[1] for f in sorted_features]

    fig = px.bar(
        x=importance,
        y=features,
        orientation='h',
        labels={'x': '重要性', 'y': '特征'},
        color=importance,
        color_continuous_scale='Reds'
    )
    fig.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def create_ai_radar_chart(ai_scores):
    """创建 AI 特征雷达图"""
    if not ai_scores:
        return None

    feature_names = {
        "CON_SEM_AI": "语义矛盾度",
        "COV_RISK_AI": "风险披露完整性",
        "TONE_ABN_AI": "异常乐观语调",
        "FIT_TD_AI": "文本-数据一致性",
        "HIDE_REL_AI": "关联隐藏指数",
        "DEN_ABN_AI": "信息密度异常",
        "STR_EVA_AI": "回避表述强度"
    }

    categories = [feature_names.get(k, k) for k in ai_scores.keys()]
    values = list(ai_scores.values())

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
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        height=300,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig


# ================= 顶部导航栏 =================
def render_top_navigation():
    """渲染顶部导航栏 - 包含登录/注册按钮"""
    # 使用 columns 创建顶部栏布局
    col1, col2, col3, col4 = st.columns([5, 2, 1.5, 1.5])

    with col1:
        st.markdown("### 🔍 慧审 - 财务舞弊识别 SaaS 平台")

    with col2:
        if st.session_state.logged_in:
            username = st.session_state.user_info.get('username', '用户')
            membership = st.session_state.user_info.get('membership_level', 'free')
            membership_emoji = {"free": "🆓", "pro": "⭐", "enterprise": "🏢"}
            st.caption(f"👤 {username} | {membership_emoji.get(membership, '🆓')} {membership.upper()}")
        else:
            st.caption("👤 未登录")

    with col3:
        if st.session_state.logged_in:
            # 显示剩余检测次数
            remaining = st.session_state.user_info.get('free_detections_remaining')
            if remaining and remaining > 0:
                st.caption(f"🔢 剩余 {remaining} 次检测")
            elif remaining == -1 or remaining is None:
                st.caption("🔢 无限次检测")

    with col4:
        if st.session_state.logged_in:
            if st.button("🚪 退出", use_container_width=True, key="top_logout"):
                # 清除持久化登录信息
                AuthManager.clear_auth()

                st.session_state.logged_in = False
                st.session_state.token = None
                st.session_state.user_info = None
                st.rerun()
        else:
            if st.button("🔐 登录 / 注册", use_container_width=True, type="primary", key="top_login"):
                st.session_state.show_login_modal = True
                st.rerun()

    st.divider()


# ================= 登录弹窗 =================
def render_login_modal():
    """渲染登录/注册弹窗"""
    # 使用 expander 替代 dialog
    with st.expander("🔐 用户登录 / 注册", expanded=True):
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            st.subheader("已有账号？登录")
            login_username = st.text_input("用户名/邮箱/手机号", key="modal_login_username")
            login_password = st.text_input("密码", type="password", key="modal_login_password")

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("登录", use_container_width=True, key="modal_login_btn", type="primary"):
                    if login_username and login_password:
                        result = make_api_request(
                            "/user/login",
                            method="POST",
                            data={"username": login_username, "password": login_password}
                        )

                        if result and "access_token" in result:
                            st.session_state.token = result["access_token"]
                            st.session_state.user_info = result["user"]
                            st.session_state.logged_in = True
                            st.session_state.show_login_modal = False

                            # 持久化登录信息
                            AuthManager.save_auth(result["access_token"], result["user"])

                            st.success("✅ 登录成功！")
                            st.rerun()
                        else:
                            st.error("登录失败，请检查用户名和密码")

        with tab2:
            st.subheader("新用户？注册")
            reg_username = st.text_input("用户名*", key="modal_reg_username")
            reg_email = st.text_input("邮箱", key="modal_reg_email")
            reg_phone = st.text_input("手机号", key="modal_reg_phone")
            reg_password = st.text_input("密码*", type="password", key="modal_reg_password")

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("注册", use_container_width=True, key="modal_register_btn", type="primary"):
                    if reg_username and reg_password:
                        result = make_api_request(
                            "/user/register",
                            method="POST",
                            data={
                                "username": reg_username,
                                "email": reg_email or None,
                                "phone": reg_phone or None,
                                "password": reg_password,
                                "user_type": "individual"
                            }
                        )

                        if result:
                            st.success("✅ 注册成功！请切换到「登录」标签登录")
                        else:
                            st.error("注册失败")

        # 关闭按钮
        if st.button("❌ 关闭", use_container_width=True):
            st.session_state.show_login_modal = False
            st.rerun()




# ================= 侧边栏导航 =================
def render_sidebar():
    """渲染侧边栏导航 - 纯导航菜单"""
    with st.sidebar:
        st.markdown("### 📍 功能导航")
        st.divider()

        # 主导航 - 根据登录状态显示不同选项
        if st.session_state.logged_in:
            menu = st.radio(
                "导航",
                ["🏠 首页", "🔍 舞弊检测", "💬 AI 问答", "📊 我的检测", "📁 报告管理", "💎 会员中心", "⚙️ 账号设置"],
                label_visibility="collapsed"
            )
        else:
            menu = st.radio(
                "导航",
                ["🏠 首页", "💬 AI 问答(预览)", "📋 价格中心", "📖 案例中心"],
                label_visibility="collapsed"
            )

        st.divider()

        # 快捷帮助
        with st.expander("❓ 帮助中心"):
            st.markdown("""
            - [如何使用](#)
            - [常见问题](#)
            - [联系客服](#)
            """)

        return menu


# ================= 首页 =================
def render_home():
    """渲染首页"""
    st.title("🔍 财务舞弊识别 SaaS 平台")
    st.subheader("基于生成式 AI 的上市公司财务舞弊智能识别系统")

    # Hero Section
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ### 核心功能

        - **📊 双模输入分析**: 结构化财务数据 + MD&A 非结构化文本
        - **🤖 AI 可解释性**: SHAP 特征重要性分析，解决"黑箱"问题
        - **🏷️ 风险标签可视化**: 自动生成"存贷双高"等可读性强的风险标签
        - **💬 AI 智能问答**: 财务舞弊理论、案例解析、实操指导

        ### 适用场景

        | 用户类型 | 应用场景 |
        |---------|---------|
        | 监管机构 | 非现场监管、风险预警 |
        | 会计师事务所 | 审计辅助分析 |
        | 投资者 | 个股风险检测、投资标的筛查 |
        | 上市公司 | 财务舞弊自查、信息披露优化 |
        """)

    with col2:
        st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400", caption="AI 驱动的财务分析")

    st.divider()

    # 经典案例展示
    st.subheader("📚 经典案例库")

    # 获取预设案例(使用缓存)
    cases = get_cached_demo_cases(featured_only=True, _token=st.session_state.token)

    if cases:
        cols = st.columns(min(len(cases), 4))
        for idx, case in enumerate(cases[:4]):
            with cols[idx]:
                case_type_emoji = "🔴" if case["case_type"] == "fraud" else "🟢"
                st.markdown(f"### {case_type_emoji} {case['case_name']}")
                st.caption(case.get('description', '')[:50] + "...")

    st.divider()

    # 核心优势
    st.subheader("🌟 核心优势")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AI 识别准确率", "92%+")
        st.caption("基于多模型融合 + SHAP 分析")
    with col2:
        st.metric("已检测企业", "1000+")
        st.caption("涵盖 A 股、港股、中概股")
    with col3:
        st.metric("用户满意度", "96%")
        st.caption("来自会计师事务所和投资机构")


# ================= 舞弊检测页面 =================
def render_detection():
    """渲染舞弊检测页面 - 文件上传为主"""
    st.title("🔍 舞弊检测")

    # 检查登录状态
    if not st.session_state.logged_in:
        st.warning("请先登录以使用检测功能")
        return

    # 初始化上传相关session state
    if 'upload_years' not in st.session_state:
        st.session_state.upload_years = [2023]
    if 'uploaded_files_data' not in st.session_state:
        st.session_state.uploaded_files_data = {}
    if 'parsed_results' not in st.session_state:
        st.session_state.parsed_results = None

    # 选项卡：文件上传 / 预设案例 / 手动录入
    tab1, tab2, tab3 = st.tabs(["📁 文件上传", "📚 内置案例库", "📝 手动录入"])

    # ============ 文件上传标签页(默认)============
    with tab1:
        st.subheader("上传财务文件进行检测")
        st.info("💡 **上传说明**：您可以将多年度财务数据整理在一个Excel/CSV文件中上传（每行一个年度），系统会自动识别各年度数据。也可以只上传结构化财务数据，MD&A文本可在后续补充。")

        # 企业基本信息
        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input("企业名称*", key="upload_company_name",
                                         placeholder="例如：贵州茅台")
        with col2:
            stock_code = st.text_input("证券代码", key="upload_stock_code",
                                       placeholder="例如：600519")

        st.divider()

        # 年份区间设置
        st.subheader("📅 设置数据年份区间")
        col_start, col_end = st.columns(2)
        with col_start:
            start_year = st.number_input("起始年份", min_value=2000, max_value=2025, value=2020, key="start_year")
        with col_end:
            end_year = st.number_input("结束年份", min_value=2000, max_value=2025, value=2023, key="end_year")

        if start_year > end_year:
            st.error("起始年份不能大于结束年份")

        st.divider()

        # 文件上传 - 支持包含多年度数据的单个文件
        st.subheader("📂 上传财务数据文件")
        st.caption("支持上传包含多年度数据的Excel或CSV文件，系统将自动按年份解析")

        uploaded_file = st.file_uploader(
            "📂 上传财务数据文件（可包含多年度数据）",
            type=['xlsx', 'xls', 'csv', 'txt'],
            key="financial_file_uploader",
            accept_multiple_files=False
        )

        # 可选：补充上传MD&A文本
        st.subheader("📝 补充上传MD&A文本（可选）")
        st.caption("如有MD&A管理层讨论文本，可在此上传多个文件以进行文本风险分析")

        mdna_files = st.file_uploader(
            "📂 上传MD&A文本文件（可选，可多选）",
            type=['txt', 'docx', 'doc', 'pdf'],
            key="mdna_file_uploader",
            accept_multiple_files=True
        )

        # 文件预览与解析
        if uploaded_file:
            st.subheader("📋 文件预览与数据确认")

            # 显示上传的文件信息
            st.info(f"📊 上传文件: {uploaded_file.name} | 年份区间: {start_year}-{end_year}")

            # 解析按钮
            if st.button("🔍 解析文件内容", type="secondary", use_container_width=True):
                with st.spinner("正在解析文件，请稍候..."):
                    try:
                        # 读取上传的文件
                        file_content = uploaded_file.getvalue()

                        # 根据文件类型解析
                        if uploaded_file.name.endswith(('.xlsx', '.xls')):
                            import pandas as pd
                            df = pd.read_excel(io.BytesIO(file_content))
                        elif uploaded_file.name.endswith('.csv'):
                            import pandas as pd
                            df = pd.read_csv(io.BytesIO(file_content))
                        elif uploaded_file.name.endswith('.txt'):
                            # 文本文件作为MD&A内容
                            mdna_content = file_content.decode('utf-8', errors='ignore')
                            st.session_state.parsed_results = {
                                "type": "single_mdna",
                                "mdna_text": mdna_content,
                                "year_range": f"{start_year}-{end_year}"
                            }
                            st.success("✅ 文本文件解析成功")
                            st.stop()

                        # 检查是否包含年份列
                        year_col = None
                        for col in df.columns:
                            if str(col).lower() in ['year', '年份', '年度']:
                                year_col = col
                                break

                        # 解析结果
                        results = []
                        if year_col:
                            # 按年份分组
                            for year_val, year_df in df.groupby(year_col):
                                if start_year <= int(year_val) <= end_year:
                                    # 将DataFrame转换为财务数据字典
                                    financial_data = {}
                                    for col in year_df.columns:
                                        if col != year_col:
                                            val = year_df[col].iloc[0] if not year_df[col].empty else 0
                                            try:
                                                financial_data[str(col)] = float(val)
                                            except:
                                                pass
                                    results.append({
                                        "year": int(year_val),
                                        "financial_data": financial_data,
                                        "parsed_success": True
                                    })
                        else:
                            # 没有年份列，将整个文件作为一个年度的数据
                            financial_data = {}
                            for col in df.columns:
                                try:
                                    # 尝试取第一行作为数据
                                    val = df[col].iloc[0] if not df[col].empty else 0
                                    financial_data[str(col)] = float(val)
                                except:
                                    pass
                            # 使用起始年份
                            results.append({
                                "year": start_year,
                                "financial_data": financial_data,
                                "parsed_success": True
                            })

                        # 如果有MD&A文件，读取内容（支持多个文件）
                        mdna_text = ""
                        if mdna_files:
                            mdna_parts = []
                            for i, mdna_f in enumerate(mdna_files):
                                content = mdna_f.getvalue().decode('utf-8', errors='ignore')
                                if content.strip():
                                    mdna_parts.append(f"【MD&A文件{i+1}: {mdna_f.name}】\n{content}")
                            mdna_text = "\n\n---\n\n".join(mdna_parts)

                        # 保存解析结果
                        st.session_state.parsed_results = {
                            "type": "multi_year",
                            "results": results,
                            "year_range": f"{start_year}-{end_year}",
                            "mdna_text": mdna_text
                        }

                        st.success(f"✅ 成功解析 {len(results)} 个年份的数据")
                        st.rerun()

                    except Exception as e:
                        st.error(f"解析失败：{str(e)}")

            # 显示解析结果预览
            if st.session_state.parsed_results:
                parsed = st.session_state.parsed_results

                with st.expander("📊 查看解析结果预览", expanded=True):
                    for r in parsed.get('results', []):
                        year = r.get('year', '-')
                        success = r.get('parsed_success', False)

                        if success:
                            with st.container(border=True):
                                col_info, col_data = st.columns([1, 2])

                                with col_info:
                                    st.success(f"✅ {year}年")

                                with col_data:
                                    # 显示提取的财务数据
                                    financial_data = r.get('financial_data', {})
                                    if financial_data:
                                        st.caption("提取的财务指标：")
                                        data_cols = st.columns(min(len(financial_data), 4))
                                        for idx, (key, val) in enumerate(list(financial_data.items())[:8]):
                                            with data_cols[idx % 4]:
                                                st.metric(key, f"{val:,.0f}")

                                    # 显示MD&A文本预览
                                    mdna_text = parsed.get('mdna_text', '')
                                    if mdna_text:
                                        st.caption(f"📝 MD&A文本: {len(mdna_text)}字符")
                        else:
                            st.error(f"❌ {year}年 解析失败")

        # 批量检测按钮
        st.divider()
        col_detect, col_clear = st.columns([3, 1])

        with col_detect:
            if st.button("🚀 开始批量检测", type="primary", use_container_width=True,
                        disabled=not st.session_state.parsed_results):
                if not company_name:
                    st.error("请输入企业名称")
                else:
                    # 执行多年份检测
                    parsed_results = st.session_state.parsed_results
                    all_yearly_results = []

                    # 显示多年份检测进度
                    total_years = len([r for r in parsed_results.get('results', []) if r.get('parsed_success', False)])
                    progress_text = st.empty()
                    year_progress = st.progress(0)

                    # 获取MD&A文本（从单独上传的文件或解析结果中）
                    mdna_text = parsed_results.get('mdna_text', '')

                    for idx, result in enumerate(parsed_results.get('results', [])):
                        if not result.get('parsed_success', False):
                            continue

                        year = result.get('year')
                        progress_text.markdown(f"📅 **正在分析 {year} 年度数据** ({idx+1}/{total_years})")

                        financial_data = result.get('financial_data', {})

                        # 构建检测数据
                        detection_data = {
                            "company_name": company_name,
                            "stock_code": stock_code or None,
                            "year": year,
                            "financial_data": financial_data,
                            "mdna_text": mdna_text
                        }

                        # 调用检测API(使用120秒超时)
                        detection_result = make_api_request(
                            "/detection/analyze",
                            method="POST",
                            data=detection_data,
                            timeout=120
                        )

                        if detection_result:
                            all_yearly_results.append({
                                "year": year,
                                **detection_result
                            })

                        # 更新进度
                        year_progress.progress((idx + 1) / total_years)

                    progress_text.empty()
                    year_progress.empty()

                    if all_yearly_results:
                        # 保存多年份结果并展示
                        st.session_state.multi_year_results = {
                            "company_name": company_name,
                            "stock_code": stock_code,
                            "yearly_results": all_yearly_results
                        }
                        st.success(f"✅ 完成 {len(all_yearly_results)} 个年度的检测！")
                        render_multi_year_results(st.session_state.multi_year_results)

        with col_clear:
            if st.button("🔄 清空数据", use_container_width=True):
                st.session_state.parsed_results = None
                st.session_state.multi_year_results = None
                st.rerun()

    # ============ 内置案例库标签页 ============
    with tab2:
        st.subheader("选择预设案例")
        st.info("使用经典案例快速体验平台效果")

        cases = make_api_request("/detection/cases")

        if cases:
            # 以卡片形式展示案例
            cols = st.columns(min(len(cases), 3))
            for idx, case in enumerate(cases):
                with cols[idx % 3]:
                    case_type_emoji = "🔴" if case["case_type"] == "fraud" else "🟢"
                    with st.container(border=True):
                        st.markdown(f"### {case_type_emoji} {case['case_name']}")
                        st.caption(case.get('description', ''))

                        if st.button("加载此案例", key=f"load_case_{case['id']}", use_container_width=True):
                            demo_data = make_api_request(f"/detection/cases/{case['id']}/load", method="POST")
                            if demo_data:
                                st.session_state.demo_data = demo_data
                                st.success("案例已加载！请切换到「手动录入」标签查看")

    # ============ 手动录入标签页 ============
    with tab3:
        st.subheader("手动录入企业数据")
        st.info("适用于已有结构化数据的场景")

        # 如果有预设案例数据，自动填充
        if hasattr(st.session_state, 'demo_data') and st.session_state.demo_data:
            default_company = st.session_state.demo_data.get('company_name', '')
            default_stock_code = st.session_state.demo_data.get('stock_code', '')
            default_year = st.session_state.demo_data.get('year', 2022)
            default_financial = st.session_state.demo_data.get('financial_data', {})
            default_mdna = st.session_state.demo_data.get('mdna_text', '')
            demo_case_id = st.session_state.demo_data.get('demo_case_id')
        else:
            default_company = ''
            default_stock_code = ''
            default_year = 2022
            default_financial = {}
            default_mdna = ''
            demo_case_id = None

        col1, col2, col3 = st.columns(3)
        with col1:
            company_name_manual = st.text_input("企业名称*", value=default_company, key="manual_company")
        with col2:
            stock_code_manual = st.text_input("证券代码", value=default_stock_code, key="manual_stock")
        with col3:
            year_manual = st.number_input("年度", min_value=2000, max_value=2025, value=default_year, key="manual_year")

        st.divider()

        # 财务数据录入
        st.subheader("📊 财务数据 (单位：亿元)")

        financial_cols = st.columns(4)
        financial_data_manual = {}

        with financial_cols[0]:
            financial_data_manual["货币资金"] = st.number_input("货币资金", min_value=0.0, value=float(default_financial.get("货币资金", 0))/1000000000 if default_financial.get("货币资金") else 0.0, key="f1")
            financial_data_manual["短期借款"] = st.number_input("短期借款", min_value=0.0, value=float(default_financial.get("短期借款", 0))/1000000000 if default_financial.get("短期借款") else 0.0, key="f2")
            financial_data_manual["存货"] = st.number_input("存货", min_value=0.0, value=float(default_financial.get("存货", 0))/1000000000 if default_financial.get("存货") else 0.0, key="f3")

        with financial_cols[1]:
            financial_data_manual["营业收入"] = st.number_input("营业收入", min_value=0.0, value=float(default_financial.get("营业收入", 0))/1000000000 if default_financial.get("营业收入") else 0.0, key="f4")
            financial_data_manual["净利润"] = st.number_input("净利润", value=float(default_financial.get("净利润", 0))/100000000 if default_financial.get("净利润") else 0.0, key="f5")
            financial_data_manual["总资产"] = st.number_input("总资产", min_value=0.0, value=float(default_financial.get("总资产", 0))/1000000000 if default_financial.get("总资产") else 0.0, key="f6")

        with financial_cols[2]:
            financial_data_manual["经营活动现金流净额"] = st.number_input("经营现金流净额", value=float(default_financial.get("经营活动现金流净额", 0))/1000000000 if default_financial.get("经营活动现金流净额") else 0.0, key="f7")
            financial_data_manual["ROE"] = st.number_input("ROE (%)", min_value=-100.0, max_value=100.0, value=float(default_financial.get("ROE", 0))*100 if default_financial.get("ROE") else 0.0, key="f8") / 100
            financial_data_manual["资产负债率"] = st.number_input("资产负债率 (%)", min_value=0.0, max_value=100.0, value=float(default_financial.get("资产负债率", 0))*100 if default_financial.get("资产负债率") else 0.0, key="f9") / 100

        with financial_cols[3]:
            financial_data_manual["营业收入增长率"] = st.number_input("营收增长率 (%)", min_value=-100.0, max_value=1000.0, value=float(default_financial.get("营业收入增长率", 0))*100 if default_financial.get("营业收入增长率") else 0.0, key="f10") / 100

        st.divider()

        # MD&A 文本录入
        st.subheader("📝 MD&A 文本分析")
        mdna_text_manual = st.text_area(
            "请输入或粘贴 MD&A 章节内容*",
            value=default_mdna,
            height=300,
            placeholder="请粘贴年报中「管理层讨论与分析」章节的内容...",
            key="manual_mdna"
        )

        # 检测按钮
        st.divider()
        if st.button("🚀 开始检测", type="primary", use_container_width=True, key="manual_detect"):
            if not company_name_manual:
                st.error("请输入企业名称")
            elif not mdna_text_manual:
                st.error("请输入 MD&A 文本")
            else:
                detection_data = {
                    "company_name": company_name_manual,
                    "stock_code": stock_code_manual or None,
                    "year": year_manual,
                    "financial_data": financial_data_manual,
                    "mdna_text": mdna_text_manual
                }

                if demo_case_id:
                    detection_data["demo_case_id"] = demo_case_id

                result = run_detection_with_progress(detection_data)

                if result:
                    st.session_state.current_detection = result
                    st.success("检测完成！")
                    render_detection_result(result)
                else:
                    st.error("检测失败，请重试")


def render_multi_year_results(multi_year_data):
    """渲染多年份检测结果"""
    st.divider()
    st.subheader("📊 多年份检测综合报告")

    company_name = multi_year_data.get("company_name", "未命名企业")
    yearly_results = multi_year_data.get("yearly_results", [])

    if not yearly_results:
        st.warning("暂无检测结果")
        return

    # 按年份排序
    yearly_results = sorted(yearly_results, key=lambda x: x.get("year", 0))

    # 概览卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("检测年度数", f"{len(yearly_results)} 年")
    with col2:
        avg_prob = sum(r.get("fraud_probability", 0) for r in yearly_results) / len(yearly_results)
        st.metric("平均舞弊概率", f"{avg_prob:.2%}")
    with col3:
        max_prob = max(r.get("fraud_probability", 0) for r in yearly_results)
        st.metric("最高风险年份", f"{max_prob:.2%}")

    # 趋势分析图表
    st.subheader("📈 风险趋势分析")

    trend_df = pd.DataFrame([
        {
            "年份": r.get("year"),
            "舞弊概率": r.get("fraud_probability", 0) * 100,
            "风险评分": r.get("risk_score", 0)
        }
        for r in yearly_results
    ])

    fig = px.line(
        trend_df,
        x="年份",
        y="舞弊概率",
        markers=True,
        title=f"{company_name} - 舞弊概率趋势",
        range_y=[0, 100]
    )
    fig.update_traces(line_color="red", marker_size=10)
    st.plotly_chart(fig, use_container_width=True)

    # 各年度对比表格
    st.subheader("📋 各年度风险对比")

    comparison_data = []
    for r in yearly_results:
        comparison_data.append({
            "年份": r.get("year", "-"),
            "舞弊概率": f"{r.get('fraud_probability', 0):.2%}",
            "风险等级": show_risk_level_badge(r.get("risk_level", "low")),
            "风险评分": f"{r.get('risk_score', 0):.1f}",
            "风险标签": ", ".join([l.get("label", l) if isinstance(l, dict) else str(l) for l in r.get("risk_labels", [])[:3]])
        })

    st.dataframe(comparison_data, use_container_width=True)

    # 年度详情选择
    st.subheader("🔍 年度详情查看")

    year_options = [r.get("year") for r in yearly_results]
    selected_year = st.selectbox("选择年份查看详细结果", year_options)

    if selected_year:
        selected_result = next((r for r in yearly_results if r.get("year") == selected_year), None)
        if selected_result:
            render_detection_result(selected_result, show_divider=False)

    # 批量生成报告
    st.divider()
    st.subheader("📄 批量报告生成")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 生成综合报告", use_container_width=True):
            st.info("综合报告生成功能开发中...")
    with col2:
        if st.button("📥 导出所有年份数据", use_container_width=True):
            # 导出为CSV
            export_df = pd.DataFrame([
                {
                    "企业名称": company_name,
                    "年份": r.get("year"),
                    "舞弊概率": r.get("fraud_probability", 0),
                    "风险等级": r.get("risk_level", "low"),
                    "风险评分": r.get("risk_score", 0)
                }
                for r in yearly_results
            ])
            csv = export_df.to_csv(index=False)
            st.download_button(
                label="下载CSV",
                data=csv,
                file_name=f"{company_name}_检测数据.csv",
                mime="text/csv"
            )


def render_detection_result(result, show_divider=True):
    """渲染检测结果 - 增强版智能报告"""
    if show_divider:
        st.divider()
    st.subheader(f"📊 智能检测报告 - {result.get('year', '')}年")

    # 获取智能报告详情
    smart_report = None
    if result.get('id'):
        smart_report = make_api_request(f"/detection/{result['id']}/smart-report")

    # ============ 1. 风险概览卡片 ============
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        fraud_prob = result.get("fraud_probability", 0)
        st.metric("舞弊概率", f"{fraud_prob:.2%}")

        # 仪表盘图表
        fig = create_fraud_probability_gauge(fraud_prob)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        risk_level = result.get("risk_level", "low")
        st.metric("风险等级", show_risk_level_badge(risk_level))

        risk_score = result.get("risk_score", 0)
        st.metric("风险评分", f"{risk_score:.1f}")

    with col3:
        # IPO对标信息
        if smart_report and smart_report.get('ipo_comparison', {}).get('similar_cases'):
            similar_count = len(smart_report['ipo_comparison']['similar_cases'])
            st.metric("相似被否案例", f"{similar_count}家")
            top_similarity = smart_report['ipo_comparison']['comparison_summary'].get('highest_similarity', 0)
            st.caption(f"最高相似度: {top_similarity:.1%}")
        else:
            st.metric("相似被否案例", "0家")
            st.caption("无显著相似")

    with col4:
        # 整改任务数
        if smart_report and smart_report.get('remediation_plan', {}).get('summary'):
            total_tasks = smart_report['remediation_plan']['summary'].get('total_risks', 0)
            st.metric("需整改风险", f"{total_tasks}项")
            high_priority = smart_report['remediation_plan']['summary'].get('high_priority', 0)
            if high_priority > 0:
                st.caption(f"⚠️ 高优先级: {high_priority}项")
        else:
            risk_labels = result.get("risk_labels", [])
            st.metric("风险标签", f"{len(risk_labels)}个")

    # ============ 2. AI特征雷达图 ============
    st.divider()
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("🤖 AI风险特征雷达图")
        ai_scores = result.get("ai_feature_scores", {})

        if ai_scores:
            fig = create_ai_radar_chart(ai_scores)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # 显示雷达图自动分析解读
            radar_analysis = result.get("radar_analysis")
            if radar_analysis:
                with st.expander("📊 雷达图智能分析解读", expanded=True):
                    st.markdown(radar_analysis.get("summary", ""))
                    if radar_analysis.get("details"):
                        st.markdown(radar_analysis["details"])
                    if radar_analysis.get("recommendations"):
                        st.info(radar_analysis["recommendations"])

    with col_chart2:
        st.subheader("🔬 SHAP特征重要性")
        shap_features = result.get("shap_features", {})

        if shap_features:
            # 显示TOP5特征 - 使用绝对值作为进度条，保留正负号显示
            sorted_features = sorted(shap_features.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            for feature, importance in sorted_features:
                # 使用绝对值作为进度条显示，但文本显示正负号
                abs_importance = abs(importance)
                display_value = min(abs_importance * 2, 1.0)  # 放大2倍以便显示，最大1.0
                direction = "📈" if importance > 0 else "📉"
                feature_names = {
                    "CON_SEM_AI": "语义矛盾度",
                    "COV_RISK_AI": "风险披露完整性",
                    "TONE_ABN_AI": "异常乐观语调",
                    "FIT_TD_AI": "文本-数据一致性",
                    "HIDE_REL_AI": "关联隐藏指数",
                    "DEN_ABN_AI": "信息密度异常",
                    "STR_EVA_AI": "回避表述强度"
                }
                feature_name = feature_names.get(feature, feature)
                st.progress(display_value, text=f"{direction} {feature_name}: {importance:+.4f}")

            # 显示SHAP分析解读
            shap_analysis = result.get("shap_analysis")
            if shap_analysis:
                with st.expander("🔍 SHAP分析解读", expanded=True):
                    summary = shap_analysis.get("summary", "")
                    if summary:
                        st.markdown(summary)

                    # 显示详细解读
                    details = shap_analysis.get("details", "")
                    if details:
                        st.markdown("---")
                        st.markdown(details)

                    # 显示结论
                    conclusion = shap_analysis.get("conclusion", "")
                    if conclusion:
                        st.markdown("---")
                        st.success(conclusion)

                    # 显示净效应
                    net_effect = shap_analysis.get("net_effect")
                    if net_effect is not None:
                        st.caption(f"**净效应值**: {net_effect:+.4f} (正值表示整体风险偏高)")
            else:
                # 简单的默认解读
                with st.expander("🔍 SHAP分析解读", expanded=False):
                    st.markdown("**SHAP分析说明：**")
                    st.markdown("- 📈 正值表示该特征推高了舞弊概率判断")
                    st.markdown("- 📉 负值表示该特征降低了舞弊概率判断")
                    st.markdown("- 绝对值越大，该特征对模型决策的影响越大")

    # ============ 3. 风险证据定位(增强版) ============
    # 从结果中直接获取风险证据(后端现在直接返回)
    risk_evidences = result.get('risk_evidence_locations', [])
    if not risk_evidences and smart_report and smart_report.get('evidence_analysis', {}).get('risk_evidence_locations'):
        risk_evidences = smart_report['evidence_analysis']['risk_evidence_locations']

    if risk_evidences:
        st.divider()
        st.subheader("📍 风险证据定位 - 从几百页材料中找出的可疑之处")
        st.caption(f"共发现 **{len(risk_evidences)}** 处风险证据")

        for i, evidence in enumerate(risk_evidences[:6]):  # 显示前6个证据
            feature_name = evidence.get('feature_name', evidence.get('feature_code', '未知特征'))
            category_name = evidence.get('category_name', '风险证据')
            location = evidence.get('location', '未知位置')

            with st.expander(f"🔍 {category_name} - {feature_name}"):
                col_e1, col_e2 = st.columns([3, 1])
                with col_e1:
                    # 显示"为什么选择这一项"
                    st.markdown("**🎯 为什么选择这一项？**")
                    why_selected = evidence.get('why_selected', 'AI模型检测到该特征存在异常信号')
                    st.markdown(f"> {why_selected}")

                    # 显示"风险在哪里"
                    st.markdown("**📍 风险在哪里？**")
                    where_risk = evidence.get('where_is_risk', '需进一步核查')
                    st.markdown(f"> {where_risk}")

                    # 显示文本片段
                    if evidence.get('text_snippet'):
                        st.markdown("**📝 相关文本片段：**")
                        st.markdown(f"> {evidence.get('text_snippet', '')[:400]}...")

                with col_e2:
                    score = evidence.get('score', 0)
                    st.metric('AI评分', f'{score:.2f}')

                    # 显示影响方向（根据AI评分）
                    if score > 0.6:
                        st.caption('📈 推高风险')
                    elif score > 0.4:
                        st.caption('⚡ 风险中等')
                    else:
                        st.caption('➖ 影响中性')

                    if score >= 0.7:
                        st.error("⚠️ 高风险")
                    elif score >= 0.5:
                        st.warning("⚡ 中风险")
                    else:
                        st.info("ℹ️ 低风险")

                # 显示详细分析(如果有)
                detailed = evidence.get('detailed_analysis', {})
                if detailed:
                    st.markdown("**🔎 深度分析：**")
                    st.markdown(detailed.get('detailed_explanation', ''))

                    # 显示相关特征分析
                    related = detailed.get('related_features_analysis', [])
                    if related:
                        st.markdown("**📊 相关特征：**")
                        for rf in related[:3]:
                            level_emoji = "🔴" if rf.get('risk_level') == '高风险' else "🟡" if rf.get('risk_level') == '中等风险' else "🟢"
                            st.markdown(f"{level_emoji} {rf.get('feature', '')}: {rf.get('score', 0):.2f} ({rf.get('risk_level', '')})")

    # ============ 4. 可疑文本片段高亮(新增) ============
    if smart_report and smart_report.get('evidence_analysis', {}).get('suspicious_segments'):
        st.divider()
        st.subheader("🚨 可疑文本片段 - 高亮显示")

        segments = smart_report['evidence_analysis']['suspicious_segments']

        for i, seg in enumerate(segments[:3]):  # 显示前3个
            confidence = seg.get('confidence', 0)
            confidence_color = "🔴" if confidence > 0.7 else "🟡" if confidence > 0.5 else "🟢"

            with st.container(border=True):
                col_s1, col_s2 = st.columns([4, 1])
                with col_s1:
                    st.markdown(f"{confidence_color} **{seg.get('risk_type', '未知风险')}**")
                    st.caption(f"📍 位置: {seg.get('location', '未知')}")
                with col_s2:
                    st.metric("置信度", f"{confidence:.1%}")

                # 高亮显示原文
                if seg.get('text'):
                    st.markdown("**原文片段：**")
                    st.markdown(f"```\n{seg.get('text')[:500]}\n```")

    # ============ 5. 过会风险对标(新增) ============
    if smart_report and smart_report.get('ipo_comparison', {}).get('similar_cases'):
        st.divider()
        st.subheader("⚖️ 过会风险对标 - 与近三年被否IPO案例比对")

        comparison = smart_report['ipo_comparison']
        summary = comparison.get('comparison_summary', {})

        # 对标摘要
        if summary.get('has_similar_cases'):
            st.warning(f"⚠️ 发现与 **{summary.get('most_similar_case')}** 存在相似风险特征，相似度 **{summary.get('highest_similarity', 0):.1%}**")

            if summary.get('common_risk_features'):
                st.caption(f"共性风险: {', '.join(summary['common_risk_features'])}")

        # 相似案例列表
        similar_cases = comparison.get('similar_cases', [])
        if similar_cases:
            st.markdown("**相似被否案例详情：**")

            for case in similar_cases[:3]:  # 显示前3个
                similarity = case.get('similarity', 0)
                similarity_color = "🔴" if similarity > 0.7 else "🟡" if similarity > 0.5 else "🟢"

                with st.container(border=True):
                    col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
                    with col_c1:
                        st.markdown(f"{similarity_color} **{case.get('company_name', '未知')}**")
                        st.caption(f"被否日期: {case.get('rejected_date', '未知')}")
                    with col_c2:
                        matched = case.get('matched_features', [])
                        if matched:
                            st.caption(f"匹配特征: {', '.join([f.get('feature_name', '') for f in matched[:2]])}")
                    with col_c3:
                        st.metric("相似度", f"{similarity:.1%}")

                    # 被否原因
                    if case.get('rejection_reason'):
                        st.markdown(f"📋 **被否原因:** {case.get('rejection_reason')[:200]}...")

    # ============ 6. 整改建议引擎(新增) ============
    if smart_report and smart_report.get('remediation_plan', {}).get('remediation_plans'):
        st.divider()
        st.subheader("✅ 整改建议引擎 - 可执行的操作指引")

        remediation = smart_report['remediation_plan']
        summary = remediation.get('summary', {})

        # 整改摘要
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("需整改风险", f"{summary.get('total_risks', 0)}项")
        with col_r2:
            st.metric("高优先级", f"{summary.get('high_priority', 0)}项")
        with col_r3:
            st.metric("预计完成", f"{summary.get('total_estimated_days', 0)}天")

        # 优先行动清单
        prioritized = remediation.get('prioritized_actions', [])
        if prioritized:
            st.markdown("**📋 优先行动清单：**")
            for i, action in enumerate(prioritized[:5]):
                priority_icon = "🔴" if action.get('priority') == 'high' else "🟡" if action.get('priority') == 'medium' else "🟢"
                with st.container():
                    st.markdown(f"{i+1}. {priority_icon} **{action.get('action', '')}**")
                    st.caption(f"责任部门: {action.get('responsible', '未知')} | 时限: {action.get('timeline', '待定')}")

        # 详细整改方案
        st.markdown("**📑 详细整改方案：**")
        plans = remediation.get('remediation_plans', [])

        for plan in plans:
            risk_level = plan.get('risk_level', 'low')
            risk_icon = "🔴" if risk_level == 'high' else "🟡" if risk_level == 'medium' else "🟢"

            with st.expander(f"{risk_icon} {plan.get('title', '未知整改方案')}"):
                st.markdown(f"**问题描述:** {plan.get('description', '')}")

                # 行动步骤
                actions = plan.get('actions', [])
                if actions:
                    st.markdown("**行动步骤：**")
                    for action in actions:
                        step_icon = "✅" if action.get('priority') == 'high' else "⬜"
                        st.markdown(f"{step_icon} **第{action.get('step')}步** - {action.get('action')}")
                        st.caption(f"责任人: {action.get('responsible')} | 交付物: {action.get('deliverable')} | 时限: {action.get('timeline')}")

                # 参考法规
                regulations = plan.get('regulations', [])
                if regulations:
                    st.markdown("**📚 参考法规：**")
                    for reg in regulations:
                        st.caption(f"• {reg.get('name')} - {reg.get('article')}")

    # ============ 7. 报告生成按钮 ============
    st.divider()
    st.subheader("📄 报告导出")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 生成基础报告", use_container_width=True, key=f"basic_report_{result.get('id', 0)}"):
            with st.spinner("🔄 正在生成报告，请稍候..."):
                report_result = make_api_request(f"/report/{result['id']}/generate", method="POST")
            if report_result:
                st.success("✅ 报告生成成功！")
                st.balloons()
    with col2:
        if st.button("📄 生成专业报告", use_container_width=True, key=f"pro_report_{result.get('id', 0)}"):
            with st.spinner("🔄 正在生成专业报告，请稍候..."):
                report_result = make_api_request(f"/report/{result['id']}/generate", method="POST", data={"report_type": "professional"})
            if report_result:
                st.success("✅ 专业报告生成成功！")
                st.balloons()
    with col3:
        if st.button("📄 生成完整智能报告", use_container_width=True, type="primary", key=f"smart_report_{result.get('id', 0)}"):
            # 导出包含所有智能分析的报告
            st.info("完整智能报告功能开发中...")


# ================= AI 问答页面 =================
def render_qa():
    """渲染 AI 问答页面 - 支持流式输出"""
    st.title("💬 AI 智能问答")
    st.subheader("财务舞弊领域专业问答助手")

    # 检查登录状态
    if not st.session_state.logged_in:
        st.info("💡 AI 问答功能仅对登录用户开放")
        st.divider()
        render_login_register()
        return

    # 初始化流式输出相关状态
    if 'streaming_answer' not in st.session_state:
        st.session_state.streaming_answer = ""
    if 'is_streaming' not in st.session_state:
        st.session_state.is_streaming = False

    # 获取推荐问题
    suggestions = make_api_request("/qa/suggestions")

    # 侧边栏显示推荐问题
    with st.sidebar:
        st.subheader("💡 推荐问题")
        if suggestions:
            for cat in suggestions:
                with st.expander(cat["category"]):
                    for q in cat["questions"]:
                        if st.button(q, key=f"sug_{q[:20]}"):
                            st.session_state.selected_question = q

    # 显示历史消息
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 显示用户消息
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 流式输出回答
        with st.chat_message("assistant"):
            # 创建占位符用于流式显示
            answer_placeholder = st.empty()

            # 使用流式API
            try:
                import requests

                url = f"{API_BASE_URL}/qa/ask-stream"
                headers = {
                    "Authorization": f"Bearer {st.session_state.token}",
                    "Content-Type": "application/json"
                }
                data = {"question": prompt}

                # 发送流式请求
                response = requests.post(url, json=data, headers=headers, stream=True, timeout=60)

                if response.status_code == 200:
                    full_answer = ""

                    # 逐行读取 SSE 流
                    for line in response.iter_lines(decode_unicode=True):
                        if not line:
                            continue

                        # 解析 SSE 数据行
                        if line.startswith("data: "):
                            data_str = line[6:]  # 去掉 "data: " 前缀

                            try:
                                event_data = json.loads(data_str)

                                # 处理内容块
                                if "content" in event_data:
                                    content = event_data["content"]
                                    full_answer += content
                                    # 实时更新显示
                                    answer_placeholder.markdown(full_answer + "▌")

                                # 处理完成标记
                                elif event_data.get("done"):
                                    break

                                # 处理错误
                                elif "error" in event_data:
                                    st.error(f"流式输出错误: {event_data['error']}")
                                    break

                            except json.JSONDecodeError:
                                continue

                    # 最终显示(去掉光标)
                    answer_placeholder.markdown(full_answer)

                    # 保存到历史记录
                    st.session_state.chat_history.append({"role": "assistant", "content": full_answer})

                else:
                    # 流式API失败，回退到非流式API
                    result = make_api_request("/qa/ask", method="POST", data={"question": prompt})
                    if result and "answer" in result:
                        answer = result["answer"]
                        answer_placeholder.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    else:
                        answer_placeholder.error("回答失败，请稍后重试")

            except Exception as e:
                # 异常时回退到非流式API
                result = make_api_request("/qa/ask", method="POST", data={"question": prompt})
                if result and "answer" in result:
                    answer = result["answer"]
                    answer_placeholder.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                else:
                    answer_placeholder.error(f"回答失败: {str(e)}")


# ================= 我的检测页面 =================
def render_my_detections():
    """渲染「我的检测」页面"""
    st.title("📊 我的检测")

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    # 获取检测历史(使用缓存)
    with st.spinner("加载中..."):
        history = get_cached_detection_history(st.session_state.token)

    # 刷新按钮
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 刷新", key="refresh_history"):
            # 清除缓存并重新加载
            get_cached_detection_history.clear()
            st.rerun()

    if history:
        # 表格展示
        df = pd.DataFrame(history)

        # 格式化显示
        display_data = []
        for _, row in df.iterrows():
            display_data.append({
                "企业名称": row.get("company_name", ""),
                "证券代码": row.get("stock_code", "-"),
                "年度": row.get("year", "-"),
                "舞弊概率": f"{row.get('fraud_probability', 0)*100:.1f}%",
                "风险等级": show_risk_level_badge(row.get("risk_level", "low")),
                "检测时间": row.get("created_at", "")[:10]
            })

        st.dataframe(display_data, use_container_width=True)

        # 点击查看详情
        if len(df) > 0:
            selected_company = st.selectbox("查看检测详情", df["company_name"].tolist())
            if selected_company:
                detection = df[df["company_name"] == selected_company].iloc[0].to_dict()
                render_detection_result(detection)
    else:
        st.info("暂无检测记录，快去试试吧！")


# ================= 会员中心页面 =================
def render_membership():
    """渲染会员中心页面"""
    st.title("💎 会员中心")

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    user = st.session_state.user_info
    membership = user.get("membership_level", "free")

    # 当前会员状态
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("当前会员状态")
        membership_emoji = {"free": "🆓", "pro": "⭐", "enterprise": "🏢"}
        st.metric("会员等级", f"{membership_emoji.get(membership, '🆓')} {membership.upper()}")

        remaining = user.get('free_detections_remaining')
        if remaining and remaining > 0:
            st.metric("剩余检测次数", remaining)
        else:
            st.metric("检测次数", "无限")

    with col2:
        st.subheader("会员权益")
        if membership == "free":
            st.markdown("""
            - ✅ 基础检测 3 次/月
            - ✅ AI 问答 5 次/天
            - ❌ 报告导出
            - ❌ 批量检测
            """)
        elif membership == "pro":
            st.markdown("""
            - ✅ 无限次检测
            - ✅ AI 问答 50 次/天
            - ✅ PDF/HTML 报告导出
            - ✅ SHAP 特征分析
            """)
        else:
            st.markdown("""
            - ✅ 专业版全部权益
            - ✅ 批量检测(100 家/次)
            - ✅ API 接口调用
            - ✅ 专属客服
            """)

    st.divider()

    # 套餐选择
    st.subheader("套餐选择")

    # 获取会员套餐(使用缓存)
    plans = get_cached_membership_plans(_token=st.session_state.token)

    if plans:
        cols = st.columns(3)
        for idx, plan in enumerate(plans):
            with cols[idx]:
                st.markdown(f"### {plan['name']}")
                st.markdown(f"## ¥{plan['price']}")
                st.caption(f"¥{plan['price']/plan['duration_days']*30:.0f}/月")

                st.markdown("**权益包括:**")
                for benefit in plan.get("benefits", []):
                    st.markdown(f"- {benefit}")

                if st.button(f"选择{plan['name']}", use_container_width=True, key=f"plan_{plan['plan_type']}"):
                    # 创建订阅订单
                    result = make_api_request(
                        f"/order/subscribe/{plan['plan_type']}",
                        method="POST"
                    )
                    if result:
                        st.success(f"订单创建成功！订单号：{result['order_no']}")

                        # 支付方式选择
                        payment_method = st.selectbox("选择支付方式", ["支付宝", "微信支付"])
                        if st.button("立即支付"):
                            st.info("支付功能开发中...")


# ================= 报告管理页面 =================
def render_report_management():
    """渲染报告管理页面"""
    st.title("📁 报告管理")

    if not st.session_state.logged_in:
        st.warning("请先登录以查看报告")
        return

    # 获取检测历史和报告列表
    # 构建认证headers
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    
    history = cached_api_request("/detection/history", headers=headers, cache_ttl=300) or []
    reports = cached_api_request("/report/list", headers=headers, cache_ttl=300) or []
    
    # 创建报告查找字典 (detection_id -> report_info)
    report_map = {r.get('record_id'): r for r in reports if r.get('record_id')}
    
    # 调试信息
    if st.checkbox("显示调试信息", key="debug_report"):
        st.write(f"检测历史数量: {len(history)}")
        st.write(f"报告列表数量: {len(reports)}")
        st.write(f"报告映射: {report_map}")

    if not history and not reports:
        st.info("暂无报告，请先进行检测或生成报告")
        return

    # 报告筛选
    st.subheader("📋 报告筛选")
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_company = st.text_input("搜索企业名称", placeholder="输入企业名称...")
    with col2:
        risk_levels = ["全部", "高风险", "中风险", "低风险"]
        filter_risk = st.selectbox("风险等级", risk_levels)
    with col3:
        sort_by = st.selectbox("排序方式", ["最新优先", "最早优先", "风险从高到低", "风险从低到高"])

    # 过滤和排序
    filtered_history = history
    if filter_company:
        filtered_history = [h for h in filtered_history if filter_company.lower() in h.get("company_name", "").lower()]

    if filter_risk != "全部":
        risk_map = {"高风险": "high", "中风险": "medium", "低风险": "low"}
        filtered_history = [h for h in filtered_history if h.get("risk_level") == risk_map.get(filter_risk)]

    # 排序
    if sort_by == "最新优先":
        filtered_history = sorted(filtered_history, key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort_by == "最早优先":
        filtered_history = sorted(filtered_history, key=lambda x: x.get("created_at", ""))
    elif sort_by == "风险从高到低":
        filtered_history = sorted(filtered_history, key=lambda x: x.get("fraud_probability", 0), reverse=True)
    elif sort_by == "风险从低到高":
        filtered_history = sorted(filtered_history, key=lambda x: x.get("fraud_probability", 0))

    st.divider()

    # 批量操作
    st.subheader("📊 报告列表")

    if st.session_state.get("selected_reports") is None:
        st.session_state.selected_reports = set()

    # 报告列表
    for report in filtered_history[:20]:  # 限制显示前20条
        risk_level = report.get("risk_level", "low")
        risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk_level, "🟢")

        with st.container(border=True):
            cols = st.columns([0.5, 3, 1.5, 1.5, 1.5])

            with cols[0]:
                is_selected = report["id"] in st.session_state.selected_reports
                if st.checkbox("", value=is_selected, key=f"select_{report['id']}"):
                    st.session_state.selected_reports.add(report["id"])
                else:
                    st.session_state.selected_reports.discard(report["id"])

            with cols[1]:
                st.markdown(f"**{report.get('company_name', '未命名')}**")
                st.caption(f"{report.get('stock_code', '-')} | {report.get('year', '-')}年度")

            with cols[2]:
                fraud_prob = report.get("fraud_probability", 0)
                st.markdown(f"{risk_emoji} {fraud_prob:.1%}")
                st.caption(f"风险评分: {report.get('risk_score', 0):.1f}")

            with cols[3]:
                created = report.get("created_at", "")[:10]
                st.caption(f"检测日期: {created}")

            with cols[4]:
                # 检查是否有已生成的报告
                has_report = report['id'] in report_map
                report_info = report_map.get(report['id'])

                if has_report and report_info:
                    st.success("已生成")
                    if report_info.get('report_type'):
                        st.caption(f"格式: {report_info['report_type'].upper()}")
                else:
                    st.info("未生成")

                col_dl, col_del = st.columns(2)
                with col_dl:
                    # 导出格式选择
                    export_formats = ["PDF", "Word", "Excel"]
                    selected_format = st.selectbox(
                        "格式",
                        export_formats,
                        key=f"format_{report['id']}",
                        label_visibility="collapsed"
                    )
                    format_map = {"PDF": "pdf", "Word": "word", "Excel": "excel"}

                    if st.button("📥", key=f"dl_report_{report['id']}", help=f"下载{selected_format}报告"):
                        with st.spinner(f"生成{selected_format}报告中..."):
                            format_code = format_map[selected_format]
                            # 调用新的导出API
                            result = make_api_request(
                                f"/report/{report['id']}/export?format={format_code}",
                                method="POST"
                            )
                            if result and result.get("download_url"):
                                st.success(f"{selected_format}报告已生成！")
                                # 使用认证下载
                                download_url = f"{API_BASE_URL}{result['download_url']}"
                                filename = result.get("filename", f"报告.{format_code}")
                                download_file_with_auth(download_url, filename, st.session_state.token)
                            else:
                                st.error("生成失败")
                with col_del:
                    if st.button("🗑️", key=f"del_report_{report['id']}", help="删除"):
                        if make_api_request(f"/detection/{report['id']}", method="DELETE"):
                            st.success("已删除")
                            st.rerun()

    # 批量操作栏
    if st.session_state.selected_reports:
        st.divider()
        st.subheader(f"📦 批量操作 (已选择 {len(st.session_state.selected_reports)} 项)")

        col1, col2, col3 = st.columns(3)
        with col1:
            export_format = st.selectbox(
                "导出格式",
                ["PDF", "Excel(汇总)"],
                key="batch_export_format"
            )
            if st.button("📥 批量导出", use_container_width=True):
                if not st.session_state.selected_reports:
                    st.warning("请先选择要导出的报告")
                else:
                    with st.spinner("准备批量导出..."):
                        # 收集选中报告的数据
                        export_data = []
                        for rid in st.session_state.selected_reports:
                            report_detail = make_api_request(f"/detection/{rid}")
                            if report_detail:
                                export_data.append({
                                    "企业名称": report_detail.get("company_name", ""),
                                    "证券代码": report_detail.get("stock_code", ""),
                                    "年度": report_detail.get("year", ""),
                                    "舞弊概率": report_detail.get("fraud_probability", 0),
                                    "风险等级": report_detail.get("risk_level", ""),
                                    "风险评分": report_detail.get("risk_score", 0),
                                    "检测日期": report_detail.get("created_at", "")[:10]
                                })

                        if export_data:
                            import pandas as pd
                            df = pd.DataFrame(export_data)

                            if export_format == "PDF":
                                st.info("批量PDF导出：请逐个下载选中的报告")
                            else:
                                # Excel汇总导出
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 下载汇总Excel",
                                    data=csv,
                                    file_name=f"报告汇总_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv"
                                )
        with col2:
            if st.button("📧 发送邮件", use_container_width=True):
                st.info("邮件发送功能开发中...")
        with col3:
            if st.button("🗑️ 批量删除", use_container_width=True):
                st.warning("确认删除选中的报告？")
                if st.button("确认删除"):
                    for rid in list(st.session_state.selected_reports):
                        make_api_request(f"/detection/{rid}", method="DELETE")
                    st.session_state.selected_reports.clear()
                    st.rerun()


# ================= 账号设置页面 =================
def render_account_settings():
    """渲染账号设置页面"""
    st.title("⚙️ 账号设置")

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    user = st.session_state.user_info

    # 个人信息
    st.subheader("👤 个人信息")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("用户名", value=user.get("username", ""), disabled=True)
            st.text_input("邮箱", value=user.get("email", "") or "未设置")
            st.text_input("手机号", value=user.get("phone", "") or "未设置")
        with col2:
            st.text_input("用户类型", value=user.get("user_type", "individual"))
            st.text_input("注册时间", value=user.get("created_at", "")[:10] if user.get("created_at") else "-")

        if st.button("💾 保存修改", type="primary"):
            st.info("修改功能开发中...")

    # 修改密码
    st.divider()
    st.subheader("🔒 修改密码")
    with st.container(border=True):
        old_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_password = st.text_input("确认新密码", type="password")

        if st.button("🔐 修改密码", type="primary"):
            if new_password != confirm_password:
                st.error("两次输入的新密码不一致")
            elif not old_password or not new_password:
                st.error("请填写所有密码字段")
            else:
                st.info("密码修改功能开发中...")

    # API 密钥管理
    st.divider()
    st.subheader("🔑 API 密钥管理")
    with st.container(border=True):
        st.info("API密钥用于第三方系统调用，请妥善保管。")

        if st.button("🔁 重新生成密钥"):
            st.warning("确定要重新生成API密钥吗？旧的密钥将立即失效。")


# ================= 案例中心页面 =================
def render_case_center():
    """渲染案例中心页面"""
    st.title("📖 案例中心")
    st.subheader("A股历史舞弊案例库")

    # 获取所有案例
    cases = make_api_request("/detection/cases")

    if not cases:
        st.info("暂无案例数据")
        return

    # 案例分类
    case_types = {
        "fraud": "🔴 已确认舞弊案例",
        "normal": "🟢 健康企业案例",
        "warning": "🟡 风险提示案例"
    }

    # 按类型分组
    fraud_cases = [c for c in cases if c.get("case_type") == "fraud"]
    normal_cases = [c for c in cases if c.get("case_type") == "normal"]

    # 舞弊案例
    if fraud_cases:
        st.markdown("### 🔴 已确认舞弊案例")
        cols = st.columns(min(len(fraud_cases), 3))
        for idx, case in enumerate(fraud_cases):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### {case['case_name']}")
                    st.caption(case.get('description', '')[:100])
                    if st.button("查看详情", key=f"case_detail_{case['id']}", use_container_width=True):
                        # 加载案例
                        demo_data = make_api_request(f"/detection/cases/{case['id']}/load", method="POST")
                        if demo_data:
                            st.session_state.demo_data = demo_data
                            st.session_state.active_tab = "内置案例库"
                            st.success("案例已加载！请到「舞弊检测」页面查看")

    # 健康企业案例
    if normal_cases:
        st.divider()
        st.markdown("### 🟢 健康企业案例")
        cols = st.columns(min(len(normal_cases), 3))
        for idx, case in enumerate(normal_cases):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### {case['case_name']}")
                    st.caption(case.get('description', '')[:100])
                    if st.button("查看详情", key=f"case_normal_{case['id']}", use_container_width=True):
                        demo_data = make_api_request(f"/detection/cases/{case['id']}/load", method="POST")
                        if demo_data:
                            st.session_state.demo_data = demo_data
                            st.success("案例已加载！请到「舞弊检测」页面查看")

    # 案例学习资料
    st.divider()
    st.markdown("### 📚 学习资料")

    with st.expander("财务舞弊常见手段"):
        st.markdown("""
        #### 1. 虚增收入
        - 虚构销售合同
        - 提前确认收入
        - 关联方交易非关联化

        #### 2. 虚减成本
        - 少计存货成本
        - 资本化费用化混淆
        - 关联交易转移成本

        #### 3. 资产造假
        - 虚构货币资金
        - 存货虚增
        - 应收账款造假
        """)

    with st.expander("监管处罚案例"):
        st.markdown("""
        - 康美药业 (600518)：存贷双高，虚构货币资金887亿元
        - 瑞幸咖啡 (LK)：虚增收入22亿元
        - 獐子岛 (002069)：存货异常，多次扇贝死亡事件
        """)


# ================= 登录/注册页面 (保留但不在侧边栏显示) =================
def render_login_register():
    """渲染登录/注册页面 - 备用页面"""
    st.title("🔐 用户登录/注册")

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        st.subheader("已有账号？登录")
        login_username = st.text_input("用户名/邮箱/手机号", key="login_username")
        login_password = st.text_input("密码", type="password", key="login_password")

        if st.button("登录", use_container_width=True, key="login_btn"):
            if login_username and login_password:
                result = make_api_request(
                    "/user/login",
                    method="POST",
                    data={"username": login_username, "password": login_password}
                )

                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user_info = result["user"]
                    st.session_state.logged_in = True
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("登录失败，请检查用户名和密码")

    with tab2:
        st.subheader("新用户？注册")
        reg_username = st.text_input("用户名*", key="reg_username")
        reg_email = st.text_input("邮箱", key="reg_email")
        reg_phone = st.text_input("手机号", key="reg_phone")
        reg_password = st.text_input("密码*", type="password", key="reg_password")

        if st.button("注册", use_container_width=True, key="register_btn"):
            if reg_username and reg_password:
                result = make_api_request(
                    "/user/register",
                    method="POST",
                    data={
                        "username": reg_username,
                        "email": reg_email or None,
                        "phone": reg_phone or None,
                        "password": reg_password,
                        "user_type": "individual"
                    }
                )

                if result:
                    st.success("注册成功！请登录")
                else:
                    st.error("注册失败")


# ================= 主程序 =================
def main():
    """主程序"""
    # 初始化 Cookie Manager(必须在所有组件之前)
    cookie_manager = AuthManager.get_cookie_manager_instance()

    # 尝试自动恢复登录状态(仅执行一次)
    if not st.session_state.auth_initialized:
        AuthManager.try_auto_login()
        st.session_state.auth_initialized = True

    # 显示顶部导航栏
    render_top_navigation()

    # 显示登录弹窗(如果需要)
    if st.session_state.get('show_login_modal', False) and not st.session_state.logged_in:
        render_login_modal()

    # 显示侧边栏导航
    menu = render_sidebar()

    # 路由分发
    if st.session_state.logged_in:
        if menu == "🏠 首页":
            render_home()
        elif menu == "🔍 舞弊检测":
            render_detection()
        elif menu == "💬 AI 问答":
            render_qa()
        elif menu == "📊 我的检测":
            render_my_detections()
        elif menu == "📁 报告管理":
            render_report_management()
        elif menu == "💎 会员中心":
            render_membership()
        elif menu == "⚙️ 账号设置":
            render_account_settings()
    else:
        if menu == "🏠 首页":
            render_home()
        elif menu == "💬 AI 问答(预览)":
            render_qa()
        elif menu == "📋 价格中心":
            st.title("📋 价格中心")
            render_membership()
        elif menu == "📖 案例中心":
            render_case_center()


if __name__ == "__main__":
    main()
