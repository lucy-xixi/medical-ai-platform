# -*- coding: utf-8 -*-
"""Clinical RAG 模块统一日志配置。"""

from __future__ import annotations

import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "rag.log"

_CONFIGURED = False


def setup_logger(name: str = "rag") -> logging.Logger:
    """配置并返回 RAG 日志记录器。"""
    global _CONFIGURED

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not _CONFIGURED:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        root = logging.getLogger("rag")
        root.setLevel(logging.INFO)

        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(formatter)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)

        root.addHandler(fh)
        root.addHandler(ch)
        _CONFIGURED = True

    return logging.getLogger(name)
