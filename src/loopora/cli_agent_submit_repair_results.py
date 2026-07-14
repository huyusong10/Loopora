from __future__ import annotations

import json
from pathlib import Path

from loopora.agent_native_evidence_refs import agent_known_evidence_ref_summaries as _agent_known_evidence_ref_summaries
from loopora.agent_native_projection_state import agent_native_active_step_view as _agent_native_active_step_view
from loopora.cli_agent_result_files import (
    RESULT_FILE_INVALID_JSON_ERROR,
    RESULT_FILE_OBJECT_ERROR,
    RESULT_FILE_UNREADABLE_ERROR,
)
from loopora.cli_agent_runtime_support import agent_next_command_hint as _agent_next_command_hint
from loopora.cli_agent_submit_repair_guidance import (
    _agent_submit_core_blocker_kind as _agent_submit_core_blocker_kind,
    _agent_submit_error_is_repairable as _agent_submit_error_is_repairable,
    _agent_submit_next_repair_step as _agent_submit_next_repair_step,
    _agent_submit_result_file_dispatch_summary as _agent_submit_result_file_dispatch_summary,
    _host_dispatch_error_is_repairable as _host_dispatch_error_is_repairable,
    _result_file_missing as _result_file_missing,
)
from loopora.cli_agent_submit_repair_schema import (
    active_step_coverage_target_ids as _active_step_coverage_target_ids,
    output_schema_error_hints as _output_schema_error_hints,
    result_file_null_placeholder_focus as _result_file_null_placeholder_focus,
)
from loopora.service import LooporaError


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


def _active_agent_native_step_view(service, *, run_id: str) -> dict:
    if service is None or not run_id:
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
    elif RESULT_FILE_UNREADABLE_ERROR in error:
        focus.append("make result_file_to_repair readable as UTF-8 JSON or recreate it from the active result template")
    elif RESULT_FILE_INVALID_JSON_ERROR in error or "result file is not valid JSON" in error:
        focus.append("fix JSON syntax; the file must be one wrapper object with loopora_host_dispatch and result")
    if RESULT_FILE_OBJECT_ERROR in error:
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
