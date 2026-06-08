from __future__ import annotations

import re

from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot_has_governance_markers


GOVERNANCE_MARKER_PATTERN = (
    r"agents\.md|design/readme\.md|design/|tests/|project-local|project local|"
    r"local\s+design/test|design/test\s+obligations?|skipped\s+local\s+governance|项目本地"
)


def local_governance_evidence_issue(text: str, *, workdir_snapshot: str = "") -> bool:
    if not re.search(GOVERNANCE_MARKER_PATTERN, text, re.IGNORECASE) and not alignment_workdir_snapshot_has_governance_markers(
        workdir_snapshot
    ):
        return False
    return not alignment_governance_marker_responsibilities_present(text)


def alignment_governance_marker_responsibilities_present(text: str) -> bool:
    builder_reads = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:builder|generator)\b|构建者|构建|执行方|实施方",
        action_pattern=(
            r"\b(?:read|reads|consult|consults|follow|follows|respect|respects|use|uses|using|locate|locates|identify|identifies)\b"
            r"|读取|查阅|查找|定位|识别|遵守|遵循|使用|读"
        ),
    )
    review_checks = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:inspector|inspectors|custom|review|reviewer|reviewers)\b|检查者|巡检|检查|审查|验证|检视方|评审方",
        action_pattern=r"\b(?:verify|verifies|verification|check|checks|review|reviews|validate|validates|test|tests)\b|检查|审查|验证|测试|核对",
    )
    gatekeeper_gates = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决|最终判断|最终裁决|收口|验收",
        action_pattern=(
            r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects|gate|gates|gating)\b"
            r"|弱证据|未证明|阻断|缺少|跳过|拒绝|视为"
        ),
    )
    return builder_reads and review_checks and gatekeeper_gates


def alignment_governance_marker_responsibility_present(
    text: str,
    *,
    actor_pattern: str,
    action_pattern: str,
) -> bool:
    segments = re.split(r"[\n.;。；]+", text)
    marker_windows: list[str] = []
    for match in re.finditer(GOVERNANCE_MARKER_PATTERN, text, flags=re.IGNORECASE):
        start = max(0, match.start() - 320)
        end = min(len(text), match.end() + 320)
        marker_windows.append(text[start:end])
    for segment in [*segments, *marker_windows]:
        if (
            re.search(GOVERNANCE_MARKER_PATTERN, segment, flags=re.IGNORECASE)
            and re.search(actor_pattern, segment, flags=re.IGNORECASE)
            and re.search(action_pattern, segment, flags=re.IGNORECASE)
        ):
            return True
    return False
