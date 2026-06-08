from __future__ import annotations

import typer

from loopora.agent_native_adapter_contracts import agent_adapter_native_surface_summary
from loopora.agent_native_coverage_summary import (
    coverage_classification_note as _agent_coverage_classification_note,
    required_coverage_summary as _required_coverage_summary,
)
from loopora.agent_native_next_step_sections import (
    action_policy_summary as _action_policy_summary,
    agent_dispatch_next_summary as _agent_dispatch_next_summary,
    agent_dispatch_unavailable_summary as _agent_dispatch_unavailable_summary,
)
from loopora.agent_native_step_view_paths import agent_native_step_contract_path_text as _agent_native_step_contract_path_text
from loopora.cli_agent_current_step_continuation_output import print_agent_continuation as _print_agent_continuation
from loopora.cli_agent_current_step_evidence_output import (
    print_agent_current_step_evidence_scope as _print_agent_current_step_evidence_scope,
)
from loopora.cli_agent_current_step_evidence_output import (
    print_agent_current_step_known_evidence as _print_agent_current_step_known_evidence,
)
from loopora.cli_agent_current_step_evidence_output import (
    print_agent_current_step_known_evidence_refs as _print_agent_current_step_known_evidence_refs,
)
from loopora.cli_agent_current_step_iteration_output import print_agent_iteration_context as _print_agent_iteration_context
from loopora.cli_summary_helpers import clip as _clip
from loopora.cli_summary_helpers import non_bool_int as _non_bool_int
from loopora.system_prompt_assets import load_system_prompt_asset


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
            dispatch_unavailable = _agent_dispatch_unavailable_summary(
                adapter=adapter,
                workdir="$PWD",
                role_dispatch=role_dispatch,
            )
            check_command = str(dispatch_unavailable.get("check_command") or "").strip()
            repair_command = str(dispatch_unavailable.get("repair_command") or "").strip()
            typer.echo(
                "dispatch_unavailable: "
                f"{target_agent} config is missing; run {check_command} "
                f"and repair with {repair_command} before dispatching this role"
            )
        else:
            typer.echo(f"dispatch_next: {_agent_dispatch_next_summary(role_dispatch)}")
            _print_agent_native_dispatch_contract(next_step, target_agent)
    _print_agent_native_todo(next_step.get("native_todo"))
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
    _print_agent_current_step_technical_handoff(next_step, submit_hint)


def _print_agent_native_todo(native_todo: object) -> None:
    if not isinstance(native_todo, dict) or native_todo.get("recommended") is not True:
        return
    policy = str(native_todo.get("host_policy") or "").strip()
    if policy:
        typer.echo(f"native_todo: {_clip(policy, 220)}")
    items = [str(item).strip() for item in list(native_todo.get("items") or []) if str(item).strip()]
    if items:
        typer.echo("native_todo_items:")
        for item in items[:6]:
            typer.echo(f"- {_clip(item, 180)}")


def _print_agent_current_step_technical_handoff(next_step: dict, submit_hint: dict) -> None:
    typer.echo("technical_handoff:")
    _print_agent_current_step_paths(next_step, submit_hint)
    _print_agent_current_step_submit_hint(submit_hint)


def _print_agent_native_dispatch_contract(next_step: dict, target_agent: str) -> None:
    adapter = str(next_step.get("adapter") or "").strip() or "codex"
    surface = agent_adapter_native_surface_summary(adapter)
    native_dispatch = surface.get("native_dispatch") if isinstance(surface.get("native_dispatch"), dict) else {}
    nested_provider_cli = str(native_dispatch.get("nested_provider_cli") or "").strip()
    submit_contract = str(native_dispatch.get("submit_contract") or "").strip()
    if nested_provider_cli or submit_contract:
        typer.echo(
            f"native_dispatch_contract: host-native {target_agent}; "
            f"nested_provider_cli={nested_provider_cli}; submit_contract={submit_contract}"
        )
    host_mechanism = str(native_dispatch.get("host_mechanism") or "").strip()
    if host_mechanism:
        typer.echo(f"native_dispatch_mechanism: {host_mechanism}")
    proof_boundary = str(native_dispatch.get("proof_boundary") or "").strip()
    if proof_boundary:
        typer.echo(f"native_proof_boundary: {proof_boundary}")


def _print_agent_current_step_paths(next_step: dict, submit_hint: dict) -> None:
    context_path = str(next_step.get("context_absolute_path") or next_step.get("context_path") or "").strip()
    if context_path:
        typer.echo(f"next_context_path: {context_path}")
    agent_step_view_path = str(next_step.get("agent_step_view_absolute_path") or next_step.get("agent_step_view_path") or "").strip()
    if agent_step_view_path:
        typer.echo(f"next_agent_step_view_path: {agent_step_view_path}")
    step_contract_path = _agent_native_step_contract_path_text(next_step, absolute=True)
    if step_contract_path:
        typer.echo(f"next_step_contract_path: {step_contract_path}")
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
            template_fill = load_system_prompt_asset("agent_native/result-template-fill-save-copy.md").strip()
        else:
            template_fill = load_system_prompt_asset("agent_native/result-template-fill-submit-copy.md").strip()
        typer.echo(f"result_template_fill: {template_fill}")
    result_outbox_dir = str(submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir") or "").strip()
    if result_outbox_dir:
        typer.echo(f"result_outbox_dir: {result_outbox_dir}")
    submit_command = str(submit_hint.get("command") or "").strip()
    if submit_command:
        typer.echo(f"submit_hint: {submit_command}")


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
