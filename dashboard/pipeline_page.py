# -*- coding: utf-8 -*-
"""Streamlit 数据流水线交互页面。"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analytics.warehouse_loader import REPORTS_DIR
from dashboard.pipeline_runner import (
    ANALYTICS_REPORT,
    FAISS_INDEX,
    QUALITY_REPORT,
    get_oltp_counts,
    get_pipeline_status,
    get_warehouse_counts,
    run_analytics_report,
    run_build_warehouse,
    run_etl_pipeline,
    run_full_pipeline,
    run_init_database,
    run_knowledge_base,
    run_quality_report,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _status_badge(ready: bool) -> str:
    return "✅ 已就绪" if ready else "⏳ 未运行"


def _run_step(label: str, runner, success_msg: str) -> None:
    """通用步骤运行按钮与结果展示。"""
    if st.button(f"运行 · {label}", type="primary", key=f"run_{label}"):
        with st.spinner(f"正在执行 {label}..."):
            ok, output = runner()
        if ok:
            st.success(success_msg)
        else:
            st.error(f"{label} 失败")
        if output:
            st.code(output, language="text")
        if ok:
            st.rerun()


def _show_html_report(path: Path, height: int = 720) -> None:
    if path.exists():
        html = path.read_text(encoding="utf-8")
        components.html(html, height=height, scrolling=True)
    else:
        st.info("报告尚未生成，请先运行对应步骤。")


def _read_report_csv_sections(csv_path: Path) -> dict[str, pd.DataFrame]:
    """解析 analytics 模块生成的多段 CSV（以 # 标题分段）。"""
    text = csv_path.read_text(encoding="utf-8-sig")
    if not any(line.startswith("#") for line in text.splitlines()):
        return {"": pd.read_csv(StringIO(text))}

    sections: dict[str, pd.DataFrame] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_name, current_lines
        if current_name is not None and current_lines:
            sections[current_name] = pd.read_csv(StringIO("\n".join(current_lines)))
        current_name = None
        current_lines = []

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_name = line.lstrip("# ").strip()
        elif line.strip():
            current_lines.append(line)
        else:
            flush()

    flush()
    return sections


def _show_csv_preview(filename: str, title: str) -> None:
    csv_path = REPORTS_DIR / filename
    if not csv_path.exists():
        st.caption(f"{title}：暂无数据")
        return

    st.markdown(f"**{title}**")
    try:
        sections = _read_report_csv_sections(csv_path)
        for section_name, df in sections.items():
            if section_name:
                st.caption(section_name)
            st.dataframe(df, use_container_width=True)
    except Exception as exc:
        st.warning(f"{title} 预览失败: {exc}")


def render_pipeline_page() -> None:
    """渲染数据流水线页面。"""
    st.subheader("数据流水线")
    st.caption("在界面中逐步运行各模块，无需切换终端。")

    statuses = get_pipeline_status()
    cols = st.columns(len(statuses))
    for col, status in zip(cols, statuses):
        col.metric(status.title.replace("1. ", "").replace("2. ", "").replace("3. ", "").replace("4. ", "").replace("5. ", ""), _status_badge(status.ready))
        col.caption(status.detail)

    st.markdown("---")

    # 一键全流程
    with st.expander("一键运行全流程", expanded=False):
        st.warning("将 **重新初始化数据库** 并依次执行质量 → 数仓 → 分析 → 知识库。知识库构建可能需要数分钟。")
        include_etl = st.checkbox("同时运行 ETL（从 CSV 增量入库，可选）", value=False)
        if st.button("开始全流程", type="primary", key="run_full"):
            progress = st.progress(0, text="准备中...")
            log_box = st.empty()
            lines: list[str] = []

            step_runners = [
                ("初始化数据库", run_init_database),
            ]
            if include_etl:
                step_runners.append(("ETL 流水线", run_etl_pipeline))
            step_runners.extend(
                [
                    ("数据质量评估", run_quality_report),
                    ("构建数据仓库", run_build_warehouse),
                    ("临床统计分析", run_analytics_report),
                    ("构建知识库", run_knowledge_base),
                ]
            )

            total = len(step_runners)
            for i, (name, runner) in enumerate(step_runners):
                progress.progress(i / total, text=f"正在执行: {name}...")
                ok, output = runner()
                lines.append(f"=== {name} ===\n{'成功' if ok else '失败'}\n{output}")
                log_box.code("\n\n".join(lines), language="text")
                if not ok:
                    st.error(f"全流程在「{name}」步骤失败，已停止。")
                    return
            progress.progress(1.0, text="完成")
            st.success("全流程执行完成！")
            st.rerun()

    tabs = st.tabs([s.title for s in statuses] + ["6. Clinical RAG"])

    # Tab 1: 数据库
    with tabs[0]:
        st.markdown("生成 Synthetic EHR 测试数据，写入 `database/hospital.db`。")
        counts = get_oltp_counts()
        if counts:
            st.dataframe(
                pd.DataFrame([{"表名": k, "记录数": v} for k, v in counts.items()]),
                use_container_width=True,
                hide_index=True,
            )
        st.warning("重新运行将 **清空并重建** 现有数据库。")
        _run_step("初始化数据库", run_init_database, "数据库初始化完成。")

        st.markdown("---")
        st.markdown("##### 可选：ETL 流水线")
        st.caption("从 `data/raw/` 读取 CSV → 清洗 → 写入数据库（小样本演示）。")
        _run_step("ETL 流水线", run_etl_pipeline, "ETL 流水线完成。")

    # Tab 2: 质量
    with tabs[1]:
        st.markdown("对 `hospital.db` 执行 Completeness / Accuracy / Consistency / Uniqueness 检查。")
        _run_step("数据质量评估", run_quality_report, "数据质量报告已生成。")
        st.markdown("##### 报告预览")
        _show_html_report(QUALITY_REPORT)

    # Tab 3: 数仓
    with tabs[2]:
        st.markdown("从 OLTP 构建星型模型至 `warehouse/warehouse.db`。")
        wh_counts = get_warehouse_counts()
        if wh_counts:
            st.dataframe(
                pd.DataFrame([{"表名": k, "记录数": v} for k, v in wh_counts.items()]),
                use_container_width=True,
                hide_index=True,
            )
        st.warning("重新运行将 **清空并重建** 数据仓库。")
        _run_step("构建数据仓库", run_build_warehouse, "数据仓库构建完成。")

    # Tab 4: 分析
    with tabs[3]:
        st.markdown("基于数仓生成 CSV 统计与 HTML 综合分析报告。")
        _run_step("临床统计分析", run_analytics_report, "临床分析报告已生成。")

        col1, col2 = st.columns(2)
        with col1:
            _show_csv_preview("hospital_kpi.csv", "医院 KPI")
            _show_csv_preview("disease_statistics.csv", "疾病统计 Top10")
        with col2:
            _show_csv_preview("patient_statistics.csv", "患者统计")
            _show_csv_preview("medication_statistics.csv", "用药统计")

        st.markdown("##### HTML 报告预览")
        _show_html_report(ANALYTICS_REPORT)

    # Tab 5: 知识库
    with tabs[4]:
        st.markdown("采集临床文档 → 切分 → 向量化 → 建立 FAISS 索引。")
        if FAISS_INDEX.exists():
            st.success(f"FAISS 索引已存在: `{FAISS_INDEX.relative_to(PROJECT_ROOT)}`")
        st.info("首次运行需下载 embedding 模型，可能需要 3–10 分钟，请耐心等待。")
        _run_step("构建知识库", run_knowledge_base, "临床知识库构建完成。")

    # Tab 6: RAG 引导
    with tabs[5]:
        st.markdown("知识库与数仓就绪后，请前往侧边栏 **「Clinical RAG 问答」** 页面进行智能问答。")
        rag_ready = FAISS_INDEX.exists() and get_warehouse_counts()
        if rag_ready:
            st.success("RAG 依赖已就绪，可以直接提问。")
        else:
            st.warning("请先完成步骤 3（数仓）和步骤 5（知识库）。")
        st.markdown(
            """
            **示例问题：**
            - 糖尿病患者 HbA1c 多少需要关注？
            - 医院有多少患者？
            - 最常见的疾病是什么？
            """
        )
