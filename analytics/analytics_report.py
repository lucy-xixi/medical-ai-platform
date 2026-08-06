#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clinical Analytics 综合报告生成器

从 warehouse/warehouse.db 读取数据，执行临床统计与运营分析，
输出 CSV 报告、图表及 HTML 综合分析报告。

运行:
    python analytics/analytics_report.py
"""

from __future__ import annotations

import base64
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.disease_analysis import analyze_diseases, save_disease_statistics
from analytics.hospital_kpi import analyze_hospital_kpi, save_hospital_kpi
from analytics.laboratory_analysis import analyze_laboratory, save_laboratory_statistics
from analytics.logger import LOG_FILE, setup_logger
from analytics.medication_analysis import analyze_medications, save_medication_statistics
from analytics.patient_analysis import analyze_patients, save_patient_statistics
from analytics.warehouse_loader import CHARTS_DIR, REPORTS_DIR, ensure_report_dirs, load_warehouse_tables

logger = setup_logger("analytics.report")

REPORT_HTML = REPORTS_DIR / "clinical_analytics_report.html"

# 中文字体回退
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _save_chart(fig, filename: str) -> str:
    """保存 matplotlib 图表并返回相对路径。"""
    ensure_report_dirs()
    path = CHARTS_DIR / filename
    fig.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return f"charts/{filename}"


def _chart_to_base64(fig) -> str:
    """将图表转为 base64 嵌入 HTML。"""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def plot_age_distribution(age_group_stats: pd.DataFrame) -> str:
    """患者年龄分组分布图。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(age_group_stats["age_group"], age_group_stats["Patient Count"], color="#2980b9")
    ax.set_title("Patient Age Distribution")
    ax.set_xlabel("Age Group")
    ax.set_ylabel("Patient Count")
    ax.grid(axis="y", alpha=0.3)
    return _chart_to_base64(fig)


def plot_disease_top10(top10: pd.DataFrame) -> str:
    """Top 10 疾病柱状图。"""
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = top10["condition_name"].str[:20]
    ax.barh(labels[::-1], top10["Patient Count"][::-1], color="#e74c3c")
    ax.set_title("Top 10 Diseases by Patient Count")
    ax.set_xlabel("Patient Count")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return _chart_to_base64(fig)


def plot_medication_usage(usage_rank: pd.DataFrame) -> str:
    """Top 10 药物使用量图。"""
    top = usage_rank.head(10)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["drug_name"][::-1], top["Usage_Count"][::-1], color="#27ae60")
    ax.set_title("Top 10 Medication Usage")
    ax.set_xlabel("Usage Count")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    return _chart_to_base64(fig)


def plot_laboratory_distribution(fact_observation: pd.DataFrame) -> str:
    """实验室指标分布图（HbA1c + Creatinine）。"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, mtype, title in [
        (axes[0], "hba1c", "HbA1c Distribution"),
        (axes[1], "creatinine", "Creatinine Distribution"),
    ]:
        subset = fact_observation[fact_observation["measurement_type"] == mtype]
        values = pd.to_numeric(subset["value"], errors="coerce").dropna()
        if not values.empty:
            ax.hist(values, bins=30, color="#8e44ad", edgecolor="white", alpha=0.85)
        ax.set_title(title)
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        ax.grid(alpha=0.3)

    fig.tight_layout()
    return _chart_to_base64(fig)


def _df_to_html_table(df: pd.DataFrame, max_rows: int = 15) -> str:
    """DataFrame 转 HTML 表格。"""
    display = df.head(max_rows)
    return display.to_html(index=False, classes="data-table", border=0)


def render_html_report(
    patient_summary: pd.DataFrame,
    age_group_stats: pd.DataFrame,
    disease_top10: pd.DataFrame,
    usage_rank: pd.DataFrame,
    lab_stats: pd.DataFrame,
    kpi_df: pd.DataFrame,
    charts: dict,
) -> str:
    """渲染 HTML 综合分析报告。"""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Healthcare Clinical Analytics Report</title>
    <style>
        body {{ font-family: "Segoe UI","Microsoft YaHei",Arial,sans-serif; background:#f0f2f5; color:#2c3e50; margin:0; }}
        .container {{ max-width:1100px; margin:30px auto; background:#fff; border-radius:8px; box-shadow:0 2px 12px rgba(0,0,0,.08); }}
        .header {{ background:linear-gradient(135deg,#1a5276,#16a085); color:#fff; padding:32px 40px; }}
        .header h1 {{ margin:0 0 8px; font-size:26px; }}
        .section {{ padding:28px 40px; border-bottom:1px solid #ecf0f1; }}
        .section h2 {{ color:#1a5276; font-size:18px; border-bottom:2px solid #16a085; padding-bottom:8px; }}
        .chart {{ text-align:center; margin:20px 0; }}
        .chart img {{ max-width:100%; border-radius:6px; box-shadow:0 1px 6px rgba(0,0,0,.1); }}
        table.data-table {{ width:100%; border-collapse:collapse; font-size:14px; margin-top:12px; }}
        table.data-table th {{ background:#1a5276; color:#fff; padding:10px; text-align:left; }}
        table.data-table td {{ padding:9px 10px; border-bottom:1px solid #ecf0f1; }}
        table.data-table tr:hover td {{ background:#f8f9fa; }}
        .kpi-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }}
        .kpi-card {{ background:#f8f9fa; border-radius:6px; padding:16px; text-align:center; }}
        .kpi-card .val {{ font-size:24px; font-weight:bold; color:#16a085; }}
        .kpi-card .lbl {{ font-size:12px; color:#7f8c8d; margin-top:4px; }}
        .footer {{ padding:20px; text-align:center; font-size:12px; color:#95a5a6; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>Healthcare Clinical Analytics Report</h1>
        <p>医疗临床统计分析报告 | Medical Data Intelligence Platform</p>
        <p>Generated: {generated}</p>
    </div>

    <div class="section">
        <h2>1. Patient Overview</h2>
        {_df_to_html_table(patient_summary)}
        <div class="chart"><img src="data:image/png;base64,{charts['age']}" alt="Age Distribution"></div>
    </div>

    <div class="section">
        <h2>2. Disease Distribution</h2>
        {_df_to_html_table(disease_top10)}
        <div class="chart"><img src="data:image/png;base64,{charts['disease']}" alt="Disease Top10"></div>
    </div>

    <div class="section">
        <h2>3. Medication Utilization</h2>
        {_df_to_html_table(usage_rank.head(10))}
        <div class="chart"><img src="data:image/png;base64,{charts['medication']}" alt="Medication Usage"></div>
    </div>

    <div class="section">
        <h2>4. Laboratory Statistics</h2>
        {_df_to_html_table(lab_stats)}
        <div class="chart"><img src="data:image/png;base64,{charts['laboratory']}" alt="Laboratory Distribution"></div>
    </div>

    <div class="section">
        <h2>5. Hospital KPI</h2>
        <div class="kpi-grid">
            {"".join(f'<div class="kpi-card"><div class="val">{row["Value"]:,}</div><div class="lbl">{row["KPI"]}</div></div>' for _, row in kpi_df.iterrows())}
        </div>
    </div>

    <div class="footer">Clinical Analytics Module &mdash; Data Source: warehouse/warehouse.db (Read-Only)</div>
</div>
</body>
</html>"""


def run_analytics() -> Path:
    """执行全部分析并生成报告。"""
    logger.info("========== Clinical Analytics 开始 ==========")
    logger.info("日志: %s", LOG_FILE)

    data = load_warehouse_tables()

    # 1. 患者分析
    patient_summary, age_group_stats, gender_stats = analyze_patients(data["dim_patient"])
    save_patient_statistics(patient_summary, age_group_stats, gender_stats)

    # 2. 疾病分析
    disease_summary, disease_top10, chronic_stats = analyze_diseases(
        data["dim_condition"], data["fact_condition"]
    )
    save_disease_statistics(disease_summary, disease_top10, chronic_stats)

    # 3. 用药分析
    usage_rank, patient_dist = analyze_medications(
        data["dim_medication"], data["fact_medication"], data["dim_patient"]
    )
    save_medication_statistics(usage_rank, patient_dist)

    # 4. 实验室分析
    lab_stats = analyze_laboratory(data["fact_observation"])
    save_laboratory_statistics(lab_stats)

    # 5. KPI
    kpi_df = analyze_hospital_kpi(data)
    save_hospital_kpi(kpi_df)

    # 6. 图表
    charts = {
        "age": plot_age_distribution(age_group_stats),
        "disease": plot_disease_top10(disease_top10),
        "medication": plot_medication_usage(usage_rank),
        "laboratory": plot_laboratory_distribution(data["fact_observation"]),
    }

    # 7. HTML 报告
    html = render_html_report(
        patient_summary,
        age_group_stats,
        disease_top10,
        usage_rank,
        lab_stats,
        kpi_df,
        charts,
    )
    ensure_report_dirs()
    REPORT_HTML.write_text(html, encoding="utf-8")
    logger.info("HTML 报告: %s", REPORT_HTML)
    logger.info("========== Clinical Analytics 完成 ==========")
    return REPORT_HTML


def main() -> int:
    try:
        output = run_analytics()
        print("Clinical analytics report generated successfully.")
        print(output)
        return 0
    except Exception as exc:
        logger.exception("分析失败: %s", exc)
        print(f"Analytics failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
