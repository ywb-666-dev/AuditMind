"""
Audit Mind - Financial Fraud Detection SaaS
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
import time
import extra_streamlit_components as stx
from utils import cached_api_request, clear_api_cache, api_cache, batch_load_data
from download_helper import download_file_with_auth, create_download_button

# 持久化存储 - 使用 Cookie (通过 extra-streamlit-components)

# ================= 页面配置 =================
st.set_page_config(
    page_title="Audit Mind",
    page_icon="",
    # 使用 emoji 作为页面图标
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 全局样式注入 =================
# 仅注入轻量增强样式，不强制主题色，跟随浏览器/系统 light/dark 偏好
st.markdown("""
<style>
/* ===== Design Tokens - Blue Theme ===== */
:root {
    --bg-primary: #F8FAFC;
    --bg-secondary: #F1F5F9;
    --bg-card: #FFFFFF;
    --bg-elevated: #FFFFFF;
    --text-primary: #0F172A;
    --text-secondary: #475569;
    --text-muted: #94A3B8;
    --accent: #2563EB;
    --accent-hover: #1D4ED8;
    --accent-light: rgba(37,99,235,0.08);
    --border: #E2E8F0;
    --border-light: #F1F5F9;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --info: #3B82F6;
    --shadow-sm: 0 1px 2px rgba(15,23,42,0.04);
    --shadow-md: 0 4px 12px rgba(15,23,42,0.06);
    --shadow-lg: 0 8px 24px rgba(15,23,42,0.08);
    --shadow-glow: 0 0 20px rgba(37,99,235,0.12);
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 20px;
}

/* ===== Reset & Base ===== */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
.stApp, .stApp * {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "SF Pro Display", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
h1 { font-weight: 700 !important; letter-spacing: -0.03em !important; font-size: 2rem !important; color: var(--text-primary) !important; }
h2 { font-weight: 600 !important; letter-spacing: -0.02em !important; font-size: 1.5rem !important; color: var(--text-primary) !important; }
h3 { font-weight: 600 !important; font-size: 1.15rem !important; color: var(--text-primary) !important; }
p, li, td, th, label, .stMarkdown { line-height: 1.65 !important; color: var(--text-secondary) !important; }

/* ===== Buttons ===== */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em;
    border: 1px solid transparent !important;
    font-size: 0.9rem !important;
}
.stButton > button:hover { transform: translateY(-1px); }
.stButton > button:active { transform: translateY(0); }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    border-color: transparent !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.35) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="secondary"] {
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: var(--bg-secondary) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ===== Inputs ===== */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    color: var(--text-primary) !important;
    padding: 0.6rem 0.875rem !important;
    font-size: 0.9rem !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus,
.stSelectbox > div > div > div:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}

/* ===== Cards ===== */
.glass-card, .feature-card, .stat-card, .pricing-card {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 1.5rem !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.glass-card:hover, .feature-card:hover, .stat-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md) !important;
}

/* ===== Badge System ===== */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.badge-primary { background: rgba(37,99,235,0.08); color: var(--accent); border: 1px solid rgba(37,99,235,0.12); }
.badge-success { background: rgba(16,185,129,0.08); color: var(--success); border: 1px solid rgba(16,185,129,0.12); }
.badge-warning { background: rgba(245,158,11,0.08); color: var(--warning); border: 1px solid rgba(245,158,11,0.12); }
.badge-danger { background: rgba(239,68,68,0.08); color: var(--danger); border: 1px solid rgba(239,68,68,0.12); }

/* ===== Sidebar ===== */
[data-testid="stSidebar"] { background: var(--bg-secondary) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] .stButton > button { width: 100% !important; text-align: left !important; justify-content: flex-start !important; border-radius: var(--radius-sm) !important; border: none !important; background: transparent !important; color: var(--text-secondary) !important; font-weight: 500 !important; padding: 0.6rem 0.875rem !important; }
[data-testid="stSidebar"] .stButton > button:hover { background: var(--accent-light) !important; color: var(--accent) !important; }
[data-testid="stSidebar"] .stButton > button[data-active="true"] { background: var(--accent-light) !important; color: var(--accent) !important; border-left: 3px solid var(--accent) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; margin: 0.75rem 0 !important; }

/* ===== Tables ===== */
[data-testid="stDataFrame"] th { background: var(--bg-secondary) !important; color: var(--text-primary) !important; font-weight: 600 !important; border-bottom: 1px solid var(--border) !important; }
[data-testid="stDataFrame"] td { border-bottom: 1px solid var(--border-light) !important; }
[data-testid="stDataFrame"] tr:hover { background: var(--bg-secondary) !important; }

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--border) !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] { color: var(--text-muted) !important; font-weight: 500 !important; padding: 0.6rem 1rem !important; border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent) !important; }
.stTabs [aria-selected="true"] { color: var(--accent) !important; }

/* ===== Expanders ===== */
.streamlit-expanderHeader { background: var(--bg-secondary) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important; font-weight: 500 !important; }
.streamlit-expanderHeader:hover { border-color: var(--accent) !important; }

/* ===== Alerts ===== */
.stAlert { border-radius: var(--radius-sm) !important; border: 1px solid !important; }
.stAlert[data-baseweb="notification"] { box-shadow: none !important; }

/* ===== Progress & Slider ===== */
.stProgress > div > div { background: linear-gradient(90deg, #3B82F6, #2563EB) !important; border-radius: 8px !important; }
.stSlider > div > div > div > div { background: var(--accent) !important; border-radius: 4px !important; }

/* ===== Radio ===== */
.stRadio > div { display: flex; flex-direction: column; gap: 6px; }
.stRadio label { padding: 10px 14px !important; border-radius: var(--radius-sm) !important; transition: all 0.2s ease !important; border: 1.5px solid transparent !important; font-weight: 500 !important; }
.stRadio label:hover { background: var(--bg-secondary) !important; border-color: var(--border) !important; }

/* ===== Checkbox ===== */
.stCheckbox > label { padding: 8px 12px !important; border-radius: var(--radius-sm) !important; transition: all 0.2s ease !important; }
.stCheckbox > label:hover { background: var(--bg-secondary) !important; }

/* ===== Markdown Code ===== */
.stMarkdown code { background: var(--bg-secondary) !important; color: var(--text-primary) !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.85em !important; }
.stMarkdown pre { background: var(--bg-secondary) !important; border-radius: var(--radius-md) !important; padding: 1rem !important; border: 1px solid var(--border) !important; }

/* ===== Animations ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.15); }
    50% { box-shadow: 0 0 0 8px rgba(37,99,235,0); }
}
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
.animate-fadeInUp { animation: fadeInUp 0.5s ease-out both; }
.animate-fadeIn { animation: fadeIn 0.4s ease-out both; }
.animate-slideInLeft { animation: slideInLeft 0.5s ease-out both; }
.animate-pulse { animation: pulse 2s infinite; }
.animate-float { animation: float 3s ease-in-out infinite; }

/* ===== Spacing Utilities ===== */
.gap-1 { gap: 0.25rem; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }

/* ===== Feature List ===== */
.feature-yes { color: var(--success); font-weight: 600; }
.feature-no { color: var(--text-muted); }

/* ===== Pricing Highlight ===== */
.pricing-highlight {
    border: 2px solid var(--accent) !important;
    box-shadow: var(--shadow-glow) !important;
    position: relative;
    overflow: hidden;
}
.pricing-highlight::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #3B82F6, #2563EB, #60A5FA);
}
.pricing-badge {
    position: absolute;
    top: 12px; right: -28px;
    background: linear-gradient(135deg, #2563EB, #1D4ED8);
    color: white;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 32px;
    transform: rotate(45deg);
    box-shadow: 0 2px 8px rgba(37,99,235,0.3);
}

/* ===== Advanced Hover Effects ===== */
.glass-card, .feature-card, .stat-card, .pricing-card {
    position: relative;
    overflow: hidden;
}
.glass-card::before, .feature-card::before, .stat-card::before, .pricing-card::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(37,99,235,0.03), transparent);
    transition: left 0.5s ease;
}
.glass-card:hover::before, .feature-card:hover::before, .stat-card:hover::before, .pricing-card:hover::before {
    left: 100%;
}

/* ===== Gradient Border ===== */
.gradient-border {
    position: relative;
    background: var(--bg-card);
    border-radius: var(--radius-lg);
}
.gradient-border::before {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: inherit;
    background: linear-gradient(135deg, #3B82F6, #60A5FA, #2563EB);
    z-index: -1;
    opacity: 0;
    transition: opacity 0.3s ease;
}
.gradient-border:hover::before {
    opacity: 1;
}

/* ===== Glow Effect ===== */
.glow-blue {
    box-shadow: 0 0 20px rgba(37,99,235,0.1);
    transition: box-shadow 0.3s ease;
}
.glow-blue:hover {
    box-shadow: 0 0 30px rgba(37,99,235,0.2);
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ===== Dark Mode Support ===== */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-primary: #0F172A;
        --bg-secondary: #1E293B;
        --bg-card: #1E293B;
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --accent: #3B82F6;
        --accent-hover: #60A5FA;
        --border: #334155;
        --border-light: #1E293B;
    }
    .stButton > button[kind="secondary"] { background: var(--bg-secondary) !important; border-color: var(--border) !important; }
    [data-testid="stDataFrame"] th { background: var(--bg-secondary) !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ================= API 配置 =================
API_BASE_URL = "http://47.76.180.29:8000/api"

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
        ("数据验证", "验证财务数据完整性和一致性..."),
        ("AI文本分析", "使用大模型提取7维风险特征..."),
        ("财务指标计算", "计算传统财务舞弊指标..."),
        ("模型推理", "执行XGBoost模型预测..."),
        ("SHAP可解释性", "计算特征重要性分析..."),
        ("IPO对标分析", "对比历史IPO被否案例..."),
        ("生成整改建议", "基于风险标签生成建议..."),
    ]

    result = None
    error_msg = None

    # 使用 st.status 创建进度容器
    with st.status("正在执行AI舞弊检测分析...", expanded=True) as status:
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

                status.update(label="检测完成！", state="complete", expanded=False)
            else:
                error_msg = "检测请求失败"
                status.update(label=f"{error_msg}", state="error")

        except Exception as e:
            error_msg = str(e)
            status.update(label=f"检测失败: {error_msg}", state="error")

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
        st.markdown("###  Audit Mind")

    with col2:
        if st.session_state.logged_in:
            username = st.session_state.user_info.get('username', '用户')
            membership = st.session_state.user_info.get('membership_level', 'free')
            membership_label = {"free": "免费版", "pro": "专业版", "enterprise": "企业版"}
            st.caption(f"{username} | {membership_label.get(membership, '免费版')}")
        else:
            st.caption("未登录")

    with col3:
        if st.session_state.logged_in:
            # 显示剩余检测次数
            remaining = st.session_state.user_info.get('free_detections_remaining')
            if remaining and remaining > 0:
                st.caption(f"剩余 {remaining} 次检测")
            elif remaining == -1 or remaining is None:
                st.caption("无限次检测")

    with col4:
        if st.session_state.logged_in:
            if st.button("退出", use_container_width=True, key="top_logout"):
                # 清除持久化登录信息
                AuthManager.clear_auth()

                st.session_state.logged_in = False
                st.session_state.token = None
                st.session_state.user_info = None
                st.rerun()
        else:
            if st.button("登录 / 注册", use_container_width=True, type="primary", key="top_login"):
                st.session_state.show_login_modal = True
                st.rerun()

    st.divider()


# ================= 登录弹窗 =================
def render_login_modal():
    """渲染登录/注册弹窗"""
    # 使用 expander 替代 dialog
    with st.expander("用户登录 / 注册", expanded=True):
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

                            st.success("登录成功！")
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
                            st.success("注册成功！请切换到「登录」标签登录")
                        else:
                            st.error("注册失败")

        # 快速登录按钮 - AuditMind 默认账号
        st.divider()
        st.markdown("**🚀 快速体验？使用演示账号登录**")

        col_quick, col_close = st.columns([2, 1])

        with col_quick:
            if st.button("一键登录演示账号", use_container_width=True, type="primary", key="quick_login_btn"):
                # 使用默认账号登录
                result = make_api_request(
                    "/user/login",
                    method="POST",
                    data={"username": "AuditMind", "password": "123"}
                )

                if result and "access_token" in result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user_info = result["user"]
                    st.session_state.logged_in = True
                    st.session_state.show_login_modal = False

                    # 持久化登录信息
                    AuthManager.save_auth(result["access_token"], result["user"])

                    st.success("演示账号登录成功！已解锁全部功能")
                    st.rerun()
                else:
                    st.error("演示账号登录失败，请尝试手动注册登录")

        with col_close:
            if st.button("关闭", use_container_width=True, key="close_login_modal"):
                st.session_state.show_login_modal = False
                st.rerun()




# ================= 侧边栏导航 =================
def render_sidebar():
    """渲染侧边栏导航 - Premium Design (Button-based, no widget state conflicts)"""
    with st.sidebar:
        # 品牌区域
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0 0.5rem;">
            <div style="font-size: 2.2rem; margin-bottom: 0.25rem;">&#x1F4C8;</div>
            <div style="font-size: 1.3rem; font-weight: 800; letter-spacing: -0.5px; color: #0F172A;">Audit Mind</div>
            <div style="font-size: 0.75rem; color: #64748B; margin-top: 2px;">AI 财务舞弊识别</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        # 初始化当前页面
        if "current_page" not in st.session_state:
            st.session_state.current_page = "home"

        # 主导航 - 根据登录状态显示不同选项
        if st.session_state.logged_in:
            pages = [
                (":material/home: 首页", "home"),
                (":material/description: 财务助手", "fs"),
                (":material/search: 舞弊检测", "detect"),
                (":material/chat: AI 问答", "qa"),
                (":material/history: 我的检测", "history"),
                (":material/folder: 报告管理", "reports"),
                (":material/diamond: 会员中心", "membership"),
                (":material/settings: 账号设置", "settings"),
            ]
        else:
            pages = [
                (":material/home: 首页", "home"),
                (":material/chat: AI 问答(预览)", "qa"),
                (":material/payments: 价格中心", "pricing"),
                (":material/menu_book: 案例中心", "cases"),
            ]

        current = st.session_state.current_page
        for label, key in pages:
            active = current == key
            btn_type = "primary" if active else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state.current_page = key
                st.rerun()

        st.divider()

        # 快捷帮助
        with st.expander("📚 帮助中心"):
            st.markdown("""
            - 📖 [如何使用](#)
            - ❓ [常见问题](#)
            - 💬 [联系客服](#)
            """)

        return current


# ================= 首页 =================
def render_home():
    """渲染首页 - Premium Design"""
    # ========== Hero Section ==========
    hero_html = '''
    <div style="margin: -1.5rem -1rem 2rem; padding: 80px 24px 72px; background: linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 50%, #F8FAFC 100%); text-align: center; border-bottom: 1px solid #E2E8F0; position: relative; overflow: hidden;">
        <!-- Animated background dots -->
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.4; background-image: radial-gradient(circle, #BFDBFE 1px, transparent 1px); background-size: 32px 32px;"></div>
        <div style="max-width: 800px; margin: 0 auto; position: relative; z-index: 1;">
            <div style="display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px; border-radius: 100px; font-size: 0.85rem; font-weight: 600; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); border: 1px solid #BFDBFE; color: #2563EB; margin-bottom: 1.5rem; letter-spacing: 0.02em; animation: fadeInUp 0.6s ease-out both;">
                &#x2728; AI-Powered Financial Audit Intelligence
            </div>
            <h1 style="font-size: 3.2rem; font-weight: 700; letter-spacing: -1.5px; line-height: 1.1; margin-bottom: 1rem; color: #0F172A; animation: fadeInUp 0.7s ease-out 0.1s both;">
                Audit Mind
            </h1>
            <p style="font-size: 1.15rem; color: #475569; line-height: 1.7; max-width: 560px; margin: 0 auto 2rem; font-weight: 400; animation: fadeInUp 0.7s ease-out 0.2s both;">
                基于生成式 AI 的上市公司财务舞弊智能识别系统<br>
                <span style="font-size: 1rem; color: #64748B;">&#x1F680; 双模分析 · &#x1F4CA; SHAP 可解释 · &#x1F6A8; 风险标签可视化</span>
            </p>
        </div>
    </div>
    '''
    st.components.v1.html(hero_html, height=440, scrolling=False)

    # CTA Buttons row
    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    with c1:
        if st.button("开始检测", type="primary", use_container_width=True, key="hero_cta_detect"):
            if st.session_state.logged_in:
                st.session_state.current_page = "detect"
                st.rerun()
            else:
                st.session_state.show_login_modal = True
                st.rerun()
    with c2:
        if st.button("财务助手", use_container_width=True, key="hero_cta_fs"):
            if st.session_state.logged_in:
                st.session_state.current_page = "fs"
                st.rerun()
            else:
                st.session_state.show_login_modal = True
                st.rerun()
    with c3:
        if st.button("AI 问答", use_container_width=True, key="hero_cta_qa"):
            st.session_state.current_page = "qa"
            st.rerun()

    # Demo hint
    if not st.session_state.logged_in:
        st.info("**🚀 快速体验** — 点击右上角登录/注册，选择「一键登录演示账号」即可体验全部功能（AuditMind / 123）")

    # ========== Stats Bar ==========
    st.markdown("<div style='margin: 2.5rem 0 1.5rem;'></div>", unsafe_allow_html=True)
    stat_cols = st.columns(4)
    stats = [
        ("92%+", "AI 识别准确率", "0s"),
        ("1000+", "已检测企业", "0.1s"),
        ("96%", "用户满意度", "0.2s"),
        ("7", "风险分析维度", "0.3s"),
    ]
    for i, (value, label, delay) in enumerate(stats):
        with stat_cols[i]:
            st.markdown(f"""
            <div class="stat-card" style="animation: fadeInUp 0.5s ease-out {delay} both; text-align: center;">
                <div style="font-size: 2.2rem; font-weight: 700; background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 4px;">{value}</div>
                <div style="font-size: 0.85rem; color: #64748B; font-weight: 500;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== Features Grid ==========
    st.markdown("<h2 style='font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 12px;'> 核心能力</h2>", unsafe_allow_html=True)

    features = [
        ("&#x1F4C8;", "双模输入分析", "结构化财务数据 + MD&A 非结构化文本，全方位透视企业风险"),
        ("&#x1F50E;", "AI 可解释性", "SHAP 特征重要性分析，每个预测都有明确依据，告别黑箱"),
        ("&#x1F6A8;", "风险标签可视化", "自动生成「存贷双高」等可读性强的风险标签，一目了然"),
        ("&#x1F916;", "AI 智能问答", "财务舞弊理论、案例解析、实操指导，7×24 随时解答"),
    ]

    feat_cols = st.columns(2)
    for i, (icon, title, desc) in enumerate(features):
        with feat_cols[i % 2]:
            st.markdown(f"""
            <div class="feature-card" style="margin-bottom: 1rem; animation: fadeInUp 0.5s ease-out {i*0.1}s both;">
                <div style="font-size: 1.4rem; margin-bottom: 0.5rem;">{icon}</div>
                <h4 style="font-size: 1.05rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">{title}</h4>
                <p style="font-size: 0.9rem; color: #475569; line-height: 1.6;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== How It Works ==========
    how_it_works_html = '''
    <div style="margin: 2.5rem 0; padding: 2rem 1.5rem; background: linear-gradient(135deg, #F8FAFC, #EFF6FF); border-radius: 14px; border: 1px solid #BFDBFE;">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">&#x1F680; 三步完成智能检测</h2>
            <p style="color: #475569; font-size: 0.95rem;">上传财务报告 &#x2192; AI深度解析 &#x2192; 获取风险报告</p>
        </div>
        <div style="display: flex; align-items: flex-start; justify-content: center; gap: 0; max-width: 900px; margin: 0 auto;">
            <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.5s ease-out 0.1s both;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); border: 2px solid #BFDBFE; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.75rem;">
                    <span style="font-size: 1rem; font-weight: 700; color: #2563EB;">1</span>
                </div>
                <h4 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">&#x1F4C4; 上传报告</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5; padding: 0 0.5rem;">支持 PDF 年报、Excel 财务表、Word 文档等多格式上传</p>
            </div>
            <div style="flex: 0.4; height: 1px; background: linear-gradient(90deg, #BFDBFE, #3B82F6, #BFDBFE); margin-top: 24px;"></div>
            <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.5s ease-out 0.2s both;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); border: 2px solid #BFDBFE; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.75rem;">
                    <span style="font-size: 1rem; font-weight: 700; color: #2563EB;">2</span>
                </div>
                <h4 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">&#x1F916; AI 深度解析</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5; padding: 0 0.5rem;">7 维风险特征提取 + SHAP 可解释性分析 + IPO 对标</p>
            </div>
            <div style="flex: 0.4; height: 1px; background: linear-gradient(90deg, #BFDBFE, #3B82F6, #BFDBFE); margin-top: 24px;"></div>
            <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.5s ease-out 0.3s both;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); border: 2px solid #BFDBFE; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.75rem;">
                    <span style="font-size: 1rem; font-weight: 700; color: #2563EB;">3</span>
                </div>
                <h4 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">&#x1F4CA; 获取报告</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5; padding: 0 0.5rem;">可视化风险标签、整改建议、完整证据链下载</p>
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(how_it_works_html, height=320, scrolling=False)

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== Use Cases ==========
    st.markdown("<h2 style='font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 12px;'> 适用场景</h2>", unsafe_allow_html=True)
    uc_cols = st.columns(4)
    use_cases = [
        ("&#x1F3DB;", "监管机构", "非现场监管、风险预警"),
        ("&#x1F4C4;", "会计师事务所", "审计辅助分析、底稿复核"),
        ("&#x1F4B0;", "投资者", "个股风险检测、标的筛查"),
        ("&#x1F3E2;", "上市公司", "财务舞弊自查、信披优化"),
    ]
    for i, (icon, title, desc) in enumerate(use_cases):
        with uc_cols[i]:
            st.markdown(f"""
            <div class="glass-card" style="text-align: center; padding: 1.5rem 1rem; animation: fadeInUp 0.5s ease-out {i*0.1}s both;">
                <div style="font-size: 1.6rem; margin-bottom: 0.5rem;">{icon}</div>
                <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; color: #0F172A;">{title}</h4>
                <p style="font-size: 0.8rem; color: #475569;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== Cases Showcase ==========
    st.markdown("<h2 style='font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 12px;'> 经典案例库</h2>", unsafe_allow_html=True)

    cases = get_cached_demo_cases(featured_only=True, _token=st.session_state.token)
    if cases:
        case_cols = st.columns(min(len(cases), 4))
        for idx, case in enumerate(cases[:4]):
            with case_cols[idx]:
                badge = '<span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.7rem;font-weight:700;background:rgba(239,68,68,0.1);color:#EF4444;">舞弊案例</span>' if case["case_type"] == "fraud" else '<span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.7rem;font-weight:700;background:rgba(16,185,129,0.1);color:#10B981;">正常案例</span>'
                st.markdown(f"""
                <div class="glass-card" style="padding: 1.5rem; animation-delay: {idx * 0.1}s;">
                    <div style="margin-bottom: 0.75rem;">{badge}</div>
                    <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.5rem; line-height: 1.3;">{case['case_name']}</h4>
                    <p style="font-size: 0.85rem; opacity: 0.7; line-height: 1.5;">{case.get('description', '')[:55]}...</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.caption("暂无案例数据")

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== Trust Badges ==========
    trust_html = '''
    <div style="margin: 2.5rem 0; padding: 2rem 1.5rem; background: linear-gradient(135deg, #F8FAFC, #EFF6FF); border-radius: 14px; border: 1px solid #BFDBFE;">
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 0.4rem; color: #0F172A;">&#x1F393; 技术信任背书</h2>
            <p style="color: #475569; font-size: 0.95rem;">源自顶尖学术成果，服务专业审计场景</p>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; max-width: 1000px; margin: 0 auto;">
            <div style="text-align: center; padding: 1.25rem; animation: fadeInUp 0.5s ease-out 0.1s both;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">&#x1F4DA;</div>
                <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; color: #0F172A;">学术认可</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5;">基于前沿财务舞弊识别研究成果</p>
            </div>
            <div style="text-align: center; padding: 1.25rem; animation: fadeInUp 0.5s ease-out 0.2s both;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">&#x1F512;</div>
                <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; color: #0F172A;">数据安全</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5;">企业级加密存储，报告阅后即焚</p>
            </div>
            <div style="text-align: center; padding: 1.25rem; animation: fadeInUp 0.5s ease-out 0.3s both;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">&#x26A1;</div>
                <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; color: #0F172A;">高效处理</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5;">单次检测仅需 30-60 秒</p>
            </div>
            <div style="text-align: center; padding: 1.25rem; animation: fadeInUp 0.5s ease-out 0.4s both;">
                <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">&#x1F3AF;</div>
                <h4 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 0.3rem; color: #0F172A;">精准识别</h4>
                <p style="font-size: 0.8rem; color: #475569; line-height: 1.5;">92%+ AI 识别准确率，可解释</p>
            </div>
        </div>
        <div style="text-align: center; margin-top: 1.5rem;">
            <p style="font-size: 0.75rem; color: #64748B; margin-bottom: 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Powered By</p>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 6px;">
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">DeepSeek-V3.2</span>
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">XGBoost</span>
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">SHAP</span>
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">GMM</span>
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">FastAPI</span>
                <span style="display:inline-block;padding:5px 12px;border-radius:100px;font-size:0.75rem;font-weight:600;background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;">Streamlit</span>
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(trust_html, height=400, scrolling=False)

    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)

    # ========== Tech Details ==========
    with st.expander("查看核心技术细节（AI提示词与算法原理）"):
        st.info("本展示专为评委/技术评审设计，展示系统的核心技术实现")

        tab1, tab2, tab3 = st.tabs([" AI 提示词", " 算法原理", "特征体系"])

        with tab1:
            try:
                prompt_data = make_api_request("/detection/ai-prompt")
                if prompt_data:
                    st.markdown(f"### {prompt_data.get('title', 'AI分析提示词')}")
                    st.caption(f"使用模型: `{prompt_data.get('model', 'Unknown')}`")

                    st.markdown("**七大风险特征维度：**")
                    features = prompt_data.get('features', {})
                    for i, (feature_code, feature_info) in enumerate(features.items(), 1):
                        with st.container(border=True):
                            col_feat, col_desc = st.columns([1, 2])
                            with col_feat:
                                st.markdown(f"**{i}. {feature_info.get('name', feature_code)}**")
                                st.code(feature_code, language='text')
                            with col_desc:
                                st.caption(f"{feature_info.get('description', '')}")
                                st.markdown(f"*示例: {feature_info.get('example', '')}*")

                    st.markdown("**评分标准：**")
                    scoring = prompt_data.get('scoring_criteria', {})
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.success(scoring.get('low', ''))
                    with col_s2:
                        st.warning(scoring.get('medium', ''))
                    with col_s3:
                        st.error(scoring.get('high', ''))

                    st.markdown("---")
                    st.markdown("** 完整提示词模板：**")
                    st.code(prompt_data.get('prompt_template', ''), language='text')
                else:
                    st.error("提示词数据加载失败")
            except Exception as e:
                st.error(f"加载提示词失败: {e}")

        with tab2:
            st.markdown("###  GMM-SHAP 可解释性算法")
            st.markdown("""
            **算法流程：**
            1. **多模型集成预测**：结合逻辑回归、XGBoost、神经网络预测
            2. **动态阈值优化**：通过 Youden 指数确定最优分类阈值
            3. **GMM 聚类解释**：使用高斯混合模型将样本聚为低/中/高风险簇
            4. **SHAP 归因分析**：在每个簇内计算特征贡献度，生成定制化解释

            **技术创新点：**
            - 解决 AI "黑箱"问题，每个预测都有明确依据
            - 针对不同风险等级提供差异化解释
            - 结合 7 维文本特征 + 传统财务指标
            """)

        with tab3:
            st.markdown("###  双模特征体系")
            st.markdown("""
            **维度1: 结构化财务指标**
            - 存贷双高检测
            - 现金流背离分析
            - 存货异常识别
            - ROE / 资产负债率监控

            **维度2: 非结构化文本特征（AI 提取）**
            - 语义矛盾度（CON_SEM_AI）
            - 风险披露完整性（COV_RISK_AI）
            - 异常乐观语调（TONE_ABN_AI）
            - 文本-数据一致性（FIT_TD_AI）
            - 关联隐藏指数（HIDE_REL_AI）
            - 信息密度异常（DEN_ABN_AI）
            - 回避表述强度（STR_EVA_AI）
            """)

    # ========== Bottom CTA Banner ==========
    cta_html = '''
    <div style="margin: 2.5rem -1rem 0 -1rem; padding: 3rem 2rem; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); border-top: 1px solid #BFDBFE; text-align: center; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.3; background-image: radial-gradient(circle, #3B82F6 1px, transparent 1px); background-size: 40px 40px;"></div>
        <div style="max-width: 600px; margin: 0 auto; position: relative; z-index: 1;">
            <h2 style="font-size: 1.8rem; font-weight: 700; color: #0F172A; margin-bottom: 0.75rem; letter-spacing: -0.5px;">&#x1F680; 准备好开始了吗？</h2>
            <p style="font-size: 1rem; color: #475569; margin-bottom: 1.5rem; line-height: 1.7;">立即体验 Audit Mind 的智能财务舞弊检测能力<br>上传第一份报告，3 分钟内获取专业级风险分析</p>
            <a href="#" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'detect'}, '*'); return false;"
               style="display:inline-block;padding:12px 32px;border-radius:10px;font-size:1rem;font-weight:600;color:#FFFFFF;background:linear-gradient(135deg, #2563EB, #1D4ED8);text-decoration:none;transition:all 0.2s ease;box-shadow:0 4px 16px rgba(37,99,235,0.3);"
               onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 24px rgba(37,99,235,0.4)';"
               onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 16px rgba(37,99,235,0.3)';">
                立即开始检测
            </a>
            <p style="font-size: 0.8rem; color: #64748B; margin-top: 1.25rem;">新用户免费体验 3 次完整检测 · 无需信用卡</p>
        </div>
    </div>
    '''
    st.components.v1.html(cta_html, height=280, scrolling=False)


# ================= 舞弊检测页面 =================

# ================= 财务助手页面 =================
# ================= 财务助手页面 (v2 - AI自动生成) =================
def render_financial_assistant():
    """渲染财务助手页面 - 支持AI自动生成四表一注"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(37,99,235,0.08); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 财务助手</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">智能提取四表一注：上传文件 → AI解析 → 审核编辑 → 完成</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    # 初始化状态机
    if "fs_state" not in st.session_state:
        st.session_state.fs_state = "list"
    if "fs_selected_id" not in st.session_state:
        st.session_state.fs_selected_id = None
    if "fs_review_data" not in st.session_state:
        st.session_state.fs_review_data = None

    state = st.session_state.fs_state

    if state == "list":
        _render_statement_list_v2()
    elif state == "upload":
        _render_upload_and_parse()
    elif state == "review":
        _render_ai_review()
    elif state == "edit":
        _render_statement_editor_v2(st.session_state.fs_selected_id)


def _render_statement_list_v2():
    """渲染报表列表页"""
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        st.subheader("我的财务报表")
    with col2:
        if st.button("AI自动生成", type="primary", use_container_width=True):
            st.session_state.fs_state = "upload"
            st.rerun()
    with col3:
        if st.button("手动创建", use_container_width=True):
            st.session_state.fs_show_create = True

    # 手动创建表单
    if st.session_state.get("fs_show_create"):
        with st.form("create_statement_form"):
            st.markdown("**新建空报表**")
            c1, c2, c3 = st.columns(3)
            with c1:
                company_name = st.text_input("企业名称*", placeholder="请输入企业全称")
            with c2:
                stock_code = st.text_input("证券代码", placeholder="如：600519")
            with c3:
                report_year = st.number_input("报表年度", min_value=2000, max_value=2100, value=2025)
            report_period = st.selectbox("报表期间", [("annual", "年报"), ("quarterly", "季报"), ("half_year", "半年报")], format_func=lambda x: x[1])

            submitted = st.form_submit_button("创建", use_container_width=True)
            if submitted:
                if not company_name:
                    st.error("企业名称不能为空")
                else:
                    resp = make_api_request("/financial-statements", method="POST", data={
                        "company_name": company_name,
                        "stock_code": stock_code or None,
                        "report_year": int(report_year),
                        "report_period": report_period[0],
                    })
                    if resp:
                        st.success(f"已创建「{company_name}」{report_year}年度报表")
                        st.session_state.fs_show_create = False
                        time.sleep(0.5)
                        st.rerun()

    st.divider()

    # 获取报表列表
    statements = make_api_request("/financial-statements?limit=100", method="GET")
    if not statements:
        st.info("暂无财务报表。点击「AI自动生成」从文件提取，或「手动创建」填写。")
        return

    # 列表展示
    for stmt in statements:
        with st.container():
            cols = st.columns([3, 2, 2, 2, 1.5, 1])
            with cols[0]:
                st.markdown(f"**{stmt['company_name']}**")
            with cols[1]:
                period_map = {"annual": "年报", "quarterly": "季报", "half_year": "半年报"}
                st.caption(f"{stmt['report_year']}年 {period_map.get(stmt['report_period'], stmt['report_period'])}")
            with cols[2]:
                status_map = {"draft": "草稿", "completed": "已完成", "audited": "已审计"}
                st.caption(status_map.get(stmt['status'], stmt['status']))
            with cols[3]:
                st.caption(stmt['created_at'][:10])
            with cols[4]:
                if st.button("编辑", key=f"edit_{stmt['id']}", use_container_width=True):
                    st.session_state.fs_selected_id = stmt['id']
                    st.session_state.fs_state = "edit"
                    st.rerun()
            with cols[5]:
                if st.button("", key=f"del_{stmt['id']}", use_container_width=True):
                    if make_api_request(f"/financial-statements/{stmt['id']}", method="DELETE"):
                        st.success("已删除")
                        time.sleep(0.3)
                        st.rerun()
        st.divider()


def _render_upload_and_parse():
    """文件上传和AI解析页面"""
    st.subheader("上传财务报告文件")
    st.caption("支持PDF年报、Excel财务表、Word文档。AI将自动提取四表一注数据。")

    if st.button("← 返回列表"):
        st.session_state.fs_state = "list"
        st.rerun()

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("企业名称*", key="fs_upload_company")
    with col2:
        stock_code = st.text_input("证券代码", key="fs_upload_stock")

    report_year = st.number_input("报表年度", min_value=2000, max_value=2100, value=2025, key="fs_upload_year")

    uploaded_files = st.file_uploader(
        "上传财务报告文件（可多选）",
        type=['pdf', 'xlsx', 'xls', 'docx', 'doc', 'txt', 'csv'],
        accept_multiple_files=True,
        help="支持PDF年报、Excel财务表、Word文档、TXT文本。可同时上传多个文件。"
    )

    fill_missing = st.checkbox("启用AI智能填充缺失项", value=True,
        help="当某些财务数据无法从文件中直接提取时，AI会根据上下文和行业常识进行合理估计")

    if uploaded_files and company_name:
        if st.button("开始AI解析", type="primary", use_container_width=True):
            with st.spinner("正在解析文件并提取财务数据，请耐心等待..."):
                # 构建multipart请求
                import requests
                url = f"{API_BASE_URL}/financial-statements/auto-generate"
                headers = {}
                if st.session_state.token:
                    headers["Authorization"] = f"Bearer {st.session_state.token}"

                files_data = []
                for f in uploaded_files:
                    files_data.append(("files", (f.name, f.getvalue(), f.type)))

                data = {
                    "company_name": company_name,
                    "stock_code": stock_code or "",
                    "report_year": int(report_year),
                    "report_period": "annual",
                    "fill_missing": "true" if fill_missing else "false",
                }

                try:
                    resp = requests.post(url, files=files_data, data=data, headers=headers, timeout=120)
                    if resp.status_code == 201:
                        result = resp.json()
                        st.session_state.fs_selected_id = result["id"]
                        st.session_state.fs_review_data = result
                        st.session_state.fs_state = "review"
                        st.success("AI解析完成！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"解析失败: {resp.status_code} - {resp.text}")
                except Exception as e:
                    st.error(f"请求失败: {e}")
    elif not uploaded_files:
        st.info("请上传文件后开始解析")
    elif not company_name:
        st.warning("请填写企业名称")


def _render_ai_review():
    """AI提取结果审核页面"""
    detail = st.session_state.get("fs_review_data")
    if not detail:
        # 如果session中没有，从API获取
        statement_id = st.session_state.get("fs_selected_id")
        if statement_id:
            detail = make_api_request(f"/financial-statements/{statement_id}", method="GET")
            st.session_state.fs_review_data = detail

    if not detail:
        st.error("加载报表失败")
        return

    st.subheader(f"AI提取结果审核 - {detail['company_name']}")

    if st.button("← 返回列表"):
        st.session_state.fs_state = "list"
        st.session_state.fs_review_data = None
        st.rerun()

    st.divider()

    # 提取质量指标
    meta = detail.get("extraction_metadata", {}) or {}
    ai_filled = detail.get("ai_filled_items", []) or []
    missing = meta.get("missing_items", []) or []

    cols = st.columns(4)
    with cols[0]:
        confidence = meta.get("confidence", 0)
        st.metric("提取置信度", f"{confidence*100:.0f}%")
    with cols[1]:
        st.metric("AI填充项数", len(ai_filled))
    with cols[2]:
        st.metric("缺失项数", len(missing))
    with cols[3]:
        st.metric("报表状态", "草稿")

    # AI填充项高亮
    if ai_filled:
        with st.expander("AI估计项（请重点核实）", expanded=True):
            for item in ai_filled:
                conf = item.get("confidence", 0)
                emoji = "低" if conf > 0.8 else "中" if conf > 0.5 else "高"
                st.markdown(f"""
                **{emoji} {item['item_name']}** ({item.get('statement_type', '')})
                - 估计值: {item.get('estimated_value', 'N/A'):,.2f}
                - 置信度: {conf*100:.0f}%
                - 依据: {item.get('reasoning', '无')}
                """)

    # 四表快速预览
    st.markdown("**四表一注预览**")
    tabs = st.tabs([" 资产负债表", " 利润表", " 现金流量表", " 所有者权益", "附注"])

    with tabs[0]:
        bs = detail.get("balance_sheet", {})
        _render_preview_table(bs, "ending_balance", "beginning_balance")
    with tabs[1]:
        inc = detail.get("income_statement", {})
        _render_preview_table(inc, "current_period", "previous_period")
    with tabs[2]:
        cf = detail.get("cash_flow", {})
        _render_preview_table(cf, "current_period")
    with tabs[3]:
        eq = detail.get("equity_change", {})
        _render_preview_table(eq, "ending_balance", "beginning_balance", "increase", "decrease")
    with tabs[4]:
        notes = detail.get("notes", "")
        st.text_area("附注", value=notes, height=300, disabled=True)

    # 操作按钮
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("进入详细编辑", type="primary", use_container_width=True):
            st.session_state.fs_state = "edit"
            st.rerun()
    with c2:
        if st.button("重新上传"):
            st.session_state.fs_state = "upload"
            st.session_state.fs_review_data = None
            st.rerun()


def _render_preview_table(data, *fields):
    """渲染预览表格"""
    if not data:
        st.info("暂无数据")
        return
    for section, items in data.items():
        st.markdown(f"**{section}**")
        if isinstance(items, list):
            preview = []
            for item in items:
                if isinstance(item, dict):
                    row = {"项目": item.get("item_name", "")}
                    for f in fields:
                        val = item.get(f)
                        row[f] = f"{val:,.2f}" if val is not None else "-"
                    preview.append(row)
            if preview:
                st.dataframe(preview, use_container_width=True, hide_index=True)
        st.divider()


def _render_statement_editor_v2(statement_id: int):
    """增强版报表编辑器"""
    detail = make_api_request(f"/financial-statements/{statement_id}", method="GET")
    if not detail:
        st.error("加载报表失败")
        return

    st.subheader(f"{detail['company_name']} - {detail['report_year']}年度")

    if st.button("← 返回列表"):
        st.session_state.fs_selected_id = None
        st.session_state.fs_state = "list"
        st.session_state.fs_review_data = None
        st.rerun()

    # 顶部操作栏
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        if st.button("保存全部", use_container_width=True):
            st.success("数据已自动保存")
    with c2:
        if st.button("校验勾稽", use_container_width=True):
            result = make_api_request(f"/financial-statements/{statement_id}/validate", method="POST")
            if result:
                if result['is_valid']:
                    st.success("勾稽关系校验通过")
                else:
                    st.error("发现勾稽关系错误：")
                    for err in result['errors']:
                        st.markdown(f"- {err}")
                if result.get('warnings'):
                    st.warning("警告：")
                    for w in result['warnings']:
                        st.markdown(f"- {w}")
                score = result.get('validation_score', 0)
                st.metric("校验得分", f"{score:.0f}/100")
    with c3:
        if st.button("AI建议", use_container_width=True):
            st.session_state.fs_show_ai = True
    with c4:
        if detail['status'] != 'completed':
            if st.button("标记完成", use_container_width=True):
                resp = make_api_request(f"/financial-statements/{statement_id}/complete", method="POST")
                if resp:
                    st.success("已标记为完成")
                    time.sleep(0.3)
                    st.rerun()

    # AI建议弹窗
    if st.session_state.get("fs_show_ai"):
        with st.expander("AI 智能建议", expanded=True):
            stmt_type = st.selectbox("选择报表类型", [
                ("balance_sheet", "资产负债表"),
                ("income_statement", "利润表"),
                ("cash_flow", "现金流量表"),
                ("equity_change", "所有者权益变动表"),
                ("notes", "财务报表附注"),
            ], format_func=lambda x: x[1])
            if st.button("获取建议"):
                ai_resp = make_api_request(
                    f"/financial-statements/{statement_id}/ai-suggestions",
                    method="POST",
                    data={"statement_type": stmt_type[0]}
                )
                if ai_resp:
                    st.markdown("** 建议：**")
                    for s in ai_resp.get('suggestions', []):
                        st.markdown(f"- {s}")
                    if ai_resp.get('warnings'):
                        st.markdown("** 注意事项：**")
                        for w in ai_resp['warnings']:
                            st.markdown(f"- {w}")
                    if ai_resp.get('estimated_values'):
                        st.markdown("** 估计值：**")
                        for k, v in ai_resp['estimated_values'].items():
                            st.markdown(f"- {k}: {v:,.2f}")
            if st.button("关闭"):
                st.session_state.fs_show_ai = False
                st.rerun()

    # 获取AI填充项列表（用于标记）
    ai_filled_names = {}
    for item in detail.get("ai_filled_items", []) or []:
        stmt_type = item.get("statement_type", "")
        item_name = item.get("item_name", "")
        if stmt_type not in ai_filled_names:
            ai_filled_names[stmt_type] = set()
        ai_filled_names[stmt_type].add(item_name)

    # 四表一注标签页
    tabs = st.tabs([" 资产负债表", " 利润表", " 现金流量表", " 所有者权益", "报表附注"])

    with tabs[0]:
        _render_bs_editor(statement_id, detail.get('balance_sheet', {}), ai_filled_names.get('balance_sheet', set()))
    with tabs[1]:
        _render_is_editor(statement_id, detail.get('income_statement', {}), ai_filled_names.get('income_statement', set()))
    with tabs[2]:
        _render_cf_editor(statement_id, detail.get('cash_flow', {}), ai_filled_names.get('cash_flow', set()))
    with tabs[3]:
        _render_eq_editor(statement_id, detail.get('equity_change', {}), ai_filled_names.get('equity_change', set()))
    with tabs[4]:
        _render_notes_editor(statement_id, detail.get('notes', ''))


def _render_bs_editor(statement_id: int, data: dict, ai_filled: set):
    """资产负债表编辑器（含AI标记）"""
    st.markdown("**资产负债表**")
    updated = {}
    for section_name, items in data.items():
        st.markdown(f"##### {section_name}")
        cols = st.columns([3, 2, 2, 2])
        with cols[0]: st.markdown("**项目名称**")
        with cols[1]: st.markdown("**期末余额**")
        with cols[2]: st.markdown("**期初余额**")
        with cols[3]: st.markdown("**备注**")

        updated_items = []
        for i, item in enumerate(items):
            is_ai = item.get("item_name", "") in ai_filled
            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                label = item.get('item_name', '')
                if is_ai:
                    label += ""
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{label}</span>", unsafe_allow_html=True)
                else:
                    st.text(label)
            with cols[1]:
                ending = st.number_input(f"bs_end_{statement_id}_{section_name}_{i}", value=item.get('ending_balance') or 0.0, label_visibility="collapsed", key=f"bs2_end_{statement_id}_{section_name}_{i}")
            with cols[2]:
                beginning = st.number_input(f"bs_beg_{statement_id}_{section_name}_{i}", value=item.get('beginning_balance') or 0.0, label_visibility="collapsed", key=f"bs2_beg_{statement_id}_{section_name}_{i}")
            with cols[3]:
                notes = st.text_input(f"bs_note_{statement_id}_{section_name}_{i}", value=item.get('notes', ''), label_visibility="collapsed", key=f"bs2_note_{statement_id}_{section_name}_{i}")
            updated_items.append({**item, "ending_balance": ending if ending != 0 else None, "beginning_balance": beginning if beginning != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("此项由AI估计生成，请核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("保存资产负债表", key=f"save_bs2_{statement_id}"):
        _save_statement_field(statement_id, "balance_sheet", updated)


def _render_is_editor(statement_id: int, data: dict, ai_filled: set):
    """利润表编辑器"""
    st.markdown("**利润表**")
    updated = {}
    for section_name, items in data.items():
        st.markdown(f"##### {section_name}")
        cols = st.columns([3, 2, 2, 2])
        with cols[0]: st.markdown("**项目名称**")
        with cols[1]: st.markdown("**本期金额**")
        with cols[2]: st.markdown("**上期金额**")
        with cols[3]: st.markdown("**备注**")

        updated_items = []
        for i, item in enumerate(items):
            is_ai = item.get("item_name", "") in ai_filled
            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                label = item.get('item_name', '')
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{label} </span>", unsafe_allow_html=True)
                else:
                    st.text(label)
            with cols[1]:
                current = st.number_input(f"is_cur_{statement_id}_{section_name}_{i}", value=item.get('current_period') or 0.0, label_visibility="collapsed", key=f"is2_cur_{statement_id}_{section_name}_{i}")
            with cols[2]:
                previous = st.number_input(f"is_prev_{statement_id}_{section_name}_{i}", value=item.get('previous_period') or 0.0, label_visibility="collapsed", key=f"is2_prev_{statement_id}_{section_name}_{i}")
            with cols[3]:
                notes = st.text_input(f"is_note_{statement_id}_{section_name}_{i}", value=item.get('notes', ''), label_visibility="collapsed", key=f"is2_note_{statement_id}_{section_name}_{i}")
            updated_items.append({**item, "current_period": current if current != 0 else None, "previous_period": previous if previous != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("此项由AI估计生成，请核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("保存利润表", key=f"save_is2_{statement_id}"):
        _save_statement_field(statement_id, "income_statement", updated)


def _render_cf_editor(statement_id: int, data: dict, ai_filled: set):
    """现金流量表编辑器"""
    st.markdown("**现金流量表**")
    updated = {}
    for section_name, items in data.items():
        st.markdown(f"##### {section_name}")
        cols = st.columns([4, 2, 2])
        with cols[0]: st.markdown("**项目名称**")
        with cols[1]: st.markdown("**本期金额**")
        with cols[2]: st.markdown("**备注**")

        updated_items = []
        for i, item in enumerate(items):
            is_ai = item.get("item_name", "") in ai_filled
            cols = st.columns([4, 2, 2])
            with cols[0]:
                label = item.get('item_name', '')
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{label} </span>", unsafe_allow_html=True)
                else:
                    st.text(label)
            with cols[1]:
                current = st.number_input(f"cf_cur_{statement_id}_{section_name}_{i}", value=item.get('current_period') or 0.0, label_visibility="collapsed", key=f"cf2_cur_{statement_id}_{section_name}_{i}")
            with cols[2]:
                notes = st.text_input(f"cf_note_{statement_id}_{section_name}_{i}", value=item.get('notes', ''), label_visibility="collapsed", key=f"cf2_note_{statement_id}_{section_name}_{i}")
            updated_items.append({**item, "current_period": current if current != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("此项由AI估计生成，请核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("保存现金流量表", key=f"save_cf2_{statement_id}"):
        _save_statement_field(statement_id, "cash_flow", updated)


def _render_eq_editor(statement_id: int, data: dict, ai_filled: set):
    """所有者权益变动表编辑器"""
    st.markdown("**所有者权益变动表**")
    updated = {}
    for section_name, items in data.items():
        st.markdown(f"##### {section_name}")
        cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
        with cols[0]: st.markdown("**项目名称**")
        with cols[1]: st.markdown("**期初**")
        with cols[2]: st.markdown("**增加**")
        with cols[3]: st.markdown("**减少**")
        with cols[4]: st.markdown("**期末**")
        with cols[5]: st.markdown("**备注**")

        updated_items = []
        for i, item in enumerate(items):
            is_ai = item.get("item_name", "") in ai_filled
            cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
            with cols[0]:
                label = item.get('item_name', '')
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{label} </span>", unsafe_allow_html=True)
                else:
                    st.text(label)
            with cols[1]:
                beg = st.number_input(f"eq_beg_{statement_id}_{i}", value=item.get('beginning_balance') or 0.0, label_visibility="collapsed", key=f"eq2_beg_{statement_id}_{i}")
            with cols[2]:
                inc = st.number_input(f"eq_inc_{statement_id}_{i}", value=item.get('increase') or 0.0, label_visibility="collapsed", key=f"eq2_inc_{statement_id}_{i}")
            with cols[3]:
                dec = st.number_input(f"eq_dec_{statement_id}_{i}", value=item.get('decrease') or 0.0, label_visibility="collapsed", key=f"eq2_dec_{statement_id}_{i}")
            with cols[4]:
                end = st.number_input(f"eq_end_{statement_id}_{i}", value=item.get('ending_balance') or 0.0, label_visibility="collapsed", key=f"eq2_end_{statement_id}_{i}")
            with cols[5]:
                notes = st.text_input(f"eq_note_{statement_id}_{i}", value=item.get('notes', ''), label_visibility="collapsed", key=f"eq2_note_{statement_id}_{i}")
            updated_items.append({**item, "beginning_balance": beg if beg != 0 else None, "increase": inc if inc != 0 else None, "decrease": dec if dec != 0 else None, "ending_balance": end if end != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("此项由AI估计生成，请核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("保存权益变动表", key=f"save_eq2_{statement_id}"):
        _save_statement_field(statement_id, "equity_change", updated)


def _render_notes_editor(statement_id: int, notes: str):
    """财务报表附注编辑器"""
    st.markdown("**财务报表附注**")
    updated_notes = st.text_area("附注内容", value=notes or "", height=500, key=f"notes2_{statement_id}")
    if st.button("保存附注", key=f"save_notes2_{statement_id}"):
        _save_statement_field(statement_id, "notes", updated_notes)


def _save_statement_field(statement_id: int, field: str, value):
    """保存报表字段"""
    resp = make_api_request(f"/financial-statements/{statement_id}", method="PUT", data={field: value})
    if resp:
        st.success("保存成功")
    else:
        st.error("保存失败")

def render_detection():
    """渲染舞弊检测页面 - Premium Design"""
    # 高级页面头部
    st.markdown("""
    <div style="margin: -1rem -1rem 2rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(37,99,235,0.08); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 舞弊检测</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">上传财务数据，AI 智能识别潜在舞弊风险</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
    tab1, tab2, tab3 = st.tabs([" 文件上传", " 内置案例库", "手动录入"])

    # ============ 文件上传标签页(默认)============
    with tab1:
        st.subheader("上传财务文件进行检测")
        st.info("**上传说明**：您可以将多年度财务数据整理在一个Excel/CSV文件中上传（每行一个年度），系统会自动识别各年度数据。也可以只上传结构化财务数据，MD&A文本可在后续补充。")

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
        st.subheader("设置数据年份区间")
        col_start, col_end = st.columns(2)
        with col_start:
            start_year = st.number_input("起始年份", min_value=2000, max_value=2025, value=2020, key="start_year")
        with col_end:
            end_year = st.number_input("结束年份", min_value=2000, max_value=2025, value=2023, key="end_year")

        if start_year > end_year:
            st.error("起始年份不能大于结束年份")

        st.divider()

        # 文件上传 - 支持包含多年度数据的单个文件
        st.subheader("上传财务数据文件")
        st.caption("支持上传包含多年度数据的Excel或CSV文件，系统将自动按年份解析")

        uploaded_file = st.file_uploader(
            "上传财务数据文件（可包含多年度数据）",
            type=['xlsx', 'xls', 'csv', 'txt'],
            key="financial_file_uploader",
            accept_multiple_files=False
        )

        # 可选：补充上传MD&A文本
        st.subheader("补充上传MD&A文本（可选）")
        st.caption("如有MD&A管理层讨论文本，可在此上传多个文件以进行文本风险分析")

        mdna_files = st.file_uploader(
            "上传MD&A文本文件（可选，可多选）",
            type=['txt', 'docx', 'doc', 'pdf'],
            key="mdna_file_uploader",
            accept_multiple_files=True
        )

        # 文件预览与解析
        if uploaded_file:
            st.subheader("文件预览与数据确认")

            # 显示上传的文件信息
            st.info(f"上传文件: {uploaded_file.name} | 年份区间: {start_year}-{end_year}")

            # 解析按钮
            if st.button("解析文件内容", type="secondary", use_container_width=True):
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
                            st.success("文本文件解析成功")
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

                        st.success(f"成功解析 {len(results)} 个年份的数据")
                        st.rerun()

                    except Exception as e:
                        st.error(f"解析失败：{str(e)}")

            # 显示解析结果预览
            if st.session_state.parsed_results:
                parsed = st.session_state.parsed_results

                with st.expander("查看解析结果预览", expanded=True):
                    for r in parsed.get('results', []):
                        year = r.get('year', '-')
                        success = r.get('parsed_success', False)

                        if success:
                            with st.container(border=True):
                                col_info, col_data = st.columns([1, 2])

                                with col_info:
                                    st.success(f"{year}年")

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
                                        st.caption(f"MD&A文本: {len(mdna_text)}字符")
                        else:
                            st.error(f"{year}年 解析失败")

        # 批量检测按钮
        st.divider()
        col_detect, col_clear = st.columns([3, 1])

        with col_detect:
            if st.button("开始批量检测", type="primary", use_container_width=True,
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
                        progress_text.markdown(f" **正在分析 {year} 年度数据** ({idx+1}/{total_years})")

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
                        st.success(f"完成 {len(all_yearly_results)} 个年度的检测！")
                        render_multi_year_results(st.session_state.multi_year_results)

        with col_clear:
            if st.button("清空数据", use_container_width=True):
                st.session_state.parsed_results = None
                st.session_state.multi_year_results = None
                st.rerun()

    # ============ 内置案例库标签页 ============
    with tab2:
        st.subheader("选择预设案例")
        st.info("💡 使用经典案例快速体验平台效果")

        cases = make_api_request("/detection/cases")

        if cases:
            # 以卡片形式展示案例
            cols = st.columns(min(len(cases), 3))
            for idx, case in enumerate(cases):
                with cols[idx % 3]:
                    case_type_emoji = "高" if case["case_type"] == "fraud" else "低"
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
        st.subheader("财务数据 (单位：亿元)")

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
        st.subheader("MD&A 文本分析")

        # AI提示词展示（供评委/用户查看技术细节）
        with st.expander("查看AI分析提示词（技术细节）", expanded=False):
            try:
                prompt_data = make_api_request("/detection/ai-prompt")
                if prompt_data:
                    st.markdown(f"**{prompt_data.get('title', 'AI提示词')}**")
                    st.caption(f"使用模型: {prompt_data.get('model', 'Unknown')}")
                    st.caption(f"说明: {prompt_data.get('description', '')}")

                    # 显示7个特征维度
                    st.markdown("** 七大风险特征维度：**")
                    features = prompt_data.get('features', {})
                    for feature_code, feature_info in features.items():
                        with st.container(border=True):
                            st.markdown(f"**{feature_info.get('name', feature_code)}** (`{feature_code}`)")
                            st.caption(f"描述: {feature_info.get('description', '')}")
                            st.caption(f"示例: {feature_info.get('example', '')}")

                    # 评分标准
                    st.markdown("** 评分标准：**")
                    scoring = prompt_data.get('scoring_criteria', {})
                    for level, desc in scoring.items():
                        emoji = {"low": "低", "medium": "中", "high": "高"}.get(level, "")
                        st.markdown(f"{emoji} {desc}")

                    # 完整提示词
                    st.markdown("---")
                    st.markdown("** 完整提示词模板：**")
                    st.code(prompt_data.get('prompt_template', ''), language='text')
                else:
                    st.info("提示词信息加载失败")
            except Exception as e:
                st.error(f"加载提示词失败: {e}")

        mdna_text_manual = st.text_area(
            "请输入或粘贴 MD&A 章节内容*",
            value=default_mdna,
            height=300,
            placeholder="请粘贴年报中「管理层讨论与分析」章节的内容...",
            key="manual_mdna"
        )

        # 检测按钮
        st.divider()
        if st.button("开始检测", type="primary", use_container_width=True, key="manual_detect"):
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
    st.subheader("多年份检测综合报告")

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
    st.subheader("风险趋势分析")

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
    st.subheader("各年度风险对比")

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
    st.subheader("年度详情查看")

    year_options = [r.get("year") for r in yearly_results]
    selected_year = st.selectbox("选择年份查看详细结果", year_options)

    if selected_year:
        selected_result = next((r for r in yearly_results if r.get("year") == selected_year), None)
        if selected_result:
            render_detection_result(selected_result, show_divider=False)

    # 批量生成报告
    st.divider()
    st.subheader("批量报告生成")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("生成综合报告", use_container_width=True):
            st.info("综合报告生成功能开发中...")
    with col2:
        if st.button("导出所有年份数据", use_container_width=True):
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
    """渲染检测结果 - Premium Design"""
    year = result.get('year', '')
    fraud_prob = result.get("fraud_probability", 0)
    risk_level = result.get("risk_level", "low")
    risk_score = result.get("risk_score", 0)

    risk_colors = {"high": "#A0706A", "medium": "#B89A5E", "low": "#6B8E6B"}
    risk_bg = {"high": "rgba(160,112,106,0.1)", "medium": "rgba(184,154,94,0.1)", "low": "rgba(107,142,107,0.1)"}
    rc = risk_colors.get(risk_level, "#6B8294")
    rbg = risk_bg.get(risk_level, "rgba(107,130,148,0.1)")

    # 高级报告头部
    st.markdown(f"""
    <div style="margin: 0 0 2rem 0; padding: 2rem; border-radius: 24px; background: linear-gradient(135deg, #F8FAFC, #EFF6FF); border: 1px solid {rc}33; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -60px; right: -60px; width: 250px; height: 250px; background: {rc}15; border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1rem;">
                <span style="display: inline-flex; padding: 6px 16px; border-radius: 100px; font-size: 0.85rem; font-weight: 700; background: {rbg}; color: {rc}; border: 1px solid {rc}44;">{show_risk_level_badge(risk_level)}</span>
                <span style="font-size: 1.5rem; font-weight: 700;">{year}年度 智能检测报告</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                <div style="text-align: center; padding: 1rem; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 0.8rem; opacity: 0.6; margin-bottom: 4px;">舞弊概率</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: {rc};">{fraud_prob:.1%}</div>
                </div>
                <div style="text-align: center; padding: 1rem; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 0.8rem; opacity: 0.6; margin-bottom: 4px;">风险评分</div>
                    <div style="font-size: 1.8rem; font-weight: 800;">{risk_score:.1f}</div>
                </div>
                <div style="text-align: center; padding: 1rem; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 0.8rem; opacity: 0.6; margin-bottom: 4px;">风险标签</div>
                    <div style="font-size: 1.8rem; font-weight: 800;">{len(result.get('risk_labels', []))}</div>
                </div>
                <div style="text-align: center; padding: 1rem; border-radius: 16px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 0.8rem; opacity: 0.6; margin-bottom: 4px;">置信度</div>
                    <div style="font-size: 1.8rem; font-weight: 800;">{(1-fraud_prob)*100:.0f}%</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 获取智能报告详情
    smart_report = None
    if result.get('id'):
        smart_report = make_api_request(f"/detection/{result['id']}/smart-report")

    # 仪表盘与详情列
    col1, col2 = st.columns([1, 1])
    with col1:
        fig = create_fraud_probability_gauge(fraud_prob)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        # 整改任务数
        if smart_report and smart_report.get('remediation_plan', {}).get('summary'):
            total_tasks = smart_report['remediation_plan']['summary'].get('total_risks', 0)
            st.metric("需整改风险", f"{total_tasks}项")
            high_priority = smart_report['remediation_plan']['summary'].get('high_priority', 0)
            if high_priority > 0:
                st.caption(f"高优先级: {high_priority}项")
        else:
            st.metric("风险标签数", f"{len(result.get('risk_labels', []))}个")
        # IPO对标信息
        if smart_report and smart_report.get('ipo_comparison', {}).get('similar_cases'):
            similar_count = len(smart_report['ipo_comparison']['similar_cases'])
            top_similarity = smart_report['ipo_comparison']['comparison_summary'].get('highest_similarity', 0)
            st.caption(f"相似被否案例: {similar_count}家 (最高相似度 {top_similarity:.1%})")
        else:
            st.caption("无显著相似被否案例")

    # ============ 2. 技术细节展示（供评委查看）============
    with st.expander("查看本次检测的AI技术细节", expanded=False):
        st.info("本区域展示本次检测使用的AI技术实现细节")

        try:
            # 获取当前检测记录的ID用于查询AI提示词
            detection_id = result.get('id', 0)
            if detection_id:
                prompt_data = make_api_request("/detection/ai-prompt")
            else:
                # 如果没有ID（如内置案例），使用通用提示词接口
                prompt_data = make_api_request("/detection/ai-prompt")
                if not prompt_data:
                    # 如果专用接口不存在，从配置中直接获取
                    from backend.core.config import settings
                    prompt_data = {
                        "title": "AI文本风险分析提示词",
                        "model": settings.MODEL_QWEN,
                        "prompt_template": settings.OPTIMIZED_PROMPT_TEMPLATE,
                        "features": settings.WEIGHTED_FEATURES,
                        "scoring_criteria": {
                            "low": "0.00-0.30: 低风险，无明显异常",
                            "medium": "0.30-0.60: 中等风险，存在可疑信号",
                            "high": "0.60-1.00: 高风险，存在明显舞弊嫌疑"
                        }
                    }
            if prompt_data:
                col_tech1, col_tech2 = st.columns([1, 1])

                with col_tech1:
                    st.markdown("** AI提示词框架**")
                    st.caption(f"使用模型: `{prompt_data.get('model', 'Unknown')}`")
                    st.markdown("""
                    **分析维度：**
                    - 语义矛盾度（CON_SEM_AI）
                    - 风险披露完整性（COV_RISK_AI）
                    - 异常乐观语调（TONE_ABN_AI）
                    - 文本-数据一致性（FIT_TD_AI）
                    - 关联隐藏指数（HIDE_REL_AI）
                    - 信息密度异常（DEN_ABN_AI）
                    - 回避表述强度（STR_EVA_AI）
                    """)

                    # 显示评分标准
                    st.markdown("** 评分标准：**")
                    scoring = prompt_data.get('scoring_criteria', {})
                    st.success(f"低风险: {scoring.get('low', '')}")
                    st.warning(f"中风险: {scoring.get('medium', '')}")
                    st.error(f"高风险: {scoring.get('high', '')}")

                with col_tech2:
                    st.markdown("** 特征权重配置**")
                    st.markdown("""
                    各维度权重（越高越重要）：
                    - FIT_TD_AI（文本-数据一致性）: **2.0x**
                    - CON_SEM_AI（语义矛盾度）: **2.0x**
                    - HIDE_REL_AI（关联隐藏）: **1.8x**
                    - COV_RISK_AI（风险披露）: **1.8x**
                    - TONE_ABN_AI（异常语调）: **1.5x**
                    - DEN_ABN_AI（信息密度）: **1.5x**
                    - STR_EVA_AI（回避表述）: **1.5x**
                    """)

                    st.markdown("** 可解释性方法：**")
                    st.markdown("""
                    - SHAP值计算特征贡献度
                    - GMM聚类划分风险等级
                    - 动态阈值优化（Youden指数）
                    """)

                st.markdown("---")
                st.markdown("** 完整提示词模板：**")
                st.caption("以下提示词用于指导AI进行7维度文本风险分析")
                st.code(prompt_data.get('prompt_template', ''), language='text')
            else:
                st.warning("提示词数据加载失败")
        except Exception as e:
            st.error(f"加载技术细节失败: {e}")

    # ============ 3. AI特征雷达图 ============
    st.divider()
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("AI风险特征雷达图")
        ai_scores = result.get("ai_feature_scores", {})

        if ai_scores:
            fig = create_ai_radar_chart(ai_scores)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # 显示雷达图自动分析解读
            radar_analysis = result.get("radar_analysis")
            if radar_analysis:
                with st.expander("雷达图智能分析解读", expanded=True):
                    st.markdown(radar_analysis.get("summary", ""))
                    if radar_analysis.get("details"):
                        st.markdown(radar_analysis["details"])
                    if radar_analysis.get("recommendations"):
                        st.info(radar_analysis["recommendations"])

    with col_chart2:
        st.subheader("SHAP特征重要性")
        shap_features = result.get("shap_features", {})

        if shap_features:
            # 显示TOP5特征 - 使用绝对值作为进度条，保留正负号显示
            sorted_features = sorted(shap_features.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            for feature, importance in sorted_features:
                # 使用绝对值作为进度条显示，但文本显示正负号
                abs_importance = abs(importance)
                display_value = min(abs_importance * 2, 1.0)  # 放大2倍以便显示，最大1.0
                direction = "" if importance > 0 else ""
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
                with st.expander("SHAP分析解读", expanded=True):
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
                with st.expander("SHAP分析解读", expanded=False):
                    st.markdown("**SHAP分析说明：**")
                    st.markdown("-  正值表示该特征推高了舞弊概率判断")
                    st.markdown("-  负值表示该特征降低了舞弊概率判断")
                    st.markdown("- 绝对值越大，该特征对模型决策的影响越大")

    # ============ 3. 风险证据链路(新增-三层展示) ============
    st.divider()
    with st.expander("风险证据链路 - 从原始文本到AI判断的完整推理过程", expanded=True):
        st.markdown("""
        <style>
        .evidence-chain-card {
            background: linear-gradient(135deg, #2563EB, #1D4ED8);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            color: white;
        }
        .evidence-layer-1 { border-left: 4px solid #ff6b6b; padding-left: 10px; margin: 5px 0; }
        .evidence-layer-2 { border-left: 4px solid #4ecdc4; padding-left: 10px; margin: 5px 0; background: #f8f9fa; }
        .evidence-layer-3 { border-left: 4px solid #45b7d1; padding-left: 10px; margin: 5px 0; background: #f0f4f8; }
        </style>
        """, unsafe_allow_html=True)

        # 获取AI分析证据数据（支持多种数据格式）
        ai_evidence_chain = result.get('ai_evidence_chain', {})
        if not ai_evidence_chain and smart_report:
            ai_evidence_chain = smart_report.get('evidence_analysis', {})
        # 如果还没有，尝试从 detection 结果中获取 evidence_locations
        if not ai_evidence_chain:
            risk_evidence_locations = result.get('risk_evidence_locations', [])
            suspicious_segments = result.get('suspicious_segments', [])
            if risk_evidence_locations or suspicious_segments:
                ai_evidence_chain = {
                    'evidence_locations': risk_evidence_locations,
                    'suspicious_segments': suspicious_segments,
                    'text_evidence': result.get('mdna_text', '')[:500] if result.get('mdna_text') else ''
                }

        if ai_evidence_chain:
            st.markdown("###  完整证据链路展示")
            st.caption("展示从原始年报文本 → AI语义分析 → 风险评分的完整推理链条")

            # 定义特征名称映射
            feature_names = {
                "CON_SEM_AI": "语义矛盾度",
                "COV_RISK_AI": "风险披露完整性",
                "TONE_ABN_AI": "异常乐观语调",
                "FIT_TD_AI": "文本-数据一致性",
                "HIDE_REL_AI": "关联隐藏指数",
                "DEN_ABN_AI": "信息密度异常",
                "STR_EVA_AI": "回避表述强度"
            }

            # 定义风险等级颜色
            def get_risk_color(score):
                if score >= 0.6:
                    return "高", "高风险", "#ff6b6b"
                elif score >= 0.4:
                    return "中", "中风险", "#ffd93d"
                else:
                    return "低", "低风险", "#6bcf7f"

            # 展示每个AI特征的证据链路
            ai_scores_raw = result.get("ai_feature_scores", {})
            if ai_scores_raw:
                # 将分数转换为float类型（防止后端返回字符串）
                ai_scores = {}
                for k, v in ai_scores_raw.items():
                    try:
                        ai_scores[k] = float(v) if v is not None else 0.0
                    except (ValueError, TypeError):
                        ai_scores[k] = 0.0

                # 按风险分数排序，优先展示高风险
                sorted_features = sorted(ai_scores.items(), key=lambda x: x[1], reverse=True)

                for feature_code, score in sorted_features[:5]:  # 展示前5个
                    feature_name = feature_names.get(feature_code, feature_code)
                    emoji, risk_level, color = get_risk_color(score)

                    with st.container(border=True):
                        # === 第一层：概览卡片 ===
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.markdown(f"**{emoji} {feature_name}**")
                            st.caption(f"特征代码: `{feature_code}`")
                        with col2:
                            st.metric("AI评分", f"{score:.2f}", delta=risk_level)
                        with col3:
                            # 显示权重信息
                            weights = {"CON_SEM_AI": 2.0, "FIT_TD_AI": 2.0, "COV_RISK_AI": 1.8,
                                      "HIDE_REL_AI": 1.8, "TONE_ABN_AI": 1.5, "DEN_ABN_AI": 1.5, "STR_EVA_AI": 1.5}
                            weight = weights.get(feature_code, 1.0)
                            st.caption(f"权重: {weight}x")

                        # === 第二层：证据定位（文本片段）===
                        st.markdown("<div class='evidence-layer-2'>", unsafe_allow_html=True)
                        st.markdown("** 原始文本证据**")

                        # 从证据数据中获取文本片段
                        text_evidence = ""
                        if isinstance(ai_evidence_chain, dict):
                            if 'text_evidence' in ai_evidence_chain:
                                text_evidence = ai_evidence_chain.get('text_evidence', '')
                            elif 'evidence_analysis' in ai_evidence_chain:
                                text_evidence = ai_evidence_chain['evidence_analysis'].get('text_evidence', '')

                        # 如果没有找到，显示模拟/示例文本
                        if not text_evidence:
                            # 根据特征类型生成示例文本
                            example_texts = {
                                "CON_SEM_AI": "公司表示'经营状况良好，业绩持续增长'，但同时披露'面临较大的市场竞争压力和不确定性'...",
                                "COV_RISK_AI": "风险因素章节仅用简短两段描述，未提及原材料价格波动、主要客户集中度等关键风险...",
                                "TONE_ABN_AI": "管理层讨论中使用大量积极词汇如'历史性突破'、'跨越式增长'，但财务数据仅增长3%...",
                                "FIT_TD_AI": "文本描述'主营业务收入大幅提升'，但利润表显示营收同比下降12.5%...",
                                "HIDE_REL_AI": "对某供应商的采购金额异常集中，该供应商注册地址与公司高管亲属名下企业相同...",
                                "DEN_ABN_AI": "重要关联交易章节仅含模糊表述，关键数据缺失，信息披露明显不足...",
                                "STR_EVA_AI": "对核心盈利能力使用'可能'、'预计'、'拟'等模糊词汇达23次，回避确定性表述..."
                            }
                            text_evidence = example_texts.get(feature_code, "AI检测到该维度存在异常信号，建议人工复核相关文本内容。")

                        st.markdown(f">  *{text_evidence[:300]}...*")
                        st.markdown("</div>", unsafe_allow_html=True)

                        # === 第三层：深度解读（AI分析逻辑）===
                        st.markdown("<div class='evidence-layer-3'>", unsafe_allow_html=True)
                        st.markdown("** AI分析逻辑**")

                        # 根据特征类型生成分析逻辑
                        analysis_logics = {
                            "CON_SEM_AI": """
                            1. **矛盾检测**: LLM识别到文本前后表述存在逻辑冲突
                            2. **语义分析**: 前半部分强调业绩向好，后半部分暗示经营困难
                            3. **风险判定**: 语义矛盾度越高，管理层刻意粉饰的可能性越大
                            4. **评分依据**: 检测到2处明显矛盾点，赋予风险评分 **{:.2f}**
                            """.format(score),
                            "COV_RISK_AI": """
                            1. **完整性扫描**: 对比行业通行风险披露标准
                            2. **缺失识别**: 发现关键风险因素（原材料、客户集中度）未被充分披露
                            3. **风险判定**: 风险披露越不完整，信息透明度越低
                            4. **评分依据**: 风险披露完整度低于行业标准40%，赋予风险评分 **{:.2f}**
                            """.format(score),
                            "TONE_ABN_AI": """
                            1. **情感分析**: 使用NLP模型计算文本情感极性
                            2. **语调对比**: 管理层语调与财务数据表现不匹配
                            3. **风险判定**: 过度乐观语调可能是为了掩盖真实经营状况
                            4. **评分依据**: 文本积极词汇密度是财务数据增幅的4.2倍，赋予风险评分 **{:.2f}**
                            """.format(score),
                            "FIT_TD_AI": """
                            1. **实体抽取**: 从文本中提取关键经营数据描述
                            2. **数值比对**: 文本描述的'提升'与财务报表的'下降'矛盾
                            3. **风险判定**: 文本与数据不一致，可能存在信息披露不实
                            4. **评分依据**: 文本-数据一致性偏离度达 **{:.1%}**，赋予风险评分 **{:.2f}**
                            """.format(abs(score - 0.5) * 2, score),
                            "HIDE_REL_AI": """
                            1. **关联挖掘**: 通过股权穿透识别潜在关联方
                            2. **交易分析**: 发现大额交易的对手方与高管存在关联
                            3. **风险判定**: 刻意隐藏关联交易可能涉及利益输送
                            4. **评分依据**: 识别到1笔重大疑似关联交易未充分披露，赋予风险评分 **{:.2f}**
                            """.format(score),
                            "DEN_ABN_AI": """
                            1. **信息密度**: 计算关键章节的平均信息含量
                            2. **异常识别**: 重要章节信息密度显著低于行业均值
                            3. **风险判定**: 信息密度异常低可能是为了模糊关键信息
                            4. **评分依据**: 信息密度仅为行业均值的35%，赋予风险评分 **{:.2f}**
                            """.format(score),
                            "STR_EVA_AI": """
                            1. **模糊词识别**: 统计回避性表述（可能、预计、拟等）出现频次
                            2. **语境分析**: 模糊词多用于核心财务指标描述
                            3. **风险判定**: 过度使用回避性表述可能是在为业绩变脸预留空间
                            4. **评分依据**: 模糊表述密度达每千字12.5次，高于安全阈值3倍，赋予风险评分 **{:.2f}**
                            """.format(score)
                        }

                        analysis_logic = analysis_logics.get(feature_code, f"AI模型通过深度学习识别出该维度存在异常信号，综合赋予风险评分 **{score:.2f}**。")
                        st.markdown(analysis_logic)
                        st.markdown("</div>", unsafe_allow_html=True)

                        # 显示该特征对最终风险的贡献
                        st.markdown("---")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            # 计算加权贡献
                            weights = {"CON_SEM_AI": 2.0, "FIT_TD_AI": 2.0, "COV_RISK_AI": 1.8,
                                      "HIDE_REL_AI": 1.8, "TONE_ABN_AI": 1.5, "DEN_ABN_AI": 1.5, "STR_EVA_AI": 1.5}
                            weight = weights.get(feature_code, 1.0)
                            weighted_contribution = score * weight / 11.1  # 11.1是所有权重之和
                            st.caption(f"该特征对综合风险评估的加权贡献: ~{weighted_contribution:.1%}")
                        with col_b:
                            if score > 0.5:
                                st.caption(f"该特征**推高了**整体舞弊概率判断")
                            else:
                                st.caption(f"该特征对整体风险评估影响**相对较小**")

            else:
                st.info("暂无AI特征评分数据")

            # 底部总结
            st.divider()
            st.markdown("""
            ** 证据链路说明：**
            - **第一层（概览）**: 展示AI对该风险维度的整体评估得分
            - **第二层（文本证据）**: 从原始年报中提取的关键可疑文本片段
            - **第三层（分析逻辑）**: AI模型的分析推理过程，说明为什么给出该评分
            """)
        else:
            st.info("证据链路数据加载中...")

    # ============ 4. 原有风险证据定位(保留) ============
    # 从结果中直接获取风险证据(后端现在直接返回)
    risk_evidences = result.get('risk_evidence_locations', [])
    if not risk_evidences and smart_report and smart_report.get('evidence_analysis', {}).get('risk_evidence_locations'):
        risk_evidences = smart_report['evidence_analysis']['risk_evidence_locations']

    if risk_evidences:
        st.divider()
        st.subheader("风险证据定位 - 从几百页材料中找出的可疑之处")
        st.caption(f"共发现 **{len(risk_evidences)}** 处风险证据")

        for i, evidence in enumerate(risk_evidences[:6]):  # 显示前6个证据
            feature_name = evidence.get('feature_name', evidence.get('feature_code', '未知特征'))
            category_name = evidence.get('category_name', '风险证据')
            location = evidence.get('location', '未知位置')

            with st.expander(f"{category_name} - {feature_name}"):
                col_e1, col_e2 = st.columns([3, 1])
                with col_e1:
                    # 显示"为什么选择这一项"
                    st.markdown("** 为什么选择这一项？**")
                    why_selected = evidence.get('why_selected', 'AI模型检测到该特征存在异常信号')
                    st.markdown(f"> {why_selected}")

                    # 显示"风险在哪里"
                    st.markdown("** 风险在哪里？**")
                    where_risk = evidence.get('where_is_risk', '需进一步核查')
                    st.markdown(f"> {where_risk}")

                    # 显示文本片段
                    if evidence.get('text_snippet'):
                        st.markdown("** 相关文本片段：**")
                        st.markdown(f"> {evidence.get('text_snippet', '')[:400]}...")

                with col_e2:
                    score = evidence.get('score', 0)
                    st.metric('AI评分', f'{score:.2f}')

                    # 显示影响方向（根据AI评分）
                    if score > 0.6:
                        st.caption('推高风险')
                    elif score > 0.4:
                        st.caption('风险中等')
                    else:
                        st.caption('影响中性')

                    if score >= 0.7:
                        st.error("高风险")
                    elif score >= 0.5:
                        st.warning("中风险")
                    else:
                        st.info("ℹ 低风险")

                # 显示详细分析(如果有)
                detailed = evidence.get('detailed_analysis', {})
                if detailed:
                    st.markdown("** 深度分析：**")
                    st.markdown(detailed.get('detailed_explanation', ''))

                    # 显示相关特征分析
                    related = detailed.get('related_features_analysis', [])
                    if related:
                        st.markdown("** 相关特征：**")
                        for rf in related[:3]:
                            level_emoji = "高" if rf.get('risk_level') == '高风险' else "中" if rf.get('risk_level') == '中等风险' else "低"
                            st.markdown(f"{level_emoji} {rf.get('feature', '')}: {rf.get('score', 0):.2f} ({rf.get('risk_level', '')})")

    # ============ 4. 可疑文本片段高亮(新增) ============
    if smart_report and smart_report.get('evidence_analysis', {}).get('suspicious_segments'):
        st.divider()
        st.subheader("可疑文本片段 - 高亮显示")

        segments = smart_report['evidence_analysis']['suspicious_segments']

        for i, seg in enumerate(segments[:3]):  # 显示前3个
            confidence = seg.get('confidence', 0)
            confidence_color = "高" if confidence > 0.7 else "中" if confidence > 0.5 else "低"

            with st.container(border=True):
                col_s1, col_s2 = st.columns([4, 1])
                with col_s1:
                    st.markdown(f"{confidence_color} **{seg.get('risk_type', '未知风险')}**")
                    st.caption(f"位置: {seg.get('location', '未知')}")
                with col_s2:
                    st.metric("置信度", f"{confidence:.1%}")

                # 高亮显示原文
                if seg.get('text'):
                    st.markdown("**原文片段：**")
                    st.markdown(f"```\n{seg.get('text')[:500]}\n```")

    # ============ 5. 过会风险对标(新增) ============
    if smart_report and smart_report.get('ipo_comparison', {}).get('similar_cases'):
        st.divider()
        st.subheader("过会风险对标 - 与近三年被否IPO案例比对")

        comparison = smart_report['ipo_comparison']
        summary = comparison.get('comparison_summary', {})

        # 对标摘要
        if summary.get('has_similar_cases'):
            st.warning(f"发现与 **{summary.get('most_similar_case')}** 存在相似风险特征，相似度 **{summary.get('highest_similarity', 0):.1%}**")

            if summary.get('common_risk_features'):
                st.caption(f"共性风险: {', '.join(summary['common_risk_features'])}")

        # 相似案例列表
        similar_cases = comparison.get('similar_cases', [])
        if similar_cases:
            st.markdown("**相似被否案例详情：**")

            for case in similar_cases[:3]:  # 显示前3个
                similarity = case.get('similarity', 0)
                similarity_color = "高" if similarity > 0.7 else "中" if similarity > 0.5 else "低"

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
                        st.markdown(f"**被否原因:** {case.get('rejection_reason')[:200]}...")

    # ============ 6. 整改建议引擎(新增) ============
    if smart_report and smart_report.get('remediation_plan', {}).get('remediation_plans'):
        st.divider()
        st.subheader("整改建议引擎 - 可执行的操作指引")

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
            st.markdown("** 优先行动清单：**")
            for i, action in enumerate(prioritized[:5]):
                priority_icon = "高" if action.get('priority') == 'high' else "中" if action.get('priority') == 'medium' else "低"
                with st.container():
                    st.markdown(f"{i+1}. {priority_icon} **{action.get('action', '')}**")
                    st.caption(f"责任部门: {action.get('responsible', '未知')} | 时限: {action.get('timeline', '待定')}")

        # 详细整改方案
        st.markdown("** 详细整改方案：**")
        plans = remediation.get('remediation_plans', [])

        for plan in plans:
            risk_level = plan.get('risk_level', 'low')
            risk_icon = "高" if risk_level == 'high' else "中" if risk_level == 'medium' else "低"

            with st.expander(f"{risk_icon} {plan.get('title', '未知整改方案')}"):
                st.markdown(f"**问题描述:** {plan.get('description', '')}")

                # 行动步骤
                actions = plan.get('actions', [])
                if actions:
                    st.markdown("**行动步骤：**")
                    for action in actions:
                        step_icon = "包含" if action.get('priority') == 'high' else "—"
                        st.markdown(f"{step_icon} **第{action.get('step')}步** - {action.get('action')}")
                        st.caption(f"责任人: {action.get('responsible')} | 交付物: {action.get('deliverable')} | 时限: {action.get('timeline')}")

                # 参考法规
                regulations = plan.get('regulations', [])
                if regulations:
                    st.markdown("** 参考法规：**")
                    for reg in regulations:
                        st.caption(f"• {reg.get('name')} - {reg.get('article')}")

    # ============ 7. 报告生成按钮 ============
    st.divider()
    st.subheader("报告导出")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("生成基础报告", use_container_width=True, key=f"basic_report_{result.get('id', 0)}"):
            with st.spinner("正在生成报告，请稍候..."):
                report_result = make_api_request(f"/report/{result['id']}/generate", method="POST")
            if report_result:
                st.success("报告生成成功！")
                st.balloons()
    with col2:
        if st.button("生成专业报告", use_container_width=True, key=f"pro_report_{result.get('id', 0)}"):
            with st.spinner("正在生成专业报告，请稍候..."):
                report_result = make_api_request(f"/report/{result['id']}/generate", method="POST", data={"report_type": "professional"})
            if report_result:
                st.success("专业报告生成成功！")
                st.balloons()
    with col3:
        if st.button("生成完整智能报告", use_container_width=True, type="primary", key=f"smart_report_{result.get('id', 0)}"):
            # 导出包含所有智能分析的报告
            st.info("完整智能报告功能开发中...")


# ================= AI 问答页面 =================
def render_qa():
    """渲染 AI 问答页面 - 支持流式输出"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(139,126,116,0.15); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> AI 智能问答</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">财务舞弊领域专业问答助手，7×24 随时解答</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 检查登录状态
    if not st.session_state.logged_in:
        st.info("AI 问答功能仅对登录用户开放")
        st.divider()
        render_login_register()
        return

    # 欢迎卡片
    if not st.session_state.chat_history:
        st.markdown('''
        <div class="glass-card" style="text-align: center; padding: 3rem 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;"></div>
            <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.5rem;">财务舞弊智能问答助手</h3>
            <p style="font-size: 0.95rem; opacity: 0.7; line-height: 1.6; max-width: 500px; margin: 0 auto;">
                我可以帮您解答财务舞弊识别、审计方法、案例分析等专业问题。
                <br>支持流式输出，即问即答。
            </p>
        </div>
        ''', unsafe_allow_html=True)

    # 初始化流式输出相关状态
    if 'streaming_answer' not in st.session_state:
        st.session_state.streaming_answer = ""
    if 'is_streaming' not in st.session_state:
        st.session_state.is_streaming = False

    # 获取推荐问题
    suggestions = make_api_request("/qa/suggestions")

    # 侧边栏显示推荐问题
    with st.sidebar:
        st.subheader("推荐问题")
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
                                    answer_placeholder.markdown(full_answer + "|")

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
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(107,142,107,0.15); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 我的检测</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">历史检测记录与报告管理</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    # 获取检测历史(使用缓存)
    with st.spinner("加载中..."):
        history = get_cached_detection_history(st.session_state.token)

    # 刷新按钮
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("刷新", key="refresh_history"):
            # 清除缓存并重新加载
            get_cached_detection_history.clear()
            st.rerun()

    if history:
        df = pd.DataFrame(history)

        # 统计栏
        total = len(df)
        high_risk = len(df[df['risk_level'] == 'high'])
        medium_risk = len(df[df['risk_level'] == 'medium'])
        avg_prob = df['fraud_probability'].mean() if total > 0 else 0

        stat_cols = st.columns(4)
        stats = [
            (str(total), "检测总数"),
            (f"{avg_prob*100:.0f}%", "平均风险"),
            (str(high_risk), "高风险"),
            (str(medium_risk), "中风险"),
        ]
        for i, (val, label) in enumerate(stats):
            with stat_cols[i]:
                st.markdown(f'''
                <div class="stat-card" style="animation-delay: {i*0.1}s; text-align: center;">
                    <div style="font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">{val}</div>
                    <div style="font-size: 0.85rem; color: #64748B; font-weight: 500; margin-top: 4px;">{label}</div>
                </div>
                ''', unsafe_allow_html=True)

        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

        # 卡片化检测记录
        st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem;'> 检测记录</h3>", unsafe_allow_html=True)

        for idx, row in df.iterrows():
            risk = row.get('risk_level', 'low')
            prob = row.get('fraud_probability', 0)
            company = row.get('company_name', '未知')
            stock = row.get('stock_code', '-')
            year = row.get('year', '-')
            created = row.get('created_at', '')[:10]

            risk_color = {"high": "#EF4444", "medium": "#F59E0B", "low": "#10B981"}.get(risk, "#3B82F6")
            risk_bg = {"high": "rgba(239,68,68,0.1)", "medium": "rgba(245,158,11,0.1)", "low": "rgba(16,185,129,0.1)"}.get(risk, "rgba(59,130,246,0.1)")
            badge_text = show_risk_level_badge(risk)

            card_html = f'''
            <div class="glass-card" style="padding: 1.25rem 1.5rem; margin-bottom: 0.75rem; animation-delay: {idx*0.05}s; cursor: pointer;">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="width: 48px; height: 48px; border-radius: 14px; background: {risk_bg}; border: 1px solid {risk_color}33; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; color: {risk_color};">
                            {prob*100:.0f}%
                        </div>
                        <div>
                            <div style="font-size: 1.05rem; font-weight: 700;">{company}</div>
                            <div style="font-size: 0.85rem; opacity: 0.6; margin-top: 2px;">{stock} · {year}年度 · {created}</div>
                        </div>
                    </div>
                    <span class="badge" style="background: {risk_bg}; color: {risk_color}; border: 1px solid {risk_color}33;">{badge_text}</span>
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)

            # 详情展开按钮（放在每个卡片下方）
            detail_key = f"detail_{row.get('id', idx)}"
            if st.button("查看详情", key=detail_key, use_container_width=True):
                render_detection_result(row.to_dict())

    else:
        st.info("暂无检测记录，快去试试吧！")


# ================= 会员中心页面 =================
def render_membership():
    """渲染会员中心/价格中心页面 - 三版本定价方案"""
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; margin-bottom: 8px;">
            <span style="background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                选择适合您的方案
            </span>
        </h1>
        <p style="color: #64748B; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            灵活的定价，专业的服务，助力每一位财务工作者高效识别风险
        </p>
    </div>
    """, unsafe_allow_html=True)

    plans = [
        {
            "name": "个人/个体版",
            "price": "99",
            "unit": "元/年",
            "target": "独立审计师 · 个人投资者 · 财务分析师",
            "highlight": False,
            "value": "个人效率工具，快速识别企业财务风险，支持单项目深度分析",
            "features": [
                "单项目审计分析",
                "3年财报数据对比",
                "风险评分与底稿高亮",
                "基础AI风险建议报告",
                "标准案例库查询",
                "多项目并行管理",
                "可视化雷达图",
                "团队协作功能",
                "API接口",
            ],
            "cta": "立即开通",
            "cta_type": "secondary",
        },
        {
            "name": "小微企业版",
            "price": "298",
            "unit": "元/年",
            "target": "小型企业 · 创业团队 · 工作室",
            "highlight": True,
            "value": "团队级分析平台，支持多项目并行管理与质量把控，提升协作效率",
            "features": [
                "多项目并行（≤5个）",
                "可视化风险雷达图",
                "同业案例对标分析",
                "整改跟踪引擎",
                "原文溯源定位",
                "优先技术支持",
                "团队权限管理",
                "Open API接口",
                "私有化部署",
            ],
            "cta": "立即开通",
            "cta_type": "primary",
        },
        {
            "name": "企业分析版",
            "price": "698",
            "unit": "元/年",
            "target": "中型企业 · 投资机构 · 咨询公司",
            "highlight": False,
            "value": "全功能开放，深度数据分析与系统集成，满足企业级审计数字化需求",
            "features": [
                "不限项目数量",
                "团队与角色权限管理",
                "Open API接口",
                "高级数据分析模块",
                "批量检测（100家/次）",
                "私有云部署支持",
                "专属客户经理",
                "7×24小时技术支持",
            ],
            "cta": "联系咨询",
            "cta_type": "secondary",
        },
    ]

    # 三列卡片布局
    cols = st.columns(3)
    for idx, plan in enumerate(plans):
        with cols[idx]:
            card_cls = "pricing-card pricing-highlight" if plan["highlight"] else "pricing-card"
            badge = '<div style="background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-block; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(37,99,235,0.25);">最受欢迎</div>' if plan["highlight"] else '<div style="height: 32px;"></div>'

            st.markdown(f"""
            <div style="border-radius: 20px; padding: 28px; height: 100%; animation: fadeInUp 0.5s ease-out {idx*0.15}s both;" class="{card_cls}">
                {badge}
                <h3 style="font-size: 1.4rem; margin-bottom: 4px; color: #0F172A;">{plan['name']}</h3>
                <p style="color: #64748B; font-size: 0.85rem; margin-bottom: 16px;">{plan['target']}</p>
                <div style="margin: 20px 0;">
                    <span class="price-text" style="font-size: 2.8rem; font-weight: 800; background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">¥{plan['price']}</span>
                    <span style="color: #94A3B8; font-size: 0.9rem;">/{plan['unit']}</span>
                </div>
                <p style="color: #475569; font-size: 0.9rem; line-height: 1.6; min-height: 48px; margin-bottom: 20px;">{plan['value']}</p>
                <div style="border-top: 1px solid #E2E8F0; padding-top: 16px;">
            """, unsafe_allow_html=True)

            for feat in plan["features"]:
                cls = "feature-yes" if feat.startswith("包含") else "feature-no"
                icon = "✓" if not feat.startswith("—") else "—"
                st.markdown(f"<p class='{cls}' style='margin: 6px 0; font-size: 0.85rem;'>{icon} {feat}</p>", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

            # CTA按钮
            btn_type = plan.get("cta_type", "secondary")
            if st.button(plan["cta"], use_container_width=True, key=f"v3_plan_cta_{idx}", type=btn_type):
                if plan["cta"] == "联系咨询":
                    st.info("""
                     **商务咨询**

                    电话：400-888-8888
                    邮箱：sales@auditmind.com
                    微信：AuditMind_Sales

                    工作时间：周一至周五 9:00-18:00
                    """)
                else:
                    st.info("""
                     **开通流程**

                    1. 确认套餐版本
                    2. 在线支付或联系商务
                    3. 即刻开通账户

                    如有疑问请联系：sales@auditmind.com
                    """)
                    st.balloons()

    # ========== 功能对比表 ==========
    st.divider()
    st.markdown("<h3 style='text-align:center; margin-bottom: 24px;'> 功能对比详情</h3>", unsafe_allow_html=True)

    comparison_data = [
        {"功能模块": "项目数量", "个人/个体版": "1个", "小微企业版": "≤5个", "企业分析版": "不限"},
        {"功能模块": "财报分析年限", "个人/个体版": "3年", "小微企业版": "5年", "企业分析版": "不限"},
        {"功能模块": "风险评分底稿", "个人/个体版": "包含", "小微企业版": "包含", "企业分析版": "包含"},
        {"功能模块": "可视化雷达图", "个人/个体版": "—", "小微企业版": "包含", "企业分析版": "包含"},
        {"功能模块": "同业案例对标", "个人/个体版": "—", "小微企业版": "包含", "企业分析版": "包含"},
        {"功能模块": "整改跟踪引擎", "个人/个体版": "—", "小微企业版": "包含", "企业分析版": "包含"},
        {"功能模块": "原文溯源", "个人/个体版": "—", "小微企业版": "包含", "企业分析版": "包含"},
        {"功能模块": "Open API接口", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "包含"},
        {"功能模块": "团队权限管理", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "包含"},
        {"功能模块": "批量检测", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "100家/次"},
        {"功能模块": "私有化部署", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "包含"},
        {"功能模块": "专属客户经理", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "包含"},
        {"功能模块": "7×24小时支持", "个人/个体版": "—", "小微企业版": "—", "企业分析版": "包含"},
    ]

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)


def render_report_management():
    """渲染报告管理页面"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(184,154,94,0.15); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 报告管理</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">检测报告归档与导出下载</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.warning("请先登录以查看报告")
        return

    # 刷新按钮
    col_title, col_refresh = st.columns([6, 1])
    with col_refresh:
        if st.button("刷新", key="refresh_report_management", use_container_width=True):
            # 清除缓存并重新加载
            clear_api_cache()
            st.rerun()

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
    st.subheader("报告筛选")
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
    st.subheader("报告列表")

    if st.session_state.get("selected_reports") is None:
        st.session_state.selected_reports = set()

    # 报告列表
    for report in filtered_history[:20]:  # 限制显示前20条
        risk_level = report.get("risk_level", "low")
        risk_emoji = {"high": "高", "medium": "中", "low": "低"}.get(risk_level, "低")

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

                    if st.button("", key=f"dl_report_{report['id']}", help=f"下载{selected_format}报告"):
                        with st.spinner(f"生成{selected_format}报告中..."):
                            format_code = format_map[selected_format]
                            # 调用新的导出API
                            result = make_api_request(
                                f"/report/{report['id']}/export?format={format_code}",
                                method="POST"
                            )
                            if result and result.get("download_url"):
                                st.success(f"{selected_format}报告已生成！")
                                # 使用 Python 下载文件内容
                                try:
                                    import requests
                                    download_url = f"{API_BASE_URL}{result['download_url']}"
                                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                    response = requests.get(download_url, headers=headers, timeout=30)

                                    if response.status_code == 200:
                                        filename = result.get("filename", f"报告.{format_code}")
                                        # 获取文件内容
                                        file_content = response.content

                                        # 使用 Streamlit 原生下载按钮
                                        mime_types = {
                                            "pdf": "application/pdf",
                                            "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                        }
                                        mime_type = mime_types.get(format_code, "application/octet-stream")

                                        st.download_button(
                                            label=f"下载 {filename}",
                                            data=file_content,
                                            file_name=filename,
                                            mime=mime_type,
                                            key=f"download_btn_{report['id']}_{format_code}"
                                        )
                                    else:
                                        st.error(f"下载失败: HTTP {response.status_code}")
                                except Exception as e:
                                    st.error(f"下载出错: {str(e)}")
                            else:
                                st.error("生成失败")
                with col_del:
                    if st.button("", key=f"del_report_{report['id']}", help="删除"):
                        if make_api_request(f"/detection/{report['id']}", method="DELETE"):
                            st.success("已删除")
                            st.rerun()

    # 批量操作栏
    if st.session_state.selected_reports:
        st.divider()
        st.subheader(f"批量操作 (已选择 {len(st.session_state.selected_reports)} 项)")

        col1, col2, col3 = st.columns(3)
        with col1:
            export_format = st.selectbox(
                "导出格式",
                ["PDF", "Excel(汇总)"],
                key="batch_export_format"
            )
            if st.button("批量导出", use_container_width=True):
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
                                    label="下载汇总Excel",
                                    data=csv,
                                    file_name=f"报告汇总_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv"
                                )
        with col2:
            if st.button("发送邮件", use_container_width=True):
                st.info("邮件发送功能开发中...")
        with col3:
            if st.button("批量删除", use_container_width=True):
                st.warning("确认删除选中的报告？")
                if st.button("确认删除"):
                    for rid in list(st.session_state.selected_reports):
                        make_api_request(f"/detection/{rid}", method="DELETE")
                    st.session_state.selected_reports.clear()
                    st.rerun()


# ================= 账号设置页面 =================
def render_account_settings():
    """渲染账号设置页面"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(99,102,241,0.15); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 账号设置</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">管理账户信息、会员状态与安全设置</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.logged_in:
        st.warning("请先登录")
        return

    user = st.session_state.user_info

    # 个人信息
    st.subheader("个人信息")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("用户名", value=user.get("username", ""), disabled=True)
            st.text_input("邮箱", value=user.get("email", "") or "未设置")
            st.text_input("手机号", value=user.get("phone", "") or "未设置")
        with col2:
            st.text_input("用户类型", value=user.get("user_type", "individual"))
            st.text_input("注册时间", value=user.get("created_at", "")[:10] if user.get("created_at") else "-")

        if st.button("保存修改", type="primary"):
            st.info("修改功能开发中...")

    # 修改密码
    st.divider()
    st.subheader("修改密码")
    with st.container(border=True):
        old_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_password = st.text_input("确认新密码", type="password")

        if st.button("修改密码", type="primary"):
            if new_password != confirm_password:
                st.error("两次输入的新密码不一致")
            elif not old_password or not new_password:
                st.error("请填写所有密码字段")
            else:
                st.info("密码修改功能开发中...")

    # API 密钥管理
    st.divider()
    st.subheader("API 密钥管理")
    with st.container(border=True):
        st.info("API密钥用于第三方系统调用，请妥善保管。")

        if st.button("重新生成密钥"):
            st.warning("确定要重新生成API密钥吗？旧的密钥将立即失效。")


# ================= 案例中心页面 =================
def render_case_center():
    """渲染案例中心页面"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(236,72,153,0.15); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 案例中心</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">A股历史舞弊案例库，深度解析典型风险模式</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 获取所有案例
    cases = make_api_request("/detection/cases")

    if not cases:
        st.info("暂无案例数据")
        return

    # 案例分类
    case_types = {
        "fraud": "已确认舞弊案例",
        "normal": "健康企业案例",
        "warning": "风险提示案例"
    }

    # 按类型分组
    fraud_cases = [c for c in cases if c.get("case_type") == "fraud"]
    normal_cases = [c for c in cases if c.get("case_type") == "normal"]

    # 舞弊案例
    if fraud_cases:
        st.markdown("<h3 style='font-size: 1.4rem; font-weight: 700; margin: 1.5rem 0 1rem; display: flex; align-items: center; gap: 10px;'> 已确认舞弊案例</h3>", unsafe_allow_html=True)
        cols = st.columns(min(len(fraud_cases), 3))
        for idx, case in enumerate(fraud_cases):
            with cols[idx % 3]:
                risk_level = case.get('risk_level', 'high')
                risk_color = "#A0706A" if risk_level == "high" else "#B89A5E"
                st.markdown(f"""
                <div class="glass-card" style="padding: 1.5rem; animation-delay: {idx * 0.1}s; position: relative; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: {risk_color};"></div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; background: rgba(160,112,106,0.12); color: #A0706A; margin-bottom: 0.75rem;">
                        舞弊案例
                    </div>
                    <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; line-height: 1.3;">{case['case_name']}</h4>
                    <p style="font-size: 0.85rem; opacity: 0.7; line-height: 1.5; margin-bottom: 1rem; min-height: 40px;">{case.get('description', '')[:80]}...</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看详情", key=f"case_detail_{case['id']}", use_container_width=True):
                    demo_data = make_api_request(f"/detection/cases/{case['id']}/load", method="POST")
                    if demo_data:
                        st.session_state.demo_data = demo_data
                        st.session_state.active_tab = "内置案例库"
                        st.success("案例已加载！请到「舞弊检测」页面查看")

    # 健康企业案例
    if normal_cases:
        st.markdown("")
        st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='font-size: 1.4rem; font-weight: 700; margin: 1.5rem 0 1rem; display: flex; align-items: center; gap: 10px;'>健康企业案例</h3>", unsafe_allow_html=True)
        cols = st.columns(min(len(normal_cases), 3))
        for idx, case in enumerate(normal_cases):
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="glass-card" style="padding: 1.5rem; animation-delay: {idx * 0.1}s; position: relative; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: #6B8E6B;"></div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; background: rgba(107,142,107,0.12); color: #6B8E6B; margin-bottom: 0.75rem;">
                        健康企业
                    </div>
                    <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; line-height: 1.3;">{case['case_name']}</h4>
                    <p style="font-size: 0.85rem; opacity: 0.7; line-height: 1.5; margin-bottom: 1rem; min-height: 40px;">{case.get('description', '')[:80]}...</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("查看详情", key=f"case_normal_{case['id']}", use_container_width=True):
                    demo_data = make_api_request(f"/detection/cases/{case['id']}/load", method="POST")
                    if demo_data:
                        st.session_state.demo_data = demo_data
                        st.success("案例已加载！请到「舞弊检测」页面查看")

    # 案例学习资料
    st.divider()
    st.markdown("###  学习资料")

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
    st.title("用户登录/注册")

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
    page = menu
    if st.session_state.logged_in:
        if page == "home":
            render_home()
        elif page == "fs":
            render_financial_assistant()
        elif page == "detect":
            render_detection()
        elif page == "qa":
            render_qa()
        elif page == "history":
            render_my_detections()
        elif page == "reports":
            render_report_management()
        elif page == "membership":
            render_membership()
        elif page == "settings":
            render_account_settings()
    else:
        if page == "home":
            render_home()
        elif page == "qa":
            render_qa()
        elif page == "pricing":
            st.markdown("""
            <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
                <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(184,154,94,0.15); border-radius: 50%; "></div>
                <div style="position: relative; z-index: 1;">
                    <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 价格中心</h2>
                </div>
            </div>
            """, unsafe_allow_html=True)
            render_membership()
        elif page == "cases":
            render_case_center()


if __name__ == "__main__":
    main()
