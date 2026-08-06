# -*- coding: utf-8 -*-
"""
数据一致性检查 (Consistency)

验证跨表引用完整性与业务逻辑约束。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

import pandas as pd

from quality.logger import setup_logger

logger = setup_logger("quality.consistency")


@dataclass
class ConsistencyRuleResult:
    """单条一致性规则检查结果。"""

    table: str
    rule: str
    violation_count: int
    severity: str = "High"


@dataclass
class ConsistencyReport:
    """一致性检查汇总报告。"""

    results: List[ConsistencyRuleResult] = field(default_factory=list)

    @property
    def total_violations(self) -> int:
        return sum(r.violation_count for r in self.results)


def _orphan_count(child_ids: pd.Series, parent_ids: Set) -> int:
    """统计子表中不存在于父表的 patient_id 数量。"""
    if child_ids.empty:
        return 0
    return int((~child_ids.isin(parent_ids)).sum())


def run_consistency_checks(data: Dict[str, pd.DataFrame]) -> ConsistencyReport:
    """
    执行全部一致性检查。

    检查项:
        1. conditions.patient_id 必须存在于 patients
        2. medications.patient_id 必须存在于 patients
        3. medications.start_date <= end_date
    """
    logger.info("========== Consistency 检查开始 ==========")
    report = ConsistencyReport()

    patients = data.get("patients", pd.DataFrame())
    conditions = data.get("conditions", pd.DataFrame())
    medications = data.get("medications", pd.DataFrame())

    valid_patient_ids: Set = set(patients["patient_id"].tolist()) if not patients.empty else set()

    # 1. conditions 外键一致性
    if not conditions.empty and "patient_id" in conditions.columns:
        orphan = _orphan_count(conditions["patient_id"], valid_patient_ids)
        report.results.append(
            ConsistencyRuleResult(
                "conditions",
                "patient_id not in patients",
                orphan,
            )
        )
        logger.info("Consistency | conditions.patient_id 孤儿记录: %d", orphan)

    # 2. medications 外键一致性
    if not medications.empty and "patient_id" in medications.columns:
        orphan = _orphan_count(medications["patient_id"], valid_patient_ids)
        report.results.append(
            ConsistencyRuleResult(
                "medications",
                "patient_id not in patients",
                orphan,
            )
        )
        logger.info("Consistency | medications.patient_id 孤儿记录: %d", orphan)

    # 3. 用药日期逻辑: start_date <= end_date
    if not medications.empty and {"start_date", "end_date"}.issubset(medications.columns):
        meds = medications.copy()
        meds["start_date"] = pd.to_datetime(meds["start_date"], errors="coerce")
        meds["end_date"] = pd.to_datetime(meds["end_date"], errors="coerce")
        has_both = meds["start_date"].notna() & meds["end_date"].notna()
        invalid = has_both & (meds["start_date"] > meds["end_date"])
        violation = int(invalid.sum())
        report.results.append(
            ConsistencyRuleResult(
                "medications",
                "start_date > end_date",
                violation,
            )
        )
        logger.info("Consistency | 日期逻辑违规: %d", violation)

    logger.info("Consistency 检查完成 | 总违规: %d", report.total_violations)
    return report
