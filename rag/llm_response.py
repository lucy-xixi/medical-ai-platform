# -*- coding: utf-8 -*-
"""
LLM 响应生成器

支持 OpenAI API（可选）及本地模板回退模式。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from rag.logger import setup_logger

logger = setup_logger("rag.llm")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _generate_with_openai(prompt: str) -> Optional[str]:
    """尝试使用 OpenAI API 生成回答。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model, temperature=0.2, api_key=api_key)
        response = llm.invoke([
            SystemMessage(content="你是专业的医疗数据分析与临床知识辅助助手。请用中文回答。"),
            HumanMessage(content=prompt),
        ])
        return response.content
    except ImportError:
        logger.warning("langchain-openai 未安装，跳过 OpenAI 调用")
        return None
    except Exception as exc:
        logger.warning("OpenAI 调用失败，使用本地回退: %s", exc)
        return None


def _generate_local(prompt: str, question: str, patient_text: str, knowledge_text: str) -> str:
    """
    本地模板回退回答（无需 API Key，基于检索上下文合成）。
    """
    parts = [
        "【Clinical RAG 回答】",
        "",
        f"您的问题：{question}",
        "",
    ]

    if "（未检索到相关结构化患者数据）" not in patient_text:
        parts.extend(["[数据仓库检索结果]", patient_text, ""])

    if "（未检索到相关医学知识文档）" not in knowledge_text:
        parts.extend(["[临床知识库检索结果]"])
        for block in knowledge_text.split("\n\n")[:2]:
            summary = block.strip().replace("\n", " ")[:400]
            parts.append(f"  {summary}...")
        parts.append("")

    parts.extend([
        "[综合说明]",
        "以上回答基于医院数据仓库（warehouse.db）的结构化统计数据",
        "以及 FAISS 临床知识库中的指南文档综合生成。",
        "",
        "注意：本回答仅供医院信息中心内部辅助参考，不能替代专业临床判断。",
    ])

    return "\n".join(parts)


def generate_response(prompt: str, question: str = "", patient_text: str = "", knowledge_text: str = "") -> str:
    """
    生成 LLM 回答。

    优先使用 OpenAI API；若无 API Key 则使用本地模板合成。
    """
    logger.info("生成 LLM 回答...")

    llm_answer = _generate_with_openai(prompt)
    if llm_answer:
        logger.info("使用 OpenAI 生成回答")
        return llm_answer

    logger.info("使用本地模板回退生成回答")
    return _generate_local(prompt, question, patient_text, knowledge_text)
