# -*- coding: utf-8 -*-
"""平台概览页 — KPI、流水线状态、架构与快捷入口。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from analytics.warehouse_loader import REPORTS_DIR
from dashboard.pipeline_page import _read_report_csv_sections
from dashboard.pipeline_runner import (
    ANALYTICS_REPORT,
    FAISS_INDEX,
    QUALITY_REPORT,
    get_oltp_counts,
    get_pipeline_status,
    get_warehouse_counts,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PIPELINE_STEPS = [
    ("init_db", "初始化数据库", "Synthetic EHR · hospital.db"),
    ("quality", "数据质量评估", "Completeness / Accuracy / Consistency"),
    ("warehouse", "构建数据仓库", "Star Schema · warehouse.db"),
    ("analytics", "临床统计分析", "KPI · CSV · HTML 报告"),
    ("knowledge", "构建知识库", "FAISS 临床指南向量检索"),
    ("rag", "Clinical RAG", "双路检索 + 智能问答"),
]


def _navigate_to(page: str) -> None:
    st.session_state.nav_page = page
    st.rerun()


def render_overview_page(kpi_df: pd.DataFrame) -> None:
    """渲染平台概览。"""
    st.subheader("平台概览")
    st.markdown(
        "医院信息中心 **医疗数据智能分析平台** — 覆盖数据采集、质量治理、数仓建模、"
        "临床统计、知识库与 RAG 问答的完整演示链路。"
    )

    # ---- KPI ----
    st.markdown("#### 运营指标")
    if not kpi_df.empty:
        cols = st.columns(len(kpi_df))
        for col, (_, row) in zip(cols, kpi_df.iterrows()):
            col.metric(label=row["KPI"], value=f"{row['Value']:,}")
    else:
        st.warning("暂无 KPI 数据。请先在「数据流水线」中完成 **初始化数据库 → 构建数据仓库 → 临床统计分析**。")

    st.markdown("---")

    # ---- 流水线状态 ----
    statuses = {s.key: s for s in get_pipeline_status()}
    ready_count = sum(1 for s in statuses.values() if s.ready)
    rag_ready = FAISS_INDEX.exists() and bool(get_warehouse_counts())
    total_steps = len(PIPELINE_STEPS)
    done_count = ready_count + (1 if rag_ready else 0)

    st.markdown("#### 流水线状态")
    prog_col, action_col = st.columns([3, 1])
    with prog_col:
        st.progress(done_count / total_steps, text=f"已完成 {done_count} / {total_steps} 步")
    with action_col:
        if st.button("打开数据流水线", type="primary", use_container_width=True):
            _navigate_to("数据流水线")

    step_cols = st.columns(3)
    for i, (key, title, desc) in enumerate(PIPELINE_STEPS):
        if key == "rag":
            ready = rag_ready
            detail = "可提问" if ready else "需先完成数仓与知识库"
        else:
            status = statuses.get(key)
            ready = status.ready if status else False
            detail = status.detail if status else "未运行"

        with step_cols[i % 3]:
            badge = "✅" if ready else "⏳"
            st.markdown(f"**{badge} {title}**")
            st.caption(desc)
            st.caption(detail)

    st.markdown("---")

    # ---- 架构 + 数据量 ----
    arch_col, data_col = st.columns([1.2, 1])

    with arch_col:
        st.markdown("#### 系统架构")
        st.markdown(
            """
```mermaid
flowchart LR
    A[OLTP 数据库] --> B[数据质量]
    A --> C[数据仓库]
    C --> D[临床分析]
    E[临床文档] --> F[知识库 FAISS]
    C --> G[Clinical RAG]
    F --> G
```
            """
        )
        st.caption("数据流：结构化 EHR → 质控 → 星型数仓 → 统计报表；非结构化指南 → 向量检索 → RAG 融合回答。")

    with data_col:
        st.markdown("#### 数据资产")
        oltp = get_oltp_counts()
        wh = get_warehouse_counts()

        if oltp:
            st.markdown("**OLTP** (`hospital.db`)")
            st.dataframe(
                pd.DataFrame([{"表": k, "记录": f"{v:,}"} for k, v in oltp.items()]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("OLTP 数据库尚未初始化")

        if wh:
            st.markdown("**数仓** (`warehouse.db`)")
            st.dataframe(
                pd.DataFrame([{"表": k, "记录": f"{v:,}"} for k, v in wh.items()]),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("---")

    # ---- 报告与洞察 ----
    insight_col, report_col = st.columns(2)

    with insight_col:
        st.markdown("#### 临床洞察")
        disease_csv = REPORTS_DIR / "disease_statistics.csv"
        if disease_csv.exists():
            sections = _read_report_csv_sections(disease_csv)
            top10 = sections.get("Top 10 Diseases")
            if top10 is not None and not top10.empty:
                st.dataframe(top10.head(5), use_container_width=True, hide_index=True)
            else:
                st.caption("暂无疾病统计数据")
        else:
            st.caption("运行「临床统计分析」后可在此查看 Top 5 疾病")

    with report_col:
        st.markdown("#### 报告与产物")
        artifacts = [
            ("数据质量报告", QUALITY_REPORT, "数据流水线 · 步骤 2"),
            ("临床分析报告", ANALYTICS_REPORT, "数据流水线 · 步骤 4"),
            ("FAISS 向量索引", FAISS_INDEX, "数据流水线 · 步骤 5"),
        ]
        for name, path, hint in artifacts:
            if path.exists():
                st.markdown(f"✅ **{name}** — `{path.relative_to(PROJECT_ROOT)}`")
            else:
                st.markdown(f"⏳ **{name}** — {hint}")

        if rag_ready:
            if st.button("前往 RAG 问答", use_container_width=True):
                _navigate_to("Clinical RAG 问答")
        elif ready_count >= 3:
            st.caption("完成知识库构建后即可使用 RAG 问答")

    st.markdown("---")

    # ---- 模块一览 ----
    st.markdown("#### 功能模块")
    st.markdown(
        """
| 模块 | 路径 | 能力 |
|------|------|------|
| Database | `database/` | SQLite 模拟 EHR，Synthetic 数据生成 |
| ETL | `etl/` | 原始 CSV 采集、清洗、入库 |
| Quality | `quality/` | 完整性 / 准确性 / 一致性 / 唯一性 |
| Warehouse | `warehouse/` | 星型模型维度表与事实表 |
| Analytics | `analytics/` | 患者、疾病、用药、检验、KPI |
| Knowledge Base | `knowledge_base/` | 文档切分、Embedding、FAISS |
| RAG | `rag/` | 患者数据 + 指南知识双路检索 |
| Dashboard | `dashboard/` | 本演示界面 |
        """
    )
