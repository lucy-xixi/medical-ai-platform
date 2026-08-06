# -*- coding: utf-8 -*-
"""
实验室指标分析

基于 fact_observation，统计 HbA1c、血压、肌酐等指标的描述统计与异常比例。
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from analytics.logger import setup_logger
from analytics.warehouse_loader import REPORTS_DIR, ensure_report_dirs

logger = setup_logger("analytics.laboratory")

# 实验室指标映射（显示名 -> 仓库 measurement_type）
LAB_METRICS = {
    "HbA1c": ["hba1c"],
    "Blood Pressure (Systolic)": ["systolic_blood_pressure"],
    "Blood Pressure (Diastolic)": ["diastolic_blood_pressure"],
    "Creatinine": ["creatinine"],
}

# 临床参考范围（用于异常判定）
ABNORMAL_RULES = {
    "hba1c": lambda v: v > 6.5,
    "systolic_blood_pressure": lambda v: (v > 140) | (v < 90),
    "diastolic_blood_pressure": lambda v: (v > 90) | (v < 60),
    "creatinine": lambda v: v > 133,
}


def _abnormal_ratio(values: pd.Series, mtype: str) -> float:
    """计算异常值比例。"""
    rule = ABNORMAL_RULES.get(mtype)
    if rule is None or values.empty:
        return 0.0
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    abnormal = rule(numeric).sum()
    return round(abnormal / len(numeric) * 100, 2)


def analyze_laboratory(fact_observation: pd.DataFrame) -> pd.DataFrame:
    """
    执行实验室指标统计分析。

    Returns:
        各指标描述统计与异常比例 DataFrame
    """
    logger.info("开始实验室指标分析...")
    rows: List[dict] = []

    for display_name, mtypes in LAB_METRICS.items():
        subset = fact_observation[fact_observation["measurement_type"].isin(mtypes)]
        if subset.empty:
            rows.append(
                {
                    "Metric": display_name,
                    "Count": 0,
                    "Mean": np.nan,
                    "Median": np.nan,
                    "Max": np.nan,
                    "Min": np.nan,
                    "Abnormal Percentage": "0%",
                }
            )
            continue

        values = pd.to_numeric(subset["value"], errors="coerce").dropna()
        mtype = mtypes[0]
        abn_pct = _abnormal_ratio(subset["value"], mtype)

        rows.append(
            {
                "Metric": display_name,
                "Count": len(values),
                "Mean": round(values.mean(), 2),
                "Median": round(values.median(), 2),
                "Max": round(values.max(), 2),
                "Min": round(values.min(), 2),
                "Abnormal Percentage": f"{abn_pct}%",
            }
        )

    result = pd.DataFrame(rows)
    logger.info("实验室指标分析完成 | 指标数: %d", len(result))
    return result


def save_laboratory_statistics(stats: pd.DataFrame) -> str:
    """保存实验室统计 CSV。"""
    ensure_report_dirs()
    output = REPORTS_DIR / "laboratory_statistics.csv"
    stats.to_csv(output, index=False, encoding="utf-8-sig")
    logger.info("已保存: %s", output)
    return str(output)
