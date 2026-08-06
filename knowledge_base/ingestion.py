#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识采集模块 (Ingestion)

扫描 knowledge_base/documents/ 目录，读取全部 txt 知识文档。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, TypedDict

KB_ROOT = Path(__file__).resolve().parent
if str(KB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(KB_ROOT.parent))

from knowledge_base.config import DOCUMENTS_DIR
from knowledge_base.logger import setup_logger

logger = setup_logger("knowledge_base.ingestion")


class DocumentRecord(TypedDict):
    """单篇知识文档记录。"""

    filename: str
    content: str
    char_count: int


def ingest_documents(documents_dir: Path | None = None) -> List[DocumentRecord]:
    """
    扫描并读取 documents/ 下所有 txt 文件。

    Returns:
        document_list — 文档列表，每项含 filename / content / char_count
    """
    docs_dir = documents_dir or DOCUMENTS_DIR
    logger.info("========== 知识采集开始 ==========")
    logger.info("扫描目录: %s", docs_dir)

    if not docs_dir.exists():
        raise FileNotFoundError(f"文档目录不存在: {docs_dir}")

    document_list: List[DocumentRecord] = []
    txt_files = sorted(docs_dir.glob("*.txt"))

    if not txt_files:
        logger.warning("未找到任何 txt 文档")
        return document_list

    for file_path in txt_files:
        content = file_path.read_text(encoding="utf-8")
        record: DocumentRecord = {
            "filename": file_path.name,
            "content": content,
            "char_count": len(content),
        }
        document_list.append(record)
        logger.info("已读取 | %s | 字符数: %d", file_path.name, record["char_count"])

    logger.info("知识采集完成 | 文档数: %d", len(document_list))
    return document_list


def main() -> int:
    """命令行入口。"""
    try:
        docs = ingest_documents()
        print(f"Ingested {len(docs)} documents.")
        for doc in docs:
            print(f"  - {doc['filename']} ({doc['char_count']} chars)")
        return 0
    except Exception as exc:
        logger.exception("知识采集失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
