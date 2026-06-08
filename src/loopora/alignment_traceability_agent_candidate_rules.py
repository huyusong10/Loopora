from __future__ import annotations

import re

from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_execution_strategy_categories,
    agent_candidate_fake_done_categories,
    agent_candidate_has_labeled_execution_strategy,
    agent_candidate_residual_risk_policy_categories,
    agent_candidate_success_surface_categories,
    agent_candidate_tradeoff_categories,
)


def alignment_agent_candidate_tradeoff_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_tradeoff_categories(task_text)
    if len(categories) < 2:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent judgment tradeoffs into runnable surfaces: ",
    )


def alignment_agent_candidate_execution_strategy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_execution_strategy_categories(task_text)
    if not categories:
        return []
    if len(categories) < 2 and not agent_candidate_has_labeled_execution_strategy(task_text):
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent execution strategy into runnable surfaces: ",
    )


def alignment_agent_candidate_residual_risk_policy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_residual_risk_policy_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=normalized_bundle_text,
        message_prefix="agent-first candidate must project explicit host Agent residual-risk policy into runnable surfaces: ",
    )


def alignment_agent_candidate_success_surface_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_success_surface_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=_without_residual_demotion_text(normalized_bundle_text),
        message_prefix="agent-first candidate must project explicit host Agent success criteria into runnable surfaces: ",
    )


def alignment_agent_candidate_fake_done_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_fake_done_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=_without_fake_done_demotion_text(normalized_bundle_text),
        message_prefix="agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: ",
    )


def alignment_agent_candidate_evidence_preference_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_evidence_preference_categories(task_text)
    if not categories:
        return []
    return _category_projection_issues(
        categories,
        normalized_bundle_text=_without_residual_demotion_text(normalized_bundle_text),
        message_prefix="agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: ",
    )


def _without_accepted_residual_risk_block(normalized_bundle_text: str) -> str:
    return re.sub(
        (
            r"(?:^| )-?\s*(?:accepted residual risk|可接受残余风险)[:：].*?"
            r"(?= -?\s*(?:fail closed if|失败关闭|必须阻断):| # role notes| ## |$)"
        ),
        " ",
        normalized_bundle_text,
        flags=re.IGNORECASE,
    )


def _without_fake_done_demotion_text(normalized_bundle_text: str) -> str:
    text = _without_accepted_residual_risk_block(normalized_bundle_text)
    return re.sub(
        (
            r"[^.!?。；;#]{0,560}"
            r"(?:\baccepted residual\b|\bhandled later\b|\blater residual risks?\b|"
            r"\bas later residual risks?\b|\bcan be handled later\b|"
            r"\b(?:do not|don't|not)\s+(?:handle|check|verify|prove|cover)\b|"
            r"\b(?:only|just|merely)\s+(?:check|verify|collect|implement|handle)\b|"
            r"\b(?:do not|don't|not)\s+block\b|"
            r"\b(?:not|isn't|is not)\s+(?:a\s+)?(?:blocker|blocking item|blocking criterion|"
            r"acceptance criterion|success criterion)\b|"
            r"可接受残余风险|后续残余风险|后续处理|后续补|后补|"
            r"不处理|不验证|不检查|不证明|不覆盖|只检查|只验证|只收集|只实现|只处理|"
            r"暂不|暂时不|本轮不|不作为(?:本轮)?(?:阻断项|完成条件|验收条件)|"
            r"暂不阻断|不阻断|不要阻断|不用阻断|无需阻断)"
            r"[^.!?。；;#]{0,560}"
        ),
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _without_residual_demotion_text(normalized_bundle_text: str) -> str:
    text = _without_accepted_residual_risk_block(normalized_bundle_text)
    return re.sub(
        (
            r"[^.!?。；;#]{0,560}"
            r"(?:\bresidual risks?\b|\baccepted residual\b|\bhandled later\b|"
            r"\bas later residual risks?\b|\bcan be handled later\b|"
            r"\b(?:do not|don't|not)\s+(?:handle|check|verify|prove|cover)\b|"
            r"\b(?:only|just|merely)\s+(?:check|verify|collect|implement|handle)\b|"
            r"\b(?:do not|don't|not)\s+block\b|"
            r"\b(?:not|isn't|is not)\s+(?:a\s+)?(?:blocker|blocking item|blocking criterion|"
            r"acceptance criterion|success criterion)\b|"
            r"残余风险|可接受残余风险|后续处理|后续补|后补|"
            r"不处理|不验证|不检查|不证明|不覆盖|只检查|只验证|只收集|只实现|只处理|"
            r"暂不|暂时不|本轮不|不作为(?:本轮)?(?:阻断项|完成条件|验收条件)|"
            r"暂不阻断|不阻断|不要阻断|不用阻断|无需阻断)"
            r"[^.!?。；;#]{0,560}"
        ),
        " ",
        text,
        flags=re.IGNORECASE,
    )


def _category_projection_issues(
    categories: list[tuple[str, str]],
    *,
    normalized_bundle_text: str,
    message_prefix: str,
) -> list[str]:
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.IGNORECASE)
    ]
    if not missing:
        return []
    return [message_prefix + "missing " + ", ".join(missing)]
