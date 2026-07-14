from __future__ import annotations

import json
from pathlib import Path

from loopora.agent_native_guidance import core_blocker_kind as _core_blocker_kind
from loopora.cli_agent_result_files import (
    RESULT_FILE_INVALID_JSON_ERROR,
    RESULT_FILE_MISSING_ERROR,
    RESULT_FILE_OBJECT_ERROR,
    RESULT_FILE_UNREADABLE_ERROR,
)
from loopora.cli_summary_helpers import non_bool_int as _non_bool_int
from loopora.cli_summary_helpers import set_summary_text as _set_summary_text


def _agent_submit_next_repair_step(result: dict) -> str:
    error = str(result.get("error") or "")
    result_file_step = _result_file_read_repair_step(result, error)
    if result_file_step:
        step = result_file_step
    elif result.get("submitted_template_file"):
        result_file_to_write = str(result.get("active_result_file_to_write") or "").strip()
        if result_file_to_write:
            destination = f" to {result_file_to_write}"
        else:
            outbox = str(result.get("result_outbox_dir") or "").strip()
            destination = f" under {outbox}" if outbox else " beside the template or in the result outbox"
        step = (
            "save a filled result copy"
            f"{destination}; do not overwrite the .result.template.json audit template; preserve loopora_host_dispatch, "
            "replace null placeholders, then submit the filled copy"
        )
    elif "submitted step_id does not match" in error or "agent-native step was already submitted" in error:
        active_step_id = str(result.get("active_step_id") or "").strip()
        step_part = f" for active step {active_step_id}" if active_step_id else ""
        stale_detail = _agent_submit_stale_dispatch_detail(result)
        stale_part = f"{stale_detail}; " if stale_detail else ""
        lookup = str(result.get("schema_lookup") or "agent next --json").strip()
        step = (
            "discard the stale result file for the previous step; "
            f"{stale_part}run {lookup}, fill the active result template{step_part}, then submit that filled file"
        )
    elif _host_dispatch_missing(error):
        step = (
            "restore loopora_host_dispatch by copying it from the active result template or rerun agent next --json to locate it; "
            "keep adapter/run_id/step_id exact, then submit again"
        )
    elif _host_dispatch_error_is_repairable(error):
        target = str(result.get("active_target_agent") or "").strip()
        target_part = f" target_agent and actual_agent to {target}," if target else " target_agent and actual_agent,"
        step = (
            "fix loopora_host_dispatch to match the active role dispatch:"
            f"{target_part} accepted dispatch_mode, inline=false, and exact adapter/run_id/iter/step_id/step_order; then submit again"
        )
    elif "evidence_refs_unknown" in error:
        known = [str(item).strip() for item in list(result.get("active_known_evidence_ids") or []) if str(item).strip()]
        known_part = f" ({', '.join(known[:6])})" if known else ""
        step = (
            "replace invented evidence_refs with exact active known_evidence_ids"
            f"{known_part}, or remove/mark weak the claim that cannot cite known evidence; then submit again"
        )
    elif "coverage_results_unknown_target_id" in error:
        target_ids = [str(item).strip() for item in list(result.get("active_coverage_target_ids") or []) if str(item).strip()]
        target_part = f" ({', '.join(target_ids[:8])})" if target_ids else ""
        step = (
            "replace invented coverage_results.target_id with an exact active coverage target ID"
            f"{target_part}, or remove that coverage_result; then submit again"
        )
    elif "read-only step cannot claim workspace artifact fields" in error:
        step = (
            "remove workspace artifact fields from this read_only role result; report observations/checks instead of claiming changed files, "
            "then submit again"
        )
    else:
        step = "edit the result JSON, preserve loopora_host_dispatch, rerun agent next --json if you need the active output_schema, then submit again"
    return step


def _result_file_read_repair_step(result: dict, error: str) -> str:
    if _result_file_missing(error):
        template = str(result.get("active_result_template") or "the active result template").strip()
        return (
            "create the missing filled result file by copying "
            f"{template}, replacing null placeholders in result, preserving loopora_host_dispatch, then submit again"
        )
    if RESULT_FILE_UNREADABLE_ERROR in error:
        return (
            "make result_file_to_repair readable as UTF-8 JSON or recreate it from the active result template, "
            "preserve loopora_host_dispatch, then submit again"
        )
    if RESULT_FILE_INVALID_JSON_ERROR in error:
        return (
            "fix JSON syntax in result_file_to_repair, keep one wrapper object with loopora_host_dispatch and result, "
            "then submit again"
        )
    return ""


def _agent_submit_result_file_dispatch_summary(result_file: Path) -> dict:
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    dispatch = payload.get("loopora_host_dispatch")
    if not isinstance(dispatch, dict):
        return {}
    summary: dict[str, object] = {}
    for key in ("adapter", "run_id", "step_id", "target_agent", "actual_agent", "dispatch_mode"):
        _set_summary_text(summary, key, dispatch.get(key))
    for key in ("iter", "step_order"):
        value = _non_bool_int(dispatch.get(key))
        if value is not None:
            summary[key] = value
    if isinstance(dispatch.get("inline"), bool):
        summary["inline"] = dispatch.get("inline")
    return summary


def _agent_submit_stale_dispatch_detail(result: dict) -> str:
    submitted = result.get("submitted_dispatch")
    if not isinstance(submitted, dict) or not submitted:
        return ""
    submitted_step = str(submitted.get("step_id") or "").strip()
    submitted_bits: list[str] = []
    submitted_iter = submitted.get("iter")
    if isinstance(submitted_iter, int) and not isinstance(submitted_iter, bool):
        submitted_bits.append(f"iter {submitted_iter}")
    submitted_step_order = submitted.get("step_order")
    if isinstance(submitted_step_order, int) and not isinstance(submitted_step_order, bool):
        submitted_bits.append(f"step_order {submitted_step_order}")
    submitted_label = submitted_step or "another step"
    if submitted_bits:
        submitted_label = f"{submitted_label} ({', '.join(submitted_bits)})"
    active_step_id = str(result.get("active_step_id") or "").strip()
    if not active_step_id:
        return f"submitted file is for {submitted_label}"
    active_bits: list[str] = []
    active_iter = result.get("active_iter")
    if isinstance(active_iter, int) and not isinstance(active_iter, bool):
        active_bits.append(f"iter {active_iter}")
    active_step_order = result.get("active_step_order")
    if isinstance(active_step_order, int) and not isinstance(active_step_order, bool):
        active_bits.append(f"step_order {active_step_order}")
    active_label = active_step_id
    if active_bits:
        active_label = f"{active_label} ({', '.join(active_bits)})"
    return f"submitted file is for {submitted_label}, but active step is {active_label}"


def _agent_submit_error_is_repairable(error: str) -> bool:
    markers = (
        RESULT_FILE_MISSING_ERROR,
        RESULT_FILE_UNREADABLE_ERROR,
        RESULT_FILE_INVALID_JSON_ERROR,
        RESULT_FILE_OBJECT_ERROR,
        "result file is not valid JSON",
        "agent-native result does not match output_schema",
        "result wrapper must contain",
        "loopora_host_dispatch",
        "agent-native host dispatch",
        "agent-native submit used",
        "agent-native submit dispatch_mode must be one of",
        "agent-native submit cannot claim inline role execution",
        "evidence_refs_unknown",
        "coverage_results_unknown_target_id",
        "read-only step cannot claim workspace artifact fields",
        "submitted step_id does not match",
        "agent-native step was already submitted",
    )
    return any(marker in error for marker in markers)


def _agent_submit_core_blocker_kind(error: str) -> str:
    return _core_blocker_kind(error)


def _host_dispatch_missing(error: str) -> bool:
    return "result wrapper must contain loopora_host_dispatch object" in error or "requires loopora_host_dispatch proof" in error


def _result_file_missing(error: str) -> bool:
    return RESULT_FILE_MISSING_ERROR in error or (
        "result file is not valid JSON" in error and ("No such file or directory" in error or "Errno 2" in error)
    )


def _host_dispatch_error_is_repairable(error: str) -> bool:
    return any(
        marker in error
        for marker in (
            "loopora_host_dispatch",
            "agent-native host dispatch",
            "agent-native submit used",
            "agent-native submit dispatch_mode must be one of",
            "agent-native submit cannot claim inline role execution",
        )
    )
