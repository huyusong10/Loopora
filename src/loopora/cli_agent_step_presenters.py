from __future__ import annotations

import typer

from loopora.agent_native_coverage_summary import coverage_gap_summaries, required_coverage_summary
from loopora.agent_native_task_proof import (
    AGENT_RUN_LIFECYCLE_SOURCE,
    AGENT_TASK_PROOF_SOURCE,
    PASSING_TASK_VERDICT_STATUSES,
)
from loopora.agent_native_surface import agent_native_run_surface_for_result, native_surface_plain_lines
from loopora.cli_agent_current_step_output import _print_agent_current_step
from loopora.cli_agent_runtime_support import print_web_status as _print_web_status
from loopora.cli_agent_submit_results import (
    _agent_submit_json_payload,
    _agent_submit_summary,
    _agent_submitted_step_summary,
)
from loopora.cli_agent_step_results import (
    _agent_next_json_payload,
    _agent_next_step_summary,
    _agent_next_summary,
    _attach_agent_run_dispatch_summary,
    _attach_agent_run_summary,
    _task_verdict_status,
)
from loopora.cli_agent_submitted_step_output import _print_agent_submitted_step
from loopora.cli_agent_work_panel import print_agent_work_panel as _print_agent_work_panel
from loopora.cli_run_output import print_run_contract_summary, print_task_verdict
from loopora.cli_shared import echo_json
from loopora.cli_summary_helpers import clip as _clip
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run
from loopora.system_prompt_assets import load_system_prompt_asset

__all__ = [
    "_agent_next_json_payload",
    "_agent_next_step_summary",
    "_agent_next_summary",
    "_agent_submit_json_payload",
    "_agent_submit_summary",
    "_agent_submitted_step_summary",
    "_attach_agent_run_dispatch_summary",
    "_attach_agent_run_summary",
    "_print_agent_loop_result",
    "_print_agent_next_result",
    "_print_agent_step_result",
    "_task_verdict_status",
]


def _print_agent_loop_result(result: dict, *, json_output: bool, compact_json_output: bool = False) -> None:
    if json_output or compact_json_output:
        _attach_agent_run_summary(result, include_raw=not compact_json_output, compact=compact_json_output)
        echo_json(result["agent_v3_envelope"])
        return
    _print_agent_work_panel(result)
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run_status_from_run(run)}")
    _print_agent_loop_start_state(result)
    _print_agent_native_run_surface(result)
    print_run_contract_summary(run)
    task_verdict = task_verdict_from_run(run)
    if result.get("complete"):
        print_task_verdict(task_verdict)
        _print_terminal_task_next_action(task_verdict, result.get("task_next_action"))
        _print_agent_native_terminal_state(task_verdict)
    typer.echo(f"run_url: {result.get('run_url') or result.get('run_path')}")
    _print_web_status(result)
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    if next_step:
        _print_agent_current_step(next_step)


def _print_agent_loop_start_state(result: dict) -> None:
    if "started_new_run" not in result:
        return
    if result.get("started_new_run") is True:
        typer.echo("run_start: started_new_agent_runner_run")
    elif result.get("complete") is True:
        typer.echo("run_start: replayed_existing_terminal_run")
    else:
        typer.echo("run_start: resumed_existing_agent_runner_run")


def _print_agent_step_result(result: dict, *, json_output: bool, compact_json_output: bool = False) -> None:
    if json_output or compact_json_output:
        echo_json(_agent_submit_json_payload(result, include_raw=not compact_json_output))
        return
    _print_agent_work_panel(result)
    if result.get("auto_repair_applied") is True:
        actions = [str(item).strip() for item in list(result.get("auto_repair_actions") or []) if str(item).strip()]
        rendered = ", ".join(actions[:4]) if actions else "safe wrapper repair"
        typer.echo(f"auto_repair: submitted result format repaired before submit ({rendered})")
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    typer.echo(f"Loopora run: {run.get('id')}")
    typer.echo(f"run_status: {run_status_from_run(run)}")
    _print_agent_native_run_surface(result)
    _print_agent_submitted_step(result.get("submitted_step"))
    _print_agent_coverage_after_submit(result)
    print_run_contract_summary(run)
    task_verdict = task_verdict_from_run(run)
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


def _print_agent_next_result(result: dict, *, json_output: bool, compact_json_output: bool = False) -> None:
    if json_output or compact_json_output:
        echo_json(_agent_next_json_payload(result, include_raw=not compact_json_output))
        return
    _print_agent_step_result(result, json_output=False)


def _print_agent_native_run_surface(result: dict) -> None:
    next_step = result.get("next_step") if isinstance(result.get("next_step"), dict) else {}
    surface = agent_native_run_surface_for_result(result, next_step)
    for line in native_surface_plain_lines(surface):
        typer.echo(line)


def _print_agent_coverage_after_submit(result: dict) -> None:
    coverage = result.get("coverage_after_submit") if isinstance(result.get("coverage_after_submit"), dict) else {}
    if not coverage:
        return
    summary = required_coverage_summary(coverage)
    if summary:
        typer.echo(f"coverage_after_submit: {summary}")
    source = str(coverage.get("source") or "").strip()
    if source:
        typer.echo(f"coverage_after_submit_source: {source}")
    top_gaps = coverage_gap_summaries(coverage.get("top_gaps"), limit=3)
    if not top_gaps:
        return
    typer.echo("coverage_after_submit_top_gaps:")
    for gap in top_gaps:
        target_id = str(gap.get("target_id") or "").strip()
        status = str(gap.get("status") or "").strip()
        reason = str(gap.get("reason") or gap.get("text") or "").strip()
        rendered = " ".join(item for item in (target_id, status) if item)
        if reason:
            rendered = f"{rendered}: {reason}" if rendered else reason
        typer.echo(f"- {rendered}")


def _print_agent_native_terminal_state(task_verdict: object) -> None:
    status = _task_verdict_status(task_verdict)
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo("agent_runner: complete")
        _print_agent_native_terminal_sources()
        return
    if not status:
        status = "not_evaluated"
    typer.echo("agent_runner: lifecycle_closed_task_unproven")
    typer.echo(f"agent_runner_task_verdict: {status}")
    _print_agent_native_terminal_sources()


def _print_agent_native_terminal_sources() -> None:
    typer.echo(f"task_proof_source: {AGENT_TASK_PROOF_SOURCE}")
    typer.echo(f"run_lifecycle_source: {AGENT_RUN_LIFECYCLE_SOURCE}")


def _print_terminal_task_next_action(task_verdict: object, task_next_action: object = None) -> None:
    action = task_next_action if isinstance(task_next_action, dict) else {}
    status = _task_verdict_status(task_verdict)
    summary = ""
    if isinstance(task_verdict, dict):
        summary = str(task_verdict.get("summary") or "").strip()
    if status in PASSING_TASK_VERDICT_STATUSES:
        typer.echo(f"task_next_action: {_lowercase_first(load_system_prompt_asset('agent_native/task-verdict-already-passed.md').strip())}")
        return
    if not status:
        status = "not_evaluated"
    guidance = str(action.get("guidance") or "").strip() if action else ""
    typer.echo(
        "task_next_action: "
        + (
            guidance or load_system_prompt_asset("agent_native/task-verdict-continue-evidence-terminal.md").strip()
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


def _lowercase_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else ""
