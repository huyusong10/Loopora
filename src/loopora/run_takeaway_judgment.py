from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.run_artifacts import RunArtifactLayout
from loopora.run_takeaway_common import _string_value, clean_takeaway_text, safe_read_json_file
from loopora.service_bundle_control_trace_mining import (
    build_execution_strategy_trace,
    build_judgment_tradeoff_trace,
    build_loop_fit_trace,
    build_runtime_local_governance_trace,
)
from loopora.structured_numbers import structured_non_negative_int


def empty_judgment_contract() -> dict[str, Any]:
    return {
        "contract_path": "",
        "source_bundle": {},
        "collaboration_summary": "",
        "loop_fit_reasons": [],
        "goal": "",
        "constraints": "",
        "check_mode": "",
        "check_count": 0,
        "completion_mode": "",
        "strategy_preset": "",
        "strategy_collaboration_intent": "",
        "judgment_tradeoffs": [],
        "execution_strategy": [],
        "local_governance": [],
        "role_postures": [],
        "coverage_targets": [],
        "success_surface": [],
        "fake_done_states": [],
        "evidence_preferences": [],
        "residual_risk": "",
        "inherited_from_run_id": "",
    }


def build_judgment_contract(run: Mapping[str, Any]) -> dict[str, Any]:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if not runs_dir_value:
        return empty_judgment_contract()

    layout = RunArtifactLayout(Path(runs_dir_value))
    run_contract = safe_read_json_file(layout.run_contract_path)
    if not run_contract:
        return empty_judgment_contract()
    return normalize_judgment_contract_payload(
        run_contract,
        default_contract_path=layout.relative(layout.run_contract_path),
    )


def normalize_judgment_contract_payload(value: object, *, default_contract_path: str = "") -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    compiled_spec = raw.get("compiled_spec") if isinstance(raw.get("compiled_spec"), Mapping) else raw
    strategy_snapshot = raw.get("workflow") if isinstance(raw.get("workflow"), Mapping) else raw
    normalized = empty_judgment_contract()
    normalized["contract_path"] = _string_value(raw.get("contract_path")) or default_contract_path
    normalized["source_bundle"] = _normalize_judgment_source_bundle(raw.get("source_bundle"))
    normalized["collaboration_summary"] = clean_takeaway_text(raw.get("collaboration_summary"), max_length=600)
    normalized["loop_fit_reasons"] = _takeaway_text_list(
        raw.get("loop_fit_reasons") or build_loop_fit_trace(raw.get("collaboration_summary"))
    )
    normalized["goal"] = clean_takeaway_text(raw.get("goal") or compiled_spec.get("goal"), max_length=600)
    normalized["constraints"] = clean_takeaway_text(raw.get("constraints") or compiled_spec.get("constraints"), max_length=600)
    normalized["check_mode"] = clean_takeaway_text(raw.get("check_mode") or compiled_spec.get("check_mode"), max_length=80)
    normalized["check_count"] = structured_non_negative_int(raw.get("check_count"), default=len(list(compiled_spec.get("checks") or [])))
    normalized["completion_mode"] = clean_takeaway_text(raw.get("completion_mode"), max_length=80)
    strategy_preset = clean_takeaway_text(raw.get("strategy_preset") or strategy_snapshot.get("preset"), max_length=120)
    strategy_collaboration_intent = clean_takeaway_text(
        raw.get("strategy_collaboration_intent") or strategy_snapshot.get("collaboration_intent"),
        max_length=600,
    )
    normalized["strategy_preset"] = strategy_preset
    normalized["strategy_collaboration_intent"] = strategy_collaboration_intent
    normalized["judgment_tradeoffs"] = _takeaway_text_list(
        raw.get("judgment_tradeoffs")
        or build_judgment_tradeoff_trace(
            collaboration_summary=raw.get("collaboration_summary"),
            raw_sections=compiled_spec.get("raw_sections") if isinstance(compiled_spec, Mapping) else {},
            roles=strategy_snapshot.get("roles") if isinstance(strategy_snapshot, Mapping) else [],
            strategy_source=strategy_snapshot,
        )
    )
    normalized["execution_strategy"] = _takeaway_text_list(
        raw.get("execution_strategy")
        or build_execution_strategy_trace(
            collaboration_summary=raw.get("collaboration_summary"),
            raw_sections=compiled_spec.get("raw_sections") if isinstance(compiled_spec, Mapping) else {},
            roles=strategy_snapshot.get("roles") if isinstance(strategy_snapshot, Mapping) else [],
            strategy_source=strategy_snapshot,
        )
    )
    if "local_governance" in raw:
        normalized["local_governance"] = _takeaway_text_list(raw.get("local_governance"))
    else:
        normalized["local_governance"] = _takeaway_text_list(
            build_runtime_local_governance_trace(
                raw_sections=compiled_spec.get("raw_sections") if isinstance(compiled_spec, Mapping) else {},
                roles=strategy_snapshot.get("roles") if isinstance(strategy_snapshot, Mapping) else [],
                strategy_source=strategy_snapshot,
            )
        )
    normalized["role_postures"] = _role_posture_takeaway_list(raw.get("role_postures") or strategy_snapshot.get("roles"))
    normalized["coverage_targets"] = _takeaway_mapping_list(raw.get("coverage_targets") or compiled_spec.get("coverage_targets"))
    normalized["success_surface"] = _takeaway_text_list(raw.get("success_surface") or compiled_spec.get("success_surface"))
    normalized["fake_done_states"] = _takeaway_text_list(raw.get("fake_done_states") or compiled_spec.get("fake_done_states"))
    normalized["evidence_preferences"] = _takeaway_text_list(raw.get("evidence_preferences") or compiled_spec.get("evidence_preferences"))
    normalized["residual_risk"] = clean_takeaway_text(raw.get("residual_risk") or compiled_spec.get("residual_risk"), max_length=600)
    normalized["inherited_from_run_id"] = _string_value(raw.get("inherited_from_run_id"))
    continuation_context = raw.get("continuation_context") if isinstance(raw.get("continuation_context"), Mapping) else None
    if continuation_context:
        normalized["inherited_from_run_id"] = _string_value(continuation_context.get("previous_run_id")) or normalized["inherited_from_run_id"]
    return normalized


def _normalize_judgment_source_bundle(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    bundle_id = _string_value(value.get("id"))
    if not bundle_id:
        return {}
    source = {
        "id": bundle_id,
        "name": clean_takeaway_text(value.get("name"), max_length=240),
        "revision": structured_non_negative_int(value.get("revision")),
        "source_bundle_id": _string_value(value.get("source_bundle_id")),
        "imported_from_path": _string_value(value.get("imported_from_path")),
    }
    bundle_sha256 = _string_value(value.get("bundle_sha256"))
    bundle_bytes = structured_non_negative_int(value.get("bundle_bytes"))
    bundle_yaml_path = _string_value(value.get("bundle_yaml_path"))
    if bundle_sha256:
        source["bundle_sha256"] = bundle_sha256
    if bundle_bytes:
        source["bundle_bytes"] = bundle_bytes
    if bundle_yaml_path:
        source["bundle_yaml_path"] = bundle_yaml_path
    return source


def _takeaway_text_list(value: object, *, max_items: int = 4, max_length: int = 240) -> list[str]:
    if not isinstance(value, list):
        return []
    texts = [clean_takeaway_text(item, max_length=max_length) for item in value]
    return [text for text in texts if text][:max_items]


def _takeaway_mapping_list(value: object, *, max_items: int = 40) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)][:max_items]


def _role_posture_takeaway_list(value: object, *, max_items: int = 6, max_length: int = 300) -> list[str]:
    if not isinstance(value, list):
        return []
    summaries: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            posture = clean_takeaway_text(item.get("posture_notes"), max_length=max_length)
            if not posture:
                continue
            role_name = clean_takeaway_text(item.get("role_name") or item.get("name"), max_length=80)
            archetype = clean_takeaway_text(item.get("archetype"), max_length=40)
            label = role_name or archetype
            if label and archetype and archetype not in label.lower():
                label = f"{label} ({archetype})"
            summaries.append(f"{label}: {posture}" if label else posture)
            continue
        text = clean_takeaway_text(item, max_length=max_length)
        if text:
            summaries.append(text)
    return summaries[:max_items]
