# -*- coding: utf-8 -*-
"""
数据完整性检查 (Completeness)

评估关键字段的非空覆盖率，是数据治理六维度之一。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from quality.logger import setup_logger

logger = setup_logger("quality.completeness")

# 各表需检查完整性的关键字段
COMPLETENESS_RULES: Dict[str, List[str]] = {
    "patients": ["patient_id", "gender", "birth_date"],
    "conditions": ["patient_id", "icd_code", "condition_name"],
    "medications": ["patient_id", "drug_name", "start_date"],
}


@dataclass
class CompletenessResult:
    """单字段完整性检查结果。"""

    table: str
    field: str
    total_records: int
    missing_records: int
    completeness_pct: float

    @property
    def label(self) -> str:
        """格式化输出标签，如 'Patient gender completeness'。"""
        singular = self.table.rstrip("s")
        return f"{singular.capitalize()} {self.field} completeness"


def _is_missing(series: pd.Series) -> pd.Series:
    """判断缺失值（含 NULL、空字符串、纯空白）。"""
    if series.dtype == object:
        stripped = series.astype(str).str.strip()
        return series.isna() | stripped.eq("") | stripped.eq("nan") | stripped.eq("None")
    return series.isna()


def check_field_completeness(df: pd.DataFrame, table: str, field: str) -> CompletenessResult:
    """
    检查单个字段的完整性。

    Args:
        df: 数据表 DataFrame
        table: 表名
        field: 字段名

    Returns:
        CompletenessResult 完整性结果
    """
    total = len(df)
    if total == 0:
        return CompletenessResult(table, field, 0, 0, 100.0)

    missing = int(_is_missing(df[field]).sum())
    pct = round((total - missing) / total * 100, 2)

    logger.info(
        "%s: %.1f%% (total=%d, missing=%d)",
        f"{table}.{field}",
        pct,
        total,
        missing,
    )
    return CompletenessResult(table, field, total, missing, pct)


def run_completeness_checks(data: Dict[str, pd.DataFrame]) -> List[CompletenessResult]:
    """
    执行全部完整性检查。

    Returns:
        各字段完整性结果列表
    """
    logger.info("========== Completeness 检查开始 ==========")
    results: List[CompletenessResult] = []

    for table, fields in COMPLETENESS_RULES.items():
        df = data.get(table, pd.DataFrame())
        for field in fields:
            if field not in df.columns:
                logger.warning("字段不存在 | %s.%s", table, field)
                continue
            result = check_field_completeness(df, table, field)
            results.append(result)
            print(f"{result.label}: {result.completeness_pct}%")

    if results:
        avg = round(sum(r.completeness_pct for r in results) / len(results), 2)
        logger.info("Completeness 平均分: %.2f%%", avg)
    logger.info("Completeness 检查完成")
    return results


def overall_completeness_score(results: List[CompletenessResult]) -> float:
    """计算完整性总体得分（各字段完整率的算术平均）。"""
    if not results:
        return 100.0
    return round(sum(r.completeness_pct for r in results) / len(results), 2)
