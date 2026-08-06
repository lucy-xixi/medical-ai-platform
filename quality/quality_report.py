#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗数据质量报告生成器

运行:
    python quality/quality_report.py

输出:
    reports/data_quality_report.html
    logs/data_quality.log
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from quality.accuracy import AccuracyReport, run_accuracy_checks
from quality.completeness import CompletenessResult, overall_completeness_score, run_completeness_checks
from quality.consistency import ConsistencyReport, run_consistency_checks
from quality.data_loader import load_all_tables
from quality.logger import LOG_FILE, setup_logger
from quality.uniqueness import UniquenessReport, run_uniqueness_checks

logger = setup_logger("quality.report")

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_FILE = REPORT_DIR / "data_quality_report.html"


@dataclass
class QualityIssue:
    """质量问题条目，用于报告表格。"""

    table: str
    rule: str
    issue_count: int
    severity: str


@dataclass
class QualityReportData:
    """汇总全部质量检查结果。"""

    generated_at: str
    patient_count: int
    condition_count: int
    medication_count: int
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    uniqueness_score: float
    overall_score: float
    issues: List[QualityIssue] = field(default_factory=list)


def _collect_issues(
    completeness: List[CompletenessResult],
    accuracy: AccuracyReport,
    consistency: ConsistencyReport,
    uniqueness: UniquenessReport,
) -> List[QualityIssue]:
    """汇总各维度发现的质量问题。"""
    issues: List[QualityIssue] = []

    for r in completeness:
        if r.missing_records > 0:
            issues.append(
                QualityIssue(
                    r.table,
                    f"missing {r.field}",
                    r.missing_records,
                    "Medium",
                )
            )

    for r in accuracy.results:
        if r.error_count > 0:
            issues.append(
                QualityIssue(r.table, r.rule, r.error_count, r.severity)
            )

    for r in consistency.results:
        if r.violation_count > 0:
            issues.append(
                QualityIssue(r.table, r.rule, r.violation_count, r.severity)
            )

    for r in uniqueness.results:
        if r.duplicate_count > 0:
            issues.append(
                QualityIssue(
                    r.table,
                    f"duplicate {r.id_field}",
                    r.duplicate_count,
                    "Critical",
                )
            )

    return issues


def _calc_consistency_score(consistency: ConsistencyReport, total_records: int) -> float:
    """基于违规数与总记录数计算一致性得分。"""
    if total_records == 0:
        return 100.0
    return round(max(0.0, (1 - consistency.total_violations / total_records) * 100), 2)


def build_report_data(data: dict) -> QualityReportData:
    """执行全部质量检查并构建报告数据。"""
    logger.info("========== 数据质量评估开始 ==========")

    completeness_results = run_completeness_checks(data)
    accuracy_report = run_accuracy_checks(data)
    consistency_report = run_consistency_checks(data)
    uniqueness_report = run_uniqueness_checks(data)

    patient_count = len(data.get("patients", []))
    condition_count = len(data.get("conditions", []))
    medication_count = len(data.get("medications", []))
    total_records = patient_count + condition_count + medication_count

    completeness_score = overall_completeness_score(completeness_results)
    accuracy_score = accuracy_report.overall_accuracy_pct
    consistency_score = _calc_consistency_score(consistency_report, total_records)
    uniqueness_score = uniqueness_report.overall_uniqueness_pct

    overall_score = round(
        (completeness_score + accuracy_score + consistency_score + uniqueness_score) / 4,
        2,
    )

    issues = _collect_issues(
        completeness_results,
        accuracy_report,
        consistency_report,
        uniqueness_report,
    )

    logger.info(
        "质量评分 | Completeness=%.1f%% Accuracy=%.1f%% Consistency=%.1f%% Uniqueness=%.1f%% Overall=%.1f%%",
        completeness_score,
        accuracy_score,
        consistency_score,
        uniqueness_score,
        overall_score,
    )

    return QualityReportData(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        patient_count=patient_count,
        condition_count=condition_count,
        medication_count=medication_count,
        completeness_score=completeness_score,
        accuracy_score=accuracy_score,
        consistency_score=consistency_score,
        uniqueness_score=uniqueness_score,
        overall_score=overall_score,
        issues=issues,
    )


def _score_color(score: float) -> str:
    """根据得分返回 CSS 颜色。"""
    if score >= 95:
        return "#27ae60"
    if score >= 85:
        return "#f39c12"
    return "#e74c3c"


def render_html(report: QualityReportData) -> str:
    """使用 HTML 模板渲染数据质量报告。"""
    issues_rows = ""
    if report.issues:
        for issue in report.issues:
            sev_color = {"Critical": "#e74c3c", "High": "#e67e22", "Medium": "#f39c12"}.get(
                issue.severity, "#7f8c8d"
            )
            issues_rows += f"""
            <tr>
                <td>{issue.table}</td>
                <td>{issue.rule}</td>
                <td>{issue.issue_count}</td>
                <td><span class="badge" style="background:{sev_color}">{issue.severity}</span></td>
            </tr>"""
    else:
        issues_rows = """
            <tr><td colspan="4" style="text-align:center;color:#27ae60;">
                No quality issues detected. All checks passed.
            </td></tr>"""

    overall_color = _score_color(report.overall_score)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Healthcare Data Quality Assessment Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
            background: #f0f2f5;
            color: #2c3e50;
            line-height: 1.6;
        }}
        .container {{
            max-width: 960px;
            margin: 30px auto;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1a5276, #2980b9);
            color: #fff;
            padding: 32px 40px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header p {{ opacity: 0.85; font-size: 14px; }}
        .section {{ padding: 28px 40px; border-bottom: 1px solid #ecf0f1; }}
        .section h2 {{
            font-size: 18px;
            color: #1a5276;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #2980b9;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }}
        .summary-card {{
            background: #f8f9fa;
            border-radius: 6px;
            padding: 20px;
            text-align: center;
        }}
        .summary-card .number {{
            font-size: 32px;
            font-weight: bold;
            color: #2980b9;
        }}
        .summary-card .label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 4px;
        }}
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}
        .score-card {{
            text-align: center;
            padding: 16px;
            border-radius: 6px;
            background: #f8f9fa;
        }}
        .score-card .score {{
            font-size: 28px;
            font-weight: bold;
        }}
        .score-card .dim {{
            font-size: 13px;
            color: #7f8c8d;
            margin-top: 4px;
        }}
        .overall-score {{
            text-align: center;
            padding: 24px;
            margin-top: 16px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .overall-score .value {{
            font-size: 48px;
            font-weight: bold;
            color: {overall_color};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            background: #1a5276;
            color: #fff;
            padding: 10px 14px;
            text-align: left;
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover td {{ background: #f8f9fa; }}
        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            color: #fff;
            font-size: 12px;
        }}
        .footer {{
            padding: 20px 40px;
            text-align: center;
            font-size: 12px;
            color: #95a5a6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Healthcare Data Quality Assessment Report</h1>
            <p>医疗数据质量评估报告 | Medical Data Intelligence Platform</p>
            <p>Generated: {report.generated_at}</p>
        </div>

        <div class="section">
            <h2>1. Dataset Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="number">{report.patient_count:,}</div>
                    <div class="label">Patients</div>
                </div>
                <div class="summary-card">
                    <div class="number">{report.condition_count:,}</div>
                    <div class="label">Conditions</div>
                </div>
                <div class="summary-card">
                    <div class="number">{report.medication_count:,}</div>
                    <div class="label">Medications</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>2. Data Quality Score</h2>
            <div class="score-grid">
                <div class="score-card">
                    <div class="score" style="color:{_score_color(report.completeness_score)}">{report.completeness_score}%</div>
                    <div class="dim">Completeness</div>
                </div>
                <div class="score-card">
                    <div class="score" style="color:{_score_color(report.accuracy_score)}">{report.accuracy_score}%</div>
                    <div class="dim">Accuracy</div>
                </div>
                <div class="score-card">
                    <div class="score" style="color:{_score_color(report.consistency_score)}">{report.consistency_score}%</div>
                    <div class="dim">Consistency</div>
                </div>
                <div class="score-card">
                    <div class="score" style="color:{_score_color(report.uniqueness_score)}">{report.uniqueness_score}%</div>
                    <div class="dim">Uniqueness</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>3. Quality Issues</h2>
            <table>
                <thead>
                    <tr>
                        <th>Table</th>
                        <th>Rule</th>
                        <th>Issue Count</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    {issues_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>4. Overall Score</h2>
            <div class="overall-score">
                <div class="value">{report.overall_score}%</div>
                <div style="color:#7f8c8d;margin-top:8px;">
                    综合数据质量评分（Completeness + Accuracy + Consistency + Uniqueness 均值）
                </div>
            </div>
        </div>

        <div class="footer">
            Medical Data Intelligence Platform &mdash; Data Governance &amp; Quality Module
        </div>
    </div>
</body>
</html>"""


def generate_report() -> Path:
    """执行质量检查并生成 HTML 报告。"""
    data = load_all_tables()
    report_data = build_report_data(data)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    html = render_html(report_data)
    REPORT_FILE.write_text(html, encoding="utf-8")

    logger.info("报告已生成: %s", REPORT_FILE)
    return REPORT_FILE


def main() -> int:
    """命令行入口。"""
    try:
        logger.info("数据质量报告生成启动 | 日志: %s", LOG_FILE)
        output = generate_report()
        print(f"Data quality report generated:\n{output}")
        return 0
    except Exception as exc:
        logger.exception("报告生成失败: %s", exc)
        print(f"Report generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
