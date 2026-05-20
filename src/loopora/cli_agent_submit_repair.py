from __future__ import annotations

import json
import re
from pathlib import Path

import typer

from loopora.cli_agent_native import _agent_next_command_hint, _non_bool_int, _set_summary_list, _set_summary_text
from loopora.cli_agent_step_presenters import _agent_known_evidence_ref_summaries
from loopora.cli_shared import echo_json
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
    )
    if not result:
        return False
    if json_output:
        echo_json(_agent_submit_repair_json_payload(result))
        return True
    _print_agent_submit_repair_header(result)
    _print_agent_submit_repair_context(result)
    _print_agent_submit_repair_focus(result)
    typer.echo(f"next_repair_step: {result.get('next_repair_step')}", err=True)
    if result.get("schema_lookup"):
        typer.echo(f"schema_lookup: {result.get('schema_lookup')}", err=True)
    return True


def _print_agent_submit_repair_header(result: dict) -> None:
    typer.echo("submit_repair: result JSON needs repair before this Loopora step can advance", err=True)
    typer.echo(f"result_file_to_repair: {result.get('result_file_to_repair')}", err=True)
    for key in (
        "active_step_id",
        "active_role",
        "active_target_agent",
        "active_context_path",
        "active_result_template",
        "active_result_file_to_write",
        "result_outbox_dir",
    ):
        value = result.get(key)
        if value:
            typer.echo(f"{key}: {value}", err=True)
    _print_agent_submit_submitted_dispatch(result)


def _print_agent_submit_repair_focus(result: dict) -> None:
    focus = [str(item) for item in list(result.get("repair_focus") or []) if str(item).strip()]
    if not focus:
        return
    typer.echo("repair_focus:", err=True)
    for item in focus:
        typer.echo(f"- {item}", err=True)


def _print_agent_submit_repair_context(result: dict) -> None:
    known_ids = [str(item).strip() for item in list(result.get("active_known_evidence_ids") or []) if str(item).strip()]
    if known_ids:
        _print_agent_submit_repair_plain_list("active_known_evidence_ids", known_ids, limit=8)
    refs = result.get("active_known_evidence_refs")
    if isinstance(refs, list) and refs:
        _print_agent_submit_repair_known_evidence_refs(refs)
    target_ids = [str(item).strip() for item in list(result.get("active_coverage_target_ids") or []) if str(item).strip()]
    if target_ids:
        _print_agent_submit_repair_plain_list("active_coverage_target_ids", target_ids, limit=16)


def _print_agent_submit_repair_plain_list(label: str, items: list[str], *, limit: int) -> None:
    displayed = items[:limit]
    typer.echo(f"{label}:", err=True)
    for item in displayed:
        typer.echo(f"- {item}", err=True)
    if len(items) > len(displayed):
        typer.echo(f"{label}_more: {len(items) - len(displayed)}", err=True)


def _print_agent_submit_repair_known_evidence_refs(refs: list[object]) -> None:
    summaries = [item for item in refs if isinstance(item, dict)]
    if not summaries:
        return
    typer.echo("active_known_evidence_refs:", err=True)
    for item in summaries[:5]:
        parts = [str(item.get("id") or "").strip()]
        result = str(item.get("result") or "").strip()
        if result:
            parts.append(f"result={result}")
        support = str(item.get("gatekeeper_support") or "").strip()
        if support:
            parts.append(f"support={support}")
        reason = str(item.get("gatekeeper_support_reason") or "").strip()
        if reason:
            parts.append(f"reason={reason}")
        typer.echo(f"- {' '.join(part for part in parts if part)}", err=True)
        claim = str(item.get("claim") or "").strip()
        if claim:
            typer.echo(f"  claim: {claim}", err=True)
        coverage_targets = item.get("coverage_target_ids") if isinstance(item.get("coverage_target_ids"), list) else []
        coverage = [str(target).strip() for target in coverage_targets if str(target).strip()]
        if coverage:
            typer.echo(f"  coverage_targets: {', '.join(coverage[:6])}", err=True)
    if len(summaries) > 5:
        typer.echo(f"active_known_evidence_refs_more: {len(summaries) - 5}", err=True)


def _print_agent_submit_submitted_dispatch(result: dict) -> None:
    submitted_dispatch = result.get("submitted_dispatch")
    if not isinstance(submitted_dispatch, dict) or not submitted_dispatch:
        return
    plain_parts = _agent_submit_dispatch_plain_parts(submitted_dispatch)
    if plain_parts:
        typer.echo(f"submitted_dispatch: {', '.join(plain_parts)}", err=True)


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
) -> dict:
    error = str(exc)
    if not _agent_submit_error_is_repairable(error):
        return {}
    active_step = _active_agent_native_step(service, run_id=run_id)
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
    submitted_dispatch = _agent_submit_result_file_dispatch_summary(result_file)
    if submitted_dispatch:
        result["submitted_dispatch"] = submitted_dispatch
    if active_step:
        _attach_agent_submit_active_step_repair_context(result, active_step, result_file)
    focus = _agent_submit_repair_focus(error, active_step)
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


def _agent_submit_repair_json_payload(result: dict) -> dict:
    payload = {"agent_submit_repair_summary": _agent_submit_repair_summary(result)}
    payload.update(result)
    return payload


def _agent_submit_repair_summary(result: dict) -> dict:
    summary: dict[str, object] = {
        "ready": bool(result.get("ready")),
        "submit_repair": str(result.get("submit_repair") or "").strip(),
    }
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
    ):
        _set_summary_text(summary, key, result.get(key))
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


def _attach_agent_submit_active_step_repair_context(result: dict, active_step: dict, result_file: Path) -> None:
    role = active_step.get("role") if isinstance(active_step.get("role"), dict) else {}
    dispatch = active_step.get("role_dispatch") if isinstance(active_step.get("role_dispatch"), dict) else {}
    submit_hint = active_step.get("submit_hint") if isinstance(active_step.get("submit_hint"), dict) else {}
    target_agent = str(dispatch.get("target_agent") or active_step.get("target_agent") or "").strip()
    result["active_step_id"] = active_step.get("step_id")
    result["active_role"] = role.get("name") or role.get("id")
    _attach_agent_submit_active_step_position(result, active_step)
    if target_agent:
        result["active_target_agent"] = target_agent
    context_path = str(active_step.get("context_absolute_path") or active_step.get("context_path") or "").strip()
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
    known_evidence_ids = [str(item).strip() for item in list(active_step.get("known_evidence_ids") or []) if str(item).strip()]
    if known_evidence_ids:
        result["active_known_evidence_ids"] = known_evidence_ids
    known_evidence_refs = _agent_known_evidence_ref_summaries(active_step.get("known_evidence_refs"), limit=5)
    if known_evidence_refs:
        result["active_known_evidence_refs"] = known_evidence_refs
    coverage_target_ids = _active_step_coverage_target_ids(active_step)
    if coverage_target_ids:
        result["active_coverage_target_ids"] = coverage_target_ids


def _attach_agent_submit_active_step_position(result: dict, active_step: dict) -> None:
    if isinstance(active_step.get("iter"), int) and not isinstance(active_step.get("iter"), bool):
        result["active_iter"] = active_step.get("iter")
    if isinstance(active_step.get("step_order"), int) and not isinstance(active_step.get("step_order"), bool):
        result["active_step_order"] = active_step.get("step_order")


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
        active_step = str(result.get("active_step_id") or "").strip()
        step_part = f" for active step {active_step}" if active_step else ""
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


def _agent_submit_dispatch_plain_parts(dispatch: dict) -> list[str]:
    parts: list[str] = []
    for key in ("run_id", "step_id", "iter", "step_order", "target_agent", "actual_agent", "dispatch_mode", "inline"):
        value = dispatch.get(key)
        if value in ("", None):
            continue
        parts.append(f"{key}={value}")
    return parts


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
    active_step = str(result.get("active_step_id") or "").strip()
    if not active_step:
        return f"submitted file is for {submitted_label}"
    active_bits: list[str] = []
    active_iter = result.get("active_iter")
    if isinstance(active_iter, int) and not isinstance(active_iter, bool):
        active_bits.append(f"iter {active_iter}")
    active_step_order = result.get("active_step_order")
    if isinstance(active_step_order, int) and not isinstance(active_step_order, bool):
        active_bits.append(f"step_order {active_step_order}")
    active_label = active_step
    if active_bits:
        active_label = f"{active_label} ({', '.join(active_bits)})"
    return f"submitted file is for {submitted_label}, but active step is {active_label}"


def _result_file_null_placeholder_focus(result_file: Path) -> str:
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    result = payload.get("result") if isinstance(payload, dict) else None
    paths: list[str] = []
    _collect_null_paths(result, "$", paths)
    if not paths:
        return ""
    return "replace null placeholders before submit: " + _format_bounded_list(paths, limit=12)


def _collect_null_paths(value: object, path: str, paths: list[str]) -> None:
    if value is None:
        paths.append(path)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            _collect_null_paths(child, f"{path}.{key}", paths)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _collect_null_paths(child, f"{path}[{index}]", paths)


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


def _active_agent_native_step(service, *, run_id: str) -> dict:
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
    active = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
    capsule = active.get("capsule") if isinstance(active.get("capsule"), dict) else {}
    return capsule if isinstance(capsule, dict) else {}


def _agent_submit_repair_focus(error: str, active_step: dict) -> list[str]:
    focus: list[str] = []
    if _result_file_missing(error):
        focus.append("create the filled result JSON file at result_file_to_repair before submitting")
    elif "result file is not valid JSON" in error:
        focus.append("fix JSON syntax; the file must be one wrapper object with loopora_host_dispatch and result")
    if "result file must contain one JSON object" in error:
        focus.append("replace the file with one JSON object; do not submit an array, string, or multiple documents")
    schema = active_step.get("output_schema") if isinstance(active_step.get("output_schema"), dict) else {}
    focus.extend(_output_schema_error_hints(error, schema))
    if "result wrapper must contain" in error:
        focus.append("use one wrapper JSON object with loopora_host_dispatch and result")
    focus.extend(_host_dispatch_repair_focus(error, active_step))
    focus.extend(_evidence_ref_repair_focus(error, active_step))
    focus.extend(_coverage_target_repair_focus(error, active_step))
    if "read-only step cannot claim workspace artifact fields" in error:
        focus.append("remove workspace artifact fields such as changed_files/proof_files from this read_only role result")
    if "submitted step_id does not match" in error:
        focus.append("submit the active step_id exactly; rerun agent next --json if the run advanced or the result file is stale")
    if "agent-native step was already submitted" in error:
        focus.append("do not resubmit a stale result file; rerun agent next --json and submit only the active step")
    if not focus and "output_schema" in error:
        focus.append("make result match next_step.output_schema exactly; do not add fields outside the schema")
    return list(dict.fromkeys(focus))[:6]


def _host_dispatch_repair_focus(error: str, active_step: dict) -> list[str]:
    if not _host_dispatch_error_is_repairable(error):
        return []
    role_dispatch = active_step.get("role_dispatch") if isinstance(active_step.get("role_dispatch"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if target_agent:
        return [
            f"set loopora_host_dispatch.target_agent and actual_agent to {target_agent}, inline to false, "
            "and keep adapter/run_id/iter/step_id/step_order exact"
        ]
    return [
        "preserve loopora_host_dispatch with exact adapter, run_id, iter, step_id, step_order, target_agent, actual_agent, dispatch_mode, and inline=false"
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


def _evidence_ref_repair_focus(error: str, active_step: dict) -> list[str]:
    if "evidence_refs_unknown" not in error:
        return []
    known = [str(item) for item in list(active_step.get("known_evidence_ids") or []) if str(item).strip()]
    if known:
        return ["use only known_evidence_ids in evidence_refs: " + ", ".join(known[:6])]
    return ["remove invented evidence_refs; evidence_refs must be exact IDs from the active capsule"]


def _coverage_target_repair_focus(error: str, active_step: dict) -> list[str]:
    if "coverage_results_unknown_target_id" not in error:
        return []
    target_ids = _active_step_coverage_target_ids(active_step)
    if target_ids:
        return ["use only frozen coverage target IDs: " + ", ".join(target_ids[:8])]
    return ["coverage_results.target_id must come from the active judgment_contract coverage targets"]


_SCHEMA_TYPE_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) expected (?P<expected>[A-Za-z_]+), got (?P<actual>[A-Za-z_]+)")
_SCHEMA_REQUIRED_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) is required")
_SCHEMA_EXTRA_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) is not allowed by output_schema")
_SCHEMA_ENUM_ERROR_RE = re.compile(r"(?P<path>\$(?:\.[A-Za-z0-9_-]+|\[\d+\])*) must be one of (?P<values>\[[^\]]+\])")


def _output_schema_error_hint(error: str, schema: dict) -> str:
    hints = _output_schema_error_hints(error, schema)
    return hints[0] if hints else ""


def _output_schema_error_hints(error: str, schema: dict, *, limit: int = 6) -> list[str]:
    hints: list[str] = []
    type_matches = list(_SCHEMA_TYPE_ERROR_RE.finditer(error))
    null_paths = [match.group("path") for match in type_matches if match.group("actual") == "null"]
    if len(null_paths) > 1:
        hints.append("replace null placeholders before submit: " + _format_bounded_list(null_paths, limit=6))
    for match in type_matches:
        hints.append(_schema_type_error_hint(match, schema))
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_REQUIRED_ERROR_RE.finditer(error):
        hints.append(f"add missing result field {match.group('path').removeprefix('$.')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_EXTRA_ERROR_RE.finditer(error):
        hints.append(f"remove non-schema result field {match.group('path').removeprefix('$.')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    for match in _SCHEMA_ENUM_ERROR_RE.finditer(error):
        hints.append(f"{match.group('path')} must use one allowed value: {match.group('values')}")
        if len(hints) >= limit:
            return list(dict.fromkeys(hints))[:limit]
    return list(dict.fromkeys(hints))[:limit]


def _schema_type_error_hint(match: re.Match[str], schema: dict) -> str:
    path = match.group("path")
    expected = match.group("expected")
    node = _schema_node_at_path(schema, path)
    shape = _schema_shape_hint(node)
    if shape:
        return f"{path} must be {shape}"
    return f"{path} must be {expected}; rewrite that value inside result"


def _format_bounded_list(items: list[str], *, limit: int) -> str:
    visible = items[:limit]
    suffix = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return ", ".join(visible) + suffix


def _schema_node_at_path(schema: dict, path: str) -> dict:
    node: object = schema
    for segment in _schema_path_segments(path):
        if not isinstance(node, dict):
            return {}
        if isinstance(segment, int):
            node = node.get("items")
        else:
            properties = node.get("properties") if isinstance(node.get("properties"), dict) else {}
            node = properties.get(segment)
    return node if isinstance(node, dict) else {}


def _schema_path_segments(path: str) -> list[str | int]:
    segments: list[str | int] = []
    for match in re.finditer(r"\.([A-Za-z0-9_-]+)|\[(\d+)\]", path):
        if match.group(1) is not None:
            segments.append(match.group(1))
        else:
            segments.append(int(match.group(2)))
    return segments


def _schema_shape_hint(node: dict) -> str:
    schema_type = str(node.get("type") or "").strip()
    if schema_type == "object":
        required = [str(item) for item in list(node.get("required") or []) if str(item).strip()]
        if required:
            return "an object with required fields: " + ", ".join(required)
        return "an object"
    if schema_type == "array":
        item_shape = _schema_shape_hint(node.get("items") if isinstance(node.get("items"), dict) else {})
        return f"an array of {item_shape}" if item_shape else "an array"
    if schema_type:
        return schema_type
    return ""


def _active_step_coverage_target_ids(active_step: dict) -> list[str]:
    judgment_contract = active_step.get("judgment_contract") if isinstance(active_step.get("judgment_contract"), dict) else {}
    ids: list[str] = []
    for item in list(judgment_contract.get("coverage_targets") or []):
        if isinstance(item, dict):
            target_id = str(item.get("id") or item.get("target_id") or "").strip()
            if target_id:
                ids.append(target_id)
    return list(dict.fromkeys(ids))
