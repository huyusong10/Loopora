from __future__ import annotations

import re

LOCAL_GOVERNANCE_MARKER_PATTERN = r"agents\.md|design/readme\.md|design/|tests/"


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
        actor_pattern=r"\b(?:builder|generator)\b|构建者|构建",
        action_pattern=r"\b(?:read|reads|consult|consults|follow|follows|respect|respects)\b|读取|查阅|遵守|遵循",
    ):
        return 0
    if local_governance_role_responsibility_present(
        text,
        actor_pattern=r"\b(?:inspector|custom|review|reviewer)\b|检查者|巡检|检查|审查|验证",
        action_pattern=r"\b(?:verify|verifies|check|checks|review|reviews|validate|validates|test|tests)\b|检查|审查|验证|测试",
    ):
        return 1
    if local_governance_role_responsibility_present(
        text,
        actor_pattern=r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决",
        action_pattern=(
            r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects)\b"
            r"|弱证据|未证明|阻断|缺少|跳过|拒绝"
        ),
    ):
        return 2
    return None


def local_governance_runtime_chain_complete(traces: list[str]) -> bool:
    text = "\n".join(str(item) for item in traces if str(item).strip())
    if not text.strip():
        return False
    builder_reads = local_governance_role_responsibility_present(
        text,
        actor_pattern=r"\b(?:builder|generator)\b|构建者|构建",
        action_pattern=r"\b(?:read|reads|consult|consults|follow|follows|respect|respects)\b|读取|查阅|遵守|遵循",
    )
    review_checks = local_governance_role_responsibility_present(
        text,
        actor_pattern=r"\b(?:inspector|custom|review|reviewer)\b|检查者|巡检|检查|审查|验证",
        action_pattern=r"\b(?:verify|verifies|check|checks|review|reviews|validate|validates|test|tests)\b|检查|审查|验证|测试",
    )
    gatekeeper_gates = local_governance_role_responsibility_present(
        text,
        actor_pattern=r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决",
        action_pattern=(
            r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects)\b"
            r"|弱证据|未证明|阻断|缺少|跳过|拒绝"
        ),
    )
    return builder_reads and review_checks and gatekeeper_gates


def local_governance_role_responsibility_present(
    text: str,
    *,
    actor_pattern: str,
    action_pattern: str,
) -> bool:
    return bool(
        re.search(actor_pattern, text, re.IGNORECASE)
        and re.search(LOCAL_GOVERNANCE_MARKER_PATTERN, text, re.IGNORECASE)
        and re.search(action_pattern, text, re.IGNORECASE)
    )


def local_governance_markers_present(candidates: list[object]) -> bool:
    return any(re.search(LOCAL_GOVERNANCE_MARKER_PATTERN, str(candidate or ""), re.IGNORECASE) for candidate in candidates)


def _compact_trace_candidate(candidate: object) -> str:
    return re.sub(r"\s+", " ", str(candidate or "")).strip()
