from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_workdir_recovery import (
    AdapterWorkdirRetryPolicy,
    adapter_workdir_recovery_payload,
    adapter_workdir_state,
)
from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_v3 import agent_v3_envelope, agent_v3_legacy_raw, agent_v3_technical_handoff
from loopora.cli_shared import echo_json
from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)


@dataclass(frozen=True)
class AgentRuntimeWorkdirRecoveryRequest:
    adapter: str
    workdir: Path
    action: str
    entry_source: str
    json_output: bool
    compact_json_output: bool
    result_file: Path | None = None


def exit_if_unusable_agent_runtime_workdir(request: AgentRuntimeWorkdirRecoveryRequest) -> None:
    state = adapter_workdir_state(request.workdir)
    if state["status"] == "ready":
        return
    payload = adapter_workdir_recovery_payload(
        request.adapter,
        action=request.action,
        workdir_state=state,
        retry_policy=AdapterWorkdirRetryPolicy(
            command=_runtime_retry_command(
                adapter=request.adapter,
                action=request.action,
                workdir=str(state["workdir"]),
                result_file=request.result_file,
            ),
            entry_source=request.entry_source,
        ),
    )
    if request.json_output or request.compact_json_output:
        echo_json(_agent_runtime_workdir_recovery_json_payload(payload, include_raw=not request.compact_json_output))
    else:
        _print_agent_runtime_workdir_recovery(payload)
    raise typer.Exit(code=1)


def exit_with_missing_agent_submit_result_file(request: AgentRuntimeWorkdirRecoveryRequest) -> None:
    payload = _agent_submit_result_file_recovery_payload(request)
    if request.json_output or request.compact_json_output:
        echo_json(_agent_submit_result_file_recovery_json_payload(payload, include_raw=not request.compact_json_output))
    else:
        _print_agent_submit_result_file_recovery(payload)
    raise typer.Exit(code=1)


def _runtime_retry_command(*, adapter: str, action: str, workdir: str, result_file: Path | None) -> str:
    quoted_adapter = shlex.quote(str(adapter))
    quoted_workdir = shlex.quote(workdir)
    if action == "submit":
        result_arg = shlex.quote(str(result_file)) if result_file else "<result-file>"
        return f"loopora agent {quoted_adapter} submit --result-file {result_arg} --workdir {quoted_workdir}"
    return {
        "plan": f"loopora agent {quoted_adapter} plan --workdir {quoted_workdir}",
        "run": f"loopora agent {quoted_adapter} run --workdir {quoted_workdir}",
        "next": f"loopora agent {quoted_adapter} next --workdir {quoted_workdir}",
    }[action]


def _agent_runtime_workdir_recovery_json_payload(payload: dict[str, object], *, include_raw: bool) -> dict:
    summary = _agent_runtime_workdir_recovery_summary(payload)
    extras: dict[str, object] = {
        "technical_handoff": agent_v3_technical_handoff(summary),
        "diagnostics": {"legacy_summary_key": "agent_workdir_recovery_summary"},
    }
    if include_raw:
        extras["raw"] = agent_v3_legacy_raw(
            summary_key="agent_workdir_recovery_summary",
            summary=summary,
            payload=payload,
        )
    return agent_v3_envelope(
        kind="agent_recovery",
        status="blocked",
        summary=summary,
        extras=extras,
    )


def _agent_runtime_workdir_recovery_summary(payload: dict[str, object]) -> dict[str, object]:
    adapter = str(payload.get("adapter") or "").strip() or "codex"
    next_actions = payload.get("next_actions") or []
    structured_actions = [action for action in list(next_actions or []) if isinstance(action, dict)]
    summary: dict[str, object] = {
        "ready": False,
        "loop_recovery": payload.get("loop_recovery"),
        "status": payload.get("status"),
        "adapter": adapter,
        "action": payload.get("action"),
        "workdir": payload.get("workdir"),
        "workdir_state": payload.get("workdir_state"),
        "summary": payload.get("summary"),
        "next_actions": next_actions,
        "next_action_kinds": _agent_runtime_workdir_action_kinds(structured_actions),
    }
    project_first_use_action_readiness_summary(
        summary,
        prefix="next_action",
        readiness=first_use_action_readiness_summary(structured_actions),
    )
    attach_native_run_surface(summary, adapter=adapter, compact=True)
    return {key: value for key, value in summary.items() if value not in ("", [], {}, None)}


def _agent_runtime_workdir_action_kinds(actions: object) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in list(actions or []) if isinstance(action, dict) and str(action.get("kind") or "").strip()]


def _print_agent_runtime_workdir_recovery(payload: dict[str, object]) -> None:
    label = str(payload.get("label") or "Agent")
    action = str(payload.get("action") or "run")
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else {}
    typer.echo(f"{label} Loopora Agent {action} is blocked")
    typer.echo(f"target project: {payload.get('workdir')}")
    typer.echo(f"project directory state: {workdir_state.get('status')}")
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(f"note: {summary}")
    typer.echo("next:")
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        command = str(item.get("command") or "").strip()
        label_text = _runtime_action_label(kind)
        typer.echo(f"- {label_text}: {command}" if command else f"- {label_text}")


def _agent_submit_result_file_recovery_payload(request: AgentRuntimeWorkdirRecoveryRequest) -> dict[str, object]:
    next_actions = _agent_submit_result_file_next_actions(request)
    return project_next_action_readiness_contract(
        {
            "loop_recovery": "result_file_required",
            "status": "blocked_by_missing_result_file",
            "adapter": request.adapter,
            "action": "submit",
            "workdir": str(request.workdir.expanduser().resolve()),
            "required_identifier": "result_file",
            "required_identifier_label": "Filled Agent Native result JSON file",
            "summary": (
                "Submit needs the filled result JSON produced from the active result template; run agent next to get "
                "the current template and handoff before submitting."
            ),
            "next_actions": next_actions,
            "next_action_kinds": _agent_runtime_workdir_action_kinds(next_actions),
        }
    )


def _agent_submit_result_file_next_actions(request: AgentRuntimeWorkdirRecoveryRequest) -> list[dict[str, object]]:
    quoted_adapter = shlex.quote(str(request.adapter))
    quoted_workdir = shlex.quote(str(request.workdir.expanduser().resolve()))
    claim_command = f"loopora agent {quoted_adapter} next --workdir {quoted_workdir}"
    retry_command = f"loopora agent {quoted_adapter} submit --result-file <result-file> --workdir {quoted_workdir}"
    suffix = "--compact-json" if request.compact_json_output else "--json" if request.json_output else ""
    if suffix:
        claim_command = f"{claim_command} {suffix}"
        retry_command = f"{retry_command} {suffix}"
    return [
        {
            "kind": "claim_current_step",
            "label": "Get the active step, result template, and submit hint",
            "command": copyable_loopora_command(claim_command),
        },
        {
            "kind": "fill_result_template",
            "label": "Fill the active result template instead of submitting ad hoc observations",
            "after_action": "claim_current_step",
        },
        {
            "kind": "retry_submit_after_result_file",
            "label": "Submit the filled result JSON file",
            "command_template": copyable_loopora_command(retry_command),
            "after_action": "fill_result_template",
        },
    ]


def _agent_submit_result_file_recovery_json_payload(payload: dict[str, object], *, include_raw: bool) -> dict:
    summary = _agent_submit_result_file_recovery_summary(payload)
    extras: dict[str, object] = {
        "technical_handoff": agent_v3_technical_handoff(summary),
        "diagnostics": {"legacy_summary_key": "agent_submit_result_file_recovery_summary"},
    }
    if include_raw:
        extras["raw"] = agent_v3_legacy_raw(
            summary_key="agent_submit_result_file_recovery_summary",
            summary=summary,
            payload=payload,
        )
    return agent_v3_envelope(
        kind="agent_recovery",
        status="blocked",
        summary=summary,
        extras=extras,
    )


def _agent_submit_result_file_recovery_summary(payload: dict[str, object]) -> dict[str, object]:
    adapter = str(payload.get("adapter") or "").strip() or "codex"
    summary: dict[str, object] = {
        "ready": False,
        "loop_recovery": payload.get("loop_recovery"),
        "status": payload.get("status"),
        "adapter": adapter,
        "action": payload.get("action"),
        "workdir": payload.get("workdir"),
        "required_identifier": payload.get("required_identifier"),
        "summary": payload.get("summary"),
        "next_actions": payload.get("next_actions"),
        "next_action_kinds": payload.get("next_action_kinds"),
    }
    actions = [action for action in list(payload.get("next_actions") or []) if isinstance(action, dict)]
    project_first_use_action_readiness_summary(
        summary,
        prefix="next_action",
        readiness=first_use_action_readiness_summary(actions),
    )
    attach_native_run_surface(summary, adapter=adapter, compact=True)
    return {key: value for key, value in summary.items() if value not in ("", [], {}, None)}


def _print_agent_submit_result_file_recovery(payload: dict[str, object]) -> None:
    adapter = str(payload.get("adapter") or "codex")
    typer.echo(f"{adapter} Loopora Agent submit is blocked")
    typer.echo("reason: result file required")
    typer.echo(f"target project: {payload.get('workdir')}")
    typer.echo(f"required identifier: {payload.get('required_identifier_label')}")
    summary = str(payload.get("summary") or "").strip()
    if summary:
        typer.echo(f"note: {summary}")
    typer.echo("next:")
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        detail = str(item.get("command") or item.get("command_template") or "").strip()
        suffix = f": {detail}" if detail else ""
        typer.echo(f"- {item.get('label')}{suffix}")


def _runtime_action_label(kind: str) -> str:
    return {
        "create_workdir": "Create the target project directory",
        "choose_workdir": "Choose an existing project directory",
        "confirm_readiness": "Confirm readiness after the target exists",
        "retry_plan": "Retry /loopora-plan after readiness",
        "retry_run": "Retry /loopora-run after readiness",
        "retry_next": "Retry agent next after readiness",
        "retry_submit": "Retry agent submit after readiness",
    }.get(kind, kind)
