from __future__ import annotations

from pathlib import Path
import re
import shlex
from typing import Any

from loopora.agent_adapters import prefix_loopora_command
from loopora.agent_native_guidance import actionable_blocking_item as _shared_actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _shared_actionable_next_action
from loopora.agent_native_guidance import coverage_target_blocker_explanation as _shared_coverage_target_blocker_explanation
from loopora.evidence_support import evidence_item_is_supporting_gatekeeper_ref
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int


def _agent_native_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _agent_native_previous_blocked_handoff(previous_summary: dict[str, Any]) -> dict[str, Any]:
    handoffs = previous_summary.get("step_handoffs")
    if not isinstance(handoffs, list):
        return {}
    for handoff in reversed(handoffs):
        if not isinstance(handoff, dict):
            continue
        status = str(handoff.get("status") or "").strip()
        if status == "blocked" or _agent_native_string_list(handoff.get("blocking_items")):
            return handoff
    return {}


def _agent_native_actionable_blocking_item(item: str) -> str:
    return _shared_actionable_blocking_item(item)


def _agent_native_coverage_target_blocker_explanation(cleaned: str) -> str:
    return _shared_coverage_target_blocker_explanation(cleaned)


def _agent_native_actionable_repair_next_action(action: str, blocking_items: list[str]) -> str:
    return _shared_actionable_next_action(action, blocking_items)


_REPAIR_TARGET_TOKEN_RE = re.compile(
    r"\b(?:check_\d+|done_when\.check_\d+|fake_done\.risk_\d+|evidence_preference\.pref_\d+|success_surface\.surface_\d+|gatekeeper\.finish)\b"
)


def _agent_native_repair_target_tokens(top_gaps: list[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for gap in top_gaps:
        target_id = str(gap.get("target_id") or "").strip().lower()
        if not target_id:
            continue
        tokens.add(target_id)
        if "." in target_id:
            tokens.add(target_id.rsplit(".", 1)[-1])
    return tokens


def _agent_native_blocking_target_tokens(blocking_items: list[str]) -> set[str]:
    tokens: set[str] = set()
    for item in blocking_items:
        for match in _REPAIR_TARGET_TOKEN_RE.findall(str(item or "").lower()):
            tokens.add(match)
            if "." in match:
                tokens.add(match.rsplit(".", 1)[-1])
    return tokens


def _agent_native_repair_blockers_still_current(blocking_items: list[str], top_gaps: list[dict[str, Any]]) -> bool:
    blocker_tokens = _agent_native_blocking_target_tokens(blocking_items)
    if not blocker_tokens:
        return True
    return bool(blocker_tokens & _agent_native_repair_target_tokens(top_gaps))


def _agent_native_current_gap_repair_next_action(top_gaps: list[dict[str, Any]]) -> str:
    if not top_gaps:
        return "Continue with the newly supporting evidence before asking GateKeeper to pass again."
    return "Continue from the current coverage gaps instead of repeating the resolved previous blocker before asking GateKeeper to pass again."


def _agent_native_submit_command(
    *,
    adapter: str,
    run_id: str,
    step_id: str,
    entry_source: str = "",
    result_file: str = "RESULT_JSON_PATH",
) -> str:
    bits = [
        "loopora",
        "agent",
        adapter,
        "submit",
        "--workdir",
        _agent_native_command_workdir_arg(result_file),
        "--run-id",
        shlex.quote(run_id),
        "--step-id",
        shlex.quote(step_id),
        "--result-file",
        shlex.quote(str(result_file or "RESULT_JSON_PATH")),
        "--json",
    ]
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def _agent_native_command_workdir_arg(result_file: str) -> str:
    text = str(result_file or "").strip()
    if not text or text == "RESULT_JSON_PATH":
        return '"$PWD"'
    try:
        path = Path(text).expanduser()
        if not path.is_absolute():
            return '"$PWD"'
        parts = path.parts
        if ".loopora" in parts:
            loopora_index = parts.index(".loopora")
            if loopora_index > 0:
                return shlex.quote(str(Path(*parts[:loopora_index]).resolve()))
    except OSError:
        return '"$PWD"'
    return '"$PWD"'


def _agent_native_result_artifact_stem(*, run_id: str, iter_id: int, step_order: int, step_id: str) -> str:
    return f"{run_id}__iter{iter_id:03d}__step{step_order:02d}__{step_id}"


def _agent_native_capsule_has_step_position(capsule: dict[str, Any]) -> bool:
    return (
        isinstance(capsule.get("iter"), int)
        and not isinstance(capsule.get("iter"), bool)
        and isinstance(capsule.get("step_order"), int)
        and not isinstance(capsule.get("step_order"), bool)
    )


def _agent_native_path_parent(path_value: object) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    return str(Path(text).parent)


def _agent_native_submit_hint_with_scoped_result_paths(
    submit_hint: dict[str, Any],
    capsule: dict[str, Any],
    *,
    run_id: str,
    step_id: str,
) -> dict[str, Any]:
    if not _agent_native_capsule_has_step_position(capsule):
        return submit_hint
    scoped_hint = dict(submit_hint)
    result_stem = _agent_native_result_artifact_stem(
        run_id=run_id,
        iter_id=structured_non_negative_int(capsule.get("iter")),
        step_order=structured_non_negative_int(capsule.get("step_order")),
        step_id=step_id,
    )
    _agent_native_set_scoped_result_paths(
        scoped_hint,
        dir_key="result_outbox_absolute_dir",
        template_key="result_template_absolute_path",
        result_key="result_file_absolute_path",
        result_stem=result_stem,
    )
    _agent_native_set_scoped_result_paths(
        scoped_hint,
        dir_key="result_outbox_dir",
        template_key="result_template_path",
        result_key="result_file_path",
        result_stem=result_stem,
    )
    return scoped_hint


def _agent_native_set_scoped_result_paths(
    submit_hint: dict[str, Any],
    *,
    dir_key: str,
    template_key: str,
    result_key: str,
    result_stem: str,
) -> None:
    outbox_dir = str(submit_hint.get(dir_key) or "").strip()
    if not outbox_dir:
        outbox_dir = _agent_native_path_parent(submit_hint.get(template_key) or submit_hint.get(result_key))
    if not outbox_dir:
        return
    outbox = Path(outbox_dir)
    submit_hint[dir_key] = str(outbox)
    submit_hint[result_key] = str(outbox / f"{result_stem}.result.json")
    submit_hint[template_key] = str(outbox / f"{result_stem}.result.template.json")


def _agent_native_role_posture_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    postures: list[str] = []
    for item in value:
        if isinstance(item, dict):
            posture = str(item.get("posture_notes") or "").strip()
            if not posture:
                continue
            role_name = str(item.get("role_name") or item.get("name") or "").strip()
            archetype = str(item.get("archetype") or "").strip()
            label = role_name or archetype
            if label and archetype and archetype not in label.lower():
                label = f"{label} ({archetype})"
            postures.append(f"{label}: {posture}" if label else posture)
            continue
        text = str(item or "").strip()
        if text:
            postures.append(text)
    return postures


def _agent_native_output_evidence_refs(output: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(_agent_native_string_list(output.get("evidence_refs")))
    for item in list(output.get("coverage_results") or []):
        if isinstance(item, dict):
            refs.extend(_agent_native_string_list(item.get("evidence_refs")))
    return list(dict.fromkeys(refs))


def _agent_native_known_evidence_ids(active: dict, context_packet: dict) -> set[str]:
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    if isinstance(capsule.get("known_evidence_ids"), list):
        return set(_agent_native_string_list(capsule.get("known_evidence_ids")))
    evidence = context_packet.get("evidence") if isinstance(context_packet.get("evidence"), dict) else {}
    return set(_agent_native_string_list(evidence.get("known_ids")))


def _agent_native_unknown_evidence_refs(output: dict[str, Any], *, active: dict, context_packet: dict) -> list[str]:
    known_ids = _agent_native_known_evidence_ids(active, context_packet)
    return [item for item in _agent_native_output_evidence_refs(output) if item not in known_ids]


def _agent_native_output_coverage_target_ids(output: dict[str, Any]) -> list[str]:
    target_ids: list[str] = []
    for item in list(output.get("coverage_results") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return list(dict.fromkeys(target_ids))


def _agent_native_output_coverage_results(output: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in list(output.get("coverage_results") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if not target_id or not status:
            continue
        result: dict[str, Any] = {"target_id": target_id, "status": status}
        evidence_refs = _agent_native_string_list(item.get("evidence_refs"))
        if evidence_refs:
            result["evidence_refs"] = evidence_refs
        note = str(item.get("note") or "").strip()
        if note:
            result["note"] = note
        results.append(result)
    return results


def _agent_native_capsule_coverage_target_ids(active: dict[str, Any]) -> set[str]:
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    judgment_contract = capsule.get("judgment_contract") if isinstance(capsule.get("judgment_contract"), dict) else {}
    target_ids: set[str] = set()
    for item in list(judgment_contract.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if target_id:
            target_ids.add(target_id)
    return target_ids


def _agent_native_unknown_coverage_target_ids(output: dict[str, Any], *, active: dict[str, Any]) -> list[str]:
    known_target_ids = _agent_native_capsule_coverage_target_ids(active)
    return [target_id for target_id in _agent_native_output_coverage_target_ids(output) if target_id not in known_target_ids]


def _agent_native_template_coverage_targets(capsule: dict[str, Any]) -> list[dict[str, Any]]:
    judgment_contract = capsule.get("judgment_contract") if isinstance(capsule.get("judgment_contract"), dict) else {}
    targets: list[dict[str, Any]] = []
    for item in list(judgment_contract.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if not target_id:
            continue
        targets.append(
            {
                "id": target_id,
                "kind": str(item.get("kind") or "").strip(),
                "required": bool(item.get("required")),
                "text": str(item.get("text") or item.get("label") or "").strip(),
            }
        )
    return targets


def _agent_native_compact_known_evidence_refs(known_evidence_ids: list[str], context_packet: object) -> list[dict[str, Any]]:
    packet = context_packet if isinstance(context_packet, dict) else {}
    evidence = packet.get("evidence") if isinstance(packet.get("evidence"), dict) else {}
    items_by_id = {
        str(item.get("id")): item
        for item in list(evidence.get("items") or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    refs: list[dict[str, Any]] = []
    for evidence_id in known_evidence_ids:
        item = items_by_id.get(evidence_id)
        ref: dict[str, Any] = {"id": evidence_id}
        if isinstance(item, dict):
            ref.update(
                {
                    "step_id": str(item.get("step_id") or "").strip(),
                    "role_name": str(item.get("role_name") or "").strip(),
                    "archetype": str(item.get("archetype") or "").strip(),
                    "claim": str(item.get("claim") or "").strip(),
                    "result": str(item.get("result") or "").strip(),
                    "measured_evidence": bool(item.get("measured_evidence")),
                    "concrete_evidence_claim_count": structured_non_negative_int(item.get("concrete_evidence_claim_count"), default=0),
                    "coverage_target_ids": _agent_native_evidence_coverage_target_ids(item),
                    "gatekeeper_support": _agent_native_gatekeeper_support_status(item),
                    "gatekeeper_support_reason": _agent_native_gatekeeper_support_reason(item),
                    "artifact_refs": _agent_native_compact_evidence_artifact_refs(item.get("artifact_refs")),
                }
            )
        refs.append(ref)
    return refs


def _agent_native_compact_evidence_artifact_refs(value: object, *, limit: int = 4) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in list(value or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        kind = str(item.get("kind") or "").strip()
        path = str(item.get("workspace_path") or item.get("relative_path") or "").strip()
        if not path:
            continue
        if kind != "workspace" and not label.startswith(("proof-file:", "proof-artifact:", "artifact:")):
            continue
        compact = {"path": path}
        if label:
            compact["label"] = label
        refs.append(compact)
        if len(refs) >= limit:
            break
    return refs


def _agent_native_evidence_coverage_target_ids(item: dict[str, Any]) -> list[str]:
    target_ids: list[str] = []
    for coverage in list(item.get("coverage_results") or []):
        if not isinstance(coverage, dict):
            continue
        target_id = str(coverage.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return list(dict.fromkeys(target_ids))


def _agent_native_gatekeeper_support_status(item: dict[str, Any]) -> str:
    return "supporting" if evidence_item_is_supporting_gatekeeper_ref(item) else "non_supporting"


def _agent_native_gatekeeper_support_reason(item: dict[str, Any]) -> str:
    archetype = str(item.get("archetype") or "").strip().lower()
    result = str(item.get("result") or "").strip().lower()
    reason = ""
    if evidence_item_is_supporting_gatekeeper_ref(item):
        if _agent_native_has_current_proof_artifact_ref(item.get("artifact_refs")):
            reason = "has a current proof-file or proof-artifact workspace ref"
        elif archetype in {"inspector", "custom"} and _agent_native_has_supporting_verify_ref(item.get("verifies")):
            reason = "review evidence verifies a passed check or coverage target"
        elif str(item.get("evidence_kind") or "").strip().lower() == "control":
            reason = "workflow control evidence is supportable"
        elif structured_bool_is_true(item.get("measured_evidence")):
            reason = "marked as measured evidence"
        else:
            reason = "matches supporting GateKeeper evidence rules"
    elif archetype == "gatekeeper":
        reason = "GateKeeper evidence cannot support another GateKeeper pass"
    elif result in {"blocked", "failed", "fail", "rejected", "error", "errored"}:
        reason = f"result is {result}"
    else:
        reason = "no proof artifact, measured evidence, control evidence, or supporting review verification"
    return reason


def _agent_native_has_current_proof_artifact_ref(value: object) -> bool:
    for ref in list(value or []):
        if not isinstance(ref, dict):
            continue
        label = str(ref.get("label") or "").strip().lower()
        if not label.startswith(("proof-file:", "proof-artifact:")):
            continue
        absolute_path = str(ref.get("absolute_path") or "").strip()
        if not absolute_path:
            continue
        try:
            if Path(absolute_path).exists():
                return True
        except OSError:
            continue
    return False


def _agent_native_has_supporting_verify_ref(value: object) -> bool:
    supporting_results = {
        "passed",
        "pass",
        "ok",
        "success",
        "succeeded",
        "completed",
        "covered",
        "satisfied",
        "guarded",
        "verified",
        "proven",
    }
    for raw_ref in list(value or []):
        text = str(raw_ref or "").strip()
        if text.startswith("target:"):
            parts = text.split(":", 2)
            if len(parts) == 3 and parts[2].strip().lower() in supporting_results:
                return True
        if text.startswith(("check_results:", "dynamic_checks:")):
            parts = text.split(":", 2)
            if len(parts) == 3 and parts[2].strip().lower() in supporting_results:
                return True
    return False


AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS = ("changed_files", "generated_files", "proof_files", "proof_artifacts", "artifact_paths")


def _agent_native_schema_type_name(value: object) -> str:
    typed_names = (
        (bool, "boolean"),
        (dict, "object"),
        (list, "array"),
        (str, "string"),
        (int, "integer"),
        (float, "number"),
    )
    if value is None:
        return "null"
    for value_type, type_name in typed_names:
        if isinstance(value, value_type):
            return type_name
    return type(value).__name__


def _agent_native_schema_value_matches_type(value: object, expected_type: str) -> bool:
    validators = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    validator = validators.get(expected_type)
    return True if validator is None else bool(validator(value))


def _agent_native_schema_object_issues(value: dict, schema: dict[str, Any], *, path: str) -> list[str]:
    issues: list[str] = []
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = [str(item) for item in list(schema.get("required") or []) if str(item)]
    missing = [field for field in required if field not in value]
    issues.extend(f"{path}.{field} is required" for field in missing)
    if schema.get("additionalProperties") is False:
        extra_fields = sorted(str(field) for field in value if str(field) not in properties)
        issues.extend(f"{path}.{field} is not allowed by output_schema" for field in extra_fields)
    for field, field_schema in properties.items():
        if field in value:
            issues.extend(_agent_native_schema_validation_issues(value[field], field_schema, path=f"{path}.{field}"))
    return issues


def _agent_native_schema_array_issues(value: list, schema: dict[str, Any], *, path: str) -> list[str]:
    item_schema = schema.get("items")
    if not isinstance(item_schema, dict):
        return []
    issues: list[str] = []
    for index, item in enumerate(value):
        issues.extend(_agent_native_schema_validation_issues(item, item_schema, path=f"{path}[{index}]"))
    return issues


def _agent_native_schema_validation_issues(value: object, schema: object, *, path: str = "$") -> list[str]:
    if not isinstance(schema, dict):
        return []
    issues: list[str] = []
    expected_type = str(schema.get("type") or "").strip()
    if expected_type and not _agent_native_schema_value_matches_type(value, expected_type):
        return [f"{path} expected {expected_type}, got {_agent_native_schema_type_name(value)}"]
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        issues.append(f"{path} must be one of {enum_values!r}")
    if expected_type == "object" and isinstance(value, dict):
        issues.extend(_agent_native_schema_object_issues(value, schema, path=path))
    elif expected_type == "array" and isinstance(value, list):
        issues.extend(_agent_native_schema_array_issues(value, schema, path=path))
    return issues


def _agent_native_result_scaffold_from_schema(schema: object) -> object:
    if not isinstance(schema, dict):
        return None
    expected_type = str(schema.get("type") or "").strip()
    if expected_type == "object":
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        property_schemas = {str(field): field_schema for field, field_schema in properties.items()}
        required = [str(item) for item in list(schema.get("required") or []) if str(item)]
        ordered_fields = list(dict.fromkeys(required))
        ordered_fields.extend(field for field in property_schemas if field not in ordered_fields)
        return {field: _agent_native_result_scaffold_from_schema(property_schemas.get(field)) for field in ordered_fields}
    if expected_type == "array":
        item_schema = schema.get("items")
        return [_agent_native_result_scaffold_from_schema(item_schema)] if isinstance(item_schema, dict) else [None]
    return None
