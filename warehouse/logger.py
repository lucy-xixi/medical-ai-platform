# -*- coding: utf-8 -*-
"""数据仓库模块统一日志配置，输出至 logs/warehouse.log。"""

from __future__ import annotations

import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "warehouse.log"

_CONFIGURED = False


def setup_logger(name: str = "warehouse") -> logging.Logger:
    """配置并返回数据仓库日志记录器。"""
    global _CONFIGURED

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not _CONFIGURED:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        root_logger = logging.getLogger("warehouse")
        root_logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        _CONFIGURED = True

    return logging.getLogger(name)
