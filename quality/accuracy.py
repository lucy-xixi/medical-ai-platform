# -*- coding: utf-8 -*-
"""
数据准确性检查 (Accuracy)

验证字段值是否符合预定义的业务规则与格式标准。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from quality.logger import setup_logger

logger = setup_logger("quality.accuracy")

# 日期格式: YYYY-MM-DD
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ICD-10 编码格式: A00-Z99（字母 + 至少两位数字，可含小数点扩展）
ICD_PATTERN = re.compile(r"^[A-TV-Z]\d{2}(\.[0-9A-Z]{1,4})?$", re.IGNORECASE)

# 允许的 gender 值
VALID_GENDERS = {"Male", "Female"}


@dataclass
class AccuracyRuleResult:
    """单条准确性规则检查结果。"""

    table: str
    rule: str
    total_records: int
    error_count: int
    error_rate_pct: float
    severity: str = "High"


@dataclass
class AccuracyReport:
    """准确性检查汇总报告。"""

    results: List[AccuracyRuleResult] = field(default_factory=list)

    @property
    def total_checked(self) -> int:
        return sum(r.total_records for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(r.error_count for r in self.results)

    @property
    def overall_accuracy_pct(self) -> float:
        if self.total_checked == 0:
            return 100.0
        return round((1 - self.total_errors / self.total_checked) * 100, 2)


def _to_date_string(value) -> str:
    """将日期/时间值转为 YYYY-MM-DD 字符串。"""
    if pd.isna(value):
        return ""
    text = str(value)
    return text[:10] if len(text) >= 10 else text


def _check_date_format(series: pd.Series) -> pd.Series:
    """检查日期是否符合 YYYY-MM-DD 格式（非空值）。"""
    def valid(val) -> bool:
        s = _to_date_string(val)
        if not s:
            return True  # 空值由 completeness 检查
        return bool(DATE_PATTERN.match(s))

    return ~series.apply(valid)


def _check_gender(series: pd.Series) -> pd.Series:
    """检查 gender 是否为 Male / Female。"""
    def valid(val) -> bool:
        if pd.isna(val) or str(val).strip() == "":
            return True
        return str(val).strip() in VALID_GENDERS

    return ~series.apply(valid)


def _check_icd(series: pd.Series) -> pd.Series:
    """检查 ICD 编码格式 A00-Z99。"""
    def valid(val) -> bool:
        if pd.isna(val) or str(val).strip() == "":
            return True
        return bool(ICD_PATTERN.match(str(val).strip().upper()))

    return ~series.apply(valid)


def _check_numeric(series: pd.Series) -> pd.Series:
    """检查数值字段是否为有效数字。"""
    numeric = pd.to_numeric(series, errors="coerce")
    return series.notna() & numeric.isna()


def _run_rule(
    df: pd.DataFrame,
    table: str,
    rule: str,
    invalid_mask: pd.Series,
    severity: str = "High",
) -> AccuracyRuleResult:
    """执行单条准确性规则并记录结果。"""
    total = len(df)
    errors = int(invalid_mask.sum())
    rate = round(errors / total * 100, 2) if total > 0 else 0.0

    logger.info(
        "Accuracy | %s | %s | errors=%d / %d (%.2f%%)",
        table,
        rule,
        errors,
        total,
        rate,
    )
    return AccuracyRuleResult(table, rule, total, errors, rate, severity)


def run_accuracy_checks(data: Dict[str, pd.DataFrame]) -> AccuracyReport:
    """
    执行全部准确性检查。

    检查项:
        - 日期字段 YYYY-MM-DD 格式
        - gender 允许 Male / Female
        - ICD 编码 A00-Z99 格式
        - observations.value 数值有效性
    """
    logger.info("========== Accuracy 检查开始 ==========")
    report = AccuracyReport()

    patients = data.get("patients", pd.DataFrame())
    if not patients.empty and "gender" in patients.columns:
        report.results.append(
            _run_rule(
                patients,
                "patients",
                "invalid gender (must be Male/Female)",
                _check_gender(patients["gender"]),
            )
        )
    if not patients.empty and "birth_date" in patients.columns:
        report.results.append(
            _run_rule(
                patients,
                "patients",
                "invalid birth_date format",
                _check_date_format(patients["birth_date"]),
            )
        )

    conditions = data.get("conditions", pd.DataFrame())
    if not conditions.empty and "icd_code" in conditions.columns:
        report.results.append(
            _run_rule(
                conditions,
                "conditions",
                "invalid ICD code format",
                _check_icd(conditions["icd_code"]),
            )
        )
    if not conditions.empty and "onset_date" in conditions.columns:
        report.results.append(
            _run_rule(
                conditions,
                "conditions",
                "invalid onset_date format",
                _check_date_format(conditions["onset_date"]),
            )
        )

    medications = data.get("medications", pd.DataFrame())
    if not medications.empty and "start_date" in medications.columns:
        report.results.append(
            _run_rule(
                medications,
                "medications",
                "invalid start_date format",
                _check_date_format(medications["start_date"]),
            )
        )
    if not medications.empty and "end_date" in medications.columns:
        # 仅检查非空的 end_date
        non_null = medications["end_date"].notna()
        end_dates = medications.loc[non_null, "end_date"]
        if len(end_dates) > 0:
            invalid = _check_date_format(end_dates)
            errors = int(invalid.sum())
            rate = round(errors / len(medications) * 100, 2)
            report.results.append(
                AccuracyRuleResult(
                    "medications",
                    "invalid end_date format",
                    len(medications),
                    errors,
                    rate,
                )
            )

    observations = data.get("observations", pd.DataFrame())
    if not observations.empty and "value" in observations.columns:
        report.results.append(
            _run_rule(
                observations,
                "observations",
                "non-numeric value",
                _check_numeric(observations["value"]),
            )
        )

    logger.info(
        "Accuracy 检查完成 | 总错误: %d | 准确率: %.2f%%",
        report.total_errors,
        report.overall_accuracy_pct,
    )
    return report
