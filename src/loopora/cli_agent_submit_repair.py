from __future__ import annotations

import json
from pathlib import Path

from loopora.agent_native_evidence_refs import agent_known_evidence_ref_summaries as _agent_known_evidence_ref_summaries
from loopora.agent_native_guidance import core_blocker_kind as _core_blocker_kind
from loopora.agent_native_projection_state import agent_native_active_step_view as _agent_native_active_step_view
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope as _agent_v3_envelope
from loopora.agent_native_v3 import agent_v3_legacy_raw as _agent_v3_legacy_raw
from loopora.agent_native_v3 import agent_v3_technical_handoff as _agent_v3_technical_handoff
from loopora.cli_agent_runtime_support import agent_next_command_hint as _agent_next_command_hint
from loopora.cli_agent_submit_repair_output import print_agent_submit_repair_plain as _print_agent_submit_repair_plain
from loopora.cli_agent_submit_repair_schema import (
    active_step_coverage_target_ids as _active_step_coverage_target_ids,
    output_schema_error_hints as _output_schema_error_hints,
    result_file_null_placeholder_focus as _result_file_null_placeholder_focus,
)
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import (
    non_bool_int as _non_bool_int,
    set_summary_list as _set_summary_list,
    set_summary_text as _set_summary_text,
)
from loopora.service import LooporaError


def _print_agent_submit_repair_guidance(
    exc: Exception,
    *,
    service,
    adapter: str,
    context_id: str,
    run_id: str,
    entry_source: str,
    result_file: Path,
    workdir: Path,
    json_output: bool,
    auto_repair_actions: list[str] | None = None,
) -> bool:
    result = _agent_submit_repair_result(
        exc,
        service=service,
        adapter=adapter,
        context_id=context_id,
        run_id=run_id,
        entry_source=entry_source,
        result_file=result_file,
        workdir=workdir,
        auto_repair_actions=auto_repair_actions or [],
    )
    if not result:
        return False
    if json_output:
        echo_json(_agent_submit_repair_json_payload(result))
        return True
    _print_agent_submit_repair_plain(result)
    return True


def _agent_submit_repair_result(
    exc: Exception,
    *,
    service,
    adapter: str,
    context_id: str,
    run_id: str,
    entry_source: str,
    result_file: Path,
    workdir: Path,
    auto_repair_actions: list[str] | None = None,
) -> dict:
    error = str(exc)
    if not _agent_submit_error_is_repairable(error):
        return {}
    active_step_view = _active_agent_native_step_view(service, run_id=run_id)
    result = {
        "adapter": adapter,
        "ready": False,
        "submit_repair": "repair_result_json",
        "result_file_to_repair": str(result_file),
        "error": error,
        "message": "result JSON needs repair before this Loopora step can advance",
    }
    if run_id:
        result["run_id"] = run_id
    if context_id:
        result["context_id"] = context_id
    _attach_auto_repair_blocker_context(result, error, auto_repair_actions or [])
    submitted_dispatch = _agent_submit_result_file_dispatch_summary(result_file)
    if submitted_dispatch:
        result["submitted_dispatch"] = submitted_dispatch
    if active_step_view:
        _attach_agent_submit_active_step_view_repair_context(result, active_step_view, result_file)
    focus = _agent_submit_repair_focus(error, active_step_view)
    null_placeholder_focus = _result_file_null_placeholder_focus(result_file)
    if null_placeholder_focus:
        focus = [null_placeholder_focus, *[item for item in focus if not item.startswith("replace null placeholders before submit:")]]
    if focus:
        result["repair_focus"] = list(dict.fromkeys(focus))
    rerun = _agent_next_command_hint(adapter=adapter, workdir=workdir, context_id=context_id, run_id=run_id, entry_source=entry_source)
    if rerun:
        result["schema_lookup"] = rerun
    result["next_repair_step"] = _agent_submit_next_repair_step(result)
    return result


def _attach_auto_repair_blocker_context(result: dict, error: str, auto_repair_actions: list[str]) -> None:
    actions = [str(item).strip() for item in auto_repair_actions if str(item).strip()]
    if not actions:
        return
    result["auto_repair_attempted"] = True
    result["auto_repair_actions"] = list(dict.fromkeys(actions))
    result["core_blocker_preserved"] = True
    result["core_blocker_kind"] = _agent_submit_core_blocker_kind(error)


def _agent_submit_repair_json_payload(result: dict) -> dict:
    summary = _agent_submit_repair_summary(result)
    return _agent_v3_envelope(
        kind="agent_submit_repair",
        status="blocked",
        summary=summary,
        extras={
            "technical_handoff": _agent_v3_technical_handoff(summary),
            "diagnostics": {"legacy_summary_key": "agent_submit_repair_summary"},
            "raw": _agent_v3_legacy_raw(summary_key="agent_submit_repair_summary", summary=summary, payload=result),
        },
    )


def _agent_submit_repair_summary(result: dict) -> dict:
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "submit_repair": str(result.get("submit_repair") or "").strip(),
    }
    attach_native_run_surface(summary, result)
    for key in (
        "run_id",
        "context_id",
        "result_file_to_repair",
        "active_step_id",
        "active_role",
        "active_target_agent",
        "active_result_template",
        "active_result_file_to_write",
        "next_repair_step",
        "schema_lookup",
        "core_blocker_kind",
    ):
        _set_summary_text(summary, key, result.get(key))
    if result.get("auto_repair_attempted") is True:
        summary["auto_repair_attempted"] = True
    if result.get("core_blocker_preserved") is True:
        summary["core_blocker_preserved"] = True
    _set_summary_list(summary, "auto_repair_actions", result.get("auto_repair_actions"))
    for key in ("active_iter", "active_step_order"):
        value = result.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            summary[key] = value
    if result.get("submitted_template_file") is True:
        summary["submitted_template_file"] = True
    submitted_dispatch = result.get("submitted_dispatch")
    if isinstance(submitted_dispatch, dict) and submitted_dispatch:
        summary["submitted_dispatch"] = submitted_dispatch
    _set_summary_list(summary, "repair_focus", result.get("repair_focus"))
    _set_summary_list(summary, "active_known_evidence_ids", result.get("active_known_evidence_ids"))
    if isinstance(result.get("active_known_evidence_refs"), list) and result.get("active_known_evidence_refs"):
        summary["active_known_evidence_refs"] = result["active_known_evidence_refs"]
    _set_summary_list(summary, "active_coverage_target_ids", result.get("active_coverage_target_ids"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_agent_submit_active_step_view_repair_context(result: dict, active_step_view: dict, result_file: Path) -> None:
    role = active_step_view.get("role") if isinstance(active_step_view.get("role"), dict) else {}
    dispatch = active_step_view.get("role_dispatch") if isinstance(active_step_view.get("role_dispatch"), dict) else {}
    submit_hint = active_step_view.get("submit_hint") if isinstance(active_step_view.get("submit_hint"), dict) else {}
    target_agent = str(dispatch.get("target_agent") or active_step_view.get("target_agent") or "").strip()
    result["active_step_id"] = active_step_view.get("step_id")
    result["active_role"] = role.get("name") or role.get("id")
    _attach_agent_submit_active_step_view_position(result, active_step_view)
    if target_agent:
        result["active_target_agent"] = target_agent
    context_path = str(active_step_view.get("context_absolute_path") or active_step_view.get("context_path") or "").strip()
    if context_path:
        result["active_context_path"] = context_path
    result_template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
    if result_template_path:
        result["active_result_template"] = result_template_path
    result_file_to_write = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
    if result_file_to_write:
        result["active_result_file_to_write"] = result_file_to_write
    if _same_path(result_file, result_template_path):
        result["submitted_template_file"] = True
        result_outbox_dir = str(submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir") or "").strip()
        if result_outbox_dir:
            result["result_outbox_dir"] = result_outbox_dir
    known_evidence_ids = [str(item).strip() for item in list(active_step_view.get("known_evidence_ids") or []) if str(item).strip()]
    if known_evidence_ids:
        result["active_known_evidence_ids"] = known_evidence_ids
    known_evidence_refs = _agent_known_evidence_ref_summaries(active_step_view.get("known_evidence_refs"), limit=5)
    if known_evidence_refs:
        result["active_known_evidence_refs"] = known_evidence_refs
    coverage_target_ids = _active_step_coverage_target_ids(active_step_view)
    if coverage_target_ids:
        result["active_coverage_target_ids"] = coverage_target_ids


def _attach_agent_submit_active_step_view_position(result: dict, active_step_view: dict) -> None:
    if isinstance(active_step_view.get("iter"), int) and not isinstance(active_step_view.get("iter"), bool):
        result["active_iter"] = active_step_view.get("iter")
    if isinstance(active_step_view.get("step_order"), int) and not isinstance(active_step_view.get("step_order"), bool):
        result["active_step_order"] = active_step_view.get("step_order")


def _same_path(candidate: Path, reference: str) -> bool:
    if not reference:
        return False
    try:
        return candidate.expanduser().resolve() == Path(reference).expanduser().resolve()
    except OSError:
        return str(candidate) == reference


def _agent_submit_next_repair_step(result: dict) -> str:
    error = str(result.get("error") or "")
    if _result_file_missing(error):
        template = str(result.get("active_result_template") or "the active result template").strip()
        step = (
            "create the missing filled result file by copying "
            f"{template}, replacing null placeholders in result, preserving loopora_host_dispatch, then submit again"
        )
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
        "result file is not valid JSON",
        "result file must contain one JSON object",
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


def _active_agent_native_step_view(service, *, run_id: str) -> dict:
    if not run_id:
        return {}
    try:
        run = service.get_run(run_id)
    except LooporaError:
        return {}
    runs_dir = str(run.get("runs_dir") or "").strip() if isinstance(run, dict) else ""
    if not runs_dir:
        return {}
    try:
        state = json.loads((Path(runs_dir) / "agent_native" / "state.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    active_step_state = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
    return _agent_native_active_step_view(active_step_state)


def _agent_submit_repair_focus(error: str, active_step_view: dict) -> list[str]:
    focus: list[str] = []
    if _result_file_missing(error):
        focus.append("create the filled result JSON file at result_file_to_repair before submitting")
    elif "result file is not valid JSON" in error:
        focus.append("fix JSON syntax; the file must be one wrapper object with loopora_host_dispatch and result")
    if "result file must contain one JSON object" in error:
        focus.append("replace the file with one JSON object; do not submit an array, string, or multiple documents")
    schema = active_step_view.get("output_schema") if isinstance(active_step_view.get("output_schema"), dict) else {}
    focus.extend(_output_schema_error_hints(error, schema))
    if "result wrapper must contain" in error:
        focus.append("use one wrapper JSON object with loopora_host_dispatch and result")
    focus.extend(_host_dispatch_repair_focus(error, active_step_view))
    focus.extend(_evidence_ref_repair_focus(error, active_step_view))
    focus.extend(_coverage_target_repair_focus(error, active_step_view))
    if "read-only step cannot claim workspace artifact fields" in error:
        focus.append("remove workspace artifact fields such as changed_files/proof_files from this read_only role result")
    if "submitted step_id does not match" in error:
        focus.append("submit the active step_id exactly; rerun agent next --json if the run advanced or the result file is stale")
    if "agent-native step was already submitted" in error:
        focus.append("do not resubmit a stale result file; rerun agent next --json and submit only the active step")
    if not focus and "output_schema" in error:
        focus.append("make result match next_step.output_schema exactly; do not add fields outside the schema")
    return list(dict.fromkeys(focus))[:6]


def _host_dispatch_repair_focus(error: str, active_step_view: dict) -> list[str]:
    if not _host_dispatch_error_is_repairable(error):
        return []
    role_dispatch = active_step_view.get("role_dispatch") if isinstance(active_step_view.get("role_dispatch"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if target_agent:
        return [
            f"set loopora_host_dispatch.target_agent and actual_agent to {target_agent}, inline to false, "
            "keep adapter/run_id/iter/step_id/step_order exact, and preserve optional native_trace fields when the host exposed them"
        ]
    return [
        "preserve loopora_host_dispatch with exact adapter, run_id, iter, step_id, step_order, target_agent, actual_agent, dispatch_mode, inline=false, and optional native_trace fields"
    ]


def _host_dispatch_missing(error: str) -> bool:
    return "result wrapper must contain loopora_host_dispatch object" in error or "requires loopora_host_dispatch proof" in error


def _result_file_missing(error: str) -> bool:
    return "result file is not valid JSON" in error and ("No such file or directory" in error or "Errno 2" in error)


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


def _evidence_ref_repair_focus(error: str, active_step_view: dict) -> list[str]:
    if "evidence_refs_unknown" not in error:
        return []
    known = [str(item) for item in list(active_step_view.get("known_evidence_ids") or []) if str(item).strip()]
    if known:
        return ["use only known_evidence_ids in evidence_refs: " + ", ".join(known[:6])]
    return ["remove invented evidence_refs; evidence_refs must be exact IDs from the active step contract"]


def _coverage_target_repair_focus(error: str, active_step_view: dict) -> list[str]:
    if "coverage_results_unknown_target_id" not in error:
        return []
    target_ids = _active_step_coverage_target_ids(active_step_view)
    if target_ids:
        return ["use only frozen coverage target IDs: " + ", ".join(target_ids[:8])]
    return ["coverage_results.target_id must come from the active judgment_contract coverage targets"]
