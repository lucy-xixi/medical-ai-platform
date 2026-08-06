# -*- coding: utf-8 -*-
"""星型数据仓库可视化 — 模型图、表结构、样例数据浏览。"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analytics.warehouse_loader import load_warehouse_tables
from dashboard.pipeline_runner import WAREHOUSE_DB, get_warehouse_counts

STAR_SCHEMA_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
    background: #f8fafc;
    color: #1e293b;
  }
  .wrap {
    max-width: 920px;
    margin: 0 auto;
    padding: 12px 8px 20px;
  }
  .title {
    text-align: center;
    font-size: 15px;
    font-weight: 700;
    color: #0f766e;
    margin-bottom: 10px;
  }
  .canvas {
    position: relative;
    width: 100%;
    height: 430px;
    background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
  }
  .canvas svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  .node {
    position: absolute;
    transform: translate(-50%, -50%);
    min-width: 148px;
    padding: 10px 12px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
    border: 2px solid transparent;
  }
  .node .name { font-size: 13px; font-weight: 700; line-height: 1.2; }
  .node .tag {
    margin-top: 4px;
    font-size: 11px;
    opacity: 0.85;
  }
  .dim {
    background: #dbeafe;
    border-color: #3b82f6;
    color: #1e3a8a;
  }
  .dim.center {
    background: #2563eb;
    color: #fff;
    min-width: 168px;
    padding: 14px 16px;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
    z-index: 2;
  }
  .dim.center .tag { color: #dbeafe; }
  .fact {
    background: #dcfce7;
    border-color: #22c55e;
    color: #14532d;
  }
  .legend {
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 12px;
    font-size: 12px;
    color: #64748b;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .dot {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    display: inline-block;
  }
  .dot.dim { background: #3b82f6; }
  .dot.fact { background: #22c55e; }
  .line-label {
    font-size: 10px;
    fill: #64748b;
    font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="title">Star Schema · warehouse.db</div>
  <div class="canvas">
    <svg viewBox="0 0 900 430" preserveAspectRatio="xMidYMid meet">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <polygon points="0 0, 8 4, 0 8" fill="#94a3b8"/>
        </marker>
      </defs>
      <!-- hub to facts -->
      <line x1="450" y1="215" x2="450" y2="72" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
      <line x1="450" y1="215" x2="170" y2="215" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
      <line x1="450" y1="215" x2="730" y2="215" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
      <line x1="450" y1="215" x2="450" y2="358" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)"/>
      <!-- dims to facts -->
      <line x1="730" y1="95" x2="730" y2="175" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#arrow)"/>
      <line x1="170" y1="95" x2="170" y2="175" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#arrow)"/>
      <line x1="620" y1="358" x2="520" y2="358" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5,4" marker-end="url(#arrow)"/>
      <text class="line-label" x="458" y="140">patient_key</text>
      <text class="line-label" x="280" y="208">patient_key</text>
      <text class="line-label" x="560" y="208">patient_key</text>
      <text class="line-label" x="458" y="300">patient_key</text>
      <text class="line-label" x="742" y="138">condition_key</text>
      <text class="line-label" x="148" y="138">medication_key</text>
    </svg>

    <!-- center hub -->
    <div class="node dim center" style="left:50%; top:50%;">
      <div class="name">dim_patient</div>
      <div class="tag">患者维度 · 中心</div>
    </div>

    <!-- facts -->
    <div class="node fact" style="left:50%; top:16%;">
      <div class="name">fact_encounter</div>
      <div class="tag">就诊事实</div>
    </div>
    <div class="node fact" style="left:19%; top:50%;">
      <div class="name">fact_medication</div>
      <div class="tag">用药事实</div>
    </div>
    <div class="node fact" style="left:81%; top:50%;">
      <div class="name">fact_condition</div>
      <div class="tag">诊断事实</div>
    </div>
    <div class="node fact" style="left:50%; top:84%;">
      <div class="name">fact_observation</div>
      <div class="tag">检验事实</div>
    </div>

    <!-- dimensions -->
    <div class="node dim" style="left:81%; top:16%;">
      <div class="name">dim_condition</div>
      <div class="tag">诊断维度</div>
    </div>
    <div class="node dim" style="left:19%; top:16%;">
      <div class="name">dim_medication</div>
      <div class="tag">药品维度</div>
    </div>
  </div>

  <div class="legend">
    <span><i class="dot dim"></i> 维度表 Dimension</span>
    <span><i class="dot fact"></i> 事实表 Fact</span>
    <span>实线 = patient_key &nbsp;|&nbsp; 虚线 = condition / medication key</span>
  </div>
</div>
</body>
</html>
"""

DIMENSION_TABLES: List[dict] = [
    {
        "表名": "dim_patient",
        "类型": "维度表",
        "说明": "患者人口统计学：性别、出生年、年龄段",
        "主键": "patient_key",
        "业务键": "patient_id",
    },
    {
        "表名": "dim_condition",
        "类型": "维度表",
        "说明": "ICD-10 诊断编码与疾病名称",
        "主键": "condition_key",
        "业务键": "icd_code",
    },
    {
        "表名": "dim_medication",
        "类型": "维度表",
        "说明": "药品名称字典",
        "主键": "medication_key",
        "业务键": "drug_name",
    },
]

FACT_TABLES: List[dict] = [
    {
        "表名": "fact_encounter",
        "类型": "事实表",
        "说明": "就诊事件：日期、类型",
        "外键": "patient_key → dim_patient",
    },
    {
        "表名": "fact_observation",
        "类型": "事实表",
        "说明": "检验/观测：HbA1c、血压、肌酐等",
        "外键": "patient_key → dim_patient",
    },
    {
        "表名": "fact_condition",
        "类型": "事实表",
        "说明": "患者-诊断关联，支持疾病分布统计",
        "外键": "patient_key, condition_key",
    },
    {
        "表名": "fact_medication",
        "类型": "事实表",
        "说明": "患者-用药关联，支持用药频次分析",
        "外键": "patient_key, medication_key",
    },
]

TABLE_LABELS = {
    "dim_patient": "dim_patient · 患者维度",
    "dim_condition": "dim_condition · 诊断维度",
    "dim_medication": "dim_medication · 药品维度",
    "fact_encounter": "fact_encounter · 就诊事实",
    "fact_observation": "fact_observation · 检验事实",
    "fact_condition": "fact_condition · 诊断事实",
    "fact_medication": "fact_medication · 用药事实",
}


def render_star_schema_graph(height: int = 500) -> None:
    """渲染 HTML/SVG 星型模型结构图；下方附带 Streamlit 原生结构说明。"""
    # 原生备用（不依赖 iframe，确保一定能看到）
    hub, top, left, right, bottom = st.columns([1.2, 1, 1, 1, 1.2])
    with top:
        st.info("**fact_encounter**\n就诊事实")
    with left:
        st.info("**fact_medication**\n用药事实")
    with hub:
        st.success("**dim_patient**\n患者维度 · 中心")
    with right:
        st.info("**fact_condition**\n诊断事实")
    with bottom:
        st.info("**fact_observation**\n检验事实")

    d1, d2, _ = st.columns([1, 1, 2])
    with d1:
        st.markdown("🔵 **dim_medication** · 药品维度 → fact_medication")
    with d2:
        st.markdown("🔵 **dim_condition** · 诊断维度 → fact_condition")

    components.html(STAR_SCHEMA_HTML, height=height, scrolling=False)


def render_star_schema_diagram(compact: bool = False) -> None:
    """渲染星型模型结构图与表说明。"""
    st.markdown("##### 星型模型 (Star Schema)")
    render_star_schema_graph(height=480 if compact else 520)

    if not compact:
        st.caption(
            "中心 **dim_patient** 连接全部事实表；"
            "**fact_condition** / **fact_medication** 分别关联诊断与药品维度。"
        )

    dim_col, fact_col = st.columns(2)
    with dim_col:
        st.markdown("**维度表 (Dimension)**")
        st.dataframe(pd.DataFrame(DIMENSION_TABLES), use_container_width=True, hide_index=True)
    with fact_col:
        st.markdown("**事实表 (Fact)**")
        st.dataframe(pd.DataFrame(FACT_TABLES), use_container_width=True, hide_index=True)


def _load_preview_data() -> Dict[str, pd.DataFrame]:
    try:
        return load_warehouse_tables()
    except Exception:
        return {}


def render_warehouse_data_browser(max_rows: int = 8) -> None:
    """浏览数仓各表样例数据。"""
    wh_counts = get_warehouse_counts()
    if not wh_counts:
        st.info(f"数仓尚未构建。请先运行「构建数据仓库」，生成 `{WAREHOUSE_DB.name}`。")
        return

    st.markdown("##### 数仓数据浏览")
    counts_df = pd.DataFrame([{"表名": k, "记录数": f"{v:,}"} for k, v in wh_counts.items()])
    st.dataframe(counts_df, use_container_width=True, hide_index=True)

    data = _load_preview_data()

    tab_dim, tab_fact = st.tabs(["维度表", "事实表"])
    with tab_dim:
        for name in ["dim_patient", "dim_condition", "dim_medication"]:
            df = data.get(name, pd.DataFrame())
            st.markdown(f"**{TABLE_LABELS[name]}** · {len(df):,} 行")
            if not df.empty:
                st.dataframe(df.head(max_rows), use_container_width=True, hide_index=True)
            else:
                st.caption("暂无数据")

    with tab_fact:
        for name in ["fact_encounter", "fact_observation", "fact_condition", "fact_medication"]:
            df = data.get(name, pd.DataFrame())
            st.markdown(f"**{TABLE_LABELS[name]}** · {len(df):,} 行")
            if not df.empty:
                st.dataframe(df.head(max_rows), use_container_width=True, hide_index=True)
            else:
                st.caption("暂无数据")


def render_star_schema_view(*, show_browser: bool = True, compact: bool = False) -> None:
    """完整星型数仓展示：模型图 + 可选数据浏览。"""
    render_star_schema_diagram(compact=compact)
    if show_browser:
        st.markdown("---")
        render_warehouse_data_browser()
