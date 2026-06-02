from __future__ import annotations

import re

from loopora.alignment_semantics import semantic_antipattern_match_is_negated


def _semantic_text_is_specific(text: object, *, min_chars: int = 48) -> bool:
    value = str(text or "").strip()
    if len(value) < min_chars:
        return False
    generic_patterns = [
        r"requested behavior",
        r"do the task",
        r"task is done",
        r"\bit works\b",
        r"make it work",
        r"works well",
        r"requested task",
        r"alignment agreement",
        r"按需求完成",
        r"完成任务",
        r"实现需求",
    ]
    lower = value.lower()
    return not any(re.search(pattern, lower) for pattern in generic_patterns)


def _semantic_text_mentions_evidence(text: object) -> bool:
    value = str(text or "").lower()
    evidence_terms = [
        "evidence",
        "proof",
        "verify",
        "verification",
        "test",
        "browser",
        "command",
        "artifact",
        "handoff",
        "blocker",
        "证据",
        "验证",
        "测试",
        "浏览器",
        "命令",
        "产物",
        "交接",
        "阻断",
    ]
    return any(term in value for term in evidence_terms)


def _semantic_text_mentions_evidence_bucket_projection(text: object) -> bool:
    value = str(text or "")
    bucket_patterns = {
        "proven": r"\bproven\b|已证明",
        "weak": r"\bweak\b|弱证据|证据薄弱",
        "unproven": r"\bunproven\b|未证明",
        "blocking": r"\bblocking\b|阻断",
        "residual": r"\bresidual risk\b|残余风险",
    }
    segments = [segment.strip() for segment in re.split(r"[\n.;。；]", value) if segment.strip()]
    return any(all(re.search(pattern, segment, re.IGNORECASE) for pattern in bucket_patterns.values()) for segment in segments)


def _semantic_text_mentions_workflow_judgment_flow(text: object) -> bool:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value:
        return False
    evidence_flow = re.search(
        r"\b(?:evidence|proof|handoffs?|inspect(?:ion|or)?|review)\b|证据|证明|交接|检查|审查|评审",
        value,
        re.IGNORECASE,
    )
    gatekeeper_closure = re.search(
        r"\b(?:gatekeeper|gate keeper|final judgment|finish|closure|verdict)\b|守门|裁决|收束|结论",
        value,
        re.IGNORECASE,
    )
    early_exposure = re.search(
        r"\b(?:weak|unproven|fake[- ]?done|fake completion|drift|block(?:ing|er)?|gap|unsupported)\b"
        r"|弱证据|未证明|假完成|偏差|漂移|阻断|缺口|无支撑",
        value,
        re.IGNORECASE,
    )
    return bool(evidence_flow and gatekeeper_closure and early_exposure)


def _semantic_text_mentions_personality_memory_antipattern(text: object) -> bool:
    value = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    if not value:
        return False
    patterns = [
        r"\b(?:global|permanent|always-on|chat-wide)\s+(?:user\s+)?"
        r"(?:persona|personality|preference|preferences|memory|trait|style)\b",
        r"\b(?:persona|personality|preference|preferences|style)\s+(?:memory|profile)\b",
        r"\b(?:remember|store|capture|codify)\s+(?:the\s+)?(?:user's|my)\s+"
        r"(?:persona|personality|preference|preferences|style|traits?)\b",
        r"\balways\s+(?:follow|use|prefer|behave|act|answer)\b.{0,80}\b(?:user|my)\b.{0,80}"
        r"\b(?:persona|personality|preference|preferences|style|trait)\b",
        r"全局(?:人格|偏好|记忆|画像)",
        r"永久(?:人格|偏好|记忆|画像)",
        r"(?:人格|偏好|用户画像|用户特质).{0,8}(?:记忆|长期记住|全局继承)",
        r"记住.{0,12}(?:我的|用户).{0,8}(?:偏好|人格|风格)",
        r"总是.{0,16}(?:按|遵循|使用).{0,12}(?:偏好|人格|风格)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            if semantic_antipattern_match_is_negated(value, match.start()):
                continue
            return True
    return False


def _semantic_text_mentions_named_loopora_antipattern(text: object) -> bool:
    value = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    if not value:
        return False
    patterns = [
        r"\bprompt[- ]pack\b",
        r"\brole[- ]zoo\b",
        r"\bloop[- ]script\b",
        r"\bbenchmark[- ]grinder\b",
        r"\bchat[- ]wrapper\b",
        r"提示词包|堆提示词|堆角色|循环脚本|刷基准|基准刷分|聊天壳",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            if semantic_antipattern_match_is_negated(value, match.start()):
                continue
            return True
    return False
