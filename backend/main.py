"""
FastAPI 主应用入口
财务舞弊识别 SaaS 平台 - Backend API
"""
import sys
import os
# 添加项目根目录到Python路径，支持backend.xxx导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
import os

from core.config import settings
from core.database import init_db

# 导入路由
from routers import user, detection, qa, payment, report, user_account, payment_system, membership, upload, report_export, financial_statement

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于生成式 AI 的上市公司财务舞弊智能识别 SaaS 平台",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit 本地开发
        "http://localhost:3000",
        "https://*.streamlit.app",  # Streamlit Cloud
        "https://*.onrender.com"    # Render 部署
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 压缩中间件 - 提高传输速度
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 挂载静态文件目录（报告、上传文件等）
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs("result/reports", exist_ok=True)
os.makedirs("backend/templates/reports", exist_ok=True)  # 确保模板目录存在
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_FOLDER), name="uploads")
app.mount("/reports", StaticFiles(directory="result/reports"), name="reports")


# 包含路由
app.include_router(user.router, prefix=settings.API_PREFIX)
app.include_router(user_account.router, prefix=settings.API_PREFIX)
app.include_router(detection.router, prefix=settings.API_PREFIX)
app.include_router(qa.router, prefix=settings.API_PREFIX)
app.include_router(payment.router, prefix=settings.API_PREFIX)
app.include_router(payment_system.router, prefix=settings.API_PREFIX)
app.include_router(membership.router, prefix=settings.API_PREFIX)
# report_export.router 必须先注册，避免被 report.router 的/{report_id} 拦截
app.include_router(report_export.router, prefix=settings.API_PREFIX)
app.include_router(report.router, prefix=settings.API_PREFIX)
app.include_router(upload.router, prefix=settings.API_PREFIX)
app.include_router(financial_statement.router, prefix=settings.API_PREFIX)


# 健康检查
@app.get("/")
def root():
    """API 根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


# 数据库初始化（启动时自动执行）
@app.on_event("startup")
def startup_event():
    """应用启动时执行"""
    print("=" * 60)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)

    # 初始化数据库
    try:
        init_db()
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"⚠️  数据库初始化失败：{e}")

    # 尝试初始化检测引擎以加载模型
    try:
        from services.detection_service import detection_engine
        print("✅ 检测引擎初始化成功")
        if detection_engine.ai_model:
            print("✅ AI 模型加载成功")
        if detection_engine.traditional_model:
            print("✅ 传统模型加载成功")
    except Exception as e:
        print(f"⚠️  检测引擎初始化失败：{e}")

    # 打印 API 访问地址
    print(f"\n📡 API 文档地址：http://localhost:8000/docs")
    print(f"📡 本地 API 地址：http://localhost:8000{settings.API_PREFIX}")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
