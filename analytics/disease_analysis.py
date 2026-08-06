# -*- coding: utf-8 -*-
"""
疾病统计分析

基于 dim_condition 与 fact_condition，分析 ICD 疾病分布与 Top 10 疾病。
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd

from analytics.logger import setup_logger
from analytics.warehouse_loader import REPORTS_DIR, ensure_report_dirs

logger = setup_logger("analytics.disease")

# 慢性疾病 ICD-10 前缀
CHRONIC_ICD_PREFIXES = ("E11", "I10", "I25", "N18", "J44", "E78", "F32", "M54", "K21", "G43")


def analyze_diseases(
    dim_condition: pd.DataFrame,
    fact_condition: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    执行疾病统计分析。

    Returns:
        (汇总指标, Top10 疾病, 慢性疾病统计)
    """
    logger.info("开始疾病统计分析...")

    icd_count = len(dim_condition)

    # 关联患者数
    if not fact_condition.empty and not dim_condition.empty:
        merged = fact_condition.merge(dim_condition, on="condition_key", how="left")
        disease_counts = (
            merged.groupby(["condition_name", "icd_code"], as_index=False)["patient_key"]
            .nunique()
            .rename(columns={"patient_key": "Patient Count"})
            .sort_values("Patient Count", ascending=False)
        )
    else:
        disease_counts = dim_condition.copy()
        disease_counts["Patient Count"] = 0

    top10 = disease_counts.head(10)

    # 慢性疾病
    chronic_mask = dim_condition["icd_code"].str.upper().str.startswith(CHRONIC_ICD_PREFIXES)
    chronic_conditions = dim_condition[chronic_mask].copy()
    if not fact_condition.empty:
        chronic_keys = set(chronic_conditions["condition_key"])
        chronic_patients = fact_condition[fact_condition["condition_key"].isin(chronic_keys)][
            "patient_key"
        ].nunique()
    else:
        chronic_patients = 0

    chronic_stats = pd.DataFrame(
        [
            {"Metric": "Chronic Disease Types", "Value": len(chronic_conditions)},
            {"Metric": "Chronic Disease Patients", "Value": chronic_patients},
        ]
    )

    summary = pd.DataFrame([{"Metric": "Total ICD Disease Types", "Value": icd_count}])

    logger.info("ICD 疾病类型: %d | Top1: %s", icd_count, top10.iloc[0]["condition_name"] if len(top10) else "N/A")
    return summary, top10, chronic_stats


def save_disease_statistics(
    summary: pd.DataFrame,
    top10: pd.DataFrame,
    chronic_stats: pd.DataFrame,
) -> str:
    """保存疾病统计 CSV。"""
    ensure_report_dirs()
    output = REPORTS_DIR / "disease_statistics.csv"

    with open(output, "w", encoding="utf-8-sig", newline="") as f:
        f.write("# Disease Summary\n")
        summary.to_csv(f, index=False)
        f.write("\n# Top 10 Diseases\n")
        top10.to_csv(f, index=False)
        f.write("\n# Chronic Disease Statistics\n")
        chronic_stats.to_csv(f, index=False)

    logger.info("已保存: %s", output)
    return str(output)
