from __future__ import annotations

"""Input and text-unit helpers for bundle-control trace mining."""

import json
import re
from collections.abc import Mapping
from typing import NamedTuple

from loopora.alignment_semantics import trace_text_units


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
