from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import _search_refactor_improvement_readiness_evidence
from loopora.executor_alignment_agreement_responses import alignment_chinese_improvement_agreement_response


def alignment_chinese_refactor_improvement_agreement_response(feedback_text: str) -> dict:
    payload = alignment_chinese_improvement_agreement_response()
    feedback = feedback_text or "用户要求更激进但仍任务范围内的重构改进。"
    payload["assistant_message"] = "请确认这份重构改进协议；确认后我会把重构 delta 投射到 spec、阶段角色、workflow handoff 和 GateKeeper 阻断条件。"
    payload["agreement_summary"] = (
        "保留来源 Loop 的稳定搜索目标、workdir 和 executor 默认值；只允许任务范围内的重构 delta。"
        "这次改进会分阶段处理 baseline、query rewrite、retrieval、ranking、regression review 和 evidence hardening。"
        "如果复杂度只是换地方、搜索用户行为回归或证据路径仍无法复验，GateKeeper 必须阻断。"
    )
    payload["readiness_evidence"] = _search_refactor_improvement_readiness_evidence(feedback, language="zh")
    return payload
