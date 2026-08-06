# -*- coding: utf-8 -*-
"""
药物使用分析

基于 dim_medication 与 fact_medication，分析用药排名与患者用药分布。
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd

from analytics.logger import setup_logger
from analytics.warehouse_loader import REPORTS_DIR, ensure_report_dirs

logger = setup_logger("analytics.medication")


def analyze_medications(
    dim_medication: pd.DataFrame,
    fact_medication: pd.DataFrame,
    dim_patient: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    执行药物使用分析。

    Returns:
        (用药排名, 患者用药数量分布)
    """
    logger.info("开始药物使用分析...")

    if not fact_medication.empty and not dim_medication.empty:
        merged = fact_medication.merge(dim_medication, on="medication_key", how="left")
        usage_rank = (
            merged.groupby("drug_name", as_index=False)
            .agg(Usage_Count=("medication_fact_key", "count"), Patient_Count=("patient_key", "nunique"))
            .sort_values("Usage_Count", ascending=False)
        )
    else:
        usage_rank = dim_medication.rename(columns={"drug_name": "drug_name"}).copy()
        usage_rank["Usage_Count"] = 0
        usage_rank["Patient_Count"] = 0

    # 每位患者用药数量分布
    if not fact_medication.empty:
        meds_per_patient = (
            fact_medication.groupby("patient_key", as_index=False)
            .size()
            .rename(columns={"size": "Medication Count"})
        )
        patient_dist = (
            meds_per_patient.groupby("Medication Count", as_index=False)
            .size()
            .rename(columns={"size": "Patient Count"})
            .sort_values("Medication Count")
        )
    else:
        patient_dist = pd.DataFrame(columns=["Medication Count", "Patient Count"])

    total_patients = len(dim_patient)
    logger.info("药物种类: %d | 总患者: %d", len(usage_rank), total_patients)
    return usage_rank, patient_dist


def save_medication_statistics(usage_rank: pd.DataFrame, patient_dist: pd.DataFrame) -> str:
    """保存用药统计 CSV。"""
    ensure_report_dirs()
    output = REPORTS_DIR / "medication_statistics.csv"

    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        f.write("# Medication Usage Ranking\n")
        usage_rank.to_csv(f, index=False)
        f.write("\n# Patient Medication Distribution\n")
        patient_dist.to_csv(f, index=False)

    logger.info("已保存: %s", output)
    return str(output)
