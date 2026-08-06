# -*- coding: utf-8 -*-
"""
患者统计分析

基于 dim_patient 维度表，分析患者总数、性别与年龄分布。
"""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd

from analytics.logger import setup_logger
from analytics.warehouse_loader import REPORTS_DIR, ensure_report_dirs

logger = setup_logger("analytics.patient")


def _normalize_gender(gender: str) -> str:
    """统一性别标签为 Male / Female。"""
    g = str(gender).strip().lower()
    if g in ("male", "m", "男"):
        return "Male"
    if g in ("female", "f", "女"):
        return "Female"
    return "Other"


def analyze_patients(dim_patient: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    执行患者统计分析。

    Returns:
        (汇总指标 DataFrame, 年龄分组 DataFrame, 性别分布 DataFrame)
    """
    logger.info("开始患者统计分析...")
    df = dim_patient.copy()
    df["gender_norm"] = df["gender"].apply(_normalize_gender)

    total = len(df)
    male_count = int((df["gender_norm"] == "Male").sum())
    female_count = int((df["gender_norm"] == "Female").sum())
    male_pct = round(male_count / total * 100, 2) if total else 0.0
    female_pct = round(female_count / total * 100, 2) if total else 0.0

    summary = pd.DataFrame(
        [
            {"Metric": "Total Patients", "Value": total},
            {"Metric": "Male Count", "Value": male_count},
            {"Metric": "Female Count", "Value": female_count},
            {"Metric": "Male Percentage", "Value": f"{male_pct}%"},
            {"Metric": "Female Percentage", "Value": f"{female_pct}%"},
        ]
    )

    age_group_stats = (
        df.groupby("age_group", as_index=False)
        .size()
        .rename(columns={"size": "Patient Count"})
        .sort_values("age_group")
    )

    gender_stats = (
        df.groupby("gender_norm", as_index=False)
        .size()
        .rename(columns={"gender_norm": "Gender", "size": "Patient Count"})
    )

    logger.info("患者总数: %d | Male: %s%% | Female: %s%%", total, male_pct, female_pct)
    return summary, age_group_stats, gender_stats


def save_patient_statistics(
    summary: pd.DataFrame,
    age_group_stats: pd.DataFrame,
    gender_stats: pd.DataFrame,
) -> Dict[str, str]:
    """保存患者统计 CSV 报告。"""
    ensure_report_dirs()
    output = REPORTS_DIR / "patient_statistics.csv"

    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        f.write("# Patient Summary\n")
        summary.to_csv(f, index=False)
        f.write("\n# Age Group Distribution\n")
        age_group_stats.to_csv(f, index=False)
        f.write("\n# Gender Distribution\n")
        gender_stats.to_csv(f, index=False)

    logger.info("已保存: %s", output)
    return str(output)
