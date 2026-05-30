from __future__ import annotations

import typer

from loopora.agent_adapters import prefix_loopora_command
from loopora.agent_native_adapter_contracts import agent_adapter_native_surface_summary
from loopora.agent_native_coverage_summary import (
    coverage_classification_note as _agent_coverage_classification_note,
    evidence_scope_items as _evidence_scope_items,
    required_coverage_summary as _required_coverage_summary,
)
from loopora.agent_native_evidence_refs import (
    agent_known_evidence_ref_summaries as _agent_known_evidence_ref_summaries,
    known_evidence_ref_items as _known_evidence_ref_items,
)
from loopora.agent_native_next_step_summary import (
    action_policy_summary as _action_policy_summary,
    agent_current_step_evidence_scope_summary as _agent_current_step_evidence_scope_summary,
)
from loopora.agent_native_step_view_paths import agent_native_step_contract_path_text as _agent_native_step_contract_path_text
from loopora.cli_agent_submitted_step_output import _actionable_blocking_item, _actionable_next_action
from loopora.cli_summary_helpers import clip as _clip
from loopora.cli_summary_helpers import non_bool_int as _non_bool_int


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
                f"dispatch_next: invoke {target_agent} with the next context and step contract paths below; do not perform this role inline"
            )
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
    next_action = _actionable_next_action(
        str(repair.get("recommended_next_action") or "").strip(),
        [_actionable_blocking_item(item) for item in blocking_items],
    )
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
