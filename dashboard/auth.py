# -*- coding: utf-8 -*-
"""
内部演示登录模块

从 .env 读取演示账号，仅供内网/本地演示，不可用于生产环境。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# 演示默认账号（可通过 .env 覆盖）
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def get_demo_credentials() -> tuple[str, str]:
    """获取演示用户名与密码。"""
    username = os.getenv("DEMO_USERNAME", DEFAULT_USERNAME)
    password = os.getenv("DEMO_PASSWORD", DEFAULT_PASSWORD)
    return username, password


def verify_login(username: str, password: str) -> bool:
    """验证登录凭据。"""
    expected_user, expected_pass = get_demo_credentials()
    return (
        username.strip().lower() == expected_user.strip().lower()
        and password.strip() == expected_pass.strip()
    )
