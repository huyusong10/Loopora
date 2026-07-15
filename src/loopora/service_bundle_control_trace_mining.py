from __future__ import annotations

import re

from loopora.alignment_semantics import trace_text_units

def preview_list_items(markdown_text: str, *, limit: int = 4) -> list[str]:
    items = []
    for line in str(markdown_text or "").splitlines():
        cleaned = re.sub(r"^\s*[-*]\s+", "", line).strip()
        cleaned = re.sub(r"^\s*\d+[.)]\s+", "", cleaned).strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        items.append(cleaned)
        if len(items) >= limit:
            break
    if items:
        return items
    compact = re.sub(r"\s+", " ", str(markdown_text or "")).strip()
    return [compact[:180]] if compact else []

def build_role_posture_trace(roles: list[dict]) -> list[str]:
    traces: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        role_name = str(role.get("name") or role.get("key") or "").strip()
        archetype = str(role.get("archetype") or "").strip()
        posture = role_posture_preview(role)
        if posture and (role_name or archetype):
            base = f"{role_name or 'Role'} ({archetype or 'custom'})"
            traces.append(f"{base}: {posture}")
    return traces[:4]

def role_posture_preview(role: dict) -> str:
    for field in ("posture_notes", "description", "prompt_markdown"):
        for unit in trace_text_units(str(role.get(field) or "")):
            compact = re.sub(r"\s+", " ", unit).strip()
            if not compact or _role_prompt_mechanics_unit(compact):
                continue
            return compact[:180].rstrip() + ("..." if len(compact) > 180 else "")
    return ""

def _role_prompt_mechanics_unit(text: str) -> bool:
    return bool(re.fullmatch(r"(?:version|archetype)\s*:\s*.+", text.strip(), re.IGNORECASE))

"""Regex pattern catalogs for bundle-control trace mining."""

TRADEOFF_PATTERNS = (
    r"\bprefer\b.{0,120}\b(over|rather than|instead of|before|to)\b",
    r"\b(rather than|instead of)\b",
    r"\b(reject|block|fail closed)\b.{0,120}\b(when|if|over|rather than|instead|weak|speed|proof|evidence|fake[- ]done)\b",
    r"\b(proof|evidence)\b.{0,80}\b(before|over|beats?|wins?|must beat|higher than|above)\b.{0,80}\b(speed|polish|surface|breadth|completion|progress)\b",
    r"\b(speed|polish|surface completeness|progress)\b.{0,80}\b(loses?|must lose|rejected|blocked)\b.{0,80}\b(proof|evidence)\b",
    r"\b(strict|blocking|block|reject|fail closed)\b.{0,80}\b(before|over|beats?|wins?|rather than|instead of)\b.{0,80}\b(pragmatic|pragmatism|progress)\b",
    r"\b(pragmatic|pragmatism|progress)\b.{0,80}\b(loses?|must lose|wait|after|behind|rather than|instead of)\b.{0,80}\b(strict|blocking|block|reject|fail closed)\b",
    r"\bpreferir\b.{0,120}\b(?:sobre|antes que|frente a)\b",
    r"\bvelocidad\b.{0,80}\b(?:pierde|cede|debe perder)\b.{0,80}\b(?:evidencia|prueba|bloqueo|estricto)\b",
    r"\b(?:bloquear|rechazar|fallar cerrado|falla cerrado)\b.{0,120}\b(?:evidencia|prueba|falso terminado|no probado|débil)\b",
    r"(优先|先).{0,80}(而不是|不是|先于|高于|超过|证明|证据|阻断|拒绝)",
    r"(而不是|先于|高于)",
    r"(拒绝|阻断|失败关闭).{0,80}(速度|美化|漂亮|证据|证明|假完成|未证明|薄弱|不足)",
    r"(证据|证明).{0,80}(优先|先于|高于).{0,80}(速度|进度|美化|漂亮|完整)",
    r"(严格|阻断|拒绝).{0,80}(优先|先于|高于|超过|胜过).{0,80}(务实|推进|进度)",
    r"(务实|推进|进度).{0,80}(让位|低于|后于|等待).{0,80}(严格|阻断|拒绝)",
)

HIGH_SIGNAL_TRADEOFF_PATTERNS = (
    r"\b(proof|evidence)\b.{0,80}\b(before|over|beats?|wins?|must beat|higher than|above)\b.{0,80}\b(speed|polish|surface|breadth|completion|progress)\b",
    r"\b(speed|polish|surface completeness|progress)\b.{0,80}\b(loses?|must lose|rejected|blocked)\b.{0,80}\b(proof|evidence)\b",
    r"\b(strict|blocking|block|reject|fail closed)\b.{0,80}\b(before|over|beats?|wins?|rather than|instead of)\b.{0,80}\b(pragmatic|pragmatism|progress)\b",
    r"\b(pragmatic|pragmatism|progress)\b.{0,80}\b(loses?|must lose|wait|after|behind|rather than|instead of)\b.{0,80}\b(strict|blocking|block|reject|fail closed)\b",
    r"\b(reject|block|fail closed)\b.{0,120}\b(weak|proof|evidence|fake[- ]done|unproven|completion)\b",
    r"\bvelocidad\b.{0,80}\b(?:pierde|cede|debe perder)\b.{0,80}\b(?:evidencia|prueba|bloqueo|estricto)\b",
    r"\b(?:bloquear|rechazar|fallar cerrado|falla cerrado)\b.{0,120}\b(?:evidencia|prueba|falso terminado|no probado|débil)\b",
    r"(证据|证明).{0,80}(优先|先于|高于).{0,80}(速度|进度|美化|漂亮|完整)",
    r"(严格|阻断|拒绝).{0,80}(优先|先于|高于|超过|胜过).{0,80}(务实|推进|进度)",
    r"(务实|推进|进度).{0,80}(让位|低于|后于|等待).{0,80}(严格|阻断|拒绝)",
    r"(拒绝|阻断|失败关闭).{0,80}(假完成|未证明|薄弱|不足)",
)

EXECUTION_STRATEGY_PATTERNS = (
    r"\b(?:execution\s+priorit(?:y|ies)|order\s+of\s+attack|priority\s+order)\b.{0,140}\b(?:build|implement|prove|proof|evidence|repair|fix|narrow|scope|expand|polish|closure|gatekeeper|inspect|review)\b",
    r"\b(?:build|implement|prove|proof|evidence|repair|fix|narrow|scope|expand|polish|inspect|review)\b.{0,140}\b(?:execution\s+priorit(?:y|ies)|order\s+of\s+attack|priority\s+order)\b",
    r"\b(?:first|next|then|before|after|defer|postpone|hold off|delay|pause|prioriti[sz]e)\b.{0,120}\b(?:build|prove|evidence|repair|fix|narrow|scope|expand|polish|closure|gatekeeper|inspect|review)\b",
    r"\b(?:build|prove|gather|collect|repair|fix|narrow|scope|expand|polish|inspect|review)\b.{0,120}\b(?:first|next|then|before|after|defer|postpone|hold off|delay|pause|prioriti[sz]e)\b",
    r"\b(?:root cause|primary flow|focused slice|smallest real flow|direct proof|evidence gap|weak proof)\b.{0,120}\b(?:first|before|defer|repair|narrow|expand|polish)\b",
    r"\b(?:future|later|next)\s+(?:rounds?|iterations?|passes?)\b.{0,120}\b(?:build|prove|evidence|repair|narrow|expand|defer|polish)\b",
    r"\b(?:construir|implementar|probar|reparar|acotar|ampliar|diferir|inspeccionar|revisar)\b.{0,140}\b(?:primero|despu[eé]s|luego|antes|priorizar|prioridad|estrategia|ejecuci[oó]n)\b",
    r"\b(?:primero|despu[eé]s|luego|antes|priorizar|prioridad|estrategia|ejecuci[oó]n)\b.{0,140}\b(?:construir|implementar|probar|evidencia|reparar|acotar|ampliar|diferir|inspeccionar|revisar)\b",
    r"\b(?:cierre real m[ií]nimo|ruta negativa|evidencia d[eé]bil|brecha de evidencia)\b.{0,120}\b(?:primero|reparar|acotar|inspeccionar|cerrar)\b",
    r"(?:先|首先|下一轮|下一步|再|然后|之后|暂缓|推迟|先别|不要先|优先).{0,80}(?:构建|实现|证明|取证|证据|修复|根因|收窄|范围|扩展|打磨|美化|裁决)",
    r"(?:构建|实现|证明|取证|证据|修复|根因|收窄|范围|扩展|打磨|美化|裁决).{0,80}(?:先|首先|下一轮|下一步|再|然后|之后|暂缓|推迟|先别|不要先|优先)",
)

"""Input and text-unit helpers for bundle-control trace mining."""

import json


from collections.abc import Mapping

from typing import NamedTuple


class TraceTextSource(NamedTuple):
    bundle: dict
    raw_sections: dict
    roles: list[dict]
    strategy_source: dict

def strategy_source_payload(*, strategy_source: object = None, workflow: object = None) -> dict:
    payload = strategy_source if isinstance(strategy_source, Mapping) else workflow
    return dict(payload) if isinstance(payload, Mapping) else {}

def trace_input_payloads(
    *,
    raw_sections: object = None,
    roles: object = None,
    strategy_source: object = None,
    workflow: object = None,
) -> tuple[dict, list[dict], dict]:
    raw_sections_payload = dict(raw_sections) if isinstance(raw_sections, Mapping) else {}
    role_items = [dict(role) for role in list(roles or []) if isinstance(role, Mapping)] if isinstance(roles, list) else []
    strategy_payload = strategy_source_payload(strategy_source=strategy_source, workflow=workflow)
    return raw_sections_payload, role_items, strategy_payload

def trace_text_candidates(
    source: TraceTextSource,
    *,
    include_step_inputs: bool = False,
    runtime_only: bool = False,
) -> list[str]:
    candidates: list[str] = []
    for text in _trace_text_blocks(
        source,
        include_step_inputs=include_step_inputs,
        runtime_only=runtime_only,
    ):
        candidates.extend(trace_text_units(text))
    return candidates

def _trace_text_blocks(
    source: TraceTextSource,
    *,
    include_step_inputs: bool = False,
    runtime_only: bool = False,
) -> list[str]:
    text_blocks: list[str] = []
    if runtime_only:
        text_blocks.append(str(source.raw_sections.get("Role Notes") or ""))
    else:
        text_blocks.append(str(source.bundle.get("collaboration_summary") or ""))
        text_blocks.extend(str(value or "") for value in source.raw_sections.values())
    _append_role_text_blocks(text_blocks, source.roles)
    text_blocks.append(str(source.strategy_source.get("collaboration_intent") or ""))
    if include_step_inputs:
        _append_strategy_step_input_blocks(text_blocks, source.strategy_source)
    return text_blocks

def _append_role_text_blocks(text_blocks: list[str], roles: list[dict]) -> None:
    for role in roles:
        if not isinstance(role, dict):
            continue
        text_blocks.extend(
            [
                str(role.get("posture_notes") or ""),
                str(role.get("prompt_markdown") or ""),
                str(role.get("description") or ""),
            ]
        )

def _append_strategy_step_input_blocks(text_blocks: list[str], strategy_source: dict) -> None:
    for step in list(strategy_source.get("steps") or []):
        if isinstance(step, Mapping):
            inputs = step.get("inputs")
            if isinstance(inputs, Mapping) and inputs:
                text_blocks.append(_json_dumps_compact(inputs))

def compact_trace_candidate(candidate: object) -> str:
    return re.sub(r"\s+", " ", str(candidate or "")).strip()

def trace_text_source(*, bundle: dict, raw_sections: dict, roles: list[dict], strategy_source: dict) -> TraceTextSource:
    return TraceTextSource(bundle=bundle, raw_sections=raw_sections, roles=roles, strategy_source=strategy_source)

def _json_dumps_compact(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(value or "")

_compact_trace_candidate = compact_trace_candidate
_trace_input_payloads = trace_input_payloads
_trace_text_candidates = trace_text_candidates
_trace_text_source = trace_text_source

"""Text mining helpers for bundle control trace projections."""


from loopora.alignment_semantics import loop_fit_governance_trace
from loopora.residual_risk_support import residual_risk_is_unmanaged
from loopora.service_bundle_control_local_governance import (
    local_governance_candidate_chain_complete,
    local_governance_markers_present as local_governance_markers_present_for_candidates,
    local_governance_runtime_chain_complete as local_governance_runtime_chain_complete,
    select_local_governance_trace,
)


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
