from __future__ import annotations

import re
import shlex

import typer

from loopora.agent_adapters import prefix_loopora_command
from loopora.cli_agent_native import (
    PASSING_TASK_VERDICT_STATUSES,
    _clip,
    _clip_inline,
    _non_bool_int,
    _print_web_status,
    _set_summary_list,
    _set_summary_text,
)
from loopora.cli_run_support import print_run_contract_summary, print_task_verdict
from loopora.cli_shared import echo_json

def _print_agent_loop_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        _attach_agent_run_dispatch_summary(result)
        echo_json(result)
        return
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run.get('run_status') or run.get('status')}")
    _print_agent_loop_start_state(result)
    print_run_contract_summary(run)
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    if result.get("complete"):
        print_task_verdict(task_verdict)
        _print_terminal_task_next_action(task_verdict, result.get("task_next_action"))
        _print_agent_native_terminal_state(task_verdict)
    typer.echo(f"run_url: {result.get('run_url') or result.get('run_path')}")
    _print_web_status(result)
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if next_step:
        _print_agent_current_step(next_step)


def _attach_agent_run_dispatch_summary(result: dict) -> None:
    summary = result.get("agent_run_summary") if isinstance(result.get("agent_run_summary"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    if not role_dispatch:
        return
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    if not summary:
        summary = {
            "schema_version": 1,
            "run_id": str(run.get("id") or "").strip(),
            "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
            "started_new_run": bool(result.get("started_new_run")),
            "complete": bool(result.get("complete")),
            "next_step_id": str(next_step.get("step_id") or "").strip(),
            "next_target_agent": str(role_dispatch.get("target_agent") or "").strip(),
        }
        result["agent_run_summary"] = summary
    target_config = str(role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path") or "").strip()
    if target_config:
        summary["next_target_agent_config"] = target_config
    if "target_agent_config_exists" in role_dispatch:
        summary["next_target_agent_config_exists"] = role_dispatch.get("target_agent_config_exists") is True
    next_step_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)
    if next_step_summary:
        summary["next_step"] = next_step_summary
        _set_summary_text(summary, "dispatch_next", next_step_summary.get("dispatch_next"))
        _set_summary_text(summary, "next_context_path", next_step_summary.get("context_path"))
        _set_summary_text(summary, "next_capsule_path", next_step_summary.get("capsule_path"))
        _set_summary_text(summary, "next_result_template", next_step_summary.get("result_template"))
        _set_summary_text(summary, "next_submit_command", next_step_summary.get("submit_command"))
    dispatch_unavailable = _agent_dispatch_unavailable_summary(adapter=adapter, workdir=workdir, role_dispatch=role_dispatch)
    if dispatch_unavailable:
        summary["dispatch_unavailable"] = dispatch_unavailable
    summary.update(_agent_next_step_continuation_summary(next_step))


def _print_agent_loop_start_state(result: dict) -> None:
    if "started_new_run" not in result:
        return
    if result.get("started_new_run") is True:
        typer.echo("run_start: started_new_agent_native_run")
    elif result.get("complete") is True:
        typer.echo("run_start: replayed_existing_terminal_run")
    else:
        typer.echo("run_start: resumed_existing_agent_native_run")


def _print_agent_step_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(_agent_submit_json_payload(result))
        return
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run.get('run_status') or run.get('status')}")
    _print_agent_submitted_step(result.get("submitted_step"))
    print_run_contract_summary(run)
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    if result.get("complete"):
        print_task_verdict(task_verdict)
        _print_terminal_task_next_action(task_verdict, result.get("task_next_action"))
    typer.echo(f"run_url: {result.get('run_url') or result.get('run_path')}")
    _print_web_status(result)
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if result.get("complete"):
        _print_agent_native_terminal_state(task_verdict)
    elif next_step:
        _print_agent_current_step(next_step)


def _print_agent_next_result(result: dict, *, json_output: bool) -> None:
    if json_output:
        echo_json(_agent_next_json_payload(result))
        return
    _print_agent_step_result(result, json_output=False)


def _agent_next_json_payload(result: dict) -> dict:
    payload = {"agent_next_summary": _agent_next_summary(result)}
    payload.update(result)
    return payload


def _agent_next_summary(result: dict) -> dict:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
        "complete": bool(result.get("complete")),
        "handoff_kind": "current_step",
    }
    next_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)
    if next_summary:
        summary["next_step"] = next_summary
    _set_summary_text(summary, "run_url", result.get("run_url") or result.get("run_path"))
    verdict_status = _task_verdict_status(task_verdict)
    _set_summary_text(summary, "task_verdict_status", verdict_status)
    verdict_summary = ""
    if isinstance(task_verdict, dict):
        verdict_summary = _clip_inline(str(task_verdict.get("summary") or ""), 220)
        _set_summary_text(summary, "task_verdict_summary", verdict_summary)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    summary.update(
        _agent_task_proof_summary(
            complete=bool(result.get("complete")),
            task_verdict_status=verdict_status,
            task_verdict_summary=verdict_summary,
            task_next_action=task_next_action,
        )
    )
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_submit_json_payload(result: dict) -> dict:
    payload = {"agent_submit_summary": _agent_submit_summary(result)}
    payload.update(result)
    return payload


def _agent_submit_summary(result: dict) -> dict:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    adapter = str(result.get("adapter") or next_step.get("adapter") or "").strip() or "codex"
    workdir = str(result.get("workdir") or run.get("workdir") or "").strip() or "$PWD"
    task_verdict = run.get("task_verdict") or run.get("task_verdict_json")
    summary: dict[str, object] = {
        "schema_version": 1,
        "run_id": str(run.get("id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
        "complete": bool(result.get("complete")),
    }
    submitted_summary = _agent_submitted_step_summary(result.get("submitted_step"))
    if submitted_summary:
        summary["submitted_step"] = submitted_summary
    next_summary = _agent_next_step_summary(next_step, adapter=adapter, workdir=workdir)
    if next_summary:
        summary["next_step"] = next_summary
    _set_summary_text(summary, "run_url", result.get("run_url") or result.get("run_path"))
    verdict_status = _task_verdict_status(task_verdict)
    _set_summary_text(summary, "task_verdict_status", verdict_status)
    verdict_summary = ""
    if isinstance(task_verdict, dict):
        verdict_summary = _clip_inline(str(task_verdict.get("summary") or ""), 220)
        _set_summary_text(summary, "task_verdict_summary", verdict_summary)
    task_next_action = result.get("task_next_action") if isinstance(result.get("task_next_action"), dict) else {}
    if task_next_action:
        summary["task_next_action"] = task_next_action
    summary.update(
        _agent_task_proof_summary(
            complete=bool(result.get("complete")),
            task_verdict_status=verdict_status,
            task_verdict_summary=verdict_summary,
            task_next_action=task_next_action,
        )
    )
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_submitted_step_summary(submitted_step: object) -> dict:
    if not isinstance(submitted_step, dict) or not submitted_step:
        return {}
    summary: dict[str, object] = {}
    _set_summary_text(summary, "step_id", submitted_step.get("step_id"))
    _set_summary_text(summary, "status", submitted_step.get("status"))
    _set_summary_list(summary, "evidence_refs", submitted_step.get("evidence_refs"))
    coverage_results = _submitted_coverage_result_summaries(submitted_step.get("coverage_results"), limit=8)
    if coverage_results:
        summary["coverage_results"] = coverage_results
        summary["coverage_result_counts"] = _coverage_result_counts(submitted_step.get("coverage_results"))
        raw_coverage_results = [item for item in list(submitted_step.get("coverage_results") or []) if isinstance(item, dict)]
        if len(raw_coverage_results) > len(coverage_results):
            summary["coverage_results_omitted"] = len(raw_coverage_results) - len(coverage_results)
    raw_blocking_items = [str(item).strip() for item in list(submitted_step.get("blocking_items") or []) if str(item).strip()]
    blocking_items = [_actionable_blocking_item(item) for item in raw_blocking_items]
    _set_summary_list(summary, "blocking_items", blocking_items)
    raw_next_action = str(submitted_step.get("recommended_next_action") or "").strip()
    status = str(submitted_step.get("status") or "").strip()
    if _submitted_step_is_blocked(status):
        next_action = _actionable_next_action(raw_next_action, blocking_items)
        _set_summary_text(summary, "recommended_next_action", next_action)
    _set_summary_text(summary, "handoff_path", submitted_step.get("handoff_absolute_path") or submitted_step.get("handoff_path"))
    _set_summary_text(summary, "summary", _clip_inline(str(submitted_step.get("summary") or ""), 220))
    return summary


def _agent_next_step_summary(next_step: dict, *, adapter: str = "", workdir: str = "") -> dict:
    if not next_step:
        return {}
    role = next_step.get("role") if isinstance(next_step.get("role"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    submit_hint = next_step.get("submit_hint") if isinstance(next_step.get("submit_hint"), dict) else {}
    action_policy = next_step.get("action_policy") if isinstance(next_step.get("action_policy"), dict) else {}
    summary: dict[str, object] = {}
    _set_summary_text(summary, "step_id", next_step.get("step_id"))
    _set_summary_text(summary, "role", role.get("name") or role.get("id"))
    _set_summary_text(summary, "target_agent", role_dispatch.get("target_agent"))
    _set_summary_text(summary, "target_agent_config", role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path"))
    if "target_agent_config_exists" in role_dispatch:
        summary["target_agent_config_exists"] = role_dispatch.get("target_agent_config_exists") is True
    dispatch_next = _agent_dispatch_next_summary(role_dispatch)
    _set_summary_text(summary, "dispatch_next", dispatch_next)
    dispatch_unavailable = _agent_dispatch_unavailable_summary(
        adapter=str(next_step.get("adapter") or adapter or "").strip() or "codex",
        workdir=str(workdir or "").strip() or "$PWD",
        role_dispatch=role_dispatch,
    )
    if dispatch_unavailable:
        summary["dispatch_unavailable"] = dispatch_unavailable
    _set_summary_text(summary, "action_policy", _action_policy_summary(action_policy))
    _attach_agent_next_step_submit_summary(summary, next_step, submit_hint)
    _attach_agent_next_step_evidence_summary(summary, next_step)
    _attach_agent_next_step_coverage_summary(summary, next_step)
    iteration_repair = _agent_iteration_repair_summary(next_step.get("iteration_repair"))
    if iteration_repair:
        summary["iteration_repair"] = iteration_repair
    summary.update(_agent_next_step_continuation_summary(next_step))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_agent_next_step_submit_summary(summary: dict[str, object], next_step: dict, submit_hint: dict) -> None:
    _set_summary_text(summary, "context_path", next_step.get("context_absolute_path") or next_step.get("context_path"))
    _set_summary_text(summary, "capsule_path", next_step.get("capsule_absolute_path") or next_step.get("capsule_path"))
    _set_summary_text(summary, "result_template", submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path"))
    _set_summary_text(summary, "result_file_to_write", submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path"))
    _set_summary_text(summary, "result_template_contract", submit_hint.get("result_file_contract"))
    if submit_hint.get("result_file_contract") or submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path"):
        summary["result_template_fill"] = (
            "open the template, save a filled copy to result_file_to_write, replace null placeholders in result, keep loopora_host_dispatch, then submit"
        )
    _set_summary_text(summary, "result_outbox_dir", submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir"))
    _set_summary_text(summary, "submit_command", submit_hint.get("command"))


def _attach_agent_next_step_evidence_summary(summary: dict[str, object], next_step: dict) -> None:
    known_count = _non_bool_int(next_step.get("known_evidence_count"))
    if known_count is not None:
        summary["known_evidence_count"] = known_count
    known_ids = [str(item).strip() for item in list(next_step.get("known_evidence_ids") or []) if str(item).strip()]
    if known_ids:
        displayed_known_ids = known_ids[-8:]
        if len(known_ids) > len(displayed_known_ids):
            summary["known_evidence_ids_omitted"] = len(known_ids) - len(displayed_known_ids)
        summary["known_evidence_ids"] = displayed_known_ids
    known_refs = _agent_known_evidence_ref_summaries(next_step.get("known_evidence_refs"), limit=5)
    if known_refs:
        summary["known_evidence_refs"] = known_refs
    _set_summary_text(summary, "known_evidence_scope", _agent_current_step_evidence_scope_summary(next_step))


def _attach_agent_next_step_coverage_summary(summary: dict[str, object], next_step: dict) -> None:
    required_coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    coverage_summary = _required_coverage_summary(required_coverage)
    _set_summary_text(summary, "required_coverage", coverage_summary)
    _set_summary_text(summary, "coverage_classification_note", _agent_coverage_classification_note(next_step))
    top_gaps = _coverage_gap_summaries(required_coverage.get("top_gaps"), limit=5)
    if top_gaps:
        summary["top_coverage_gaps"] = top_gaps


def _agent_dispatch_next_summary(role_dispatch: dict) -> str:
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if not target_agent or role_dispatch.get("target_agent_config_exists") is False:
        return ""
    return f"invoke {target_agent} with the next context/capsule paths below; do not perform this role inline"


def _agent_dispatch_unavailable_summary(*, adapter: str, workdir: str, role_dispatch: dict) -> dict[str, object]:
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if not target_agent or role_dispatch.get("target_agent_config_exists") is not False:
        return {}
    target_config = str(
        role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path") or ""
    ).strip()
    normalized_adapter = str(adapter or "").strip() or "codex"
    normalized_workdir = str(workdir or "").strip() or "$PWD"
    return {
        "reason": "target_agent_config_missing",
        "target_agent": target_agent,
        "target_agent_config": target_config,
        "check_command": prefix_loopora_command(
            f"loopora agent {normalized_adapter} check --workdir {shlex.quote(normalized_workdir)}"
        ),
        "repair_command": prefix_loopora_command(f"loopora init {normalized_adapter} --workdir {shlex.quote(normalized_workdir)}"),
        "next": "repair the managed role agent config before dispatching this role; do not submit inline role work",
    }


def _agent_iteration_repair_summary(repair: object) -> dict[str, object]:
    if not isinstance(repair, dict) or repair.get("active") is not True:
        return {}
    summary: dict[str, object] = {"active": True}
    _set_summary_text(summary, "source_step_id", repair.get("source_step_id"))
    _set_summary_text(summary, "source_role", repair.get("source_role"))
    _set_summary_text(summary, "status", repair.get("status"))
    _set_summary_text(summary, "summary", _clip_inline(str(repair.get("summary") or ""), 220))
    blocking_items = _evidence_scope_items(repair.get("blocking_items"))
    actionable_blockers = [_actionable_blocking_item(item) for item in blocking_items]
    if actionable_blockers:
        summary["blocking_items"] = [_clip_inline(item, 220) for item in actionable_blockers[:5]]
    next_action = _actionable_next_action(str(repair.get("recommended_next_action") or "").strip(), actionable_blockers)
    _set_summary_text(summary, "recommended_next_action", _clip_inline(next_action, 220))
    evidence_refs = _evidence_scope_items(repair.get("evidence_refs"))
    if evidence_refs:
        summary["evidence_refs"] = evidence_refs[:5]
    top_gaps = _coverage_gap_summaries(repair.get("top_gaps"), limit=5)
    if top_gaps:
        summary["top_gaps"] = top_gaps
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _agent_next_step_continuation_summary(next_step: dict) -> dict[str, object]:
    continuation = next_step.get("continuation") if isinstance(next_step.get("continuation"), dict) else {}
    if not continuation or continuation.get("active") is not True:
        return {}
    previous_verdict = (
        continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    )
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    summary: dict[str, object] = {"active": True}
    _set_summary_text(summary, "previous_run_id", continuation.get("previous_run_id"))
    _set_summary_text(summary, "previous_task_verdict_status", previous_verdict.get("status"))
    _set_summary_text(summary, "previous_task_verdict_summary", _clip_inline(str(previous_verdict.get("summary") or ""), 220))
    missing_required_check_count = _non_bool_int(coverage.get("missing_check_count"))
    if missing_required_check_count is not None:
        summary["missing_required_check_count"] = missing_required_check_count
    missing_target_count = _non_bool_int(coverage.get("missing_target_count"))
    if missing_target_count is not None:
        summary["missing_target_count"] = missing_target_count
    raw_next_focus = continuation.get("next_focus")
    next_focus = (
        [_clip_inline(str(item), 220) for item in list(raw_next_focus or []) if str(item).strip()]
        if isinstance(raw_next_focus, list)
        else []
    )
    if next_focus:
        summary["next_focus"] = next_focus[:6]
    return {"continuation": {key: value for key, value in summary.items() if value not in ("", [], {})}}


def _print_agent_submitted_step(submitted_step: object) -> None:
    if not isinstance(submitted_step, dict) or not submitted_step:
        return
    step_id = str(submitted_step.get("step_id") or "").strip()
    if step_id:
        typer.echo(f"submitted_step_id: {step_id}")
    status = str(submitted_step.get("status") or "").strip()
    if status:
        typer.echo(f"submitted_status: {status}")
    evidence_refs = [str(item) for item in list(submitted_step.get("evidence_refs") or []) if str(item).strip()]
    _print_agent_submitted_step_list("submitted_evidence_refs", evidence_refs, limit=8)
    _print_agent_submitted_coverage_results(submitted_step.get("coverage_results"))
    if _submitted_step_is_blocked(status):
        blocking_items = [
            _actionable_blocking_item(str(item).strip()) for item in list(submitted_step.get("blocking_items") or []) if str(item).strip()
        ]
        _print_agent_submitted_step_list("submitted_blocking_items", blocking_items, limit=6, clip_items=True)
        next_action = _actionable_next_action(str(submitted_step.get("recommended_next_action") or "").strip(), blocking_items)
        if next_action:
            typer.echo(f"submitted_next_action: {_clip(next_action, 220)}")
    handoff_path = str(submitted_step.get("handoff_absolute_path") or submitted_step.get("handoff_path") or "").strip()
    if handoff_path:
        typer.echo(f"submitted_handoff_path: {handoff_path}")
    summary = str(submitted_step.get("summary") or "").strip()
    if summary:
        typer.echo(f"submitted_summary: {_clip(summary, 220)}")


def _submitted_step_is_blocked(status: str) -> bool:
    return status.strip().lower() in {"blocked", "failed", "errored", "rejected"}


def _actionable_blocking_item(item: str) -> str:
    cleaned = str(item or "").strip()
    if not cleaned or ":" in cleaned:
        return cleaned
    target_explanation = _coverage_target_blocker_explanation(cleaned)
    if target_explanation:
        return f"{cleaned}: {target_explanation}"
    explanations = {
        "gatekeeper_pass_has_unmanaged_residual_risk": (
            "residual_risks must name an owner, follow-up, or acceptance path; otherwise move the risk to blocking_issues before passing"
        ),
        "gatekeeper_pass_violates_no_residual_risk_policy": (
            "the run contract disallows accepted residual risk; resolve the risk or report it as blocking before passing"
        ),
        "gatekeeper_pass_refs_not_supporting_evidence": (
            "a pass must cite upstream evidence that is not blocked, failed, rejected, or errored; produce direct project-owned proof or mark passed=false"
        ),
        "gatekeeper_pass_requires_evidence_refs": (
            "a pass must cite exact supporting evidence_refs from known_evidence_ids; copy a supporting id or mark passed=false"
        ),
        "gatekeeper_pass_requires_upstream_or_measured_evidence": (
            "a pass needs supporting upstream evidence or measured self evidence; produce that proof before asking GateKeeper to pass"
        ),
    }
    explanation = explanations.get(cleaned)
    return f"{cleaned}: {explanation}" if explanation else cleaned


def _coverage_target_blocker_explanation(cleaned: str) -> str:
    if re.fullmatch(r"check_\d+", cleaned):
        return "required check id; see required_coverage.missing_check_ids and top_coverage_gaps for the contract text"
    if re.fullmatch(r"done_when\.check_\d+", cleaned):
        return "coverage target id; see required_coverage.top_coverage_gaps for status, text, and evidence refs"
    if re.fullmatch(r"(?:fake_done\.risk|evidence_preference\.pref|success_surface\.surface)_\d+", cleaned):
        return "coverage target id; see top_coverage_gaps for status, text, and evidence refs"
    if cleaned == "gatekeeper.finish":
        return "GateKeeper finish target; cite supporting evidence or keep the run blocked"
    return ""


def _actionable_next_action(action: str, blocking_items: list[str]) -> str:
    cleaned = str(action or "").strip()
    normalized_cleaned = cleaned.strip(".").strip().lower()
    generic_actions = {
        "",
        "Continue only after the blocking issues are resolved.",
        "Continue only after the blocking issues are resolved",
        "None.",
        "None",
        "No action needed.",
        "No action needed",
        "No action required.",
        "No action required",
        "N/A",
        "n/a",
        "na",
    }
    if cleaned not in generic_actions and normalized_cleaned not in {"none", "n/a", "na", "not applicable", "no action needed", "no action required"}:
        return cleaned
    joined = " ".join(blocking_items)
    actionable = cleaned
    if "gatekeeper_pass_has_unmanaged_residual_risk" in joined:
        actionable = (
            "Resolve the residual risk or make it managed with an owner, follow-up, or acceptance path before asking GateKeeper to pass again."
        )
    elif "gatekeeper_pass_violates_no_residual_risk_policy" in joined:
        actionable = "Resolve the residual risk or report it as blocking before asking GateKeeper to pass again."
    elif "gatekeeper_pass_refs_not_supporting_evidence" in joined:
        actionable = (
            "Produce new project-owned proof or cite a non-blocked supporting evidence ref before asking GateKeeper to pass again; "
            "otherwise submit GateKeeper with passed=false and blocking_issues."
        )
    elif "gatekeeper_pass_requires_evidence_refs" in joined:
        actionable = "Copy exact supporting evidence_refs from known_evidence_ids before asking GateKeeper to pass again."
    elif "gatekeeper_pass_requires_upstream_or_measured_evidence" in joined:
        actionable = "Add upstream or measured evidence for the required targets before asking GateKeeper to pass again."
    return actionable


def _print_agent_submitted_step_list(label: str, items: list[str], *, limit: int, clip_items: bool = False) -> None:
    if not items:
        return
    typer.echo(f"{label}:")
    for item in items[:limit]:
        typer.echo(f"- {_clip(item, 220) if clip_items else item}")
    if len(items) > limit:
        typer.echo(f"{label}_more: {len(items) - limit}")


def _print_agent_submitted_coverage_results(value: object) -> None:
    summaries = _submitted_coverage_result_summaries(value, limit=8)
    if not summaries:
        return
    counts = _coverage_result_counts(value)
    if counts:
        parts = [f"{status}={count}" for status, count in counts.items()]
        typer.echo(f"submitted_coverage_result_counts: {' '.join(parts)}")
    typer.echo("submitted_coverage_results:")
    for item in summaries:
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        refs = item.get("evidence_refs") if isinstance(item.get("evidence_refs"), list) else []
        refs_part = f" refs={','.join(str(ref) for ref in refs[:4])}" if refs else ""
        note = str(item.get("note") or "").strip()
        note_part = f": {_clip(note, 180)}" if note else ""
        typer.echo(f"- {target_id} {status}{refs_part}{note_part}")
    raw_items = [item for item in list(value or []) if isinstance(item, dict)] if isinstance(value, list) else []
    if len(raw_items) > len(summaries):
        typer.echo(f"submitted_coverage_results_more: {len(raw_items) - len(summaries)}")


def _submitted_coverage_result_summaries(value: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    summaries: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if not target_id or not status:
            continue
        summary: dict[str, object] = {"target_id": target_id, "status": status}
        evidence_refs = [str(ref).strip() for ref in list(item.get("evidence_refs") or []) if str(ref).strip()]
        if evidence_refs:
            summary["evidence_refs"] = evidence_refs[:6]
        note = str(item.get("note") or "").strip()
        if note:
            summary["note"] = _clip_inline(note, 180)
        summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def _coverage_result_counts(value: object) -> dict[str, int]:
    if not isinstance(value, list):
        return {}
    counts: dict[str, int] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip()
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _task_verdict_status(task_verdict: object) -> str:
    if isinstance(task_verdict, dict):
        return str(task_verdict.get("status") or "").strip()
    return ""


def _agent_task_proof_summary(
    *,
    complete: bool,
    task_verdict_status: str,
    task_verdict_summary: str,
    task_next_action: dict,
) -> dict[str, object]:
    status = str(task_verdict_status or "").strip()
    action = task_next_action if isinstance(task_next_action, dict) else {}
    action_kind = str(action.get("kind") or "").strip()
    if not (complete or status or action_kind):
        return {}

    task_proven = status in PASSING_TASK_VERDICT_STATUSES
    if task_proven:
        task_outcome = "already_proven_no_new_evidence" if action_kind == "already_passed" else "proven"
    elif action_kind == "continue_evidence":
        task_outcome = "not_proven_continue_evidence"
    elif complete:
        task_outcome = "not_proven"
    elif status and status != "not_evaluated":
        task_outcome = "not_proven_continue_evidence"
    else:
        task_outcome = "not_yet_evaluated"

    summary: dict[str, object] = {
        "task_proven": task_proven,
        "task_outcome": task_outcome,
        "lifecycle_vs_task": "run_lifecycle_active_task_proven" if task_proven else "run_lifecycle_active_task_not_proven",
    }
    if complete:
        summary["lifecycle_vs_task"] = (
            "run_lifecycle_complete_task_proven" if task_proven else "run_lifecycle_complete_task_not_proven"
        )
    if action_kind == "continue_evidence":
        summary["next_loop_command"] = str(action.get("next_loop_command") or "/loopora-run").strip()
        summary["next_plan_action"] = str(
            action.get("plan_action") or "open_run_url_improve_with_evidence_if_loop_needs_adjustment"
        ).strip()
        next_focus = _clip_inline(str(action.get("task_verdict_summary") or task_verdict_summary or ""), 220)
        if next_focus:
            summary["next_evidence_focus"] = next_focus
    elif not task_proven and task_outcome == "not_proven_continue_evidence" and task_verdict_summary:
        summary["next_evidence_focus"] = _clip_inline(task_verdict_summary, 220)
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _print_agent_native_terminal_state(task_verdict: object) -> None:
    status = _task_verdict_status(task_verdict)
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo("agent_native: complete")
        return
    if not status:
        status = "not_evaluated"
    typer.echo("agent_native: lifecycle_closed_task_unproven")
    typer.echo(f"agent_native_task_verdict: {status}")


def _print_terminal_task_next_action(task_verdict: object, task_next_action: object = None) -> None:
    action = task_next_action if isinstance(task_next_action, dict) else {}
    status = _task_verdict_status(task_verdict)
    summary = ""
    if isinstance(task_verdict, dict):
        summary = str(task_verdict.get("summary") or "").strip()
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo("task_next_action: task verdict already passed; no new evidence pass will start unless the task scope changes")
        return
    if not status:
        status = "not_evaluated"
    guidance = str(action.get("guidance") or "").strip() if action else ""
    typer.echo(
        "task_next_action: "
        + (
            guidance
            if guidance
            else "run lifecycle is complete but the task is not proven; run /loopora-run again in this Agent session to start the next evidence pass"
        )
    )
    typer.echo(f"next_loop_command: {(action.get('next_loop_command') or '/loopora-run')!s}")
    plan_action = str(action.get("plan_action") or "").strip()
    if plan_action == "open_run_url_improve_with_evidence_if_loop_needs_adjustment":
        typer.echo("next_plan_action: open run_url and use Improve plan with evidence if the Loop itself needs adjustment")
    elif plan_action:
        typer.echo(f"next_plan_action: {plan_action}")
    else:
        typer.echo("next_plan_action: open run_url and use Improve plan with evidence if the Loop itself needs adjustment")
    action_summary = str(action.get("task_verdict_summary") or "").strip()
    if action_summary:
        summary = action_summary
    if summary:
        typer.echo(f"next_evidence_focus: {_clip(summary, 220)}")


def _print_agent_current_step(next_step: dict) -> None:
    role = next_step.get("role") if isinstance(next_step.get("role"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    action_policy = next_step.get("action_policy") if isinstance(next_step.get("action_policy"), dict) else {}
    submit_hint = next_step.get("submit_hint") if isinstance(next_step.get("submit_hint"), dict) else {}
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    typer.echo(f"next_step_id: {next_step.get('step_id')}")
    typer.echo(f"next_role: {role.get('name') or role.get('id')}")
    _print_agent_iteration_context(next_step)
    if target_agent:
        typer.echo(f"next_target_agent: {target_agent}")
        target_agent_config = str(
            role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path") or ""
        ).strip()
        if target_agent_config:
            typer.echo(f"next_target_agent_config: {target_agent_config}")
        if "target_agent_config_exists" in role_dispatch:
            typer.echo(f"next_target_agent_config_exists: {str(role_dispatch.get('target_agent_config_exists') is True).lower()}")
        if role_dispatch.get("target_agent_config_exists") is False:
            adapter = str(next_step.get("adapter") or "").strip() or "codex"
            check_command = prefix_loopora_command(f'loopora agent {adapter} check --workdir "$PWD"')
            repair_command = prefix_loopora_command(f'loopora init {adapter} --workdir "$PWD"')
            typer.echo(
                "dispatch_unavailable: "
                f"{target_agent} config is missing; run {check_command} "
                f"and repair with {repair_command} before dispatching this role"
            )
        else:
            typer.echo(
                f"dispatch_next: invoke {target_agent} with the next context/capsule paths below; do not perform this role inline"
            )
    _print_agent_continuation(next_step.get("continuation"))
    action_summary = _action_policy_summary(action_policy)
    if action_summary:
        typer.echo(f"next_action_policy: {action_summary}")
    coverage_summary = _required_coverage_summary(next_step.get("required_coverage"))
    if coverage_summary:
        typer.echo(f"required_coverage: {coverage_summary}")
    coverage_note = _agent_coverage_classification_note(next_step)
    if coverage_note:
        typer.echo(f"coverage_classification_note: {coverage_note}")
    _print_top_coverage_gaps(next_step.get("required_coverage"))
    _print_agent_current_step_paths(next_step, submit_hint)
    _print_agent_current_step_submit_hint(submit_hint)


def _print_agent_iteration_context(next_step: dict) -> None:
    iteration = _non_bool_int(next_step.get("iter"))
    step_order = _non_bool_int(next_step.get("step_order"))
    if iteration is None:
        return
    typer.echo(f"next_iteration: {iteration}")
    if step_order is not None:
        typer.echo(f"next_step_order: {step_order}")
    if iteration > 0 and (step_order or 0) == 0:
        typer.echo("iteration_continuation: previous iteration completed without closing the run; address current coverage gaps in this next pass")
        _print_agent_iteration_repair(next_step.get("iteration_repair"))


def _print_agent_current_step_paths(next_step: dict, submit_hint: dict) -> None:
    context_path = str(next_step.get("context_absolute_path") or next_step.get("context_path") or "").strip()
    if context_path:
        typer.echo(f"next_context_path: {context_path}")
    capsule_path = str(next_step.get("capsule_absolute_path") or next_step.get("capsule_path") or "").strip()
    if capsule_path:
        typer.echo(f"next_capsule_path: {capsule_path}")
    known_evidence_count = _non_bool_int(next_step.get("known_evidence_count"))
    if known_evidence_count is None and isinstance(next_step.get("known_evidence_ids"), list):
        known_evidence_count = len(next_step["known_evidence_ids"])
    if known_evidence_count is not None:
        typer.echo(f"known_evidence_count: {known_evidence_count}")
    _print_agent_current_step_evidence_scope(next_step)
    _print_agent_current_step_known_evidence(next_step.get("known_evidence_ids"))
    _print_agent_current_step_known_evidence_refs(next_step.get("known_evidence_refs"))
    result_template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
    if result_template_path:
        typer.echo(f"result_template_path: {result_template_path}")


def _print_agent_iteration_repair(repair: object) -> None:
    if not isinstance(repair, dict) or repair.get("active") is not True:
        return
    source_step = str(repair.get("source_step_id") or "").strip()
    source_role = str(repair.get("source_role") or "").strip()
    if source_step or source_role:
        source = source_step
        if source_role:
            source = f"{source_step} ({source_role})" if source_step else source_role
        typer.echo(f"iteration_repair_source: {source}")
    summary = str(repair.get("summary") or "").strip()
    if summary:
        typer.echo(f"iteration_repair_summary: {_clip(summary, 220)}")
    blocking_items = _evidence_scope_items(repair.get("blocking_items"))
    if blocking_items:
        typer.echo("iteration_repair_blocking_items:")
        for item in blocking_items[:5]:
            typer.echo(f"- {_clip(_actionable_blocking_item(item), 220)}")
    next_action = _actionable_next_action(str(repair.get("recommended_next_action") or "").strip(), [_actionable_blocking_item(item) for item in blocking_items])
    if next_action:
        typer.echo(f"iteration_repair_next_action: {_clip(next_action, 220)}")
    evidence_refs = _evidence_scope_items(repair.get("evidence_refs"))
    if evidence_refs:
        typer.echo("iteration_repair_evidence_refs:")
        for item in evidence_refs[:5]:
            typer.echo(f"- {item}")


def _print_agent_current_step_evidence_scope(next_step: dict) -> None:
    scope = _agent_current_step_evidence_scope_summary(next_step)
    if scope:
        typer.echo(f"known_evidence_scope: {scope}")


def _agent_current_step_evidence_scope_summary(next_step: dict) -> str:
    inputs = next_step.get("inputs") if isinstance(next_step.get("inputs"), dict) else {}
    evidence_query = inputs.get("evidence_query") if isinstance(inputs.get("evidence_query"), dict) else {}
    if not evidence_query:
        return ""
    parts: list[str] = []
    archetypes = _evidence_scope_items(evidence_query.get("archetypes"))
    if archetypes:
        parts.append(f"archetypes={','.join(archetypes[:6])}")
    role_ids = _evidence_scope_items(evidence_query.get("role_ids"))
    if role_ids:
        parts.append(f"role_ids={','.join(role_ids[:6])}")
    step_ids = _evidence_scope_items(evidence_query.get("step_ids"))
    if step_ids:
        parts.append(f"step_ids={','.join(step_ids[:6])}")
    limit = _non_bool_int(evidence_query.get("limit"))
    if limit is not None:
        parts.append(f"limit={limit}")
    parallel_group = str(next_step.get("parallel_group") or "").strip()
    if parallel_group:
        parts.append(f"parallel_group={parallel_group}")
        parts.append("snapshot=group_start")
    if _current_step_has_coverage_gap_evidence_refs(next_step):
        parts.append("coverage_gap_refs=included")
    if parts:
        return "filtered by evidence_query " + " ".join(parts)
    return ""


def _current_step_has_coverage_gap_evidence_refs(next_step: dict) -> bool:
    coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    top_gaps = coverage.get("top_gaps")
    if not isinstance(top_gaps, list):
        return False
    for gap in top_gaps:
        if not isinstance(gap, dict):
            continue
        evidence_refs = gap.get("evidence_refs")
        if isinstance(evidence_refs, list) and any(str(item).strip() for item in evidence_refs):
            return True
    return False


def _evidence_scope_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _print_agent_current_step_known_evidence(known_evidence_ids: object) -> None:
    if not isinstance(known_evidence_ids, list):
        return
    ids = [str(item).strip() for item in known_evidence_ids if str(item).strip()]
    if not ids:
        return
    displayed_ids = ids[-8:]
    if len(ids) > len(displayed_ids):
        typer.echo(f"known_evidence_ids_omitted: {len(ids) - len(displayed_ids)} older")
    typer.echo("known_evidence_ids:")
    for evidence_id in displayed_ids:
        typer.echo(f"- {evidence_id}")


def _print_agent_current_step_known_evidence_refs(known_evidence_refs: object) -> None:
    summaries = _agent_known_evidence_ref_summaries(known_evidence_refs, limit=5)
    if not summaries:
        return
    refs = _known_evidence_ref_items(known_evidence_refs)
    omitted = max(0, len(refs) - len(summaries))
    if omitted:
        typer.echo(f"known_evidence_refs_omitted: {omitted} older")
    typer.echo("known_evidence_refs:")
    for item in summaries:
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
        typer.echo(f"- {' '.join(part for part in parts if part)}")
        claim = str(item.get("claim") or "").strip()
        if claim:
            typer.echo(f"  claim: {claim}")
        coverage_targets = item.get("coverage_target_ids") if isinstance(item.get("coverage_target_ids"), list) else []
        if coverage_targets:
            typer.echo(f"  coverage_targets: {', '.join(str(target) for target in coverage_targets)}")
        rendered_artifacts = _format_known_evidence_artifact_refs(item.get("artifact_refs"))
        if rendered_artifacts:
            typer.echo(f"  artifacts: {rendered_artifacts}")


def _known_evidence_ref_items(known_evidence_refs: object) -> list[dict]:
    if not isinstance(known_evidence_refs, list):
        return []
    return [item for item in known_evidence_refs if isinstance(item, dict)]


def _format_known_evidence_artifact_refs(artifact_refs: object) -> str:
    if not isinstance(artifact_refs, list):
        return ""
    rendered_refs: list[str] = []
    for ref in artifact_refs[:4]:
        if not isinstance(ref, dict):
            continue
        label = str(ref.get("label") or "").strip()
        path = str(ref.get("path") or "").strip()
        if path:
            rendered_refs.append(f"{label}: {path}" if label else path)
    return "; ".join(rendered_refs)


def _agent_known_evidence_ref_summaries(known_evidence_refs: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(known_evidence_refs, list):
        return []
    refs = [item for item in known_evidence_refs if isinstance(item, dict)]
    if not refs:
        return []
    displayed = refs[-limit:]
    summaries: list[dict[str, object]] = []
    for item in displayed:
        summary: dict[str, object] = {}
        _set_summary_text(summary, "id", item.get("id"))
        _set_summary_text(summary, "step_id", item.get("step_id"))
        _set_summary_text(summary, "role_name", item.get("role_name"))
        _set_summary_text(summary, "result", item.get("result"))
        _set_summary_text(summary, "gatekeeper_support", item.get("gatekeeper_support"))
        _set_summary_text(summary, "gatekeeper_support_reason", _clip_inline(str(item.get("gatekeeper_support_reason") or ""), 160))
        _set_summary_text(summary, "claim", _clip_inline(str(item.get("claim") or ""), 220))
        coverage_value = item.get("coverage_target_ids")
        coverage_targets = [str(target).strip() for target in coverage_value if str(target).strip()] if isinstance(coverage_value, list) else []
        if coverage_targets:
            summary["coverage_target_ids"] = coverage_targets[:6]
        artifact_value = item.get("artifact_refs")
        artifact_refs = [
            {
                key: value
                for key, value in {
                    "label": _clip_inline(str(artifact.get("label") or ""), 80),
                    "path": _clip_inline(str(artifact.get("path") or ""), 160),
                }.items()
                if value
            }
            for artifact in artifact_value
            if isinstance(artifact, dict) and str(artifact.get("path") or "").strip()
        ] if isinstance(artifact_value, list) else []
        if artifact_refs:
            summary["artifact_refs"] = artifact_refs[:4]
        if summary:
            summaries.append(summary)
    return summaries


def _print_agent_current_step_submit_hint(submit_hint: dict) -> None:
    result_template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
    result_contract = str(submit_hint.get("result_file_contract") or "").strip()
    if result_contract:
        typer.echo(f"result_template_contract: {result_contract}")
    result_file_path = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
    if result_file_path:
        typer.echo(f"result_file_to_write: {result_file_path}")
    if result_template_path or result_contract:
        if result_file_path:
            typer.echo(
                "result_template_fill: open the template, save a filled copy to result_file_to_write, "
                "replace null placeholders in result, keep loopora_host_dispatch, then submit"
            )
        else:
            typer.echo("result_template_fill: open the template, replace null placeholders in result, keep loopora_host_dispatch, then submit the filled copy")
    result_outbox_dir = str(submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir") or "").strip()
    if result_outbox_dir:
        typer.echo(f"result_outbox_dir: {result_outbox_dir}")
    submit_command = str(submit_hint.get("command") or "").strip()
    if submit_command:
        typer.echo(f"submit_hint: {submit_command}")


def _print_agent_continuation(continuation: object) -> None:
    if not isinstance(continuation, dict) or continuation.get("active") is not True:
        return
    verdict = continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    previous_run_id = str(continuation.get("previous_run_id") or "").strip()
    if previous_run_id:
        typer.echo(f"continuation_previous_run: {previous_run_id}")
    status = str(verdict.get("status") or "").strip()
    if status:
        typer.echo(f"continuation_task_verdict: {status}")
    summary = str(verdict.get("summary") or "").strip()
    if summary:
        typer.echo(f"continuation_task_verdict_summary: {_clip(summary, 200)}")
    _print_continuation_coverage(coverage)
    _print_continuation_focus_items("blocking", continuation.get("focus_blocking"))
    _print_continuation_focus_items("unproven", continuation.get("focus_unproven"))
    _print_continuation_focus_items("weak", continuation.get("focus_weak"))
    _print_continuation_next_focus(continuation.get("next_focus"))


def _print_continuation_coverage(coverage: dict) -> None:
    missing = coverage.get("missing_check_count")
    covered = coverage.get("covered_check_count")
    if covered is not None or missing is not None:
        typer.echo(f"continuation_required_coverage: {covered or 0} covered / {missing or 0} missing")
    target_count = coverage.get("target_count")
    covered_targets = coverage.get("covered_target_count")
    weak_targets = coverage.get("weak_target_count")
    missing_targets = coverage.get("missing_target_count")
    blocked_targets = coverage.get("blocked_target_count")
    if target_count:
        target_bits = [f"{covered_targets or 0} covered"]
        if weak_targets:
            target_bits.append(f"{weak_targets} weak")
        if missing_targets:
            target_bits.append(f"{missing_targets} missing")
        if blocked_targets:
            target_bits.append(f"{blocked_targets} blocked")
        typer.echo(f"continuation_coverage_targets: {target_count} total ({' / '.join(target_bits)})")


def _print_continuation_next_focus(items: object) -> None:
    next_focus = [str(item).strip() for item in list(items or []) if str(item).strip()]
    if next_focus:
        typer.echo("continuation_next_focus:")
        for item in next_focus[:5]:
            typer.echo(f"- {item}")


def _print_continuation_focus_items(label: str, items: object) -> None:
    focus_items = [str(item).strip() for item in list(items or []) if str(item).strip()]
    if not focus_items:
        return
    typer.echo(f"continuation_{label}:")
    for item in focus_items[:4]:
        typer.echo(f"- {_clip(item, 180)}")


def _action_policy_summary(action_policy: dict) -> str:
    workspace = str(action_policy.get("workspace") or "").strip()
    bits = [workspace] if workspace else []
    if action_policy.get("can_block") is True:
        bits.append("can_block")
    if action_policy.get("can_finish_run") is True:
        bits.append("can_finish_run")
    return ", ".join(bits)


def _required_coverage_summary(required_coverage: object) -> str:
    if not isinstance(required_coverage, dict):
        return ""
    status = str(required_coverage.get("status") or "pending").strip()
    status_label = "partial evidence" if status == "partial" else status
    covered = _non_bool_int(required_coverage.get("covered_check_count"))
    missing = _non_bool_int(required_coverage.get("missing_check_count"))
    target_count = _non_bool_int(required_coverage.get("target_count"))
    covered_targets = _non_bool_int(required_coverage.get("covered_target_count"))
    weak_targets = _non_bool_int(required_coverage.get("weak_target_count"))
    missing_targets = _non_bool_int(required_coverage.get("missing_target_count"))
    blocked_targets = _non_bool_int(required_coverage.get("blocked_target_count"))
    bits = []
    if covered is not None or missing is not None:
        bits.append(f"required checks {covered or 0} covered / {missing or 0} missing")
    if target_count:
        target_bits = [f"{covered_targets or 0}/{target_count} targets covered"]
        if weak_targets:
            target_bits.append(f"{weak_targets} weak")
        if missing_targets:
            target_bits.append(f"{missing_targets} missing")
        if blocked_targets:
            target_bits.append(f"{blocked_targets} blocked")
        bits.append(" / ".join(target_bits))
    if not bits:
        return status_label
    return f"{status_label}; {', '.join(bits)}"


def _agent_coverage_classification_note(next_step: dict) -> str:
    known_count = _non_bool_int(next_step.get("known_evidence_count"))
    if known_count is None and isinstance(next_step.get("known_evidence_ids"), list):
        known_count = len([item for item in next_step["known_evidence_ids"] if str(item).strip()])
    if not known_count:
        return ""
    coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    target_count = _non_bool_int(coverage.get("target_count"))
    if not target_count:
        return ""
    covered_targets = _non_bool_int(coverage.get("covered_target_count")) or 0
    weak_targets = _non_bool_int(coverage.get("weak_target_count")) or 0
    blocked_targets = _non_bool_int(coverage.get("blocked_target_count")) or 0
    if covered_targets or weak_targets or blocked_targets:
        if _coverage_gaps_only_gatekeeper_finish(coverage):
            return ""
        latest_unclassified = _latest_unclassified_supporting_evidence_id(next_step.get("known_evidence_refs"))
        if latest_unclassified:
            return (
                f"{latest_unclassified} is citable, but coverage still reflects earlier classifications until "
                "a review role returns coverage_results for that evidence"
            )
        return ""
    return (
        "known evidence is citable, but coverage remains unverified until a review role returns "
        "coverage_results with exact target IDs"
    )


def _coverage_gaps_only_gatekeeper_finish(coverage: dict) -> bool:
    if (_non_bool_int(coverage.get("missing_check_count")) or 0) != 0:
        return False
    gaps = [gap for gap in list(coverage.get("top_gaps") or []) if isinstance(gap, dict)]
    if not gaps:
        return False
    return all(str(gap.get("target_id") or gap.get("id") or "").strip() == "gatekeeper.finish" for gap in gaps)


def _latest_unclassified_supporting_evidence_id(value: object) -> str:
    if not isinstance(value, list):
        return ""
    for item in reversed(value):
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("id") or "").strip()
        if not evidence_id:
            continue
        support = str(item.get("gatekeeper_support") or "").strip().lower()
        if support and support != "supporting":
            continue
        if _evidence_scope_items(item.get("coverage_target_ids")):
            continue
        if str(item.get("archetype") or "").strip().lower() == "gatekeeper":
            continue
        return evidence_id
    return ""


def _print_top_coverage_gaps(required_coverage: object) -> None:
    if not isinstance(required_coverage, dict):
        return
    gaps = required_coverage.get("top_gaps")
    if not isinstance(gaps, list):
        return
    visible_gaps = [gap for gap in gaps if isinstance(gap, dict)][:3]
    if not visible_gaps:
        return
    typer.echo("top_coverage_gaps:")
    for gap in visible_gaps:
        target_id = str(gap.get("target_id") or gap.get("id") or "").strip()
        status = str(gap.get("status") or "").strip()
        source_section = str(gap.get("source_section") or "").strip()
        text = _clip(str(gap.get("text") or gap.get("reason") or "").strip(), 180)
        status_prefix = f"[{status}] " if status and status != "missing" else ""
        source_prefix = f"[{source_section}] " if source_section else ""
        if target_id and text:
            typer.echo(f"- {target_id}: {status_prefix}{source_prefix}{text}")
        elif target_id:
            typer.echo(f"- {target_id}: {status_prefix}{source_prefix}")
        elif text:
            typer.echo(f"- {status_prefix}{source_prefix}{text}")


def _coverage_gap_summaries(gaps: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(gaps, list):
        return []
    summaries: list[dict[str, object]] = []
    for gap in [item for item in gaps if isinstance(item, dict)][:limit]:
        summary: dict[str, object] = {}
        _set_summary_text(summary, "target_id", gap.get("target_id") or gap.get("id"))
        _set_summary_text(summary, "status", gap.get("status"))
        _set_summary_text(summary, "source_section", gap.get("source_section"))
        _set_summary_text(summary, "reason", _clip_inline(str(gap.get("reason") or ""), 180))
        _set_summary_text(summary, "text", _clip_inline(str(gap.get("text") or ""), 180))
        evidence_refs = _evidence_scope_items(gap.get("evidence_refs"))
        if evidence_refs:
            summary["evidence_refs"] = evidence_refs[:5]
        if summary:
            summaries.append(summary)
    return summaries
