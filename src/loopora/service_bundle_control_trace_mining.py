from __future__ import annotations

"""Text mining helpers for bundle control trace projections."""

import re

from loopora.alignment_semantics import loop_fit_governance_trace
from loopora.residual_risk_support import residual_risk_is_unmanaged
from loopora.service_bundle_control_local_governance import (
    local_governance_candidate_chain_complete,
    local_governance_markers_present as local_governance_markers_present_for_candidates,
    local_governance_runtime_chain_complete as local_governance_runtime_chain_complete,
    select_local_governance_trace,
)
from loopora.service_bundle_control_trace_inputs import (
    TraceTextSource as TraceTextSource,
    compact_trace_candidate as _compact_trace_candidate,
    strategy_source_payload as strategy_source_payload,
    trace_input_payloads as _trace_input_payloads,
    trace_text_candidates as _trace_text_candidates,
    trace_text_source as _trace_text_source,
)
from loopora.service_bundle_control_trace_patterns import (
    EXECUTION_STRATEGY_PATTERNS,
    HIGH_SIGNAL_TRADEOFF_PATTERNS,
    TRADEOFF_PATTERNS,
)
from loopora.service_bundle_control_trace_preview import preview_list_items as preview_list_items


def build_judgment_tradeoff_trace(
    *,
    collaboration_summary: object = "",
    raw_sections: object = None,
    roles: object = None,
    strategy_source: object = None,
    workflow: object = None,
) -> list[str]:
    raw_sections_payload, role_items, strategy_payload = _trace_input_payloads(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
        workflow=workflow,
    )
    return _judgment_tradeoff_trace(
        bundle={"collaboration_summary": collaboration_summary},
        raw_sections=raw_sections_payload,
        roles=role_items,
        strategy_source=strategy_payload,
    )


def build_execution_strategy_trace(
    *,
    collaboration_summary: object = "",
    raw_sections: object = None,
    roles: object = None,
    strategy_source: object = None,
    workflow: object = None,
) -> list[str]:
    raw_sections_payload, role_items, strategy_payload = _trace_input_payloads(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
        workflow=workflow,
    )
    return _execution_strategy_trace(
        bundle={"collaboration_summary": collaboration_summary},
        raw_sections=raw_sections_payload,
        roles=role_items,
        strategy_source=strategy_payload,
    )


def build_local_governance_trace(
    *,
    collaboration_summary: object = "",
    raw_sections: object = None,
    roles: object = None,
    strategy_source: object = None,
    workflow: object = None,
) -> list[str]:
    raw_sections_payload, role_items, strategy_payload = _trace_input_payloads(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
        workflow=workflow,
    )
    return _local_governance_trace(
        bundle={"collaboration_summary": collaboration_summary},
        raw_sections=raw_sections_payload,
        roles=role_items,
        strategy_source=strategy_payload,
    )


def build_runtime_local_governance_trace(
    *,
    raw_sections: object = None,
    roles: object = None,
    strategy_source: object = None,
    workflow: object = None,
) -> list[str]:
    raw_sections_payload, role_items, strategy_payload = _trace_input_payloads(
        raw_sections=raw_sections,
        roles=roles,
        strategy_source=strategy_source,
        workflow=workflow,
    )
    source = _trace_text_source(bundle={}, raw_sections=raw_sections_payload, roles=role_items, strategy_source=strategy_payload)
    candidates = _local_governance_runtime_candidates(source)
    if not local_governance_candidate_chain_complete(candidates):
        return []
    return select_local_governance_trace(candidates)


def build_loop_fit_trace(collaboration_summary: object = "") -> list[str]:
    return loop_fit_governance_trace(collaboration_summary)


def build_residual_risk_policy_trace(raw_sections: dict) -> list[str]:
    residual_risk = str(raw_sections.get("Residual Risk") or "").strip()
    if not residual_risk or residual_risk_is_unmanaged(residual_risk):
        return []
    return preview_list_items(residual_risk, limit=3)


def _judgment_tradeoff_trace(
    *,
    bundle: dict,
    raw_sections: dict,
    roles: list[dict],
    strategy_source: dict,
) -> list[str]:
    traces: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    source = _trace_text_source(bundle=bundle, raw_sections=raw_sections, roles=roles, strategy_source=strategy_source)
    for index, candidate in enumerate(_trace_text_candidates(source)):
        compact = _compact_trace_candidate(candidate)
        if not compact or compact.lower() in seen:
            continue
        if not any(re.search(pattern, compact, re.IGNORECASE) for pattern in TRADEOFF_PATTERNS):
            continue
        seen.add(compact.lower())
        traces.append((_tradeoff_trace_priority(compact), index, compact[:240].rstrip() + ("..." if len(compact) > 240 else "")))
    return [trace for _priority, _index, trace in sorted(traces, key=lambda item: (item[0], item[1]))[:4]]


def _tradeoff_trace_priority(text: str) -> int:
    if re.search(r"\btradeoff\s*:|判断取舍\s*[:：]|取舍\s*[:：]", text, re.IGNORECASE):
        return -1
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in HIGH_SIGNAL_TRADEOFF_PATTERNS):
        return 0
    if re.search(r"\bprefer\b|优先|先于|高于", text, re.IGNORECASE):
        return 1
    return 2


def _execution_strategy_trace(
    *,
    bundle: dict,
    raw_sections: dict,
    roles: list[dict],
    strategy_source: dict,
) -> list[str]:
    traces: list[str] = []
    seen: set[str] = set()
    source = _trace_text_source(bundle=bundle, raw_sections=raw_sections, roles=roles, strategy_source=strategy_source)
    for candidate in _trace_text_candidates(source, include_step_inputs=True):
        compact = _compact_trace_candidate(candidate)
        if not compact or compact.lower() in seen:
            continue
        if not any(re.search(pattern, compact, re.IGNORECASE) for pattern in EXECUTION_STRATEGY_PATTERNS):
            continue
        seen.add(compact.lower())
        traces.append(compact[:240].rstrip() + ("..." if len(compact) > 240 else ""))
        if len(traces) >= 4:
            break
    return traces


def _local_governance_trace(
    *,
    bundle: dict,
    raw_sections: dict,
    roles: list[dict],
    strategy_source: dict,
    runtime_only: bool = False,
) -> list[str]:
    source = _trace_text_source(bundle=bundle, raw_sections=raw_sections, roles=roles, strategy_source=strategy_source)
    return select_local_governance_trace(
        _trace_text_candidates(source, include_step_inputs=True, runtime_only=runtime_only)
    )


def _local_governance_runtime_candidates(source: TraceTextSource) -> list[str]:
    candidates = _role_context_trace_candidates(source.roles)
    candidates.extend(_trace_text_candidates(source, include_step_inputs=True, runtime_only=True))
    return candidates


def _role_context_trace_candidates(roles: list[dict]) -> list[str]:
    candidates: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        role_context = _role_context_label(role)
        for field in ("posture_notes", "prompt_markdown", "description"):
            role_source = str(role.get(field) or "").strip()
            if not role_source:
                continue
            role_units = _trace_text_candidates(
                _trace_text_source(bundle={}, raw_sections={}, roles=[{field: role_source}], strategy_source={})
            )
            candidates.extend(f"{role_context}: {unit}" for unit in role_units if str(unit or "").strip())
    return candidates


def _role_context_label(role: dict) -> str:
    for field_name in ("name", "key", "archetype"):
        label = str(role.get(field_name) or "").strip()
        if label:
            return label
    return "role"


def local_governance_markers_present(
    *,
    bundle: dict,
    raw_sections: dict,
    roles: list[dict],
    strategy_source: dict,
) -> bool:
    source = _trace_text_source(bundle=bundle, raw_sections=raw_sections, roles=roles, strategy_source=strategy_source)
    return local_governance_markers_present_for_candidates(
        _trace_text_candidates(source, include_step_inputs=True, runtime_only=False)
    )
