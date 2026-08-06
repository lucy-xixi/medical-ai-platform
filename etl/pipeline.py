#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医疗数据 ETL 流水线

流程: Extract → Transform → Load

运行:
    python etl/pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract import extract_all
from etl.load import load_all
from etl.logger import LOG_FILE, setup_logger
from etl.transform import transform_all

logger = setup_logger("etl.pipeline")


def run_pipeline() -> None:
    """执行完整 ETL 流程。"""
    logger.info("ETL Pipeline 启动 | 日志文件: %s", LOG_FILE)

    # Extract
    raw_data = extract_all()

    # Transform
    processed, _output_paths = transform_all(raw_data)

    # Load
    results = load_all(processed)

    logger.info(
        "ETL Pipeline 汇总 | patients=%d | conditions=%d | medications=%d",
        results["patients"],
        results["conditions"],
        results["medications"],
    )
    print("ETL pipeline completed.")


def main() -> int:
    """命令行入口。"""
    try:
        run_pipeline()
        return 0
    except Exception as exc:
        logger.exception("ETL Pipeline 失败: %s", exc)
        print(f"ETL pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
