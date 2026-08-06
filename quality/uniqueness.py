# -*- coding: utf-8 -*-
"""
数据唯一性检查 (Uniqueness)

验证主键字段不存在重复值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from quality.logger import setup_logger

logger = setup_logger("quality.uniqueness")

# 需检查唯一性的主键字段
UNIQUENESS_RULES: Dict[str, str] = {
    "patients": "patient_id",
    "encounters": "encounter_id",
    "conditions": "condition_id",
    "medications": "medication_id",
}


@dataclass
class UniquenessResult:
    """单表唯一性检查结果。"""

    table: str
    id_field: str
    total_records: int
    duplicate_count: int

    @property
    def uniqueness_pct(self) -> float:
        if self.total_records == 0:
            return 100.0
        unique_violations = self.duplicate_count
        return round((1 - unique_violations / self.total_records) * 100, 2)


@dataclass
class UniquenessReport:
    """唯一性检查汇总报告。"""

    results: List[UniquenessResult] = field(default_factory=list)

    @property
    def total_duplicates(self) -> int:
        return sum(r.duplicate_count for r in self.results)

    @property
    def overall_uniqueness_pct(self) -> float:
        if not self.results:
            return 100.0
        return round(sum(r.uniqueness_pct for r in self.results) / len(self.results), 2)


def check_uniqueness(df: pd.DataFrame, table: str, id_field: str) -> UniquenessResult:
    """
    检查指定主键字段的唯一性。

    duplicate_count 为重复出现的多余记录数（非 distinct 重复组数）。
    """
    total = len(df)
    if total == 0 or id_field not in df.columns:
        return UniquenessResult(table, id_field, total, 0)

    duplicates = int(df[id_field].duplicated(keep=False).sum())
    # 多余记录数 = 重复记录总数 - 重复组数
    dup_groups = df[id_field].duplicated(keep="first").sum()
    extra = int(dup_groups)

    logger.info(
        "Uniqueness | %s.%s | total=%d, duplicates=%d",
        table,
        id_field,
        total,
        extra,
    )
    return UniquenessResult(table, id_field, total, extra)


def run_uniqueness_checks(data: Dict[str, pd.DataFrame]) -> UniquenessReport:
    """执行全部唯一性检查。"""
    logger.info("========== Uniqueness 检查开始 ==========")
    report = UniquenessReport()

    for table, id_field in UNIQUENESS_RULES.items():
        df = data.get(table, pd.DataFrame())
        result = check_uniqueness(df, table, id_field)
        report.results.append(result)

    logger.info(
        "Uniqueness 检查完成 | 总重复: %d | 唯一性得分: %.2f%%",
        report.total_duplicates,
        report.overall_uniqueness_pct,
    )
    return report
