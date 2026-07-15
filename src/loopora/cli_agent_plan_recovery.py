from __future__ import annotations

from pathlib import Path

import typer

from loopora.agent_adapters import adapter_first_task_message_example, resolve_adapter_project_root
from loopora.agent_native_surface import agent_native_run_surface_for_result, native_surface_plain_lines
from loopora.cli_agent_runtime_support import agent_plan_cli_command
from loopora.system_prompt_assets import load_system_prompt_asset


PLAN_MESSAGE_SOURCE_POLICY = load_system_prompt_asset("agent_native/plan-message-source-policy.md").strip()
PLAN_QUESTION_DECISION_IMPACT = load_system_prompt_asset("agent_native/plan-question-decision-impact.md").strip()
PLAN_QUESTION_NATIVE_TOOL_POLICY = load_system_prompt_asset("agent_native/plan-question-native-tool-policy.md").strip()
PLAN_QUESTION_SUBAGENT_POLICY = load_system_prompt_asset("agent_native/plan-question-subagent-policy.md").strip()
PLAN_MESSAGE_REQUIRED_NEXT = load_system_prompt_asset("agent_native/plan-message-required-next.md").strip()


def agent_plan_error_requires_message(error: str) -> bool:
    return "--message task summary" in error or "--message task context" in error


def agent_plan_message_required_result(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> dict:
    root = resolve_adapter_project_root(workdir)
    context_request = agent_plan_context_guidance_fields(
        adapter=adapter,
        workdir=root,
        context_id=context_id,
        entry_source=entry_source,
    )
    return {
        "adapter": adapter,
        "workdir": str(root),
        "ready": False,
        "loop_recovery": "plan_message_required",
        "message": "A non-empty task context is required before /loopora-plan can create or review a Loop preview.",
        **context_request,
        "next_plan_command": "/loopora-plan",
        "next": PLAN_MESSAGE_REQUIRED_NEXT,
    }


def agent_plan_context_guidance_fields(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> dict:
    message_cli_command = _agent_plan_message_cli_command(
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
    )
    return {
        **agent_plan_context_request_fields(),
        "message_source_policy": PLAN_MESSAGE_SOURCE_POLICY,
        "message_cli_command": message_cli_command,
        "next_plan_cli_command": message_cli_command,
        "task_message_template": "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ...",
        "first_task_message_example": adapter_first_task_message_example(),
        "debug_cli_example_command": _agent_plan_debug_cli_example_command(
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            entry_source=entry_source,
        ),
    }


def agent_plan_context_request_fields() -> dict:
    ask_user = (
        "What long-running task should Loopora govern? Please include the goal, fake-done risks, required evidence, "
        "and any judgment tradeoff that should guide later rounds."
    )
    return {
        "required_inputs": [
            "task_goal",
            "fake_done_risks",
            "required_evidence",
            "judgment_tradeoffs",
        ],
        "ask_user": ask_user,
        "question_action": {
            "kind": "ask_user",
            "target": "main_agent_session",
            "prompt": ask_user,
            "recommended_reply_shape": "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ...",
            "decision_impact": PLAN_QUESTION_DECISION_IMPACT,
            "native_tool_policy": PLAN_QUESTION_NATIVE_TOOL_POLICY,
            "subagent_policy": PLAN_QUESTION_SUBAGENT_POLICY,
        },
        "example_user_reply": (
            "Build the account-deletion audit flow; fake done would be UI-only deletion or missing provider-failure handling; "
            "required evidence is contract tests plus an audit-log artifact; prefer a smaller proven flow over broad unverified polish."
        ),
    }


def print_agent_plan_message_required(result: dict) -> None:
    typer.echo("loop_recovery: ask one Loop-shaping question before /loopora-plan can create a preview")
    typer.echo(f"message: {result.get('message')}")
    typer.echo(f"next_plan_command: {result.get('next_plan_command') or '/loopora-plan'}")
    print_agent_plan_context_request_fields(result)
    _print_agent_native_run_surface(result)
    typer.echo(f"next: {result.get('next')}")


def print_agent_plan_context_request_fields(result: dict) -> None:
    inputs = [str(item).strip() for item in list(result.get("required_inputs") or []) if str(item).strip()]
    if inputs:
        typer.echo("required_inputs:")
        for item in inputs:
            typer.echo(f"- {item}")
    ask_user = str(result.get("ask_user") or "").strip()
    if ask_user:
        typer.echo(f"ask_user: {ask_user}")
    question_action = result.get("question_action") if isinstance(result.get("question_action"), dict) else {}
    if question_action:
        typer.echo(
            "question_action: "
            + str(question_action.get("native_tool_policy") or "Ask the user in the main Agent session.").strip()
        )
        recommended_shape = str(question_action.get("recommended_reply_shape") or "").strip()
        if recommended_shape:
            typer.echo(f"recommended_reply_shape: {recommended_shape}")
        impact = str(question_action.get("decision_impact") or "").strip()
        if impact:
            typer.echo(f"decision_impact: {impact}")
    example = str(result.get("example_user_reply") or "").strip()
    if example:
        typer.echo(f"example_user_reply: {example}")
    policy = str(result.get("message_source_policy") or "").strip()
    if policy:
        typer.echo(f"message_source_policy: {policy}")
    command = str(result.get("message_cli_command") or result.get("next_plan_cli_command") or "").strip()
    if command:
        typer.echo(f"message_cli_command: {command}")


def print_agent_plan_context_guidance_fields(result: dict) -> None:
    task_message_template = str(result.get("task_message_template") or "").strip()
    if task_message_template:
        typer.echo(f"task_message_template: {task_message_template}")
    first_task_message_example = str(result.get("first_task_message_example") or "").strip()
    if first_task_message_example:
        typer.echo("first_task_message_example:")
        typer.echo(first_task_message_example)
    debug_cli_example_command = str(result.get("debug_cli_example_command") or "").strip()
    if debug_cli_example_command:
        typer.echo(f"debug_cli_example_command: {debug_cli_example_command}")


def _agent_plan_debug_cli_example_command(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> str:
    message = agent_plan_context_request_fields()["example_user_reply"]
    return agent_plan_cli_command(
        adapter=adapter,
        workdir=workdir,
        message=message,
        context_id=context_id,
        entry_source=entry_source,
    )


def _agent_plan_message_cli_command(
    *,
    adapter: str,
    workdir: Path,
    context_id: str = "",
    entry_source: str = "",
) -> str:
    message = "<replace with current user task: goal, fake-done risks, required evidence, judgment tradeoffs>"
    return (
        agent_plan_cli_command(
            adapter=adapter,
            workdir=workdir,
            message=message,
            context_id=context_id,
            entry_source=entry_source,
        )
        + " --json --compact-json"
    )


def _print_agent_native_run_surface(result: dict) -> None:
    for line in native_surface_plain_lines(agent_native_run_surface_for_result(result)):
        typer.echo(line)
