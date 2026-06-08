from __future__ import annotations

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


def test_alignment_examples_require_rag_grounding_and_tool_safety_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "RAG grounding and tool safety example",
            "RAG support chatbot",
            "citation/source span 能回到文档版本",
            "prompt injection in documents 不能让模型泄露系统提示词或调用未授权 tool",
            "不能把“一个 demo question answered”“answer looks plausible”“embedding search 返回结果”或“UI 显示 citations”当成 RAG support chatbot 完成",
            "ai/rag-grounding-tool-safety",
            "RAG Contract Inspector",
            "Grounding Evidence Inspector",
            "source span + prompt injection + permission-filtered retrieval 证据优先",
        ),
    )
