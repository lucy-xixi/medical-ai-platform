# -*- coding: utf-8 -*-
"""从数据仓库 warehouse.db 只读加载分析数据。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warehouse.models import warehouse_engine

REPORTS_DIR = PROJECT_ROOT / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"


def load_warehouse_tables() -> Dict[str, pd.DataFrame]:
    """
    从 warehouse.db 加载全部星型模型表（只读）。

    Returns:
        表名 -> DataFrame
    """
    tables = [
        "dim_patient",
        "dim_condition",
        "dim_medication",
        "fact_encounter",
        "fact_observation",
        "fact_condition",
        "fact_medication",
    ]
    data: Dict[str, pd.DataFrame] = {}
    for table in tables:
        try:
            data[table] = pd.read_sql(f"SELECT * FROM {table}", warehouse_engine)
        except Exception:
            data[table] = pd.DataFrame()
    return data


def ensure_report_dirs() -> None:
    """确保 reports/ 与 reports/charts/ 目录存在。"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
