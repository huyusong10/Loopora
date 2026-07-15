from __future__ import annotations

"""Small, language-neutral term extraction for task and agreement traceability."""

import re

from loopora.service_alignment_traceability_projection import normalize_alignment_traceability_text


ALIGNMENT_TRACEABILITY_GENERIC_TERMS = frozenset(
    {
        "agent",
        "alignment",
        "artifact",
        "builder",
        "bundle",
        "check",
        "context",
        "evidence",
        "gatekeeper",
        "governance",
        "handoff",
        "inspector",
        "loop",
        "loopora",
        "proof",
        "result",
        "risk",
        "role",
        "step",
        "task",
        "test",
        "verdict",
        "workflow",
        "workdir",
    }
)
ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS = ALIGNMENT_TRACEABILITY_GENERIC_TERMS | {
    "blocking",
    "proven",
    "residual",
    "unproven",
    "weak",
}
ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS = frozenset(
    {"direct", "feedback", "final", "multiple", "round", "single"}
)
ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS = frozenset(
    {"任务", "证据", "角色", "工作", "流程", "检查", "实现", "用户", "结果", "风险", "修复", "裁决"}
)
ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS = frozenset("的一是在和与或及并但而为由让把被只已未就才需能会应可其此个这那")

_PATH_MARKERS = (
    "AGENTS.md",
    "design/README.md",
    "design/",
    "tests/",
    "package.json",
    "pyproject.toml",
)


def agreement_traceability_terms(value: object) -> list[str]:
    text = str(value or "")
    if not text.strip():
        return []
    lowered = text.lower()
    terms = [marker.lower() for marker in _PATH_MARKERS if marker.lower() in lowered]
    normalized = normalize_alignment_traceability_text(text)
    for raw_term in re.findall(r"[a-z0-9][a-z0-9_.-]{3,}", normalized):
        term = raw_term.strip("._-")
        if not term or term in ALIGNMENT_TRACEABILITY_GENERIC_TERMS or term.isdigit():
            continue
        if term not in terms:
            terms.append(term)
    return terms[:12]


def agreement_cjk_traceability_terms(value: object) -> list[str]:
    terms: list[str] = []
    for sequence in re.findall(r"[\u4e00-\u9fff]{2,}", str(value or "")):
        clean = "".join(char for char in sequence if char not in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS)
        if 2 <= len(clean) <= 4 and clean not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS:
            terms.append(clean)
        for index in range(0, len(clean) - 1, 2):
            term = clean[index : index + 2]
            if term not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS:
                terms.append(term)
    return list(dict.fromkeys(terms))[:12]


def agreement_repeated_cjk_traceability_terms(values: object) -> list[str]:
    counts: dict[str, int] = {}
    order: dict[str, int] = {}
    for value in list(values or []):
        for term in set(agreement_cjk_traceability_terms(value)):
            counts[term] = counts.get(term, 0) + 1
            order.setdefault(term, len(order))
    return [
        term
        for term, count in sorted(counts.items(), key=lambda item: (-item[1], order[item[0]]))
        if count >= 3
    ][:12]


def agent_candidate_traceability_terms(value: object) -> list[str]:
    text = str(value or "")
    terms = agreement_traceability_terms(text)
    terms.extend(term for term in agreement_cjk_traceability_terms(text) if term not in terms)
    if agent_candidate_ledger_term_is_internal_loopora_evidence(text):
        terms = [term for term in terms if term != "ledger"]
    return [term for term in terms if term not in ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS][:16]


def agent_candidate_task_anchor_terms(value: object) -> list[str]:
    terms = agent_candidate_traceability_terms(value)
    return terms if agent_candidate_task_anchor_should_be_required(value, terms=terms) else []


def agent_candidate_task_anchor_should_be_required(value: object, *, terms: list[str] | None = None) -> bool:
    if not normalize_alignment_traceability_text(value).strip():
        return False
    candidate_terms = terms if terms is not None else agent_candidate_traceability_terms(value)
    return len(candidate_terms) >= 2


def agent_candidate_ledger_term_is_internal_loopora_evidence(text: str) -> bool:
    normalized = normalize_alignment_traceability_text(text)
    if "ledger" not in normalized:
        return False
    return bool(
        re.search(
            r"\b(?:evidence|coverage|result|output|submit(?:ted)?|gatekeeper|refs?)\b.{0,96}\bledger\b|"
            r"\bledger\b.{0,96}\b(?:evidence|coverage|result|output|submit(?:ted)?|gatekeeper|refs?)\b",
            normalized,
        )
    )
