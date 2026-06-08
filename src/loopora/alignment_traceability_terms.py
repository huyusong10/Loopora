from __future__ import annotations

"""Traceability term extraction for alignment agreement and Agent summaries."""

import re

from loopora.alignment_traceability_term_catalog import (
    ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS as ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS,
    ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS,
    ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS as ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS,
    ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS as ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS,
    ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS,
    ALIGNMENT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_TERMS,
)
from loopora.service_alignment_traceability_projection import normalize_alignment_traceability_text

AGENT_CANDIDATE_TASK_ANCHOR_DOMAIN_TERMS = {
    "acl",
    "aml",
    "api",
    "audit",
    "billing",
    "cache",
    "cdc",
    "chargeback",
    "chatbot",
    "citation",
    "compliance",
    "consent",
    "dispute",
    "entitlement",
    "fallback",
    "feature",
    "grounding",
    "idempotency",
    "invoice",
    "kyc",
    "ledger",
    "migration",
    "payout",
    "quota",
    "rag",
    "reconciliation",
    "replay",
    "retrieval",
    "rollback",
    "signature",
    "stripe",
    "tenant",
    "token",
    "webhook",
    "对账",
    "幂等",
    "检索",
    "账本",
    "签名",
}


def agent_candidate_traceability_terms(value: object) -> list[str]:
    text = str(value or "")
    terms = agreement_traceability_terms(value)
    for term in agreement_cjk_traceability_terms(value):
        if term not in terms:
            terms.append(term)
    if agent_candidate_ledger_term_is_internal_loopora_evidence(text):
        terms = [term for term in terms if term != "ledger"]
    return [term for term in terms if term not in ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS][:16]


def agent_candidate_task_anchor_terms(value: object) -> list[str]:
    terms = agent_candidate_traceability_terms(value)
    if not agent_candidate_task_anchor_should_be_required(value, terms=terms):
        return []
    return terms


def agent_candidate_task_anchor_should_be_required(value: object, *, terms: list[str] | None = None) -> bool:
    text = normalize_alignment_traceability_text(value)
    if not text.strip():
        return False
    candidate_terms = terms if terms is not None else agent_candidate_traceability_terms(value)
    if not candidate_terms:
        return False
    domain_terms = [term for term in AGENT_CANDIDATE_TASK_ANCHOR_DOMAIN_TERMS if _agent_candidate_domain_term_present(term, text)]
    if domain_terms:
        return True
    return len([term for term in candidate_terms if "_" not in term and "-" not in term]) >= 3


def _agent_candidate_domain_term_present(term: str, normalized_text: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", term):
        return term in normalized_text
    return bool(re.search(rf"\b{re.escape(term)}\b", normalized_text, re.IGNORECASE))


def agent_candidate_ledger_term_is_internal_loopora_evidence(text: str) -> bool:
    normalized = normalize_alignment_traceability_text(text)
    if "ledger" not in normalized:
        return False
    return bool(
        re.search(
            r"\b(?:evidence|coverage|result|output|submit(?:ted)?|non-gatekeeper|gatekeeper|refs?)\b.{0,96}\bledger\b|"
            r"\bledger\b.{0,96}\b(?:evidence|coverage|result|output|submit(?:ted)?|non-gatekeeper|gatekeeper|refs?)\b",
            normalized,
        )
    )


def agreement_traceability_terms(value: object) -> list[str]:
    text = str(value or "")
    if not text.strip():
        return []
    lowered_text = text.lower()
    markers = (
        "AGENTS.md",
        "design/README.md",
        "design/",
        "tests/",
        "package.json",
        "pyproject.toml",
    )
    terms: list[str] = [marker.lower() for marker in markers if marker.lower() in lowered_text]
    normalized = normalize_alignment_traceability_text(text)
    for raw_term in re.findall(r"[a-z0-9][a-z0-9_.-]{3,}", normalized):
        term = raw_term.strip("._-")
        if not term or term in ALIGNMENT_TRACEABILITY_GENERIC_TERMS:
            continue
        if re.fullmatch(r"\d+", term):
            continue
        if term not in terms:
            terms.append(term)
    return terms[:12]


def agreement_repeated_cjk_traceability_terms(values: object) -> list[str]:
    counts: dict[str, int] = {}
    order: dict[str, int] = {}
    for value in list(values or []):
        seen_in_value: set[str] = set()
        for term in agreement_cjk_traceability_terms(value):
            if term in seen_in_value:
                continue
            seen_in_value.add(term)
            counts[term] = counts.get(term, 0) + 1
            if term not in order:
                order[term] = len(order)
    return [term for term, count in sorted(counts.items(), key=lambda item: (-item[1], order[item[0]])) if count >= 3][:12]


def agreement_cjk_traceability_terms(value: object) -> list[str]:
    terms: list[str] = []
    for raw_sequence in re.findall(r"[\u4e00-\u9fff]{2,}", str(value or "")):
        sequence = raw_sequence.strip("".join(ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS))
        if len(sequence) < 2:
            continue
        _append_cjk_domain_terms(terms, sequence)
        for segment in _cjk_traceability_segments(sequence):
            _append_short_cjk_terms(terms, segment)
    return list(dict.fromkeys(terms))


def _append_cjk_domain_terms(terms: list[str], sequence: str) -> None:
    matches = sorted(
        (
            (sequence.index(term), -len(term), term)
            for term in ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS
            if term in sequence and term not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS
        ),
        key=lambda item: (item[0], item[1]),
    )
    terms.extend(term for _index, _length, term in matches)


def _cjk_traceability_segments(sequence: str) -> list[str]:
    split_pattern = "[" + re.escape("".join(ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS)) + "]+"
    return [
        segment
        for segment in re.split(split_pattern, sequence)
        if 2 <= len(segment) <= 4 and segment not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS
    ]


def _append_short_cjk_terms(terms: list[str], segment: str) -> None:
    if any(term in segment for term in ALIGNMENT_TRACEABILITY_CJK_DOMAIN_TERMS):
        return
    if (
        2 <= len(segment) <= 4
        and segment not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS
        and not any(char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in segment)
    ):
        terms.append(segment)
    for index in range(0, len(segment) - 1, 2):
        term = segment[index : index + 2]
        if term not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS and not any(
            char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in term
        ):
            terms.append(term)
