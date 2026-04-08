"""
PostgreSQL 数据库连接模块（Phase 1: 多租户 SaaS 化）
从 SQLite 迁移到 PostgreSQL，保留 get_db 兼容接口
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://scanorder:scanorder@39.104.107.136:5432/scanorder"
)

# PostgreSQL 连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # 连接前 ping 检测
    echo=False               # 调试时改为 True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """兼容 FastAPI Depends 的数据库会话生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
