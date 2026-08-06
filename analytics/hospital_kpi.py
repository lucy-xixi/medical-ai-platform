# -*- coding: utf-8 -*-
"""
医院运营 KPI 分析

汇总数据仓库核心指标，生成 Hospital KPI Dashboard 数据。
"""

from __future__ import annotations

import pandas as pd

from analytics.logger import setup_logger
from analytics.warehouse_loader import REPORTS_DIR, ensure_report_dirs

logger = setup_logger("analytics.kpi")


def analyze_hospital_kpi(data: dict) -> pd.DataFrame:
    """
    生成医院运营 KPI 指标。

    Args:
        data: warehouse 表字典

    Returns:
        KPI DataFrame
    """
    logger.info("开始医院 KPI 分析...")

    kpi = [
        {"KPI": "Total Patients", "Value": len(data.get("dim_patient", []))},
        {"KPI": "Total Encounters", "Value": len(data.get("fact_encounter", []))},
        {"KPI": "Total Conditions", "Value": len(data.get("fact_condition", []))},
        {"KPI": "Total Medications", "Value": len(data.get("fact_medication", []))},
        {"KPI": "Total Observations", "Value": len(data.get("fact_observation", []))},
    ]

    df = pd.DataFrame(kpi)
    logger.info(
        "KPI | Patients=%d Encounters=%d Conditions=%d",
        kpi[0]["Value"],
        kpi[1]["Value"],
        kpi[2]["Value"],
    )
    return df


def save_hospital_kpi(kpi_df: pd.DataFrame) -> str:
    """保存 KPI CSV。"""
    ensure_report_dirs()
    output = REPORTS_DIR / "hospital_kpi.csv"
    kpi_df.to_csv(output, index=False, encoding="utf-8-sig")
    logger.info("已保存: %s", output)
    return str(output)
