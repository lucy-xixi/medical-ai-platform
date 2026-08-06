# -*- coding: utf-8 -*-
"""
数据库连接模块

默认使用本地 SQLite (database/hospital.db)，无需安装数据库服务。
通过环境变量 DATABASE_URL 可切换至 MySQL / PostgreSQL。

示例:
    # SQLite（默认，开发环境）
    DATABASE_URL=sqlite:///database/hospital.db

    # MySQL（生产环境）
    DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/medical_platform

    # PostgreSQL（生产环境）
    DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/medical_platform
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

DATABASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_FILE = DATABASE_DIR / "hospital.db"
PROJECT_ROOT = DATABASE_DIR.parent


def get_database_url() -> str:
    """
    获取数据库连接 URL。

    优先读取环境变量 DATABASE_URL；未设置时使用本地 SQLite。
    """
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # 使用绝对路径，避免工作目录不同导致找不到数据库文件
    return f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"


def _configure_sqlite(engine: Engine) -> None:
    """为 SQLite 启用外键约束。"""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    """创建 SQLAlchemy Engine，自动适配 SQLite / MySQL / PostgreSQL。"""
    url = database_url or get_database_url()
    connect_args: dict = {}

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, echo=False, future=True, connect_args=connect_args)

    if url.startswith("sqlite"):
        _configure_sqlite(engine)

    return engine


# 全局 Engine 与 Session 工厂
engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db(drop_existing: bool = False) -> None:
    """
    创建所有数据表。

    Args:
        drop_existing: 若为 True，先删除已有表再重建（开发环境初始化时使用）。
    """
    if drop_existing:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """获取一个新的数据库 Session（调用方负责 close）。"""
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Session 上下文管理器，自动 commit / rollback / close。"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
