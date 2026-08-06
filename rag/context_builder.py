# -*- coding: utf-8 -*-
"""
上下文构建器

合并患者结构化数据与医学知识检索结果，构建 LLM Prompt 上下文。
"""

from __future__ import annotations

from dataclasses import dataclass

from rag.knowledge_retriever import KnowledgeContext
from rag.logger import setup_logger
from rag.patient_retriever import PatientDataContext

logger = setup_logger("rag.context_builder")

SYSTEM_PROMPT = """你是一名医院信息中心的 Clinical RAG 临床辅助助手。
请基于提供的「患者数据」和「医学知识」回答用户问题。
要求：
1. 优先使用给定上下文，不要编造数据；
2. 区分统计数据（来自数据仓库）与指南知识（来自临床文档）；
3. 回答使用中文，简洁专业；
4. 若上下文不足，明确说明并给出一般性建议；
5. 提醒用户：本回答仅供辅助参考，不能替代临床决策。"""


@dataclass
class RAGContext:
    """完整 RAG 上下文。"""

    question: str
    patient_data: PatientDataContext
    knowledge: KnowledgeContext

    def build_prompt(self) -> str:
        """构建供 LLM 使用的完整 Prompt。"""
        return f"""{SYSTEM_PROMPT}

【用户问题】
{self.question}

【患者数据 — 来源: {self.patient_data.source}】
{self.patient_data.to_text()}

【医学知识 — 来源: {self.knowledge.source}】
{self.knowledge.to_text()}

请综合以上信息回答用户问题。"""

    def build_context_summary(self) -> str:
        """构建可读上下文摘要（用于日志与调试）。"""
        lines = [
            "=" * 60,
            "Context Retrieval Summary",
            "=" * 60,
            f"Question: {self.question}",
            "",
            "--- Patient Data ---",
            self.patient_data.to_text(),
            "",
            "--- Medical Knowledge ---",
        ]
        if self.knowledge.results:
            for r in self.knowledge.results:
                lines.append(f"  [{r.source}] score={r.score:.3f}: {r.text[:120]}...")
        else:
            lines.append("  (none)")
        return "\n".join(lines)


def build_context(
    question: str,
    patient_data: PatientDataContext,
    knowledge: KnowledgeContext,
) -> RAGContext:
    """合并双路检索结果为 RAGContext。"""
    ctx = RAGContext(question=question, patient_data=patient_data, knowledge=knowledge)
    logger.info("上下文构建完成 | 患者片段: %d | 知识片段: %d",
                len(patient_data.snippets), len(knowledge.results))
    return ctx
