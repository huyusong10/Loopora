from __future__ import annotations

import re

from loopora.alignment_readiness_shared import has_any_marker


def workdir_facts_evidence_issue(text: str, *, workdir_snapshot: str = "") -> bool:
    has_grounding_marker = has_any_marker(
        text,
        (
            "observed",
            "snapshot",
            "appears",
            "assumption",
            "assumed",
            "unknown",
            "uncertain",
            "cannot confirm",
            "empty",
            "观察",
            "看到",
            "快照",
            "看起来",
            "假设",
            "未知",
            "不确定",
            "无法确认",
            "空目录",
        ),
    )
    if not has_grounding_marker:
        return True
    return workdir_facts_claims_unsupported_observed_stack(text, workdir_snapshot=workdir_snapshot)


def workdir_facts_claims_unsupported_observed_stack(text: str, *, workdir_snapshot: str = "") -> bool:
    if not has_any_marker(text, ("observed", "snapshot", "appears", "观察", "看到", "快照", "看起来")):
        return False
    if has_any_marker(text, ("unknown", "uncertain", "assumption", "无法确认", "未知", "不确定", "假设")):
        return False
    snapshot = str(workdir_snapshot or "").lower()
    support_markers = {
        "package.json": (
            r"\breact\b",
            r"\bvue\b",
            r"\bsvelte\b",
            r"\bnext(?:\.js|js)\b",
            r"\bvite\b",
            r"\bnode(?:\.js|js)?\b",
            r"\bnpm\b",
            r"\bpnpm\b",
            r"\byarn\b",
            r"\bjavascript\b",
            r"\btypescript\b",
            r"\bfrontend\b",
            "前端",
        ),
        "pyproject.toml": (
            r"\bpython\b",
            r"\bpytest\b",
            r"\bruff\b",
            r"\buv\b",
            r"\bfastapi\b",
            r"\bdjango\b",
            r"\bflask\b",
        ),
        "requirements.txt": (r"\bpython\b", r"\bpytest\b", r"\bfastapi\b", r"\bdjango\b", r"\bflask\b"),
        "cargo.toml": (r"\brust\b", r"\bcargo\b"),
        "go.mod": (r"\bgolang\b", r"\bgo\s+(?:service|backend|app|module|project|codebase|stack|server)\b"),
    }
    unsupported_terms: list[str] = []
    for marker, terms in support_markers.items():
        if _snapshot_supports_marker(snapshot, marker):
            continue
        unsupported_terms.extend(term for term in terms if _term_has_unsupported_stack_claim(term, text))
    return bool(unsupported_terms)


def _term_has_unsupported_stack_claim(term_pattern: str, text: str) -> bool:
    for match in re.finditer(term_pattern, text):
        context = text[max(0, match.start() - 140) : match.end() + 140]
        if not has_any_marker(context, ("observed", "snapshot", "appears", "观察", "看到", "快照", "看起来")):
            continue
        if _stack_term_context_is_fake_done_or_negated(context):
            continue
        return True
    return False


def _stack_term_context_is_fake_done_or_negated(context: str) -> bool:
    return has_any_marker(
        context,
        (
            "fake done",
            "fake-done",
            "fail closed",
            "fails closed",
            "must fail",
            "must not pass",
            "cannot pass",
            "block ",
            "blocking",
            "do not accept",
            "not accept",
            "do not claim",
            "shallow",
            "frontend-only",
            "ui-only",
            "screenshot-only",
            "mock-only",
            "happy-path-only",
            "status-only",
            "prose-only",
            "missing ",
            "缺失",
            "阻断",
            "浅层",
            "只前端",
            "仅前端",
            "只.*界面",
            "solo frontend",
            "frontend-only",
        ),
    )


def _snapshot_supports_marker(snapshot: str, marker: str) -> bool:
    marker_text = marker.lower()
    marker_pattern = re.escape(marker_text)
    if re.search(rf"(?m)^\s*-\s*{marker_pattern}\s*$", snapshot):
        return True
    if re.search(rf"(?m)^\s*{marker_pattern}\s*$", snapshot):
        return True
    for line in snapshot.splitlines():
        label, separator, value = line.partition(":")
        if separator and label.strip().lower() == "detected markers":
            detected = {item.strip().lower() for item in value.split(",")}
            if marker_text in detected:
                return True
    return False
