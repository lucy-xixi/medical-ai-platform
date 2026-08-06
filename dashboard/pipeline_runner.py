# -*- coding: utf-8 -*-
"""数据流水线步骤执行与状态检测（供 Streamlit 界面调用）。"""

from __future__ import annotations

import io
import sqlite3
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HOSPITAL_DB = PROJECT_ROOT / "database" / "hospital.db"
WAREHOUSE_DB = PROJECT_ROOT / "warehouse" / "warehouse.db"
QUALITY_REPORT = PROJECT_ROOT / "reports" / "data_quality_report.html"
ANALYTICS_REPORT = PROJECT_ROOT / "reports" / "clinical_analytics_report.html"
FAISS_INDEX = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss.index"

OLTP_TABLES = ["patients", "encounters", "conditions", "medications", "observations"]
WAREHOUSE_TABLES = [
    "dim_patient",
    "dim_condition",
    "dim_medication",
    "fact_encounter",
    "fact_observation",
    "fact_condition",
    "fact_medication",
]


@dataclass
class StepStatus:
    """单步流水线状态。"""

    key: str
    title: str
    ready: bool
    detail: str


def _count_tables(db_path: Path, tables: List[str]) -> dict[str, int | None]:
    if not db_path.exists():
        return {}
    counts: dict[str, int | None] = {}
    with sqlite3.connect(db_path) as conn:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                counts[table] = int(row[0]) if row else 0
            except sqlite3.Error:
                counts[table] = None
    return counts


def get_pipeline_status() -> List[StepStatus]:
    """返回各步骤就绪状态。"""
    oltp_counts = _count_tables(HOSPITAL_DB, OLTP_TABLES)
    wh_counts = _count_tables(WAREHOUSE_DB, WAREHOUSE_TABLES)

    oltp_ready = HOSPITAL_DB.exists() and all(
        (oltp_counts.get(t) or 0) > 0 for t in OLTP_TABLES
    )
    quality_ready = QUALITY_REPORT.exists()
    warehouse_ready = WAREHOUSE_DB.exists() and all(
        (wh_counts.get(t) or 0) > 0 for t in WAREHOUSE_TABLES
    )
    analytics_ready = ANALYTICS_REPORT.exists()
    kb_ready = FAISS_INDEX.exists()

    oltp_detail = (
        f"共 {sum(v or 0 for v in oltp_counts.values()):,} 条记录"
        if oltp_counts
        else "数据库未生成"
    )
    wh_detail = (
        f"共 {sum(v or 0 for v in wh_counts.values()):,} 条记录"
        if wh_counts
        else "数仓未构建"
    )

    return [
        StepStatus("init_db", "1. 初始化数据库", oltp_ready, oltp_detail),
        StepStatus("quality", "2. 数据质量评估", quality_ready, "报告已生成" if quality_ready else "未运行"),
        StepStatus("warehouse", "3. 构建数据仓库", warehouse_ready, wh_detail),
        StepStatus("analytics", "4. 临床统计分析", analytics_ready, "报告已生成" if analytics_ready else "未运行"),
        StepStatus("knowledge", "5. 构建知识库", kb_ready, "FAISS 索引已就绪" if kb_ready else "未构建"),
    ]


def _capture_output(func: Callable[[], object]) -> Tuple[bool, str]:
    """执行函数并捕获 stdout，返回 (成功, 输出文本)。"""
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            func()
        return True, buffer.getvalue().strip()
    except Exception as exc:
        output = buffer.getvalue().strip()
        err = f"{type(exc).__name__}: {exc}"
        if output:
            return False, f"{output}\n\n[错误] {err}"
        return False, err


def run_init_database() -> Tuple[bool, str]:
    from database.init_data import main

    return _capture_output(main)


def run_etl_pipeline() -> Tuple[bool, str]:
    from etl.pipeline import run_pipeline

    return _capture_output(run_pipeline)


def run_quality_report() -> Tuple[bool, str]:
    from quality.quality_report import generate_report

    def _run() -> None:
        path = generate_report()
        print(f"Data quality report generated:\n{path}")

    return _capture_output(_run)


def run_build_warehouse() -> Tuple[bool, str]:
    from warehouse.build_warehouse import build_warehouse

    return _capture_output(build_warehouse)


def run_analytics_report() -> Tuple[bool, str]:
    from analytics.analytics_report import run_analytics

    def _run() -> None:
        path = run_analytics()
        print(f"Clinical analytics report generated successfully.\n{path}")

    return _capture_output(_run)


def run_knowledge_base() -> Tuple[bool, str]:
    from knowledge_base.document_processor import process_documents, save_processed
    from knowledge_base.ingestion import ingest_documents
    from knowledge_base.vector_store import build_and_save_vector_store

    def _run() -> None:
        docs = ingest_documents()
        processed = process_documents(docs)
        save_processed(processed)
        build_and_save_vector_store()
        print("Clinical Knowledge Base created successfully.")

    return _capture_output(_run)


def run_full_pipeline(include_etl: bool = False) -> List[Tuple[str, bool, str]]:
    """按顺序执行全流程，返回每步结果。"""
    steps: List[Tuple[str, Callable[[], Tuple[bool, str]]]] = [
        ("初始化数据库", run_init_database),
    ]
    if include_etl:
        steps.append(("ETL 流水线", run_etl_pipeline))
    steps.extend(
        [
            ("数据质量评估", run_quality_report),
            ("构建数据仓库", run_build_warehouse),
            ("临床统计分析", run_analytics_report),
            ("构建知识库", run_knowledge_base),
        ]
    )

    results: List[Tuple[str, bool, str]] = []
    for name, runner in steps:
        ok, msg = runner()
        results.append((name, ok, msg))
        if not ok:
            break
    return results


def get_oltp_counts() -> dict[str, int | None]:
    return _count_tables(HOSPITAL_DB, OLTP_TABLES)


def get_warehouse_counts() -> dict[str, int | None]:
    return _count_tables(WAREHOUSE_DB, WAREHOUSE_TABLES)
