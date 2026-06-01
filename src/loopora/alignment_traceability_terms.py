from __future__ import annotations

"""Traceability term extraction for alignment agreement and Agent summaries."""

import re

from loopora.alignment_traceability_term_catalog import (
    ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS as ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS,
    ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS,
    ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS as ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS,
    ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS,
    ALIGNMENT_TRACEABILITY_GENERIC_TERMS as ALIGNMENT_TRACEABILITY_GENERIC_TERMS,
)
from loopora.service_alignment_traceability_projection import normalize_alignment_traceability_text


def agent_candidate_traceability_terms(value: object) -> list[str]:
    terms = agreement_traceability_terms(value)
    for term in agreement_cjk_traceability_terms(value):
        if term not in terms:
            terms.append(term)
    return [term for term in terms if term not in ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS][:12]


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
        if (
            2 <= len(sequence) <= 4
            and sequence not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS
            and not any(char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in sequence)
        ):
            terms.append(sequence)
        for index in range(0, len(sequence) - 1, 2):
            term = sequence[index : index + 2]
            if term not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS and not any(
                char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in term
            ):
                terms.append(term)
    return list(dict.fromkeys(terms))
