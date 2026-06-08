from __future__ import annotations

import re

LOCAL_GOVERNANCE_MARKER_PATTERN = (
    r"agents\.md|design/readme\.md|design/|tests/|project-local|project local|"
    r"local\s+design/test|design/test\s+obligations?|skipped\s+local\s+governance|"
    r"gobernanza\s+local|reglas\s+locales|obligaciones\s+de\s+dise(?:ñ|n)o|pruebas"
)
BUILDER_ACTOR_PATTERN = r"\b(?:builder|generator)\b|构建者|构建|执行方|实施方"
BUILDER_ACTION_PATTERN = (
    r"\b(?:read|reads|consult|consults|follow|follows|respect|respects|use|uses|using|locate|locates|identify|identifies)\b"
    r"|\b(?:lee|leer|consulta|consultar|sigue|seguir|respeta|respetar|usa|usar)\b"
    r"|读取|查阅|查找|定位|识别|遵守|遵循|使用|读"
)
REVIEW_ACTOR_PATTERN = (
    r"\b(?:inspector|inspectors|custom|review|reviewer|reviewers)\b|检查者|巡检|检查|审查|验证|检视方|评审方"
)
REVIEW_ACTION_PATTERN = (
    r"\b(?:verify|verifies|verification|check|checks|review|reviews|validate|validates|test|tests)\b"
    r"|\b(?:verifica|verificar|revisa|revisar|valida|validar|prueba|probar)\b"
    r"|检查|审查|验证|测试|核对"
)
GATEKEEPER_ACTOR_PATTERN = r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决|最终判断|最终裁决|收口|验收"
GATEKEEPER_ACTION_PATTERN = (
    r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects|gate|gates|gating)\b"
    r"|\b(?:d[eé]bil|no\s+probado|bloqueo|bloquea|faltante|omitido|omitida|fallar cerrado|rechaza|trata)\b"
    r"|弱证据|未证明|阻断|缺少|跳过|拒绝|视为"
)


def select_local_governance_trace(candidates: list[object]) -> list[str]:
    traces: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        compact = _compact_trace_candidate(candidate)
        if not compact or compact.lower() in seen:
            continue
        if not re.search(LOCAL_GOVERNANCE_MARKER_PATTERN, compact, re.IGNORECASE):
            continue
        priority = local_governance_trace_priority(compact)
        if priority is None:
            continue
        seen.add(compact.lower())
        traces.append((priority, index, compact[:240].rstrip() + ("..." if len(compact) > 240 else "")))
    ordered_traces = sorted(traces, key=lambda item: (item[0], item[1]))
    selected: list[tuple[int, int, str]] = []
    selected_keys: set[tuple[int, int]] = set()
    covered_priorities: set[int] = set()
    for priority, index, trace in ordered_traces:
        if priority in covered_priorities:
            continue
        selected.append((priority, index, trace))
        selected_keys.add((priority, index))
        covered_priorities.add(priority)
    for priority, index, trace in ordered_traces:
        if len(selected) >= 4:
            break
        if (priority, index) in selected_keys:
            continue
        selected.append((priority, index, trace))
    return [trace for _priority, _index, trace in selected[:4]]


def local_governance_trace_priority(text: str) -> int | None:
    if local_governance_role_responsibility_present(
        text,
        actor_pattern=BUILDER_ACTOR_PATTERN,
        action_pattern=BUILDER_ACTION_PATTERN,
    ):
        return 0
    if local_governance_role_responsibility_present(
        text,
        actor_pattern=REVIEW_ACTOR_PATTERN,
        action_pattern=REVIEW_ACTION_PATTERN,
    ):
        return 1
    if local_governance_role_responsibility_present(
        text,
        actor_pattern=GATEKEEPER_ACTOR_PATTERN,
        action_pattern=GATEKEEPER_ACTION_PATTERN,
    ):
        return 2
    return None


def local_governance_runtime_chain_complete(traces: list[str]) -> bool:
    text = "\n".join(str(item) for item in traces if str(item).strip())
    if not text.strip():
        return False
    builder_reads = local_governance_role_responsibility_present(
        text,
        actor_pattern=BUILDER_ACTOR_PATTERN,
        action_pattern=BUILDER_ACTION_PATTERN,
    )
    review_checks = local_governance_role_responsibility_present(
        text,
        actor_pattern=REVIEW_ACTOR_PATTERN,
        action_pattern=REVIEW_ACTION_PATTERN,
    )
    gatekeeper_gates = local_governance_role_responsibility_present(
        text,
        actor_pattern=GATEKEEPER_ACTOR_PATTERN,
        action_pattern=GATEKEEPER_ACTION_PATTERN,
    )
    return builder_reads and review_checks and gatekeeper_gates


def local_governance_candidate_chain_complete(candidates: list[object]) -> bool:
    texts = [_compact_trace_candidate(candidate) for candidate in candidates]
    builder_reads = any(
        local_governance_role_responsibility_present(
            text,
            actor_pattern=BUILDER_ACTOR_PATTERN,
            action_pattern=BUILDER_ACTION_PATTERN,
        )
        for text in texts
    )
    review_checks = any(
        local_governance_role_responsibility_present(
            text,
            actor_pattern=REVIEW_ACTOR_PATTERN,
            action_pattern=REVIEW_ACTION_PATTERN,
        )
        for text in texts
    )
    gatekeeper_gates = any(
        local_governance_role_responsibility_present(
            text,
            actor_pattern=GATEKEEPER_ACTOR_PATTERN,
            action_pattern=GATEKEEPER_ACTION_PATTERN,
        )
        for text in texts
    )
    return builder_reads and review_checks and gatekeeper_gates


def local_governance_role_responsibility_present(
    text: str,
    *,
    actor_pattern: str,
    action_pattern: str,
) -> bool:
    if not re.search(LOCAL_GOVERNANCE_MARKER_PATTERN, text, re.IGNORECASE):
        return False
    return bool(
        re.search(actor_pattern, text, re.IGNORECASE)
        and re.search(action_pattern, text, re.IGNORECASE)
    )


def local_governance_markers_present(candidates: list[object]) -> bool:
    return any(re.search(LOCAL_GOVERNANCE_MARKER_PATTERN, str(candidate or ""), re.IGNORECASE) for candidate in candidates)


def _compact_trace_candidate(candidate: object) -> str:
    return re.sub(r"\s+", " ", str(candidate or "")).strip()
