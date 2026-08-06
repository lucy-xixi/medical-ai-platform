# -*- coding: utf-8 -*-
"""Streamlit 数据流水线交互页面（按步骤懒加载，避免卡顿）。"""

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
    run_init_database,
    run_knowledge_base,
    run_quality_report,
)
from dashboard.warehouse_view import render_star_schema_diagram, render_warehouse_data_browser

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STEP_OPTIONS = [
    "1. 初始化数据库",
    "2. 数据质量评估",
    "3. 构建数据仓库",
    "4. 临床统计分析",
    "5. 构建知识库",
    "6. Clinical RAG",
]


def _status_badge(ready: bool) -> str:
    return "已就绪" if ready else "未运行"


def _run_step(label: str, runner, success_msg: str, *, key: str) -> None:
    """通用步骤运行按钮与结果展示。"""
    if st.button(f"运行 · {label}", type="primary", key=key):
        with st.spinner(f"正在执行 {label}，请稍候..."):
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
            st.dataframe(df, width="stretch")
    except Exception as exc:
        st.warning(f"{title} 预览失败: {exc}")


def _render_step_init_db() -> None:
    st.markdown("生成 Synthetic EHR 测试数据，写入 `database/hospital.db`。")
    counts = get_oltp_counts()
    if counts:
        st.dataframe(
            pd.DataFrame([{"表名": k, "记录数": v} for k, v in counts.items()]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("数据库尚未初始化，请点击下方按钮开始。")
    st.warning("重新运行将 **清空并重建** 现有数据库。")
    _run_step("初始化数据库", run_init_database, "数据库初始化完成。", key="run_init_db")

    st.markdown("---")
    st.markdown("##### 可选：ETL 流水线")
    st.caption("从 `data/raw/` 读取 CSV → 清洗 → 写入数据库（小样本演示）。")
    _run_step("ETL 流水线", run_etl_pipeline, "ETL 流水线完成。", key="run_etl")


def _render_step_quality() -> None:
    st.markdown("对 `hospital.db` 执行 Completeness / Accuracy / Consistency / Uniqueness 检查。")
    _run_step("数据质量评估", run_quality_report, "数据质量报告已生成。", key="run_quality")
    with st.expander("报告预览", expanded=QUALITY_REPORT.exists()):
        _show_html_report(QUALITY_REPORT)


def _render_step_warehouse() -> None:
    st.markdown("从 OLTP 构建星型模型至 `warehouse/warehouse.db`。")
    render_star_schema_diagram(compact=True)

    wh_counts = get_warehouse_counts()
    if wh_counts:
        st.markdown("##### 当前表记录数")
        st.dataframe(
            pd.DataFrame([{"表名": k, "记录数": v} for k, v in wh_counts.items()]),
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("数仓尚未构建，请先运行下方按钮。")

    st.warning("重新运行将 **清空并重建** 数据仓库。")
    _run_step("构建数据仓库", run_build_warehouse, "数据仓库构建完成。", key="run_warehouse")

    st.markdown("---")
    render_warehouse_data_browser()


def _render_step_analytics() -> None:
    st.markdown("基于数仓生成 CSV 统计与 HTML 综合分析报告。")
    _run_step("临床统计分析", run_analytics_report, "临床分析报告已生成。", key="run_analytics")

    col1, col2 = st.columns(2)
    with col1:
        _show_csv_preview("hospital_kpi.csv", "医院 KPI")
        _show_csv_preview("disease_statistics.csv", "疾病统计 Top10")
    with col2:
        _show_csv_preview("patient_statistics.csv", "患者统计")
        _show_csv_preview("medication_statistics.csv", "用药统计")

    with st.expander("HTML 报告预览", expanded=ANALYTICS_REPORT.exists()):
        _show_html_report(ANALYTICS_REPORT)


def _render_step_knowledge() -> None:
    st.markdown("采集临床文档 → 切分 → 向量化 → 建立 FAISS 索引。")
    if FAISS_INDEX.exists():
        st.success(f"FAISS 索引已存在: `{FAISS_INDEX.relative_to(PROJECT_ROOT)}`")
    st.info("首次运行需下载 embedding 模型，可能需要 3–10 分钟，请耐心等待。")
    _run_step("构建知识库", run_knowledge_base, "临床知识库构建完成。", key="run_kb")


def _render_step_rag() -> None:
    st.markdown("知识库与数仓就绪后，请前往侧边栏 **「Clinical RAG 问答」** 页面进行智能问答。")
    rag_ready = FAISS_INDEX.exists() and bool(get_warehouse_counts())
    if rag_ready:
        st.success("RAG 依赖已就绪，可以直接提问。")
        if st.button("前往 RAG 问答", type="primary", key="goto_rag"):
            st.session_state.nav_page = "Clinical RAG 问答"
            st.rerun()
    else:
        st.warning("请先完成 **步骤 3（数仓）** 和 **步骤 5（知识库）**。")
    st.markdown(
        """
        **示例问题：**
        - 糖尿病患者 HbA1c 多少需要关注？
        - 医院有多少患者？
        - 最常见的疾病是什么？
        """
    )


STEP_RENDERERS = {
    "1. 初始化数据库": _render_step_init_db,
    "2. 数据质量评估": _render_step_quality,
    "3. 构建数据仓库": _render_step_warehouse,
    "4. 临床统计分析": _render_step_analytics,
    "5. 构建知识库": _render_step_knowledge,
    "6. Clinical RAG": _render_step_rag,
}


def render_pipeline_page() -> None:
    """渲染数据流水线页面（仅加载当前选中步骤）。"""
    st.subheader("数据流水线")
    st.caption("选择下方步骤，点击「运行」执行。数据保存在本地文件，刷新页面 **不会丢失**，但需重新登录。")

    statuses = get_pipeline_status()
    cols = st.columns(len(statuses))
    for col, status in zip(cols, statuses):
        short = status.title.split(". ", 1)[-1]
        col.metric(short, _status_badge(status.ready))
        col.caption(status.detail)

    st.markdown("---")

    with st.expander("一键运行全流程", expanded=False):
        st.warning("将 **重新初始化数据库** 并依次执行质量 → 数仓 → 分析 → 知识库。知识库构建可能需要数分钟。")
        include_etl = st.checkbox("同时运行 ETL（从 CSV 增量入库，可选）", value=False, key="full_etl")
        if st.button("开始全流程", type="primary", key="run_full"):
            from dashboard.pipeline_runner import (
                run_etl_pipeline as _etl,
                run_init_database as _init,
            )

            step_runners = [("初始化数据库", _init)]
            if include_etl:
                step_runners.append(("ETL 流水线", _etl))
            step_runners.extend(
                [
                    ("数据质量评估", run_quality_report),
                    ("构建数据仓库", run_build_warehouse),
                    ("临床统计分析", run_analytics_report),
                    ("构建知识库", run_knowledge_base),
                ]
            )

            progress = st.progress(0, text="准备中...")
            log_box = st.empty()
            lines: list[str] = []
            total = len(step_runners)

            for i, (name, runner) in enumerate(step_runners):
                progress.progress((i + 1) / total, text=f"正在执行: {name}...")
                ok, output = runner()
                lines.append(f"=== {name} ===\n{'成功' if ok else '失败'}\n{output}")
                log_box.code("\n\n".join(lines), language="text")
                if not ok:
                    st.error(f"全流程在「{name}」步骤失败，已停止。")
                    return

            st.success("全流程执行完成！")
            st.rerun()

    if "pipeline_step" not in st.session_state:
        st.session_state.pipeline_step = STEP_OPTIONS[0]
    current_step = st.session_state.pipeline_step
    if current_step not in STEP_OPTIONS:
        current_step = STEP_OPTIONS[0]
        st.session_state.pipeline_step = current_step

    selected = st.radio(
        "选择流水线步骤",
        STEP_OPTIONS,
        index=STEP_OPTIONS.index(current_step),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.pipeline_step = selected

    st.markdown(f"### {selected}")
    STEP_RENDERERS[selected]()
