# -*- coding: utf-8 -*-
"""数据质量模块 — 从 SQLite 加载数据为 pandas DataFrame。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import engine


def load_all_tables() -> Dict[str, pd.DataFrame]:
    """
    从 hospital.db 加载全部业务表。

    Returns:
        表名 -> DataFrame 字典
    """
    tables = ["patients", "encounters", "conditions", "medications", "observations"]
    data: Dict[str, pd.DataFrame] = {}
    for table in tables:
        data[table] = pd.read_sql(f"SELECT * FROM {table}", engine)
    return data
