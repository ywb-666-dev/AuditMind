"""
Vercel Serverless入口
财务舞弊识别 SaaS 平台
"""
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入主应用
from main import app

# Vercel需要这个handler
handler = app
