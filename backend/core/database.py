"""
数据库连接管理
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.models.database import Base

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话（依赖注入用）
    Yield 给 FastAPI 依赖系统使用
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库 - 创建所有表和索引
    """
    # 🔥 导入所有模型 + 忽略未引用提示（必须导入，用于注册表）
    from backend.models.database import (
        User, UserProfile, DetectionRecord, Report,
        Order, Transaction, Subscription, DemoCase, QAHistory, SystemConfig,
        IPORejectedCase, RemediationSuggestion
    )  # noqa: F401

    # 🔥 现在用的是【和模型一致的Base】，能创建所有表！
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功！")

    # 创建性能优化索引
    try:
        from backend.core.database_indexes import create_indexes
        create_indexes()
    except Exception as e:
        print(f"⚠️  索引创建失败（不影响功能）: {e}")


def drop_db():
    """
    删除所有表（仅开发环境使用）
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  所有数据库表已删除！")
