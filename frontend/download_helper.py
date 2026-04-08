"""
文件下载辅助工具 - 支持认证下载
"""
import streamlit as st
import requests
from typing import Optional

API_BASE_URL = "http://47.76.180.29:8000/api"


def download_file_with_auth(download_url: str, filename: str, token: str):
    """
    使用JavaScript下载文件（携带认证头）

    由于浏览器直接点击链接无法携带Authorization头，
    我们使用JavaScript发起fetch请求并触发下载
    """
    if not token:
        st.error("请先登录")
        return

    # 根据文件扩展名确定MIME类型
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    mime_types = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv'
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')

    js_code = f"""
    <script>
    (async function() {{
        try {{
            const response = await fetch('{download_url}', {{
                method: 'GET',
                headers: {{
                    'Authorization': 'Bearer {token}'
                }}
            }});

            if (!response.ok) {{
                const errorText = await response.text();
                console.error('下载失败:', response.status, errorText);
                alert('下载失败: ' + response.status + '\\n' + errorText);
                return;
            }}

            // 获取二进制数据
            const blob = await response.blob();
            console.log('下载成功，文件大小:', blob.size, '类型:', blob.type);

            // 如果服务器没有返回正确的MIME类型，强制设置
            const fileBlob = new Blob([blob], {{ type: '{mime_type}' }});

            const url = window.URL.createObjectURL(fileBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{filename}';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();

            // 延迟清理，确保下载开始
            setTimeout(() => {{
                window.URL.revokeObjectURL(url);
                if (a.parentNode) {{
                    document.body.removeChild(a);
                }}
            }}, 1000);

        }} catch (error) {{
            console.error('下载错误:', error);
            alert('下载失败: ' + error.message);
        }}
    }})();
    </script>
    """

    st.components.v1.html(js_code, height=0)
    st.success(f"正在下载: {filename}")


def create_download_button(
    detection_id: int,
    report_format: str,
    filename: str,
    button_label: str = "📥 下载"
):
    """
    创建认证下载按钮
    """
    token = st.session_state.get('token', '')

    if not token:
        st.error("请先登录")
        return

    download_url = f"{API_BASE_URL}/report/{detection_id}/download?format={report_format}"

    if st.button(button_label, key=f"download_btn_{detection_id}_{report_format}"):
        download_file_with_auth(download_url, filename, token)
