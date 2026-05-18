"""
Audit Mind - Financial Fraud Detection SaaS
"""
import streamlit as st
import streamlit.components.v1 as components
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
/* ===== Design Tokens - Cinematic Professional ===== */
:root {
    --bg: #FFFFFF;
    --bg-soft: #F8FAFC;
    --bg-muted: #F1F5F9;
    --bg-dark: #0F172A;
    --text: #0F172A;
    --text-secondary: #475569;
    --text-muted: #94A3B8;
    --accent: #2563EB;
    --accent-hover: #1D4ED8;
    --accent-light: #EFF6FF;
    --accent-glow: rgba(37,99,235,0.15);
    --border: #E2E8F0;
    --border-light: #F1F5F9;
    --success: #10B981;
    --warning: #F59E0B;
    --danger: #EF4444;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.05);
    --shadow-lg: 0 12px 32px rgba(0,0,0,0.08);
    --shadow-glow: 0 0 40px rgba(37,99,235,0.12);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
}

/* ===== Hide Sidebar ===== */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ===== FULL WIDTH Layout ===== */
.main .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}
.stApp {
    background: #FFFFFF !important;
}
.stApp, .stApp * {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "SF Pro Display", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ===== Typography Scale - Larger & Bolder ===== */
h1 { font-weight: 800 !important; letter-spacing: -0.03em !important; font-size: 3.5rem !important; color: var(--text) !important; line-height: 1.05 !important; }
h2 { font-weight: 700 !important; letter-spacing: -0.02em !important; font-size: 2.6rem !important; color: var(--text) !important; }
h3 { font-weight: 600 !important; font-size: 1.6rem !important; color: var(--text) !important; }
p, li, td, th, label, .stMarkdown { font-size: 1.05rem !important; line-height: 1.7 !important; color: var(--text-secondary) !important; }

/* Content width constraints inside full-width sections */
.content-wrap { max-width: 1280px; margin: 0 auto; padding: 0 5rem; }
.content-wrap-wide { max-width: 1400px; margin: 0 auto; padding: 0 5rem; }

/* Side decoration for full-width sections */
.side-glow-left {
    position: absolute; left: 0; top: 20%; bottom: 20%; width: 3px;
    background: linear-gradient(180deg, transparent, rgba(37,99,235,0.15), transparent);
}
.side-glow-right {
    position: absolute; right: 0; top: 20%; bottom: 20%; width: 3px;
    background: linear-gradient(180deg, transparent, rgba(37,99,235,0.15), transparent);
}
.corner-accent-tl {
    position: absolute; top: 24px; left: 24px; width: 40px; height: 40px;
    border-top: 2px solid rgba(96,165,250,0.25);
    border-left: 2px solid rgba(96,165,250,0.25);
    border-radius: 4px 0 0 0;
}
.corner-accent-br {
    position: absolute; bottom: 24px; right: 24px; width: 40px; height: 40px;
    border-bottom: 2px solid rgba(96,165,250,0.25);
    border-right: 2px solid rgba(96,165,250,0.25);
    border-radius: 0 0 4px 0;
}

/* ===== Buttons ===== */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    letter-spacing: 0.01em;
    border: 1px solid transparent !important;
    font-size: 0.95rem !important;
}
.stButton > button:hover { transform: translateY(-2px); }
.stButton > button:active { transform: translateY(0) scale(0.97); }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 16px rgba(37,99,235,0.3) !important;
}
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] div { color: #FFFFFF !important; }
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
    box-shadow: 0 8px 28px rgba(37,99,235,0.4) !important;
}
.stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: 0 2px 12px rgba(37,99,235,0.1) !important;
}

/* ===== Inputs ===== */
.stTextInput > div > div > input, .stTextArea > div > div > textarea,
.stNumberInput > div > div > input, .stSelectbox > div > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    background: #FFFFFF !important;
    color: var(--text) !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus,
.stNumberInput > div > div > input:focus, .stSelectbox > div > div > div:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(37,99,235,0.08) !important;
}

/* ===== Cards ===== */
.glass-card, .feature-card, .stat-card, .pricing-card {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 2rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03) !important;
    transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.35s ease, border-color 0.35s ease !important;
}
.glass-card:hover, .feature-card:hover, .stat-card:hover, .pricing-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 48px rgba(37,99,235,0.12), 0 8px 24px rgba(0,0,0,0.06) !important;
    border-color: #BFDBFE !important;
}

/* ===== Badge System ===== */
.badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 100px;
    font-size: 0.85rem; font-weight: 600; letter-spacing: 0.3px;
}
.badge-primary { background: var(--accent-light); color: var(--accent); border: 1px solid #BFDBFE; }
.badge-success { background: #F0FDF4; color: var(--success); border: 1px solid #BBF7D0; }
.badge-warning { background: #FFFBEB; color: var(--warning); border: 1px solid #FDE68A; }
.badge-danger { background: #FEF2F2; color: var(--danger); border: 1px solid #FECACA; }

/* ===== Tables ===== */
[data-testid="stDataFrame"] th { background: var(--bg-soft) !important; color: var(--text) !important; font-weight: 600 !important; border-bottom: 1px solid var(--border) !important; }
[data-testid="stDataFrame"] td { border-bottom: 1px solid var(--border-light) !important; }
[data-testid="stDataFrame"] tr:hover { background: var(--bg-soft) !important; }

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid var(--border) !important; gap: 8px !important; }
.stTabs [data-baseweb="tab"] { color: var(--text-muted) !important; font-weight: 500 !important; padding: 0.8rem 1.5rem !important; border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important; font-size: 0.95rem !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--accent) !important; height: 2.5px !important; }
.stTabs [aria-selected="true"] { color: var(--accent) !important; }

/* ===== Expanders ===== */
.streamlit-expanderHeader { background: var(--bg-soft) !important; border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important; font-weight: 500 !important; }
.streamlit-expanderHeader:hover { border-color: var(--accent) !important; }

/* ===== Alerts ===== */
.stAlert { border-radius: var(--radius-sm) !important; border: 1px solid !important; }

/* ===== Markdown Code ===== */
.stMarkdown code { background: var(--bg-soft) !important; color: var(--text) !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.85em !important; }
.stMarkdown pre { background: var(--bg-soft) !important; border-radius: var(--radius-md) !important; padding: 1rem !important; border: 1px solid var(--border) !important; }

/* ===== Animations ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-30px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(37,99,235,0.2); }
    50% { box-shadow: 0 0 0 16px rgba(37,99,235,0); }
}
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.animate-fadeInUp { animation: fadeInUp 0.7s ease-out both; }
.animate-fadeIn { animation: fadeIn 0.5s ease-out both; }
.animate-slideInLeft { animation: slideInLeft 0.6s ease-out both; }
.animate-pulse { animation: pulse 2.5s infinite; }
.animate-float { animation: float 4s ease-in-out infinite; }

/* Thinking dots animation */
@keyframes thinkingBounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
}

/* ===== Enhanced Interactions ===== */
.hover-lift { transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.35s ease; }
.hover-lift:hover { transform: translateY(-6px); box-shadow: 0 16px 40px rgba(0,0,0,0.1); }

/* Gradient text for hero */
.gradient-text {
    background: linear-gradient(135deg, #2563EB, #3B82F6, #60A5FA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.gradient-text-animated {
    background: linear-gradient(90deg, #2563EB, #60A5FA, #3B82F6, #2563EB);
    background-size: 300% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 4s ease infinite;
}

/* ===== Top Header Bar ===== */
.top-nav-bar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: rgba(255,255,255,0.95); backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-light);
    padding: 0 4rem;
    height: 68px;
    display: flex; align-items: center; justify-content: space-between;
}
.top-nav-accent {
    position: fixed; top: 0; left: 0; right: 0; z-index: 10000;
    height: 3px;
    background: linear-gradient(90deg, #2563EB, #3B82F6, #60A5FA, #3B82F6, #2563EB);
}
.top-nav-logo { font-size: 1.35rem; font-weight: 800; color: var(--text); letter-spacing: -0.5px; text-decoration: none; }
.top-nav-link { font-size: 0.95rem; font-weight: 500; color: var(--text-secondary); text-decoration: none; padding: 8px 14px; border-radius: 8px; transition: all 0.2s ease; }
.top-nav-link:hover { color: var(--accent); background: var(--accent-light); }
.top-nav-link.active { color: var(--accent); font-weight: 600; }
.top-nav-link.active::after { content: ''; display: block; width: 100%; height: 2.5px; background: var(--accent); border-radius: 2px; margin-top: 2px; }

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
    background: linear-gradient(90deg, transparent, rgba(37,99,235,0.04), transparent);
    transition: left 0.6s ease;
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
    box-shadow: 0 0 24px rgba(37,99,235,0.12);
    transition: box-shadow 0.3s ease;
}
.glow-blue:hover {
    box-shadow: 0 0 40px rgba(37,99,235,0.2);
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

/* ===== Section Backgrounds ===== */
.section-gradient-blue {
    background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 50%, #DBEAFE 100%);
}
.section-gradient-dark {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    color: #FFFFFF;
}
.section-gradient-dark h1, .section-gradient-dark h2, .section-gradient-dark h3 { color: #FFFFFF !important; }
.section-gradient-dark p { color: #94A3B8 !important; }
.section-soft {
    background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
}
.section-grid {
    background-image: radial-gradient(circle, #E2E8F0 1px, transparent 1px);
    background-size: 48px 48px;
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
if "tax_chat_history" not in st.session_state:
    st.session_state.tax_chat_history = []
if "auth_initialized" not in st.session_state:
    st.session_state.auth_initialized = False

# ================= 辅助函数 =================
def _render_empty_state(icon: str, title: str, description: str, action_hint: str = ""):
    """渲染美观的空状态卡片"""
    action_html = f'<p style="color: #2563EB; font-size: 0.9rem; font-weight: 600; margin-top: 8px;">{action_hint}</p>' if action_hint else ""
    st.markdown(f"""
    <div style="text-align: center; padding: 56px 24px; background: #F8FAFC; border-radius: 20px; border: 1.5px dashed #CBD5E1; margin: 24px 0;">
        <div style="font-size: 3rem; margin-bottom: 16px; line-height: 1;">{icon}</div>
        <h3 style="color: #0F172A; font-size: 1.15rem; font-weight: 700; margin-bottom: 8px;">{title}</h3>
        <p style="color: #64748B; font-size: 0.95rem; max-width: 420px; margin: 0 auto;">{description}</p>
        {action_html}
    </div>
    """, unsafe_allow_html=True)


def make_api_request(endpoint, method="GET", data=None, headers=None, timeout=60):
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


def _render_page_header(title: str, subtitle: str = ""):
    """渲染全宽页面标题区 - 大气简洁"""
    subtitle_html = f'<p style="color: #64748B; font-size: 1.05rem; margin: 0.5rem 0 0 0; line-height: 1.6;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div style="margin: -2rem -2rem 2.5rem -2rem; padding: 2.5rem 2rem; background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%); border-bottom: 1px solid #E2E8F0; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -40px; right: 5%; width: 180px; height: 180px; background: rgba(37,99,235,0.08); border-radius: 50%;"></div>
        <div style="position: absolute; bottom: -30px; left: 10%; width: 120px; height: 120px; background: rgba(96,165,250,0.06); border-radius: 50%;"></div>
        <div style="position: relative; z-index: 1;">
            <h1 style="font-size: 2.2rem; font-weight: 800; color: #0F172A; margin: 0; letter-spacing: -1px; line-height: 1.2;">{title}</h1>
            {subtitle_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


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
def render_header():
    """渲染顶部水平导航栏 - 替代侧边栏"""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    # 顶部渐变装饰条
    st.markdown("""
    <div style="position: fixed; top: 0; left: 0; right: 0; z-index: 10000; height: 3px; background: linear-gradient(90deg, #2563EB, #3B82F6, #60A5FA, #3B82F6, #2563EB);"
    ></div>
    """, unsafe_allow_html=True)

    # 品牌 + 导航 + 用户操作
    col_logo, col_nav, col_user = st.columns([1.2, 5, 1.3])

    with col_logo:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;cursor:pointer;" onclick="window.parent.postMessage({type:'streamlit:setComponentValue',value:'home'},'*');">
            <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#2563EB,#1D4ED8);display:flex;align-items:center;justify-content:center;color:#FFFFFF;font-weight:800;font-size:1rem;box-shadow:0 4px 12px rgba(37,99,235,0.25);">A</div>
            <span style="font-size:1.25rem;font-weight:800;color:#0F172A;letter-spacing:-0.5px;">Audit Mind</span>
        </div>
        """, unsafe_allow_html=True)

    with col_nav:
        if st.session_state.logged_in:
            pages = [
                ("首页", "home"),
                ("财务助手", "fs"),
                ("舞弊检测", "detect"),
                ("AI 问答", "qa"),
                ("我的检测", "history"),
                ("报告", "reports"),
                ("会员", "membership"),
            ]
        else:
            pages = [
                ("首页", "home"),
                ("AI 问答", "qa"),
                ("价格", "pricing"),
                ("案例", "cases"),
            ]

        current = st.session_state.current_page
        nav_cols = st.columns(len(pages))
        for i, (label, key) in enumerate(pages):
            with nav_cols[i]:
                active = current == key
                if active:
                    st.markdown(f"""
                    <div style="text-align:center;padding:6px 2px;">
                        <span style="font-size:0.95rem;font-weight:700;color:#2563EB;cursor:default;">{label}</span>
                        <div style="width:20px;height:3px;background:linear-gradient(90deg,#2563EB,#3B82F6);border-radius:2px;margin:4px auto 0;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    if st.button(label, key=f"nav_{key}", use_container_width=True):
                        st.session_state.current_page = key
                        st.rerun()

    with col_user:
        if st.session_state.logged_in:
            user_cols = st.columns([2, 1])
            with user_cols[0]:
                username = st.session_state.user_info.get('username', '用户')
                st.markdown(f"""
                <div style="display:flex;align-items:center;justify-content:flex-end;gap:8px;padding-top:4px;">
                    <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#2563EB,#3B82F6);display:flex;align-items:center;justify-content:center;color:#FFFFFF;font-weight:700;font-size:0.85rem;">{username[0].upper()}</div>
                    <span style="font-size:0.9rem;font-weight:600;color:#0F172A;">{username}</span>
                </div>
                """, unsafe_allow_html=True)
            with user_cols[1]:
                if st.button("退出", key="header_logout", use_container_width=True):
                    AuthManager.clear_auth()
                    st.session_state.logged_in = False
                    st.session_state.token = None
                    st.session_state.user_info = None
                    st.rerun()
        else:
            if st.button("登录 / 注册", key="header_login", use_container_width=True, type="primary"):
                st.session_state.show_login_modal = True
                st.rerun()

    st.markdown("""
    <div style="position: relative; height: 3px; background: linear-gradient(90deg, transparent, #BFDBFE, #3B82F6, #60A5FA, #3B82F6, #BFDBFE, transparent); margin: 0.25rem 0 0 0; opacity: 0.7;"></div>
    <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, #2563EB, #3B82F6, #60A5FA); opacity: 0.08;"></div>
    """, unsafe_allow_html=True)


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




# ================= 首页 =================
def render_home():
    """渲染首页 - Cinematic Full-Width Design"""

    # ========== HERO SECTION (Full Width with Dynamic Background) ==========
    hero_html = '''
    <div style="width: 100%; min-height: 580px; position: relative; overflow: hidden; background: linear-gradient(135deg, #0F172A 0%, #1E293B 40%, #0F172A 100%); display: flex; align-items: center; justify-content: center;">
        <!-- Animated grid background -->
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.15; background-image: linear-gradient(rgba(59,130,246,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.3) 1px, transparent 1px); background-size: 60px 60px;"></div>
        <!-- Floating orbs -->
        <div style="position: absolute; top: 10%; left: 15%; width: 300px; height: 300px; background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%); border-radius: 50%; animation: float 6s ease-in-out infinite;"></div>
        <div style="position: absolute; bottom: 15%; right: 10%; width: 250px; height: 250px; background: radial-gradient(circle, rgba(96,165,250,0.2) 0%, transparent 70%); border-radius: 50%; animation: float 8s ease-in-out infinite 2s;"></div>
        <div style="position: absolute; top: 40%; right: 25%; width: 150px; height: 150px; background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%); border-radius: 50%; animation: float 5s ease-in-out infinite 1s;"></div>
        <!-- Side glow lines -->
        <div class="side-glow-left" style="left: 3rem;"></div>
        <div class="side-glow-right" style="right: 3rem;"></div>
        <!-- Corner accents -->
        <div class="corner-accent-tl" style="top: 2rem; left: 2rem;"></div>
        <div class="corner-accent-br" style="bottom: 2rem; right: 2rem;"></div>

        <div style="position: relative; z-index: 2; text-align: center; max-width: 900px; padding: 0 6rem;">
            <div style="display: inline-flex; align-items: center; gap: 10px; padding: 10px 24px; border-radius: 100px; font-size: 0.9rem; font-weight: 600; background: rgba(37,99,235,0.15); border: 1px solid rgba(96,165,250,0.3); color: #60A5FA; margin-bottom: 2rem; letter-spacing: 0.03em; animation: fadeInUp 0.8s ease-out both;">
                <span style="width: 8px; height: 8px; background: #3B82F6; border-radius: 50%; display: inline-block; animation: pulse 2s infinite;"></span>
                AI-Powered Financial Audit Intelligence
            </div>
            <h1 style="font-size: 4.5rem; font-weight: 800; letter-spacing: -3px; line-height: 1.05; margin-bottom: 1.25rem; color: #FFFFFF; animation: fadeInUp 0.8s ease-out 0.15s both;">
                智能识别财务舞弊
            </h1>
            <h2 style="font-size: 2.4rem; font-weight: 500; color: #94A3B8; letter-spacing: -1px; margin-bottom: 1.5rem; animation: fadeInUp 0.8s ease-out 0.3s both;">
                守护每一笔资金的安全
            </h2>
            <p style="font-size: 1.25rem; color: #94A3B8; line-height: 1.8; max-width: 620px; margin: 0 auto 2.5rem; font-weight: 400; animation: fadeInUp 0.8s ease-out 0.45s both;">
                基于生成式 AI 的上市公司财务舞弊识别系统<br>双模分析 · SHAP 可解释 · 风险标签可视化
            </p>
            <div style="animation: fadeInUp 0.8s ease-out 0.6s both; color: #64748B; font-size: 0.95rem; margin-top: 1rem;">
                向下滚动探索更多 ↓
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(hero_html, height=580, scrolling=False)

    # ========== ANIMATED STATS BAR (Full Width Blue Gradient) ==========
    stats_html = '''
    <div id="stats" style="width: 100%; padding: 64px 0; background: linear-gradient(90deg, #2563EB, #3B82F6, #1D4ED8); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.1; background-image: radial-gradient(circle, #FFFFFF 1px, transparent 1px); background-size: 30px 30px;"></div>
        <div style="max-width: 1200px; margin: 0 auto; padding: 0 6rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 2rem; position: relative; z-index: 1;">
            <div style="text-align: center;">
                <div class="count-up" data-target="92" style="font-size: 3.5rem; font-weight: 800; color: #FFFFFF; line-height: 1;">0</div>
                <div style="font-size: 1.2rem; color: #FFFFFF; font-weight: 700; margin-top: 4px;">%</div>
                <div style="font-size: 1.05rem; color: rgba(255,255,255,0.85); margin-top: 8px; font-weight: 500;">AI 识别准确率</div>
            </div>
            <div style="text-align: center;">
                <div class="count-up" data-target="12847" style="font-size: 3.5rem; font-weight: 800; color: #FFFFFF; line-height: 1;">0</div>
                <div style="font-size: 1.05rem; color: rgba(255,255,255,0.85); margin-top: 8px; font-weight: 500;">已分析财报</div>
            </div>
            <div style="text-align: center;">
                <div class="count-up" data-target="4562" style="font-size: 3.5rem; font-weight: 800; color: #FFFFFF; line-height: 1;">0</div>
                <div style="font-size: 1.05rem; color: rgba(255,255,255,0.85); margin-top: 8px; font-weight: 500;">覆盖 A 股企业</div>
            </div>
            <div style="text-align: center;">
                <div class="count-up" data-target="7" style="font-size: 3.5rem; font-weight: 800; color: #FFFFFF; line-height: 1;">0</div>
                <div style="font-size: 1.05rem; color: rgba(255,255,255,0.85); margin-top: 8px; font-weight: 500;">风险分析维度</div>
            </div>
        </div>
    </div>
    <script>
    (function() {
        const counters = document.querySelectorAll('.count-up');
        const animate = (el) => {
            const target = parseInt(el.getAttribute('data-target'));
            const duration = 2000;
            const start = performance.now();
            const easeOutQuart = t => 1 - Math.pow(1 - t, 4);
            const step = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const eased = easeOutQuart(progress);
                el.textContent = Math.floor(eased * target).toLocaleString();
                if (progress < 1) requestAnimationFrame(step);
            };
            requestAnimationFrame(step);
        };
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animate(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        counters.forEach(c => observer.observe(c));
    })();
    </script>
    '''
    st.components.v1.html(stats_html, height=200, scrolling=False)

    # Demo hint
    if not st.session_state.logged_in:
        st.info("**快速体验** — 点击右上角登录/注册，选择「一键登录演示账号」即可体验全部功能（AuditMind / 123）")

    # CTA Buttons (functional Streamlit buttons below hero)
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("开始检测", type="primary", use_container_width=True, key="hero_cta_detect"):
            if st.session_state.logged_in:
                st.session_state.current_page = "detect"
                st.rerun()
            else:
                st.session_state.show_login_modal = True
                st.rerun()
    with c2:
        if st.button("查看价格", use_container_width=True, key="hero_cta_more"):
            st.session_state.current_page = "pricing"
            st.rerun()

    # ========== QUICK START GUIDE ==========
    st.markdown('<div class="content-wrap" style="padding-top: 3rem; padding-bottom: 3rem;">', unsafe_allow_html=True)
    st.markdown("<h2 style='font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; color: #0F172A; letter-spacing: -1px;'>快速上手指南</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 1.05rem; margin-bottom: 2rem;'>新用户？跟着下面三步，3 分钟完成第一次财务舞弊检测</p>", unsafe_allow_html=True)

    guide_cols = st.columns(3)
    guides = [
        ("1", "📤 录入数据", "注册登录后，选择「舞弊检测」上传企业年报（PDF/Excel/Word），或在「财务助手」中手动录入四表一注数据。", "#EFF6FF", "#2563EB"),
        ("2", "🤖 AI 分析", "系统自动提取 7 维风险特征，结合 XGBoost 模型与 SHAP 可解释性分析，对标历史 IPO 被否案例。", "#F0FDF4", "#10B981"),
        ("3", "📊 查看报告", "获取可视化风险标签（如「存贷双高」）、舞弊概率评分、整改建议，支持 PDF/Word/Excel 下载。", "#FFFBEB", "#F59E0B"),
    ]
    for i, (num, title, desc, bg, color) in enumerate(guides):
        with guide_cols[i]:
            st.markdown(f'''
            <div style="background: {bg}; border: 1px solid {color}33; border-radius: 16px; padding: 1.75rem; height: 100%; animation: fadeInUp 0.6s ease-out {i*0.12}s both;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 0.75rem;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: {color}; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700;">{num}</div>
                    <h4 style="font-size: 1.15rem; font-weight: 700; color: #0F172A; margin: 0;">{title}</h4>
                </div>
                <p style="font-size: 0.95rem; color: #475569; line-height: 1.7; margin: 0;">{desc}</p>
            </div>
            ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== FEATURES SECTION (With Blue Gradient Background) ==========
    features_section_html = '''
    <div id="features" style="width: 100%; padding: 100px 0; background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 50%, #EFF6FF 100%); position: relative;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #BFDBFE, transparent);"></div>
        <div class="content-wrap" style="max-width: 1280px; margin: 0 auto; padding: 0 6rem;">
            <div style="text-align: center; margin-bottom: 3.5rem;">
                <h2 style="font-size: 2.6rem; font-weight: 700; color: #0F172A; letter-spacing: -1px; margin-bottom: 0.75rem;">核心能力</h2>
                <p style="color: #64748B; font-size: 1.15rem;">四大核心模块，覆盖财务舞弊识别全链路</p>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                <div class="feature-card" style="padding: 2.25rem; animation: fadeInUp 0.6s ease-out 0.1s both;">
                    <div style="width: 52px; height: 52px; border-radius: 12px; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 1.25rem;">📈</div>
                    <h4 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.6rem; color: #0F172A;">双模输入分析</h4>
                    <p style="font-size: 1rem; color: #475569; line-height: 1.7;">结构化财务数据 + MD&A 非结构化文本，全方位透视企业风险，不留死角。</p>
                </div>
                <div class="feature-card" style="padding: 2.25rem; animation: fadeInUp 0.6s ease-out 0.2s both;">
                    <div style="width: 52px; height: 52px; border-radius: 12px; background: linear-gradient(135deg, #F0FDF4, #DCFCE7); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 1.25rem;">🔍</div>
                    <h4 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.6rem; color: #0F172A;">AI 可解释性</h4>
                    <p style="font-size: 1rem; color: #475569; line-height: 1.7;">SHAP 特征重要性分析，每个预测都有明确依据，告别黑箱，审计师也能看懂 AI。</p>
                </div>
                <div class="feature-card" style="padding: 2.25rem; animation: fadeInUp 0.6s ease-out 0.3s both;">
                    <div style="width: 52px; height: 52px; border-radius: 12px; background: linear-gradient(135deg, #FFFBEB, #FEF3C7); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 1.25rem;">🚨</div>
                    <h4 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.6rem; color: #0F172A;">风险标签可视化</h4>
                    <p style="font-size: 1rem; color: #475569; line-height: 1.7;">自动生成「存贷双高」「现金流背离」等可读性强的风险标签，一目了然。</p>
                </div>
                <div class="feature-card" style="padding: 2.25rem; animation: fadeInUp 0.6s ease-out 0.4s both;">
                    <div style="width: 52px; height: 52px; border-radius: 12px; background: linear-gradient(135deg, #F3E8FF, #E9D5FF); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; margin-bottom: 1.25rem;">🤖</div>
                    <h4 style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.6rem; color: #0F172A;">AI 智能问答</h4>
                    <p style="font-size: 1rem; color: #475569; line-height: 1.7;">财务舞弊理论、案例解析、实操指导、税务咨询，7×24 随时解答。</p>
                </div>
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(features_section_html, height=780, scrolling=False)

    # ========== HOW IT WORKS (Dark Section for Contrast) ==========
    how_it_works_html = '''
    <div style="width: 100%; padding: 100px 0; background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.08; background-image: radial-gradient(circle, #3B82F6 1px, transparent 1px); background-size: 48px 48px;"></div>
        <div style="max-width: 1200px; margin: 0 auto; padding: 0 6rem; position: relative; z-index: 1;">
            <div style="text-align: center; margin-bottom: 3.5rem;">
                <h2 style="font-size: 2.6rem; font-weight: 700; margin-bottom: 0.75rem; color: #FFFFFF; letter-spacing: -1px;">三步完成智能检测</h2>
                <p style="color: #94A3B8; font-size: 1.15rem;">上传财务报告 → AI 深度解析 → 获取风险报告</p>
            </div>
            <div style="display: flex; align-items: flex-start; justify-content: center; gap: 0;">
                <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.6s ease-out 0.1s both;">
                    <div style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #2563EB, #1D4ED8); display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; box-shadow: 0 0 30px rgba(37,99,235,0.4);">
                        <span style="font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">1</span>
                    </div>
                    <h4 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.6rem; color: #FFFFFF;">📄 上传报告</h4>
                    <p style="font-size: 1rem; color: #94A3B8; line-height: 1.6; padding: 0 1rem;">支持 PDF 年报、Excel 财务表、Word 文档等多格式上传</p>
                </div>
                <div style="flex: 0.5; height: 2px; background: linear-gradient(90deg, #2563EB, #3B82F6); margin-top: 36px; opacity: 0.5;"></div>
                <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.6s ease-out 0.25s both;">
                    <div style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #2563EB, #1D4ED8); display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; box-shadow: 0 0 30px rgba(37,99,235,0.4);">
                        <span style="font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">2</span>
                    </div>
                    <h4 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.6rem; color: #FFFFFF;">🤖 AI 深度解析</h4>
                    <p style="font-size: 1rem; color: #94A3B8; line-height: 1.6; padding: 0 1rem;">7 维风险特征提取 + SHAP 可解释性分析 + IPO 对标</p>
                </div>
                <div style="flex: 0.5; height: 2px; background: linear-gradient(90deg, #3B82F6, #2563EB); margin-top: 36px; opacity: 0.5;"></div>
                <div style="flex: 1; text-align: center; position: relative; animation: fadeInUp 0.6s ease-out 0.4s both;">
                    <div style="width: 72px; height: 72px; border-radius: 50%; background: linear-gradient(135deg, #2563EB, #1D4ED8); display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem; box-shadow: 0 0 30px rgba(37,99,235,0.4);">
                        <span style="font-size: 1.4rem; font-weight: 700; color: #FFFFFF;">3</span>
                    </div>
                    <h4 style="font-size: 1.15rem; font-weight: 600; margin-bottom: 0.5rem; color: #FFFFFF;">📊 获取报告</h4>
                    <p style="font-size: 0.9rem; color: #94A3B8; line-height: 1.6; padding: 0 1rem;">可视化风险标签、整改建议、完整证据链下载</p>
                </div>
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(how_it_works_html, height=400, scrolling=False)

    # ========== USE CASES ==========
    st.markdown('<div class="content-wrap" style="padding-top: 4rem; padding-bottom: 3rem;">', unsafe_allow_html=True)
    st.markdown("<h2 style='font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; color: #0F172A; letter-spacing: -1px;'>适用场景</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 1.05rem; margin-bottom: 2rem;'>多行业多角色，满足各类审计与风控需求</p>", unsafe_allow_html=True)

    uc_cols = st.columns(4)
    use_cases = [
        ("🏛️", "监管机构", "非现场监管、风险预警、合规审查"),
        ("📋", "会计师事务所", "审计辅助分析、底稿复核、质量把控"),
        ("💰", "投资者", "个股风险检测、标的筛查、投前尽调"),
        ("🏢", "上市公司", "财务舞弊自查、信披优化、内控建设"),
    ]
    for i, (icon, title, desc) in enumerate(use_cases):
        with uc_cols[i]:
            st.markdown(f'''
            <div class="glass-card" style="text-align: center; padding: 2rem 1.25rem; animation: fadeInUp 0.5s ease-out {i*0.1}s both;">
                <div style="font-size: 2rem; margin-bottom: 0.75rem;">{icon}</div>
                <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.4rem; color: #0F172A;">{title}</h4>
                <p style="font-size: 0.9rem; color: #475569; line-height: 1.6;">{desc}</p>
            </div>
            ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== CASES SHOWCASE ==========
    st.markdown('<div class="content-wrap" style="padding-top: 2rem; padding-bottom: 3rem;">', unsafe_allow_html=True)
    st.markdown("<h2 style='font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; color: #0F172A; letter-spacing: -1px;'>经典案例库</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 1.05rem; margin-bottom: 2rem;'>基于真实历史案例构建的检测基准</p>", unsafe_allow_html=True)

    cases = get_cached_demo_cases(featured_only=True, _token=st.session_state.token)
    if cases:
        case_cols = st.columns(min(len(cases), 4))
        for idx, case in enumerate(cases[:4]):
            with case_cols[idx]:
                badge_bg = "rgba(239,68,68,0.1)" if case["case_type"] == "fraud" else "rgba(16,185,129,0.1)"
                badge_color = "#EF4444" if case["case_type"] == "fraud" else "#10B981"
                badge_text = "舞弊案例" if case["case_type"] == "fraud" else "正常案例"
                st.markdown(f'''
                <div class="glass-card" style="padding: 1.75rem; animation: fadeInUp 0.5s ease-out {idx*0.1}s both;">
                    <div style="display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; background: {badge_bg}; color: {badge_color}; margin-bottom: 0.75rem;">{badge_text}</div>
                    <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; line-height: 1.3; color: #0F172A;">{case['case_name']}</h4>
                    <p style="font-size: 0.85rem; color: #64748B; line-height: 1.6;">{case.get('description', '')[:60]}...</p>
                </div>
                ''', unsafe_allow_html=True)
    else:
        _render_empty_state("📚", "案例库加载中", "经典案例库正在准备中，您可以先上传企业年报体验实时检测功能。", "前往「舞弊检测」开始分析")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== TRUST BADGES (Full Width Light Blue) ==========
    trust_html = '''
    <div style="width: 100%; padding: 64px 0; background: linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%); position: relative;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, #BFDBFE, transparent);"></div>
        <div style="max-width: 1200px; margin: 0 auto; padding: 0 6rem;">
            <div style="text-align: center; margin-bottom: 2.5rem;">
                <h2 style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #0F172A; letter-spacing: -0.5px;">技术信任背书</h2>
                <p style="color: #64748B; font-size: 1rem;">源自顶尖学术成果，服务专业审计场景</p>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
                <div style="text-align: center; padding: 1.5rem; animation: fadeInUp 0.5s ease-out 0.1s both;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">📚</div>
                    <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; color: #0F172A;">学术认可</h4>
                    <p style="font-size: 0.9rem; color: #64748B; line-height: 1.6;">基于前沿财务舞弊识别研究成果</p>
                </div>
                <div style="text-align: center; padding: 1.5rem; animation: fadeInUp 0.5s ease-out 0.2s both;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔒</div>
                    <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; color: #0F172A;">数据安全</h4>
                    <p style="font-size: 0.9rem; color: #64748B; line-height: 1.6;">企业级加密存储，报告阅后即焚</p>
                </div>
                <div style="text-align: center; padding: 1.5rem; animation: fadeInUp 0.5s ease-out 0.3s both;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚡</div>
                    <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; color: #0F172A;">高效处理</h4>
                    <p style="font-size: 0.9rem; color: #64748B; line-height: 1.6;">单次检测仅需 30-60 秒</p>
                </div>
                <div style="text-align: center; padding: 1.5rem; animation: fadeInUp 0.5s ease-out 0.4s both;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎯</div>
                    <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 0.4rem; color: #0F172A;">精准识别</h4>
                    <p style="font-size: 0.9rem; color: #64748B; line-height: 1.6;">92%+ AI 识别准确率，可解释</p>
                </div>
            </div>
            <div style="text-align: center;">
                <p style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px;">Powered By</p>
                <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;">
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">Qwen-Plus</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">Qwen3-235B</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">XGBoost</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">SHAP</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">GMM</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">FastAPI</span>
                    <span style="display:inline-block;padding:6px 16px;border-radius:100px;font-size:0.8rem;font-weight:600;background:#FFFFFF;color:#2563EB;border:1px solid #BFDBFE;box-shadow:0 1px 3px rgba(0,0,0,0.04);">Streamlit</span>
                </div>
            </div>
        </div>
    </div>
    '''
    st.components.v1.html(trust_html, height=420, scrolling=False)

    # ========== FAQ + TESTIMONIALS (Content Wrap) ==========
    st.markdown('<div class="content-wrap" style="padding-top: 4rem; padding-bottom: 2rem;">', unsafe_allow_html=True)

    # FAQ
    st.markdown("<h2 style='font-size: 2.2rem; font-weight: 700; color: #0F172A; letter-spacing: -1px; margin-bottom: 0.5rem; text-align: center;'>常见问题</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 1.05rem; margin-bottom: 2rem; text-align: center;'>关于 Audit Mind 的使用、定价与技术的常见疑问</p>", unsafe_allow_html=True)

    faq_items = [
        ("Audit Mind 的舞弊检测准确率如何？", "Audit Mind 采用多模型集成架构，结合 GMM-SHAP 可解释性算法，在模拟测试环境中对已知舞弊案例的识别率达到行业领先水平。系统提供风险概率而非确定性结论，建议结合专业审计判断使用。"),
        ("免费版可以体验哪些功能？", "免费用户可体验 3 次完整的舞弊检测流程（含风险评分、SHAP 特征分析、风险标签解读），每日可使用 AI 问答 5 次，财务报表解析 1 次。体验后如需更多额度，可升级会员。"),
        ("支持哪些财务数据格式？", "目前支持手动输入财务数据、上传 Excel / CSV 文件，以及在财务助手中通过 AI 自动解析年报 PDF 生成四表一注。票据识别支持发票、银行流水、工资表等图片/PDF 上传。"),
        ("会员版与免费版的核心区别是什么？", "会员版享受不限次数的舞弊检测、AI 财务助手解析、税务测算与票据识别，并可导出专业级 PDF / Word 检测报告。"),
        ("数据安全和隐私如何保障？", "所有上传的财务数据与报告均通过加密传输与存储，分析完成后可手动删除。我们不会将用户数据用于模型训练。"),
        ("检测结果中的 SHAP 图如何理解？", "SHAP 图展示每个财务指标或文本特征对最终风险评分的贡献度。红色条表示推高舞弊概率的特征，蓝色条表示降低概率的特征。通过 SHAP 可以定位具体风险点，指导后续审计核查方向。"),
    ]
    for idx, (q, a) in enumerate(faq_items):
        with st.expander(q):
            st.markdown(f"<div style='color: #475569; line-height: 1.8; font-size: 0.95rem; padding: 0.25rem 0;'>{a}</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin: 3rem 0;'></div>", unsafe_allow_html=True)

    # Testimonials
    st.markdown("<h2 style='font-size: 2.2rem; font-weight: 700; color: #0F172A; letter-spacing: -1px; margin-bottom: 0.5rem; text-align: center;'>用户心声</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748B; font-size: 1.05rem; margin-bottom: 2rem; text-align: center;'>来自审计师、财务从业者与企业主的真实反馈</p>", unsafe_allow_html=True)

    testimonials = [
        {"name": "李经理", "title": "某会计师事务所 · 审计经理", "content": "过去识别财务舞弊依赖经验和抽样，Audit Mind 的 AI 文本分析帮我们发现了好几起 MD&A 语义矛盾案例，SHAP 归因也很清晰，客户报告更有说服力了。", "color": "#EFF6FF", "border": "#BFDBFE", "accent": "#2563EB"},
        {"name": "王总监", "title": "某制造业集团 · 财务总监", "content": "税务测算功能很实用，尤其是年终奖单独计税和合并计税的对比，直接帮团队省了几十万的个税支出。简易报税的票据 AI 识别准确率也很高。", "color": "#F0FDF4", "border": "#BBF7D0", "accent": "#10B981"},
        {"name": "张老师", "title": "某财经大学 · 会计学教授", "content": "在课堂演示舞弊识别时，Audit Mind 的可视化效果非常直观，学生能通过 SHAP 图理解 AI 是如何做出判断的，是教学与科研结合的好工具。", "color": "#FFFBEB", "border": "#FDE68A", "accent": "#F59E0B"},
    ]
    testimonial_cols = st.columns(len(testimonials))
    for idx, t in enumerate(testimonials):
        with testimonial_cols[idx]:
            t_html = f'''<div style="background: {t['color']}; border: 1px solid {t['border']}; border-radius: 16px; padding: 1.75rem; height: 100%; animation: fadeInUp 0.5s ease-out {idx*0.15}s both; position: relative;">
                <div style="font-size: 2.5rem; color: {t['accent']}; opacity: 0.2; position: absolute; top: 12px; left: 16px; font-family: Georgia, serif;">"</div>
                <p style="color: #334155; font-size: 0.95rem; line-height: 1.8; margin: 1.5rem 0 1.5rem 0; position: relative; z-index: 1;">{t['content']}</p>
                <div style="display: flex; align-items: center; gap: 12px; margin-top: auto;">
                    <div style="width: 42px; height: 42px; border-radius: 50%; background: {t['accent']}; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.9rem;">{t['name'][0]}</div>
                    <div>
                        <div style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{t['name']}</div>
                        <div style="color: #64748B; font-size: 0.85rem;">{t['title']}</div>
                    </div>
                </div>
            </div>'''
            st.components.v1.html(t_html, height=280, scrolling=False)

    st.markdown('</div>', unsafe_allow_html=True)

    # ========== BOTTOM CTA (Full Width) ==========
    cta_html = '''
    <div style="width: 100%; padding: 80px 6rem; background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%); text-align: center; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0.1; background-image: radial-gradient(circle, #3B82F6 1px, transparent 1px); background-size: 40px 40px;"></div>
        <div style="position: absolute; top: 20%; left: 10%; width: 200px; height: 200px; background: radial-gradient(circle, rgba(37,99,235,0.2) 0%, transparent 70%); border-radius: 50%;"></div>
        <div style="position: absolute; bottom: 20%; right: 10%; width: 180px; height: 180px; background: radial-gradient(circle, rgba(96,165,250,0.15) 0%, transparent 70%); border-radius: 50%;"></div>
        <div style="max-width: 700px; margin: 0 auto; position: relative; z-index: 1;">
            <h2 style="font-size: 2.5rem; font-weight: 800; color: #FFFFFF; margin-bottom: 1rem; letter-spacing: -1.5px;">准备好开始了吗？</h2>
            <p style="font-size: 1.1rem; color: #94A3B8; margin-bottom: 2rem; line-height: 1.8;">立即体验 Audit Mind 的智能财务舞弊检测能力<br>上传第一份报告，3 分钟内获取专业级风险分析</p>
            <p style="font-size: 0.85rem; color: #64748B; margin-top: 1.5rem;">新用户免费体验 3 次完整检测 · 无需信用卡</p>
        </div>
    </div>
    '''
    st.components.v1.html(cta_html, height=360, scrolling=False)


# ================= 舞弊检测页面 =================

# ================= 财务助手页面 =================
# ================= 财务助手页面 (v2 - AI自动生成) =================
def render_financial_assistant():
    """渲染财务助手页面 - 支持财务报表与税务中心双模块"""
    _render_page_header("财务助手", "智能财务与税务助手：财务报表 · 税务测算 · 报税辅助 · 财税咨询")

    # ========== 财务助手会员定价（折叠面板，不占用主空间）==========
    with st.expander("查看 AI 财务助手会员方案"):
        st.markdown("""
        <div style="text-align:center; padding: 8px 0 12px 0;">
            <p style="color: #64748B; font-size: 0.85rem; margin: 0;">
                会员独享更高解析额度与专业深度
            </p>
        </div>
        """, unsafe_allow_html=True)

        fs_plans = [
            {
                "name": "个人/个体版",
                "price": "99",
                "unit": "元/年",
                "target": "独立审计师 · 个人投资者",
                "highlight": False,
                "features": [
                    ("每日 20 次 AI 解析", True),
                    ("基础财务知识库", True),
                    ("标准处理速度", True),
                    ("历史记录保存 7 天", True),
                    ("优先响应通道", False),
                    ("高级分析模型", False),
                    ("API 调用接口", False),
                ],
            },
            {
                "name": "小微企业版",
                "price": "298",
                "unit": "元/年",
                "target": "小型企业 · 创业团队",
                "highlight": True,
                "features": [
                    ("每日 100 次 AI 解析", True),
                    ("专业财务知识库", True),
                    ("优先处理速度", True),
                    ("历史记录保存 90 天", True),
                    ("优先响应通道", True),
                    ("高级分析模型", False),
                    ("API 调用接口", False),
                ],
            },
            {
                "name": "企业分析版",
                "price": "698",
                "unit": "元/年",
                "target": "中型企业 · 投资机构",
                "highlight": False,
                "features": [
                    ("不限次数 AI 解析", True),
                    ("全量财务知识库", True),
                    ("极速处理通道", True),
                    ("历史记录永久保存", True),
                    ("优先响应通道", True),
                    ("高级分析模型", True),
                    ("API 调用接口", True),
                ],
            },
        ]

        cards_html = []
        for plan in fs_plans:
            border = "2px solid #2563EB" if plan["highlight"] else "1px solid #E2E8F0"
            badge = '<div style="background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFFFFF; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; display: inline-block; margin-bottom: 10px;">推荐</div>' if plan["highlight"] else ''
            features_li = "".join([
                f'<li style="margin:5px 0;font-size:0.8rem;color:{"#0F172A" if inc else "#94A3B8"};list-style:none;"><span style="margin-right:4px;">{"✓" if inc else "—"}</span>{feat}</li>'
                for feat, inc in plan["features"]
            ])
            card = f'<div style="flex:1;min-width:240px;border-radius:16px;padding:20px;border:{border};background:#FFFFFF;box-shadow:0 2px 12px rgba(0,0,0,0.04);">{badge}<h4 style="font-size:1.15rem;margin:0 0 4px 0;color:#0F172A;">{plan["name"]}</h4><p style="color:#64748B;font-size:0.8rem;margin:0 0 12px 0;">{plan["target"]}</p><div style="margin:12px 0;"><span style="font-size:2.2rem;font-weight:800;color:#2563EB;">¥{plan["price"]}</span><span style="color:#94A3B8;font-size:0.85rem;">/{plan["unit"]}</span></div><ul style="border-top:1px solid #E2E8F0;padding-top:12px;margin:0;padding-left:0;">{features_li}</ul></div>'
            cards_html.append(card)

        pricing_block = f'<div style="display:flex;gap:16px;flex-wrap:wrap;margin:16px 0;">{"".join(cards_html)}</div>'
        st.markdown(pricing_block, unsafe_allow_html=True)

    # ========== 双模块入口：财务报表 / 税务中心 ==========
    tab_fs, tab_tax = st.tabs(["财务报表", "税务中心"])

    with tab_fs:
        if not st.session_state.logged_in:
            st.warning("请先登录以使用财务报表功能")
            render_login_register()
        else:
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

    with tab_tax:
        render_tax_module()


def render_tax_module():
    """渲染税务中心模块 - 包含税务测算、简易报税、财税咨询三个子功能"""
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["税务测算", "简易报税", "财税咨询"])

    # ========== 子 Tab 1: 税务测算 ==========
    with sub_tab1:
        st.markdown("""
        <div style="text-align:center; padding: 12px 0 16px 0;">
            <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 4px; color: #0F172A;">
                智能税务测算
            </h3>
            <p style="color: #64748B; font-size: 0.85rem; margin: 0;">
                按最新税法计算个税、企业税，对比最优纳税方案
            </p>
        </div>
        """, unsafe_allow_html=True)

        calc_tab1, calc_tab2 = st.tabs(["个税测算", "企业税测算"])

        with calc_tab1:
            st.markdown("**基本信息**")
            col1, col2 = st.columns(2)
            with col1:
                monthly_salary = st.number_input("税前月薪（元）", min_value=0, value=15000, step=500, key="tax_salary")
                annual_bonus = st.number_input("年终奖（元）", min_value=0, value=30000, step=1000, key="tax_bonus")
            with col2:
                social_insurance = st.number_input("五险一金/月（元）", min_value=0, value=3000, step=100, key="tax_si")
                special_deduction = st.number_input("专项附加扣除/月（元）", min_value=0, value=2000, step=100, key="tax_sd")

            with st.expander("更多扣除项（可选）"):
                col3, col4 = st.columns(2)
                with col3:
                    donation = st.number_input("公益捐赠/年（元）", min_value=0, value=0, step=500, key="tax_donation")
                    annuity = st.number_input("职业年金/年（元）", min_value=0, value=0, step=500, key="tax_annuity")
                with col4:
                    health_insurance = st.number_input("商业健康险/年（元，限额2400）", min_value=0, max_value=2400, value=0, step=100, key="tax_health")
                    housing_loan_interest = st.number_input("住房贷款利息/月（元）", min_value=0, value=0, step=500, key="tax_housing")

            if st.button("计算个税", type="primary", use_container_width=True, key="calc_pit"):
                annual_income = monthly_salary * 12
                annual_deduction = (
                    60000
                    + social_insurance * 12
                    + special_deduction * 12
                    + min(donation, annual_income * 0.12)
                    + min(annuity, annual_income * 0.04)
                    + min(health_insurance, 2400)
                    + min(housing_loan_interest * 12, 12000)
                )
                taxable_income = max(0, annual_income - annual_deduction)

                brackets = [
                    (0, 36000, 0.03, 0),
                    (36000, 144000, 0.10, 2520),
                    (144000, 300000, 0.20, 16920),
                    (300000, 420000, 0.25, 31920),
                    (420000, 660000, 0.30, 52920),
                    (660000, 960000, 0.35, 85920),
                    (960000, float('inf'), 0.45, 181920),
                ]

                tax = 0
                rate = 0
                quick_deduction = 0
                for low, high, r, qd in brackets:
                    if taxable_income > low:
                        rate = r
                        quick_deduction = qd

                if taxable_income > 0:
                    tax = taxable_income * rate - quick_deduction

                after_tax = annual_income - tax

                if annual_bonus > 0:
                    monthly_bonus = annual_bonus / 12
                    bonus_rate = 0
                    bonus_qd = 0
                    for low, high, r, qd in brackets:
                        if monthly_bonus > low:
                            bonus_rate = r
                            bonus_qd = qd
                    bonus_tax = annual_bonus * bonus_rate - bonus_qd
                else:
                    bonus_tax = 0

                combined_taxable = taxable_income + annual_bonus
                combined_rate = 0
                combined_qd = 0
                for low, high, r, qd in brackets:
                    if combined_taxable > low:
                        combined_rate = r
                        combined_qd = qd
                combined_bonus_tax = combined_taxable * combined_rate - combined_qd - tax

                best_option = "单独计税" if bonus_tax <= combined_bonus_tax else "合并计税"
                saving = abs(bonus_tax - combined_bonus_tax)

                st.markdown("""
                <div style="border-radius: 16px; padding: 24px; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); margin: 16px 0;">
                    <h4 style="margin: 0 0 12px 0; color: #1E40AF;">计算结果</h4>
                </div>
                """, unsafe_allow_html=True)

                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    st.metric("年收入", f"¥{annual_income:,.0f}")
                with r2:
                    st.metric("年扣除额", f"¥{annual_deduction:,.0f}")
                with r3:
                    st.metric("适用税率", f"{rate*100:.0f}%")
                with r4:
                    st.metric("年个税", f"¥{tax:,.0f}")

                st.metric("税后年收入", f"¥{after_tax:,.0f}")

                st.divider()
                with st.expander("查看应纳税所得额计算明细", expanded=True):
                    detail_data = [
                        {"项目": "税前年收入（月薪×12）", "金额": f"¥{annual_income:,.0f}", "说明": f"{monthly_salary:,.0f} × 12"},
                        {"项目": "减：基本减除费用", "金额": f"-¥60,000", "说明": "个税法规定，每年固定扣除 6 万元"},
                        {"项目": "减：五险一金（年）", "金额": f"-¥{social_insurance*12:,.0f}", "说明": f"{social_insurance:,.0f} × 12"},
                        {"项目": "减：专项附加扣除（年）", "金额": f"-¥{special_deduction*12:,.0f}", "说明": f"{special_deduction:,.0f} × 12"},
                    ]
                    if donation > 0:
                        detail_data.append({"项目": "减：公益捐赠", "金额": f"-¥{min(donation, annual_income*0.12):,.0f}", "说明": f"不超过年收入 12% 可全额扣除（您填写 {donation:,.0f}）"})
                    if annuity > 0:
                        detail_data.append({"项目": "减：职业年金", "金额": f"-¥{min(annuity, annual_income*0.04):,.0f}", "说明": f"不超过年收入 4% 可扣除（您填写 {annuity:,.0f}）"})
                    if health_insurance > 0:
                        detail_data.append({"项目": "减：商业健康险", "金额": f"-¥{min(health_insurance, 2400):,.0f}", "说明": f"限额 2,400 元/年（您填写 {health_insurance:,.0f}）"})
                    if housing_loan_interest > 0:
                        detail_data.append({"项目": "减：住房贷款利息", "金额": f"-¥{min(housing_loan_interest*12, 12000):,.0f}", "说明": f"限额 12,000 元/年（您填写 {housing_loan_interest:,.0f}/月）"})
                    detail_data.append({"项目": "= 应纳税所得额", "金额": f"¥{taxable_income:,.0f}", "说明": "以上为七级超额累进税率计税基础"})
                    st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)

                    st.caption("**税率说明**：全年应纳税所得额不超过 3.6 万部分 3%，3.6–14.4 万部分 10%，14.4–30 万部分 20%，30–42 万部分 25%，42–66 万部分 30%，66–96 万部分 35%，超过 96 万部分 45%。")

                st.divider()
                st.subheader("年终奖最优方案对比")

                bonus_detail = [
                    {"对比项": "计税方式", "单独计税": "年终奖除以 12 后按月度税率表单独计算", "合并计税": "年终奖并入当年综合所得统一计算"},
                    {"对比项": "月均奖金", "单独计税": f"¥{annual_bonus/12:,.0f}", "合并计税": "—"},
                    {"对比项": "适用税率", "单独计税": f"{bonus_rate*100:.0f}%", "合并计税": f"{combined_rate*100:.0f}%"},
                    {"对比项": "速算扣除数", "单独计税": f"¥{bonus_qd:,.0f}", "合并计税": f"¥{combined_qd:,.0f}"},
                    {"对比项": "年终奖个税", "单独计税": f"¥{bonus_tax:,.0f}", "合并计税": f"¥{combined_bonus_tax:,.0f}"},
                ]
                st.dataframe(pd.DataFrame(bonus_detail), use_container_width=True, hide_index=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div style="border-radius: 12px; padding: 16px; background: {'#DCFCE7' if best_option == '单独计税' else '#F1F5F9'}; border: 2px solid {'#22C55E' if best_option == '单独计税' else '#E2E8F0'};">
                        <h4 style="margin: 0 0 8px 0; color: #0F172A;">单独计税 {'推荐' if best_option == '单独计税' else ''}</h4>
                        <p style="margin: 0; color: #475569; font-size: 0.9rem;">年终奖个税: <strong>¥{bonus_tax:,.0f}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div style="border-radius: 12px; padding: 16px; background: {'#DCFCE7' if best_option == '合并计税' else '#F1F5F9'}; border: 2px solid {'#22C55E' if best_option == '合并计税' else '#E2E8F0'};">
                        <h4 style="margin: 0 0 8px 0; color: #0F172A;">合并计税 {'推荐' if best_option == '合并计税' else ''}</h4>
                        <p style="margin: 0; color: #475569; font-size: 0.9rem;">年终奖个税: <strong>¥{combined_bonus_tax:,.0f}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)

                st.success(f"最优方案: **{best_option}**，可节省 ¥{saving:,.0f}")

        with calc_tab2:
            col1, col2 = st.columns(2)
            with col1:
                revenue = st.number_input("营业收入（元/年）", min_value=0, value=500000, step=10000, key="biz_revenue")
                cost = st.number_input("营业成本（元/年）", min_value=0, value=300000, step=10000, key="biz_cost")
            with col2:
                taxpayer_type = st.selectbox("纳税人类型", ["小规模纳税人", "一般纳税人"], key="biz_type")
                industry = st.selectbox("行业类型", ["服务业（6%）", "交通运输/建筑（9%）", "货物销售（13%）"], key="biz_industry")

            if st.button("计算企业税", type="primary", use_container_width=True, key="calc_biz"):
                profit = revenue - cost

                # 增值税
                if taxpayer_type == "小规模纳税人":
                    vat_rate = 0.03
                    vat = revenue * vat_rate
                else:
                    vat_rates = {"服务业（6%）": 0.06, "交通运输/建筑（9%）": 0.09, "货物销售（13%）": 0.13}
                    vat_rate = vat_rates.get(industry, 0.06)
                    vat = revenue * vat_rate

                # 企业所得税
                if profit <= 0:
                    income_tax = 0
                elif profit <= 3000000:
                    income_tax = profit * 0.05
                else:
                    income_tax = profit * 0.25

                # 附加税
                surcharge = vat * 0.12
                if taxpayer_type == "小规模纳税人":
                    surcharge = vat * 0.06

                total_tax = vat + income_tax + surcharge
                net_profit = profit - total_tax

                st.markdown("""
                <div style="border-radius: 16px; padding: 24px; background: linear-gradient(135deg, #EFF6FF, #DBEAFE); margin: 16px 0;">
                    <h4 style="margin: 0 0 12px 0; color: #1E40AF;">企业税计算结果</h4>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("增值税", f"¥{vat:,.0f}")
                with c2:
                    st.metric("企业所得税", f"¥{income_tax:,.0f}")
                with c3:
                    st.metric("附加税", f"¥{surcharge:,.0f}")

                st.metric("合计应缴税额", f"¥{total_tax:,.0f}")
                st.metric("税后净利润", f"¥{net_profit:,.0f}", delta=f"利润率 {net_profit/revenue*100:.1f}%" if revenue > 0 else "")

                st.divider()
                with st.expander("查看利润与税费计算明细", expanded=True):
                    profit_data = [
                        {"项目": "营业收入", "金额": f"¥{revenue:,.0f}", "计算过程": "您填写的年度营业收入"},
                        {"项目": "减：营业成本", "金额": f"-¥{cost:,.0f}", "计算过程": "您填写的年度营业成本"},
                        {"项目": "= 利润总额", "金额": f"¥{profit:,.0f}", "计算过程": "收入 - 成本"},
                    ]
                    st.dataframe(pd.DataFrame(profit_data), use_container_width=True, hide_index=True)

                    st.markdown("**税费明细**")
                    tax_detail = []
                    if taxpayer_type == "小规模纳税人":
                        tax_detail.append({"税种": "增值税", "税率/依据": "征收率 3%", "计算过程": f"¥{revenue:,.0f} × 3% = ¥{vat:,.0f}", "应缴金额": f"¥{vat:,.0f}"})
                        tax_detail.append({"税种": "附加税", "税率/依据": "增值税 × 6%（减半征收）", "计算过程": f"¥{vat:,.0f} × 6% = ¥{surcharge:,.0f}", "应缴金额": f"¥{surcharge:,.0f}"})
                    else:
                        tax_detail.append({"税种": "增值税", "税率/依据": f"{industry}", "计算过程": f"¥{revenue:,.0f} × {vat_rate*100:.0f}% = ¥{vat:,.0f}", "应缴金额": f"¥{vat:,.0f}"})
                        tax_detail.append({"税种": "附加税", "税率/依据": "增值税 × 12%", "计算过程": f"¥{vat:,.0f} × 12% = ¥{surcharge:,.0f}", "应缴金额": f"¥{surcharge:,.0f}"})

                    if profit <= 0:
                        tax_detail.append({"税种": "企业所得税", "税率/依据": "利润 ≤ 0，无需缴纳", "计算过程": "无", "应缴金额": "¥0"})
                    elif profit <= 3000000:
                        tax_detail.append({"税种": "企业所得税", "税率/依据": "小微优惠税率 5%", "计算过程": f"¥{profit:,.0f} × 5% = ¥{income_tax:,.0f}", "应缴金额": f"¥{income_tax:,.0f}"})
                    else:
                        tax_detail.append({"税种": "企业所得税", "税率/依据": "一般税率 25%", "计算过程": f"¥{profit:,.0f} × 25% = ¥{income_tax:,.0f}", "应缴金额": f"¥{income_tax:,.0f}"})

                    st.dataframe(pd.DataFrame(tax_detail), use_container_width=True, hide_index=True)

                    st.caption("**政策说明**：增值税是对商品/服务增值部分征收的流转税；企业所得税是对企业利润征收的所得税；附加税包括城建税、教育费附加、地方教育附加，以增值税为计税基础。小规模纳税人季度销售额 ≤ 30 万元可免征增值税。")

            with st.expander("其他税种测算（印花税 / 房产税）"):
                st.markdown("**印花税**")
                contract_amount = st.number_input("合同金额（元）", min_value=0, value=100000, step=1000, key="stamp_contract")
                stamp_type = st.selectbox("合同类型", ["买卖合同（0.03%）", "借款合同（0.005%）", "产权转移（0.05%）", "营业账簿（0.025%）"], key="stamp_type")
                stamp_rates = {"买卖合同（0.03%）": 0.0003, "借款合同（0.005%）": 0.00005, "产权转移（0.05%）": 0.0005, "营业账簿（0.025%）": 0.00025}
                stamp_tax = contract_amount * stamp_rates.get(stamp_type, 0.0003)
                st.metric("应缴印花税", f"¥{stamp_tax:,.2f}")

                st.divider()
                st.markdown("**房产税**")
                property_type = st.selectbox("房产用途", ["自用（从价）", "出租（从租）"], key="property_type")
                if property_type == "自用（从价）":
                    property_value = st.number_input("房产原值（元）", min_value=0, value=500000, step=10000, key="property_value")
                    deduction_rate = st.slider("扣除比例", 0.1, 0.3, 0.2, 0.05, key="deduction_rate")
                    property_tax = property_value * (1 - deduction_rate) * 0.012
                    st.metric("应缴房产税（年）", f"¥{property_tax:,.2f}")
                else:
                    rental_income = st.number_input("年租金收入（元）", min_value=0, value=60000, step=1000, key="rental_income")
                    property_tax = rental_income * 0.12
                    st.metric("应缴房产税（年）", f"¥{property_tax:,.2f}")

    # ========== 子 Tab 2: 简易报税 ==========
    with sub_tab2:
        st.markdown("""
        <div style="text-align:center; padding: 12px 0 16px 0;">
            <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 4px; color: #0F172A;">
                简易报税辅助
            </h3>
            <p style="color: #64748B; font-size: 0.85rem; margin: 0;">
                上传票据/流水/工资表，AI 自动识别并生成申报表
            </p>
        </div>
        """, unsafe_allow_html=True)

        step = st.session_state.get("tax_filing_step", 1)

        if step == 1:
            st.subheader("第一步：上传单据")
            uploaded_files = st.file_uploader(
                "支持发票、银行流水、工资表等（JPG/PNG/PDF）",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="tax_files"
            )

            if uploaded_files:
                st.success(f"已上传 {len(uploaded_files)} 个文件")
                for f in uploaded_files:
                    st.write(f"- {f.name} ({f.size/1024:.1f} KB)")

                if st.button("开始识别", type="primary", use_container_width=True, key="start_recognize"):
                    st.session_state.tax_filing_step = 2
                    st.session_state.tax_uploaded_files = uploaded_files
                    st.rerun()

        elif step == 2:
            st.subheader("第二步：AI 识别结果")

            uploaded_files = st.session_state.get("tax_uploaded_files", [])
            recognized_results = st.session_state.get("tax_recognized_results", [])

            if not recognized_results and uploaded_files:
                with st.spinner("AI 正在识别票据内容，请稍候..."):
                    recognized_results = []
                    for f in uploaded_files:
                        try:
                            f.seek(0)
                            image_bytes = f.read()
                            b64_image = base64.b64encode(image_bytes).decode("utf-8")
                            mime = f.type if f.type else "image/jpeg"

                            resp = requests.post(
                                f"{API_BASE_URL.replace('/api', '')}/qa/ask",
                                headers={"Content-Type": "application/json"},
                                json={
                                    "question": "识别这张票据/单据，提取以下信息并以JSON格式返回：{\"票据类型\":\"...\",\"金额\":数字,\"税率\":\"百分比或-\",\"税额\":数字,\"开票日期\":\"YYYY-MM-DD或-\",\"分类\":\"收入/成本/费用\"}",
                                    "image_base64": b64_image,
                                    "image_mime": mime,
                                    "model": "qwen-vl-max"
                                },
                                timeout=60
                            )

                            if resp.status_code == 200:
                                result = resp.json()
                                answer = result.get("answer", "")
                                # 尝试从回答中提取 JSON
                                import re
                                json_match = re.search(r'\{[^}]+\}', answer)
                                if json_match:
                                    try:
                                        data = json.loads(json_match.group())
                                        recognized_results.append({
                                            "文件名": f.name,
                                            "票据类型": data.get("票据类型", "未知"),
                                            "金额": float(data.get("金额", 0) or 0),
                                            "税率": data.get("税率", "-"),
                                            "税额": float(data.get("税额", 0) or 0),
                                            "分类": data.get("分类", "未知"),
                                        })
                                    except Exception:
                                        recognized_results.append({
                                            "文件名": f.name, "票据类型": "识别失败", "金额": 0,
                                            "税率": "-", "税额": 0, "分类": "未知"
                                        })
                                else:
                                    recognized_results.append({
                                        "文件名": f.name, "票据类型": "识别失败", "金额": 0,
                                        "税率": "-", "税额": 0, "分类": "未知"
                                    })
                            else:
                                recognized_results.append({
                                    "文件名": f.name, "票据类型": "API调用失败", "金额": 0,
                                    "税率": "-", "税额": 0, "分类": "未知"
                                })
                        except Exception as e:
                            recognized_results.append({
                                "文件名": f.name, "票据类型": f"异常: {str(e)[:50]}", "金额": 0,
                                "税率": "-", "税额": 0, "分类": "未知"
                            })

                    st.session_state.tax_recognized_results = recognized_results

            if recognized_results:
                st.dataframe(recognized_results, use_container_width=True, hide_index=True)

                # 汇总统计
                total_income = sum(r["金额"] for r in recognized_results if r["分类"] == "收入")
                total_cost = sum(r["金额"] for r in recognized_results if r["分类"] in ["成本", "费用"])
                total_tax_amount = sum(r["税额"] for r in recognized_results if r["税额"])

                st.markdown(f"""
                <div style="display:flex;gap:16px;margin:12px 0;">
                    <div style="flex:1;border-radius:12px;padding:16px;background:#EFF6FF;border:1px solid #BFDBFE;">
                        <p style="margin:0;color:#64748B;font-size:0.85rem;">识别收入</p>
                        <p style="margin:0;font-size:1.5rem;font-weight:800;color:#2563EB;">¥{total_income:,.2f}</p>
                    </div>
                    <div style="flex:1;border-radius:12px;padding:16px;background:#F0FDF4;border:1px solid #BBF7D0;">
                        <p style="margin:0;color:#64748B;font-size:0.85rem;">识别成本</p>
                        <p style="margin:0;font-size:1.5rem;font-weight:800;color:#10B981;">¥{total_cost:,.2f}</p>
                    </div>
                    <div style="flex:1;border-radius:12px;padding:16px;background:#FFFBEB;border:1px solid #FDE68A;">
                        <p style="margin:0;color:#64748B;font-size:0.85rem;">进项税额</p>
                        <p style="margin:0;font-size:1.5rem;font-weight:800;color:#F59E0B;">¥{total_tax_amount:,.2f}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("确认并生成申报表", type="primary", use_container_width=True, key="gen_report"):
                    st.session_state.tax_filing_step = 3
                    st.rerun()
            else:
                st.warning("暂无识别结果，请返回重新上传")

            if st.button("返回重新上传", use_container_width=True, key="back_step1"):
                st.session_state.tax_filing_step = 1
                st.session_state.tax_recognized_results = []
                st.rerun()

        elif step == 3:
            st.subheader("第三步：简易申报表")

            recognized_results = st.session_state.get("tax_recognized_results", [])
            total_income = sum(r["金额"] for r in recognized_results if r["分类"] == "收入")
            total_cost = sum(r["金额"] for r in recognized_results if r["分类"] in ["成本", "费用"])
            input_vat = sum(r["税额"] for r in recognized_results if r["税额"] and r["分类"] == "收入")
            taxable_profit = max(0, total_income - total_cost)

            # 小规模纳税人简易计算
            vat_rate = 0.03
            vat = max(0, taxable_profit * vat_rate - input_vat)
            income_tax = taxable_profit * 0.05 if taxable_profit <= 3000000 else taxable_profit * 0.25
            surcharge = vat * 0.06
            total = vat + income_tax + surcharge

            report_data = [
                {"项目": "营业收入", "金额": f"¥{total_income:,.2f}"},
                {"项目": "营业成本", "金额": f"¥{total_cost:,.2f}"},
                {"项目": "应纳税所得额", "金额": f"¥{taxable_profit:,.2f}"},
                {"项目": "增值税（3%，抵扣后）", "金额": f"¥{vat:,.2f}"},
                {"项目": "企业所得税", "金额": f"¥{income_tax:,.2f}"},
                {"项目": "附加税", "金额": f"¥{surcharge:,.2f}"},
                {"项目": "合计应缴税额", "金额": f"¥{total:,.2f}"},
            ]

            st.dataframe(report_data, use_container_width=True, hide_index=True)

            st.markdown(f"""
            <div style="border-radius:16px;padding:20px;background:linear-gradient(135deg,#EFF6FF,#DBEAFE);margin:16px 0;">
                <h4 style="margin:0 0 8px 0;color:#1E40AF;">申报表摘要</h4>
                <p style="margin:0;color:#475569;font-size:0.9rem;">
                    基于 {len(recognized_results)} 张识别单据自动生成。
                    <br>营业收入 ¥{total_income:,.2f} - 营业成本 ¥{total_cost:,.2f} = 应纳税所得额 ¥{taxable_profit:,.2f}
                </p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("完成", type="primary", use_container_width=True, key="finish_filing"):
                st.session_state.tax_filing_step = 1
                st.session_state.tax_recognized_results = []
                st.success("申报表已生成！")
                st.rerun()

    # ========== 子 Tab 3: 财税咨询 ==========
    with sub_tab3:
        # 头部标题
        st.markdown("""
        <div style="text-align:center; padding: 24px 0 20px 0;">
            <div style="display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#EFF6FF,#DBEAFE);margin-bottom:12px;box-shadow:0 4px 12px rgba(37,99,235,0.1);">
                <span style="font-size:1.6rem;">&#x1F4AC;</span>
            </div>
            <h2 style="font-size: 1.6rem; font-weight: 700; margin-bottom: 6px; color: #0F172A; letter-spacing: -0.5px;">
                财税政策咨询
            </h2>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0; max-width: 480px; margin-left: auto; margin-right: auto; line-height: 1.6;">
                AI 财税专家，解答个税、企业税、社保公积金等政策问题
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.logged_in:
            st.info("财税咨询功能仅对登录用户开放")
            render_login_register()
        else:
            # 处理待发送的消息（来自快捷问题或输入框）
            pending_prompt = st.session_state.get("tax_pending_prompt", "")
            if pending_prompt:
                st.session_state.tax_pending_prompt = None
                st.session_state.tax_chat_history.append({"role": "user", "content": pending_prompt})

                # 调用 API 获取回答
                with st.chat_message("assistant"):
                    thinking_placeholder = st.empty()
                    thinking_placeholder.markdown("""
                    <div style="display:flex;align-items:center;gap:10px;padding:4px 0;">
                        <div style="display:flex;gap:4px;align-items:center;">
                            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0s;"></span>
                            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0.16s;"></span>
                            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0.32s;"></span>
                        </div>
                        <span style="font-size:0.85rem;color:#64748B;">AI 正在思考中...</span>
                    </div>
                    """, unsafe_allow_html=True)

                    try:
                        url = f"{API_BASE_URL}/qa/ask-stream"
                        req_headers = {
                            "Authorization": f"Bearer {st.session_state.token}",
                            "Content-Type": "application/json"
                        }
                        req_data = {
                            "question": pending_prompt,
                            "context": "你是一位中国财税政策专家，熟悉个人所得税、企业所得税、增值税、社保公积金等法规。请用通俗易懂的语言解答，涉及计算时请给出具体公式和数字示例。"
                        }

                        response = requests.post(url, json=req_data, headers=req_headers, stream=True, timeout=120)

                        if response.status_code == 200:
                            def _tax_stream():
                                for line in response.iter_lines(decode_unicode=True):
                                    if not line:
                                        continue
                                    if line.startswith("data: "):
                                        data_str = line[6:]
                                        if data_str == "[DONE]":
                                            break
                                        try:
                                            event_data = json.loads(data_str)
                                            content = event_data.get("content")
                                            if content and isinstance(content, str):
                                                yield content
                                        except json.JSONDecodeError:
                                            continue

                            full_answer = st.write_stream(_tax_stream)
                            thinking_placeholder.empty()
                            st.session_state.tax_chat_history.append({"role": "assistant", "content": full_answer})
                        else:
                            thinking_placeholder.empty()
                            fallback = make_api_request("/qa/ask", method="POST", data={"question": pending_prompt, "context": "财税专家"})
                            if fallback and "answer" in fallback:
                                answer = fallback["answer"]
                                st.markdown(answer)
                                st.session_state.tax_chat_history.append({"role": "assistant", "content": answer})
                            else:
                                st.error("咨询失败，请稍后重试")
                    except Exception as e:
                        thinking_placeholder.empty()
                        st.error(f"咨询失败: {str(e)[:100]}")

            # 欢迎卡片（无历史消息时显示）
            if not st.session_state.tax_chat_history:
                st.markdown('''
                <div class="glass-card" style="text-align: center; padding: 2.5rem 2rem; margin-bottom: 1.5rem;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">&#x1F3DB;</div>
                    <h3 style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem; color: #0F172A;">智能财税问答助手</h3>
                    <p style="font-size: 0.9rem; color: #64748B; line-height: 1.6; max-width: 460px; margin: 0 auto;">
                        我可以帮您解答个人所得税、企业所得税、增值税、社保公积金等财税政策问题。
                        <br>涉及计算时会给出具体公式和数字示例。
                    </p>
                </div>
                ''', unsafe_allow_html=True)

            # 显示所有历史消息
            for msg in st.session_state.tax_chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # 侧边栏快捷问题
            with st.sidebar:
                st.subheader("财税快捷提问")
                tax_questions = [
                    "年终奖单独计税和合并计税哪个更划算？",
                    "小规模纳税人和一般纳税人有什么区别？",
                    "专项附加扣除包括哪些项目？",
                    "个体户需要交哪些税？",
                    "最新的个税起征点和税率表是什么？",
                ]
                for q in tax_questions:
                    if st.button(q, key=f"tax_q_{q[:20]}", use_container_width=True):
                        st.session_state.tax_pending_prompt = q
                        st.rerun()
                st.divider()

            # 聊天输入（始终放在最后，确保在所有消息下方）
            if prompt := st.chat_input("请输入您的财税问题...", key="tax_chat"):
                st.session_state.tax_pending_prompt = prompt
                st.rerun()


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
        _render_empty_state("📊", "暂无财务报表", "您还没有创建任何财务报表。点击「AI自动生成」从上传的文件中提取，或选择「手动创建」自行填写。", "💡 提示：支持 PDF、Word、Excel 格式上传")
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
                if st.button("🗑️", key=f"del_{stmt['id']}", help="删除此报表", use_container_width=True):
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
        _render_empty_state("📋", "暂无数据", "当前没有可预览的财务数据。")
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


# 报表科目填写说明映射
_ITEM_HELP = {
    "货币资金": "现金、银行存款及其他货币资金。流动性最强的资产",
    "应收账款": "因销售商品、提供劳务等应收取的款项",
    "预付款项": "预先支付给供应商的款项",
    "存货": "库存商品、在产品、原材料等",
    "流动资产合计": "一年内可变现或耗用的资产总计",
    "固定资产": "房屋、机器设备等长期资产净值（原值减累计折旧）",
    "无形资产": "专利权、商标权、土地使用权等非实物资产",
    "总资产": "企业拥有或控制的全部资产",
    "短期借款": "一年内到期的银行借款、债券等",
    "应付账款": "因购买商品、接受劳务等应付给供应商的款项",
    "预收款项": "预先收取客户的货款或劳务款",
    "流动负债合计": "一年内到期的全部负债",
    "长期借款": "一年以上到期的银行借款、债券等",
    "总负债": "企业承担的全部债务",
    "实收资本": "股东实际投入的资本（注册资本）",
    "资本公积": "股东投入超过注册资本的部分、资产评估增值等",
    "盈余公积": "从净利润中提取的积累资金",
    "未分配利润": "累计未分配的净利润",
    "所有者权益合计": "股东对企业净资产的所有权（又称净资产）",
    "营业收入": "销售商品、提供劳务等主要经营活动取得的收入",
    "营业成本": "与营业收入直接相关的成本，如原材料、生产人工",
    "税金及附加": "消费税、城建税、教育费附加等经营相关税费",
    "销售费用": "广告费、销售人员薪酬、运输费等市场推广支出",
    "管理费用": "行政人员薪酬、办公费、折旧费等企业管理支出",
    "财务费用": "利息支出、汇兑损益、银行手续费等",
    "营业利润": "营业收入 - 营业成本 - 税金及附加 - 三项费用",
    "利润总额": "营业利润 + 营业外收入 - 营业外支出",
    "所得税费用": "按税法规定应缴纳的所得税",
    "净利润": "利润总额 - 所得税费用。最终归属于股东的利润",
    "经营活动现金流净额": "主营业务产生的现金净流入",
    "投资活动现金流净额": "购置/处置固定资产、股权投资等产生的现金净额",
    "筹资活动现金流净额": "借款、还款、分红、增发等融资活动产生的现金净额",
    "现金及现金等价物净增加额": "三类活动现金流净额之和",
}

def _get_item_help(item_name: str, field_type: str = "") -> str:
    """获取科目填写说明"""
    base = _ITEM_HELP.get(item_name, f"填写{item_name}的对应金额")
    if field_type == "ending":
        return base + " · 填写报表期末（本期末）时点的余额"
    if field_type == "beginning":
        return base + " · 填写报表期初（上期末）时点的余额"
    if field_type == "current":
        return base + " · 填写本期（本年）发生额"
    if field_type == "previous":
        return base + " · 填写上期（上年同期）发生额"
    if field_type == "increase":
        return base + " · 填写本期增加金额"
    if field_type == "decrease":
        return base + " · 填写本期减少金额"
    return base


def _render_bs_editor(statement_id: int, data: dict, ai_filled: set):
    """资产负债表编辑器（含AI标记）"""
    st.markdown("**资产负债表**")
    st.caption("资产 = 负债 + 所有者权益。请根据年报中的「资产负债表」对应科目填写期末/期初余额。")
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
            item_name = item.get('item_name', '')
            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{item_name}</span>", unsafe_allow_html=True)
                else:
                    st.text(item_name)
            with cols[1]:
                ending = st.number_input(
                    f"期末_{item_name}", value=item.get('ending_balance') or 0.0,
                    label_visibility="collapsed", key=f"bs2_end_{statement_id}_{section_name}_{i}",
                    help=_get_item_help(item_name, "ending")
                )
            with cols[2]:
                beginning = st.number_input(
                    f"期初_{item_name}", value=item.get('beginning_balance') or 0.0,
                    label_visibility="collapsed", key=f"bs2_beg_{statement_id}_{section_name}_{i}",
                    help=_get_item_help(item_name, "beginning")
                )
            with cols[3]:
                notes = st.text_input(
                    f"备注_{item_name}", value=item.get('notes', ''),
                    label_visibility="collapsed", key=f"bs2_note_{statement_id}_{section_name}_{i}",
                    help="如有调整事项、审计说明或特殊情况请在此备注"
                )
            updated_items.append({**item, "ending_balance": ending if ending != 0 else None, "beginning_balance": beginning if beginning != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("⚠️ 此项由AI估计生成，请重点核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("💾 保存资产负债表", key=f"save_bs2_{statement_id}", use_container_width=True):
        _save_statement_field(statement_id, "balance_sheet", updated)


def _render_is_editor(statement_id: int, data: dict, ai_filled: set):
    """利润表编辑器"""
    st.markdown("**利润表**")
    st.caption("收入 - 成本费用 = 利润。请根据年报中的「利润表」对应科目填写本期/上期发生额。")
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
            item_name = item.get('item_name', '')
            cols = st.columns([3, 2, 2, 2])
            with cols[0]:
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{item_name}</span>", unsafe_allow_html=True)
                else:
                    st.text(item_name)
            with cols[1]:
                current = st.number_input(
                    f"本期_{item_name}", value=item.get('current_period') or 0.0,
                    label_visibility="collapsed", key=f"is2_cur_{statement_id}_{section_name}_{i}",
                    help=_get_item_help(item_name, "current")
                )
            with cols[2]:
                previous = st.number_input(
                    f"上期_{item_name}", value=item.get('previous_period') or 0.0,
                    label_visibility="collapsed", key=f"is2_prev_{statement_id}_{section_name}_{i}",
                    help=_get_item_help(item_name, "previous")
                )
            with cols[3]:
                notes = st.text_input(
                    f"备注_{item_name}", value=item.get('notes', ''),
                    label_visibility="collapsed", key=f"is2_note_{statement_id}_{section_name}_{i}",
                    help="如有调整事项、审计说明或特殊情况请在此备注"
                )
            updated_items.append({**item, "current_period": current if current != 0 else None, "previous_period": previous if previous != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("⚠️ 此项由AI估计生成，请重点核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("💾 保存利润表", key=f"save_is2_{statement_id}", use_container_width=True):
        _save_statement_field(statement_id, "income_statement", updated)


def _render_cf_editor(statement_id: int, data: dict, ai_filled: set):
    """现金流量表编辑器"""
    st.markdown("**现金流量表**")
    st.caption("反映企业现金流入流出情况。请根据年报中的「现金流量表」填写本期发生额（正数=流入，负数=流出）。")
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
            item_name = item.get('item_name', '')
            cols = st.columns([4, 2, 2])
            with cols[0]:
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{item_name} </span>", unsafe_allow_html=True)
                else:
                    st.text(item_name)
            with cols[1]:
                current = st.number_input(
                    f"本期_{item_name}", value=item.get('current_period') or 0.0,
                    label_visibility="collapsed", key=f"cf2_cur_{statement_id}_{section_name}_{i}",
                    help=_get_item_help(item_name, "current")
                )
            with cols[2]:
                notes = st.text_input(
                    f"备注_{item_name}", value=item.get('notes', ''),
                    label_visibility="collapsed", key=f"cf2_note_{statement_id}_{section_name}_{i}",
                    help="如有调整事项、审计说明或特殊情况请在此备注"
                )
            updated_items.append({**item, "current_period": current if current != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("⚠️ 此项由AI估计生成，请重点核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("💾 保存现金流量表", key=f"save_cf2_{statement_id}", use_container_width=True):
        _save_statement_field(statement_id, "cash_flow", updated)


def _render_eq_editor(statement_id: int, data: dict, ai_filled: set):
    """所有者权益变动表编辑器"""
    st.markdown("**所有者权益变动表**")
    st.caption("反映股东权益各组成部分的增减变动。期初 + 增加 - 减少 = 期末。")
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
            item_name = item.get('item_name', '')
            cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
            with cols[0]:
                if is_ai:
                    st.markdown(f"<span style='background-color:#FFF3CD;padding:2px 6px;border-radius:4px;'>{item_name} </span>", unsafe_allow_html=True)
                else:
                    st.text(item_name)
            with cols[1]:
                beg = st.number_input(
                    f"期初_{item_name}", value=item.get('beginning_balance') or 0.0,
                    label_visibility="collapsed", key=f"eq2_beg_{statement_id}_{i}",
                    help=_get_item_help(item_name, "beginning")
                )
            with cols[2]:
                inc = st.number_input(
                    f"增加_{item_name}", value=item.get('increase') or 0.0,
                    label_visibility="collapsed", key=f"eq2_inc_{statement_id}_{i}",
                    help=_get_item_help(item_name, "increase")
                )
            with cols[3]:
                dec = st.number_input(
                    f"减少_{item_name}", value=item.get('decrease') or 0.0,
                    label_visibility="collapsed", key=f"eq2_dec_{statement_id}_{i}",
                    help=_get_item_help(item_name, "decrease")
                )
            with cols[4]:
                end = st.number_input(
                    f"期末_{item_name}", value=item.get('ending_balance') or 0.0,
                    label_visibility="collapsed", key=f"eq2_end_{statement_id}_{i}",
                    help=_get_item_help(item_name, "ending")
                )
            with cols[5]:
                notes = st.text_input(
                    f"备注_{item_name}", value=item.get('notes', ''),
                    label_visibility="collapsed", key=f"eq2_note_{statement_id}_{i}",
                    help="如有调整事项、审计说明或特殊情况请在此备注"
                )
            updated_items.append({**item, "beginning_balance": beg if beg != 0 else None, "increase": inc if inc != 0 else None, "decrease": dec if dec != 0 else None, "ending_balance": end if end != 0 else None, "notes": notes or None})
            if is_ai:
                st.caption("⚠️ 此项由AI估计生成，请重点核实")
        updated[section_name] = updated_items
        st.divider()

    if st.button("💾 保存权益变动表", key=f"save_eq2_{statement_id}", use_container_width=True):
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
                    is_fraud = case.get("case_type") == "fraud"
                    badge_color = "#EF4444" if is_fraud else "#10B981"
                    badge_bg = "rgba(239,68,68,0.1)" if is_fraud else "rgba(16,185,129,0.1)"
                    badge_text = "🔴 高风险" if is_fraud else "🟢 低风险"
                    top_border = f"border-top: 3px solid {badge_color};" if is_fraud else ""

                    card_html = f'''
                    <div style="background: #FFFFFF; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); {top_border} margin-bottom: 8px;">
                        <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; background: {badge_bg}; color: {badge_color}; margin-bottom: 10px;">
                            {badge_text}
                        </div>
                        <h4 style="font-size: 1.05rem; font-weight: 700; margin: 0 0 6px 0; color: #0F172A;">{case['case_name']}</h4>
                        <p style="font-size: 0.8rem; color: #64748B; line-height: 1.5; margin: 0;">{case.get('description', '')}</p>
                    </div>
                    '''
                    st.components.v1.html(card_html, height=130, scrolling=False)

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
        st.subheader("📊 财务数据录入 (单位：亿元)")
        st.caption("请根据企业年报中的资产负债表、利润表、现金流量表填写。鼠标悬停在字段名上可查看详细说明。")

        financial_data_manual = {}
        _v = lambda k, scale=1e9: float(default_financial.get(k, 0))/scale if default_financial.get(k) else 0.0

        # ========== 资产负债表 ==========
        with st.expander("📋 资产负债表 (Balance Sheet)", expanded=True):
            st.caption("反映企业在特定日期的财务状况。资产 = 负债 + 所有者权益")
            c1, c2, c3 = st.columns(3)
            with c1:
                financial_data_manual["货币资金"] = st.number_input("💰 货币资金", min_value=0.0, value=_v("货币资金"), key="f1",
                    help="现金、银行存款及其他货币资金。取自资产负债表「流动资产」科目")
                financial_data_manual["应收账款"] = st.number_input("📥 应收账款", min_value=0.0, value=_v("应收账款"), key="f11",
                    help="企业因销售商品、提供劳务等应收取的款项。取自资产负债表「流动资产」科目")
                financial_data_manual["存货"] = st.number_input("📦 存货", min_value=0.0, value=_v("存货"), key="f3",
                    help="库存商品、在产品、原材料等。取自资产负债表「流动资产」科目")
                financial_data_manual["流动资产合计"] = st.number_input("📊 流动资产合计", min_value=0.0, value=_v("流动资产合计"), key="f12",
                    help="一年内可变现或耗用的资产总计。包括货币资金、应收账款、存货等")
            with c2:
                financial_data_manual["固定资产"] = st.number_input("🏭 固定资产", min_value=0.0, value=_v("固定资产"), key="f13",
                    help="房屋、机器设备等长期资产净值（原值减累计折旧）。取自资产负债表「非流动资产」")
                financial_data_manual["总资产"] = st.number_input("🏢 总资产", min_value=0.0, value=_v("总资产"), key="f6",
                    help="企业拥有或控制的全部资产。资产 = 负债 + 所有者权益")
                financial_data_manual["短期借款"] = st.number_input("💳 短期借款", min_value=0.0, value=_v("短期借款"), key="f2",
                    help="一年内到期的银行借款、债券等。取自资产负债表「流动负债」科目")
                financial_data_manual["应付账款"] = st.number_input("📤 应付账款", min_value=0.0, value=_v("应付账款"), key="f14",
                    help="因购买商品、接受劳务等应付给供应商的款项。取自资产负债表「流动负债」")
            with c3:
                financial_data_manual["流动负债合计"] = st.number_input("📊 流动负债合计", min_value=0.0, value=_v("流动负债合计"), key="f15",
                    help="一年内到期的全部负债。包括短期借款、应付账款等")
                financial_data_manual["长期借款"] = st.number_input("🏦 长期借款", min_value=0.0, value=_v("长期借款"), key="f16",
                    help="一年以上到期的银行借款、债券等。取自资产负债表「非流动负债」")
                financial_data_manual["总负债"] = st.number_input("📉 总负债", min_value=0.0, value=_v("总负债"), key="f17",
                    help="企业承担的全部债务。负债 = 资产 - 所有者权益")
                financial_data_manual["所有者权益合计"] = st.number_input("📈 所有者权益合计", min_value=0.0, value=_v("所有者权益合计"), key="f18",
                    help="股东对企业净资产的所有权。又称「股东权益」或「净资产」")

        # ========== 利润表 ==========
        with st.expander("📈 利润表 (Income Statement)", expanded=True):
            st.caption("反映企业在一定期间内的经营成果。收入 - 成本费用 = 利润")
            c1, c2, c3 = st.columns(3)
            with c1:
                financial_data_manual["营业收入"] = st.number_input("💵 营业收入", min_value=0.0, value=_v("营业收入"), key="f4",
                    help="企业销售商品、提供劳务等主要经营活动取得的收入。利润表首行")
                financial_data_manual["营业成本"] = st.number_input("🏗️ 营业成本", min_value=0.0, value=_v("营业成本"), key="f19",
                    help="与营业收入直接相关的成本。如原材料、生产人工等。利润表第二行")
                financial_data_manual["销售费用"] = st.number_input("📢 销售费用", min_value=0.0, value=_v("销售费用"), key="f20",
                    help="广告费、销售人员薪酬、运输费等市场推广支出")
            with c2:
                financial_data_manual["管理费用"] = st.number_input("🗂️ 管理费用", min_value=0.0, value=_v("管理费用"), key="f21",
                    help="行政人员薪酬、办公费、折旧费等企业管理支出")
                financial_data_manual["财务费用"] = st.number_input("💸 财务费用", value=_v("财务费用"), key="f22",
                    help="利息支出、汇兑损益、银行手续费等。通常为正值表示支出")
                financial_data_manual["营业利润"] = st.number_input("⚖️ 营业利润", value=_v("营业利润"), key="f23",
                    help="营业收入 - 营业成本 - 税金及附加 - 三项费用。反映核心经营盈利能力")
            with c3:
                financial_data_manual["净利润"] = st.number_input("💎 净利润", value=_v("净利润", 1e8), key="f5",
                    help="最终归属于股东的利润。利润总额 - 所得税费用。利润表末行")

        # ========== 现金流量表 & 财务比率 ==========
        with st.expander("💹 现金流量表 & 关键比率 (Cash Flow & Ratios)", expanded=True):
            st.caption("反映企业现金流入流出情况，及偿债能力、盈利能力等关键指标")
            c1, c2, c3 = st.columns(3)
            with c1:
                financial_data_manual["经营活动现金流净额"] = st.number_input("🔄 经营现金流净额", value=_v("经营活动现金流净额"), key="f7",
                    help="主营业务产生的现金净流入。正值说明经营造血能力强。取自现金流量表")
                financial_data_manual["投资活动现金流净额"] = st.number_input("🏗️ 投资现金流净额", value=_v("投资活动现金流净额"), key="f24",
                    help="购置/处置固定资产、股权投资等产生的现金净额。通常为负表示扩张")
                financial_data_manual["筹资活动现金流净额"] = st.number_input("📥 筹资现金流净额", value=_v("筹资活动现金流净额"), key="f25",
                    help="借款、还款、分红、增发等融资活动产生的现金净额")
            with c2:
                financial_data_manual["资产负债率"] = st.number_input("📊 资产负债率 (%)", min_value=0.0, max_value=100.0,
                    value=float(default_financial.get("资产负债率", 0))*100 if default_financial.get("资产负债率") else 0.0, key="f9") / 100
                st.caption(f"当前: {financial_data_manual.get('资产负债率', 0)*100:.1f}% | 计算公式: 总负债 / 总资产")
                financial_data_manual["ROE"] = st.number_input("📈 净资产收益率 ROE (%)", min_value=-100.0, max_value=100.0,
                    value=float(default_financial.get("ROE", 0))*100 if default_financial.get("ROE") else 0.0, key="f8") / 100
                st.caption(f"当前: {financial_data_manual.get('ROE', 0)*100:.1f}% | 计算公式: 净利润 / 所有者权益")
            with c3:
                financial_data_manual["营业收入增长率"] = st.number_input("📉 营收增长率 (%)", min_value=-100.0, max_value=1000.0,
                    value=float(default_financial.get("营业收入增长率", 0))*100 if default_financial.get("营业收入增长率") else 0.0, key="f10") / 100
                st.caption(f"当前: {financial_data_manual.get('营业收入增长率', 0)*100:.1f}% | 计算公式: (本年营收 - 上年营收) / 上年营收")
                financial_data_manual["毛利率"] = st.number_input("🎯 毛利率 (%)", min_value=-100.0, max_value=100.0,
                    value=float(default_financial.get("毛利率", 0))*100 if default_financial.get("毛利率") else 0.0, key="f26") / 100
                st.caption(f"当前: {financial_data_manual.get('毛利率', 0)*100:.1f}% | 计算公式: (营业收入 - 营业成本) / 营业收入")

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
        _render_empty_state("📉", "暂无检测结果", "还没有生成任何年份的检测数据。请先上传企业年报并执行检测分析。", "💡 前往「舞弊检测」开始分析")
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

    risk_colors = {"high": "#EF4444", "medium": "#F59E0B", "low": "#10B981"}
    risk_bg = {"high": "rgba(239,68,68,0.1)", "medium": "rgba(245,158,11,0.1)", "low": "rgba(16,185,129,0.1)"}
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
                _render_empty_state("🤖", "暂无AI特征评分", "当前检测记录缺少AI文本特征评分数据，可能是通过快速检测生成的结果。", "💡 完整检测将自动提取7维AI特征")

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
    _render_page_header("AI 智能问答", "财务舞弊领域专业问答助手，7×24 随时解答")

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
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("""
            <div style="display:flex;align-items:center;gap:10px;padding:4px 0;">
                <div style="display:flex;gap:4px;align-items:center;">
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0s;"></span>
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0.16s;"></span>
                    <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3B82F6;animation:thinkingBounce 1.4s infinite ease-in-out both;animation-delay:0.32s;"></span>
                </div>
                <span style="font-size:0.85rem;color:#64748B;">AI 正在思考中...</span>
            </div>
            """, unsafe_allow_html=True)

            try:
                import requests

                url = f"{API_BASE_URL}/qa/ask-stream"
                req_headers = {
                    "Authorization": f"Bearer {st.session_state.token}",
                    "Content-Type": "application/json"
                }
                req_data = {"question": prompt}

                response = requests.post(url, json=req_data, headers=req_headers, stream=True, timeout=120)

                if response.status_code == 200:
                    def _stream_generator():
                        for line in response.iter_lines(decode_unicode=True):
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    event_data = json.loads(data_str)
                                    content = event_data.get("content")
                                    if content and isinstance(content, str):
                                        yield content
                                    if event_data.get("error"):
                                        break
                                except json.JSONDecodeError:
                                    continue

                    full_answer = st.write_stream(_stream_generator)
                    thinking_placeholder.empty()
                    st.session_state.chat_history.append({"role": "assistant", "content": full_answer})
                else:
                    thinking_placeholder.empty()
                    result = make_api_request("/qa/ask", method="POST", data={"question": prompt})
                    if result and "answer" in result:
                        answer = result["answer"]
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    else:
                        st.error("回答失败，请稍后重试")

            except Exception as e:
                thinking_placeholder.empty()
                result = make_api_request("/qa/ask", method="POST", data={"question": prompt})
                if result and "answer" in result:
                    answer = result["answer"]
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"回答失败: {str(e)}")


# ================= 我的检测页面 =================
def render_my_detections():
    """渲染「我的检测」页面"""
    _render_page_header("我的检测", "历史检测记录与报告管理")

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
        _render_empty_state("🔍", "暂无检测记录", "您还没有执行过任何舞弊检测。上传企业年报，AI 将自动分析财务风险。", "💡 前往「舞弊检测」开始首次分析")


# ================= 会员中心页面 =================
def render_membership():
    """渲染会员中心/价格中心页面 - 审计平台四版本B端定价"""
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px 0;">
        <h1 style="font-size: 2.5rem; font-weight: 800; margin-bottom: 8px;">
            <span style="background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
                选择适合事务所的方案
            </span>
        </h1>
        <p style="color: #64748B; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            面向会计师事务所的专业级审计数字化解决方案，按团队规模灵活选择
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ========== 上排：基础版 / 专业版 / 高级版 ==========
    plans_top = [
        {
            "name": "基础版",
            "price": "1.98",
            "price_unit": "万/年",
            "price_note": "固定年费",
            "target": "初创/小型事务所（团队 < 10人）",
            "highlight": False,
            "value": "入门级效率工具，以极低成本启用数字化审计，规范单个项目流程",
            "features": [
                ("单项目审计", True),
                ("3年财报分析", True),
                ("风险评分底稿高亮", True),
                ("基础建议报告", True),
                ("多项目并行管理", False),
                ("可视化雷达图", False),
                ("同业案例对标", False),
                ("整改跟踪引擎", False),
                ("原文溯源", False),
                ("Open API接口", False),
                ("团队权限管理", False),
                ("私有化部署", False),
            ],
            "cta": "立即咨询",
            "cta_type": "secondary",
        },
        {
            "name": "专业版",
            "price": "3.98",
            "price_unit": "万起/年",
            "price_note": "5项目版 3.98万 / 10项目版 5.98万",
            "target": "成长型/标准中型所（团队 10-50人）",
            "highlight": True,
            "value": "多项目协同管理平台，实现多个项目并行管理与质量把控，提升团队标准化水平",
            "features": [
                ("单项目审计", True),
                ("3年财报分析", True),
                ("风险评分底稿高亮", True),
                ("基础建议报告", True),
                ("多项目并行（≤10个/年）", True),
                ("可视化雷达图", True),
                ("同业案例对标", True),
                ("整改跟踪引擎", True),
                ("原文溯源", True),
                ("Open API接口", False),
                ("团队权限管理", False),
                ("私有化部署", False),
            ],
            "cta": "立即咨询",
            "cta_type": "primary",
        },
        {
            "name": "高级版",
            "price": "8.8",
            "price_unit": "万起/年",
            "price_note": "基础平台费 + 项目增量包 + 高级模块",
            "target": "成熟型中型所/区域领先所（团队 50-150人）",
            "highlight": False,
            "value": "一体化协同与集成平台，支撑跨部门复杂协作，具备与企业或内部系统集成的能力",
            "features": [
                ("含20个基础项目", True),
                ("3年财报分析", True),
                ("风险评分底稿高亮", True),
                ("高级建议报告", True),
                ("多项目并行", True),
                ("可视化雷达图", True),
                ("同业案例对标", True),
                ("整改跟踪引擎", True),
                ("原文溯源", True),
                ("Open API接口", True),
                ("团队与角色权限管理", True),
                ("高级数据分析模块", True),
                ("私有化部署", False),
            ],
            "cta": "立即咨询",
            "cta_type": "secondary",
        },
    ]

    cols = st.columns(3)
    for idx, plan in enumerate(plans_top):
        with cols[idx]:
            card_cls = "pricing-card pricing-highlight" if plan["highlight"] else "pricing-card"
            badge = '<div style="background: linear-gradient(135deg, #2563EB, #1D4ED8); color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-block; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(37,99,235,0.25);">最受欢迎</div>' if plan["highlight"] else '<div style="height: 32px;"></div>'

            st.markdown(f"""
            <div style="border-radius: 20px; padding: 28px; height: 100%; animation: fadeInUp 0.5s ease-out {idx*0.15}s both;" class="{card_cls}">
                {badge}
                <h3 style="font-size: 1.4rem; margin-bottom: 4px; color: #0F172A;">{plan['name']}</h3>
                <p style="color: #64748B; font-size: 0.85rem; margin-bottom: 16px;">{plan['target']}</p>
                <div style="margin: 20px 0;">
                    <span class="price-text" style="font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #2563EB, #1D4ED8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">¥{plan['price']}</span>
                    <span style="color: #64748B; font-size: 0.95rem; font-weight: 600;">{plan['price_unit']}</span>
                </div>
                <p style="color: #94A3B8; font-size: 0.8rem; margin: -12px 0 16px 0;">{plan['price_note']}</p>
                <p style="color: #475569; font-size: 0.9rem; line-height: 1.6; min-height: 48px; margin-bottom: 20px;">{plan['value']}</p>
                <div style="border-top: 1px solid #E2E8F0; padding-top: 16px;">
            """, unsafe_allow_html=True)

            for feat, included in plan["features"]:
                cls = "feature-yes" if included else "feature-no"
                icon = "✓" if included else "—"
                st.markdown(f"<p class='{cls}' style='margin: 6px 0; font-size: 0.85rem;'>{icon} {feat}</p>", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

            btn_type = plan.get("cta_type", "secondary")
            if st.button(plan["cta"], use_container_width=True, key=f"biz_plan_cta_{idx}", type=btn_type):
                st.info("""
                 **商务咨询**

                电话：400-888-8888
                邮箱：sales@auditmind.com
                微信：AuditMind_Sales

                工作时间：周一至周五 9:00-18:00
                """)


    # ========== 功能对比表 ==========
    st.divider()
    st.markdown("<h3 style='text-align:center; margin-bottom: 24px;'> 功能对比详情</h3>", unsafe_allow_html=True)

    comparison_data = [
        {"功能模块": "项目数量", "基础版": "1个", "专业版": "≤10个/年", "高级版": "20个基础"},
        {"功能模块": "财报分析年限", "基础版": "3年", "专业版": "5年", "高级版": "不限"},
        {"功能模块": "风险评分底稿", "基础版": "包含", "专业版": "包含", "高级版": "包含"},
        {"功能模块": "可视化雷达图", "基础版": "—", "专业版": "包含", "高级版": "包含"},
        {"功能模块": "同业案例对标", "基础版": "—", "专业版": "包含", "高级版": "包含"},
        {"功能模块": "整改跟踪引擎", "基础版": "—", "专业版": "包含", "高级版": "包含"},
        {"功能模块": "原文溯源", "基础版": "—", "专业版": "包含", "高级版": "包含"},
        {"功能模块": "Open API接口", "基础版": "—", "专业版": "—", "高级版": "包含"},
        {"功能模块": "团队权限管理", "基础版": "—", "专业版": "—", "高级版": "包含"},
        {"功能模块": "批量检测", "基础版": "—", "专业版": "—", "高级版": "包含"},
    ]

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)


def render_report_management():
    """渲染报告管理页面"""
    st.markdown("""
    <div style="margin: -1rem -1rem 1.5rem -1rem; padding: 2rem 1.5rem; background: #F8FAFC; border-bottom: 1px solid #E2E8F0; border-radius: 20px; position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(37,99,235,0.12); border-radius: 50%; "></div>
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
        _render_empty_state("📑", "暂无报告", "您还没有生成任何检测报告。完成一次舞弊检测后，系统将自动生成完整的分析报告。", "💡 前往「舞弊检测」生成您的首份报告")
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

    # 报告列表 - 精美卡片设计
    format_icons = {"PDF": "📄", "Word": "📝", "Excel": "📊"}
    format_map = {"PDF": "pdf", "Word": "word", "Excel": "excel"}

    for report in filtered_history[:20]:  # 限制显示前20条
        risk_level = report.get("risk_level", "low")
        _risk_defaults = {
            "high": {"emoji": "🔴", "label": "高风险", "color": "#EF4444", "bg": "rgba(239,68,68,0.08)"},
            "medium": {"emoji": "🟡", "label": "中风险", "color": "#F59E0B", "bg": "rgba(245,158,11,0.08)"},
            "low": {"emoji": "🟢", "label": "低风险", "color": "#10B981", "bg": "rgba(16,185,129,0.08)"}
        }
        risk_config = _risk_defaults.get(risk_level, _risk_defaults["low"])

        has_report = report['id'] in report_map
        report_info = report_map.get(report['id'])
        is_selected = report["id"] in st.session_state.selected_reports

        # 卡片头部信息 — 用 components.v1.html 避免 markdown 缩进被当成代码块
        status_badge = (
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;'
            'font-size:0.75rem;font-weight:600;background:rgba(16,185,129,0.08);color:#10B981;">✅ 已生成</span>'
            if has_report else
            '<span style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:20px;'
            'font-size:0.75rem;font-weight:600;background:rgba(148,163,184,0.1);color:#64748B;">⏳ 未生成</span>'
        )
        card_html = (
            '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:16px 20px;margin-bottom:12px;'
            'transition:all .2s ease;position:relative;overflow:hidden;" '
            'onmouseover="this.style.boxShadow=\'0 4px 16px rgba(37,99,235,0.1)\';this.style.borderColor=\'#BFDBFE\';" '
            'onmouseout="this.style.boxShadow=\'none\';this.style.borderColor=\'#E2E8F0\';">'
            '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">'
            '<div style="display:flex;align-items:center;gap:14px;flex:1;min-width:200px;">'
            '<div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#EFF6FF,#DBEAFE);'
            'display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">🏢</div>'
            '<div>'
            '<div style="font-size:1rem;font-weight:700;color:#0F172A;">' + report.get('company_name', '未命名') + '</div>'
            '<div style="font-size:0.8rem;color:#64748B;margin-top:2px;">'
            + report.get('stock_code', '-') + ' · ' + str(report.get('year', '-')) + '年度 · ' + str(report.get('created_at', ''))[:10] +
            '</div></div></div>'
            '<div style="display:flex;align-items:center;gap:16px;">'
            '<div style="text-align:center;padding:6px 14px;border-radius:10px;background:' + risk_config['bg'] + ';'
            'border:1px solid ' + risk_config['color'] + '22;">'
            '<div style="font-size:0.75rem;font-weight:700;color:' + risk_config['color'] + ';">'
            + risk_config['emoji'] + ' ' + risk_config['label'] + '</div>'
            '<div style="font-size:0.85rem;font-weight:600;color:' + risk_config['color'] + ';margin-top:2px;">'
            + f"{report.get('fraud_probability', 0):.1%}" +
            '</div></div></div>'
            '<div style="text-align:right;">' + status_badge + '</div></div></div>'
        )
        st.components.v1.html(card_html, height=85, scrolling=False)

        # 操作按钮区
        op_cols = st.columns([0.5, 2, 2, 2, 1.5])

        with op_cols[0]:
            if st.checkbox("选择", value=is_selected, key=f"select_{report['id']}", label_visibility="collapsed"):
                st.session_state.selected_reports.add(report["id"])
            else:
                st.session_state.selected_reports.discard(report["id"])

        with op_cols[1]:
            st.caption(f"风险评分: **{report.get('risk_score', 0):.1f}**")

        with op_cols[2]:
            if has_report and report_info and report_info.get('report_type'):
                st.caption(f"报告格式: {report_info['report_type'].upper()}")

        with op_cols[3]:
            # 格式选择 + 下载按钮
            dl_cols = st.columns([2, 1])
            with dl_cols[0]:
                selected_format = st.selectbox(
                    "格式",
                    ["📄 PDF", "📝 Word", "📊 Excel"],
                    key=f"format_{report['id']}",
                    label_visibility="collapsed"
                )
                # 提取纯格式名（去掉emoji）
                selected_format_clean = selected_format.replace("📄 ", "").replace("📝 ", "").replace("📊 ", "")
            with dl_cols[1]:
                if st.button("📥 下载", key=f"dl_report_{report['id']}", help=f"下载{selected_format_clean}报告", use_container_width=True):
                    with st.spinner(f"生成{selected_format_clean}报告中..."):
                        format_code = format_map[selected_format_clean]
                        result = make_api_request(
                            f"/report/{report['id']}/export?format={format_code}",
                            method="POST"
                        )
                        if result and result.get("download_url"):
                            st.success(f"✅ {selected_format_clean}报告已生成！")
                            try:
                                import requests
                                download_url = f"{API_BASE_URL}{result['download_url']}"
                                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                                response = requests.get(download_url, headers=headers, timeout=30)

                                if response.status_code == 200:
                                    filename = result.get("filename", f"报告.{format_code}")
                                    file_content = response.content

                                    mime_types = {
                                        "pdf": "application/pdf",
                                        "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    }
                                    mime_type = mime_types.get(format_code, "application/octet-stream")

                                    st.download_button(
                                        label=f"📥 下载 {filename}",
                                        data=file_content,
                                        file_name=filename,
                                        mime=mime_type,
                                        key=f"download_btn_{report['id']}_{format_code}"
                                    )
                                else:
                                    st.error(f"❌ 下载失败: HTTP {response.status_code}")
                            except Exception as e:
                                st.error(f"❌ 下载出错: {str(e)}")
                        else:
                            st.error("❌ 生成失败")

        with op_cols[4]:
            if st.button("🗑️ 删除", key=f"del_report_{report['id']}", help="删除此报告", use_container_width=True):
                if make_api_request(f"/detection/{report['id']}", method="DELETE"):
                    st.success("🗑️ 已删除")
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
            if st.button("🗑️ 批量删除", use_container_width=True):
                st.warning("确认删除选中的报告？")
                if st.button("✅ 确认删除"):
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
        <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(37,99,235,0.12); border-radius: 50%; "></div>
        <div style="position: relative; z-index: 1;">
            <h2 style="color: #0F172A; font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;"> 案例中心</h2>
            <p style="color: #475569; font-size: 1rem; margin: 0;">A股历史舞弊案例库，深度解析典型风险模式</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 获取所有案例
    cases = make_api_request("/detection/cases")

    if not cases:
        _render_empty_state("📚", "暂无案例数据", "案例库正在建设中。您可以关注真实的舞弊案例和健康企业标杆，学习识别技巧。", "💡 上传企业年报进行实时检测")
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
                risk_color = "#EF4444" if risk_level == "high" else "#F59E0B"
                st.markdown(f"""
                <div class="glass-card" style="padding: 1.5rem; animation-delay: {idx * 0.1}s; position: relative; overflow: hidden;">
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: {risk_color};"></div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; background: rgba(239,68,68,0.12); color: #EF4444; margin-bottom: 0.75rem;">
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
                    <div style="position: absolute; top: 0; left: 0; right: 0; height: 4px; background: #10B981;"></div>
                    <div style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; background: rgba(16,185,129,0.12); color: #10B981; margin-bottom: 0.75rem;">
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

    # 显示顶部水平导航栏
    render_header()

    # 显示登录弹窗(如果需要)
    if st.session_state.get('show_login_modal', False) and not st.session_state.logged_in:
        render_login_modal()

    # 路由分发
    page = st.session_state.current_page
    # 非首页页面统一包裹 content-wrap 以限制内容宽度
    non_fullwidth_pages = ["fs", "detect", "qa", "history", "reports", "membership", "settings", "pricing", "cases"]
    needs_wrap = page in non_fullwidth_pages

    if needs_wrap:
        st.markdown('<div class="content-wrap" style="padding-top: 2rem; padding-bottom: 3rem;">', unsafe_allow_html=True)

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
            <div style="margin: -2rem -2rem 2rem -2rem; padding: 3rem 2rem; background: linear-gradient(135deg, #0F172A, #1E293B); position: relative; overflow: hidden;">
                <div style="position: absolute; top: -60px; right: -60px; width: 240px; height: 240px; background: rgba(37,99,235,0.15); border-radius: 50%;"></div>
                <div style="position: absolute; bottom: -40px; left: 10%; width: 180px; height: 180px; background: rgba(96,165,250,0.1); border-radius: 50%;"></div>
                <div style="position: relative; z-index: 1; max-width: 1280px; margin: 0 auto;">
                    <h1 style="color: #FFFFFF; font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; letter-spacing: -1.5px;">价格中心</h1>
                    <p style="color: #94A3B8; font-size: 1.05rem;">选择适合您的方案，解锁全部智能审计能力</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            render_membership()
        elif page == "cases":
            render_case_center()

    if needs_wrap:
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
