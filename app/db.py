"""数据库连接管理。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """FastAPI 依赖：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
