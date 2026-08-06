#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Medical Data Intelligence Platform — 内部演示前端

Streamlit 看板，含简单登录、KPI 概览、Clinical RAG 问答。

运行:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analytics.hospital_kpi import analyze_hospital_kpi
from analytics.warehouse_loader import load_warehouse_tables
from dashboard.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME, get_demo_credentials, verify_login
from dashboard.overview_page import render_overview_page
from dashboard.pipeline_page import render_pipeline_page
from rag.clinical_rag import ask as rag_ask

# ---------------------------------------------------------------------------
# 页面配置
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Medical Data Intelligence Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 登录页
# ---------------------------------------------------------------------------


def login_page() -> None:
    """渲染登录界面。"""
    st.markdown("## Medical Data Intelligence Platform")
    st.markdown("#### 医院信息中心 · 医疗数据智能分析平台（内部演示）")

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        # 演示快速登录（内部演示用）
        if st.button("一键演示登录", type="primary", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.username = DEFAULT_USERNAME
            st.rerun()

        st.markdown("---")

        with st.form("login_form"):
            st.markdown("##### 账号登录")
            username = st.text_input("用户名", value=DEFAULT_USERNAME)
            password = st.text_input("密码", type="password", value=DEFAULT_PASSWORD)
            submitted = st.form_submit_button("登录", use_container_width=True)

            if submitted:
                if verify_login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username.strip()
                    st.rerun()
                else:
                    expected_user, _ = get_demo_credentials()
                    st.error(f"用户名或密码错误（演示账号: {expected_user} / {DEFAULT_PASSWORD}）")

        st.caption(
            f"演示账号：`{DEFAULT_USERNAME}` / `{DEFAULT_PASSWORD}` "
            f"（可在 .env 中设置 DEMO_USERNAME / DEMO_PASSWORD）"
        )
        st.caption("提示：浏览器 **刷新后会退出登录**，但本地数据库与报告文件不会丢失。")


# ---------------------------------------------------------------------------
# 主界面
# ---------------------------------------------------------------------------


def load_kpi_data() -> pd.DataFrame:
    """从数据仓库加载 KPI。"""
    try:
        data = load_warehouse_tables()
        return analyze_hospital_kpi(data)
    except Exception as exc:
        st.warning(f"无法加载 KPI 数据: {exc}")
        return pd.DataFrame()


def main_dashboard() -> None:
    """登录后的主看板。"""
    page_options = ["平台概览", "数据流水线", "Clinical RAG 问答", "系统说明"]
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = page_options[0]

    # 侧边栏（nav_page 不可作为 widget key，否则按钮跳转无法赋值）
    with st.sidebar:
        st.markdown(f"**欢迎，{st.session_state.get('username', '用户')}**")
        st.markdown("---")
        st.markdown("**功能导航**")
        current_page = st.session_state.nav_page
        if current_page not in page_options:
            current_page = page_options[0]
            st.session_state.nav_page = current_page
        page = st.radio(
            "选择页面",
            page_options,
            index=page_options.index(current_page),
            label_visibility="collapsed",
        )
        st.session_state.nav_page = page
        st.markdown("---")
        if st.button("退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pop("username", None)
            st.rerun()

    st.markdown("# Medical Data Intelligence Platform")
    st.caption("Hospital Information Center · Internal Demo")

    try:
        if page == "平台概览":
            render_overview_page(load_kpi_data())
        elif page == "数据流水线":
            render_pipeline_page()
        elif page == "Clinical RAG 问答":
            render_rag()
        else:
            render_docs()
    except Exception as exc:
        st.error(f"页面加载出错: {exc}")
        st.exception(exc)


def render_rag() -> None:
    """Clinical RAG 问答界面。"""
    st.subheader("Clinical RAG 智能问答")
    st.caption("整合数据仓库（结构化数据）+ FAISS 知识库（临床指南）")

    # 示例问题
    examples = [
        "糖尿病患者HbA1c多少需要关注？",
        "医院有多少患者？",
        "最常见的疾病是什么？",
        "Metformin 有什么作用？",
    ]
    st.markdown("**示例问题：**")
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        if col.button(ex, use_container_width=True):
            st.session_state.rag_question = ex

    question = st.text_area(
        "请输入您的问题",
        value=st.session_state.get("rag_question", ""),
        height=100,
        placeholder="例如：糖尿病患者HbA1c多少需要关注？",
    )

    if st.button("提交问题", type="primary"):
        if not question.strip():
            st.warning("请输入问题")
            return

        with st.spinner("正在检索数据仓库与知识库..."):
            try:
                answer = rag_ask(question.strip(), top_k=3)
                st.markdown("#### 回答")
                st.markdown(answer)
            except FileNotFoundError as exc:
                st.error(f"依赖未就绪: {exc}")
                st.info(
                    "请先运行：\n"
                    "```\n"
                    "python warehouse/build_warehouse.py\n"
                    "python knowledge_base/vector_store.py\n"
                    "```"
                )
            except Exception as exc:
                st.error(f"问答失败: {exc}")


def render_docs() -> None:
    """系统说明。"""
    st.subheader("系统说明")
    st.markdown(
        """
        本平台为**医院信息中心内部演示**版本，涵盖：

        | 模块 | 说明 |
        |------|------|
        | Database | SQLite 模拟 EHR 数据 |
        | ETL | 数据采集、清洗、入库 |
        | Quality | 数据质量评估报告 |
        | Warehouse | 星型模型数据仓库 |
        | Analytics | 临床统计与 KPI |
        | Knowledge Base | FAISS 临床知识库 |
        | RAG | 双路检索增强问答 |

        **登录说明：** 演示账号见 `.env.example`，默认 `admin` / `admin123`。

        **注意：** 本系统仅供内部演示，不可用于真实临床决策。
        """
    )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def main() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
