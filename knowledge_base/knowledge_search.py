#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识检索模块 (Knowledge Search)

基于 FAISS 向量索引实现语义相似度检索。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np

KB_ROOT = Path(__file__).resolve().parent
if str(KB_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(KB_ROOT.parent))

from knowledge_base.config import DEFAULT_TOP_K
from knowledge_base.embedding import embed_query
from knowledge_base.logger import setup_logger
from knowledge_base.vector_store import load_index

logger = setup_logger("knowledge_base.search")


@dataclass
class SearchResult:
    """单条检索结果。"""

    rank: int
    score: float
    chunk_id: int
    source: str
    text: str


def search(query: str, top_k: int = DEFAULT_TOP_K) -> List[SearchResult]:
    """
    知识检索主流程：

        Question → Embedding → FAISS similarity search → Top K 文档块

    Args:
        query: 用户问题
        top_k: 返回最相关的 K 条结果

    Returns:
        SearchResult 列表
    """
    logger.info("检索问题: %s", query)
    index, chunks = load_index()
    query_vec = embed_query(query)

    scores, indices = index.search(query_vec, top_k)

    results: List[SearchResult] = []
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), start=1):
        if idx < 0:
            continue
        chunk = chunks[int(idx)]
        results.append(
            SearchResult(
                rank=rank,
                score=float(score),
                chunk_id=chunk["id"],
                source=chunk["source"],
                text=chunk["text"],
            )
        )
        logger.info("Top %d | score=%.4f | source=%s | id=%d", rank, score, chunk["source"], chunk["id"])

    return results


def print_results(results: List[SearchResult]) -> None:
    """格式化打印检索结果。"""
    if not results:
        print("未找到相关内容。")
        return

    print("\n" + "=" * 60)
    print("知识检索结果")
    print("=" * 60)
    for r in results:
        print(f"\n--- Rank {r.rank} | Score: {r.score:.4f} | Source: {r.source} ---")
        print(r.text[:500] + ("..." if len(r.text) > 500 else ""))


def main() -> int:
    """命令行入口：演示检索。"""
    try:
        # 默认示例问题
        query = "糖尿病患者HbA1c多少需要关注？"
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])

        results = search(query)
        print_results(results)
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        print("请先依次运行 ingestion → document_processor → embedding → vector_store", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("检索失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
