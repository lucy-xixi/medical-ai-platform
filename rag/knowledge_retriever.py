# -*- coding: utf-8 -*-
"""
医学知识检索器

从 FAISS 向量知识库检索临床指南与用药知识。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from knowledge_base.knowledge_search import SearchResult, search
from rag.logger import setup_logger

logger = setup_logger("rag.knowledge_retriever")


@dataclass
class KnowledgeContext:
    """医学知识检索结果。"""

    results: List[SearchResult] = field(default_factory=list)
    source: str = "knowledge_base/vector_store/faiss.index"

    def to_text(self) -> str:
        if not self.results:
            return "（未检索到相关医学知识文档）"
        parts = []
        for r in self.results:
            parts.append(f"[{r.source} | 相关度:{r.score:.2f}]\n{r.text}")
        return "\n\n".join(parts)


def retrieve_knowledge(question: str, top_k: int = 3) -> KnowledgeContext:
    """
    从 FAISS 临床知识库检索与用户问题最相关的文档块。
    """
    logger.info("检索医学知识 | top_k=%d", top_k)
    try:
        results = search(question, top_k=top_k)
    except FileNotFoundError as exc:
        logger.error("知识库未构建: %s", exc)
        return KnowledgeContext()

    logger.info("医学知识检索完成 | 命中: %d", len(results))
    return KnowledgeContext(results=results)
