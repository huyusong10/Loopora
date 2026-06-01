from __future__ import annotations

from loopora.agent_native_coverage_summary import (
    coverage_classification_note,
    coverage_gap_summaries,
    required_coverage_summary,
)
from loopora.agent_native_evidence_refs import agent_known_evidence_ref_summaries
from loopora.agent_native_next_step_sections import (
    action_policy_summary,
    agent_current_step_evidence_scope_summary,
    agent_dispatch_next_summary,
    agent_dispatch_unavailable_summary,
    agent_iteration_repair_summary,
    agent_native_todo_summary,
    agent_next_step_continuation_summary,
)
from loopora.agent_native_step_view_paths import agent_native_step_contract_path_text
from loopora.summary_projection_helpers import (
    non_bool_int,
    set_summary_text,
)


def agent_next_step_summary(next_step: dict, *, adapter: str = "", workdir: str = "") -> dict:
    if not next_step:
        return {}
    role = next_step.get("role") if isinstance(next_step.get("role"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    submit_hint = next_step.get("submit_hint") if isinstance(next_step.get("submit_hint"), dict) else {}
    action_policy = next_step.get("action_policy") if isinstance(next_step.get("action_policy"), dict) else {}
    summary: dict[str, object] = {}
    set_summary_text(summary, "step_id", next_step.get("step_id"))
    set_summary_text(summary, "role", role.get("name") or role.get("id"))
    set_summary_text(summary, "target_agent", role_dispatch.get("target_agent"))
    set_summary_text(
        summary,
        "target_agent_config",
        role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path"),
    )
    if "target_agent_config_exists" in role_dispatch:
        summary["target_agent_config_exists"] = role_dispatch.get("target_agent_config_exists") is True
    set_summary_text(summary, "dispatch_next", agent_dispatch_next_summary(role_dispatch))
    native_todo = next_step.get("native_todo") if isinstance(next_step.get("native_todo"), dict) else {}
    if native_todo:
        summary["native_todo"] = agent_native_todo_summary(native_todo)
    native_trace_contract = role_dispatch.get("native_trace_contract") if isinstance(role_dispatch.get("native_trace_contract"), dict) else {}
    if native_trace_contract:
        summary["native_trace_contract"] = native_trace_contract
    dispatch_unavailable = agent_dispatch_unavailable_summary(
        adapter=str(next_step.get("adapter") or adapter or "").strip() or "codex",
        workdir=str(workdir or "").strip() or "$PWD",
        role_dispatch=role_dispatch,
    )
    if dispatch_unavailable:
        summary["dispatch_unavailable"] = dispatch_unavailable
    set_summary_text(summary, "action_policy", action_policy_summary(action_policy))
    _attach_agent_next_step_submit_summary(summary, next_step, submit_hint)
    _attach_agent_next_step_evidence_summary(summary, next_step)
    _attach_agent_next_step_coverage_summary(summary, next_step)
    iteration_repair = agent_iteration_repair_summary(next_step.get("iteration_repair"))
    if iteration_repair:
        summary["iteration_repair"] = iteration_repair
    summary.update(agent_next_step_continuation_summary(next_step))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _attach_agent_next_step_submit_summary(summary: dict[str, object], next_step: dict, submit_hint: dict) -> None:
    set_summary_text(summary, "context_path", next_step.get("context_absolute_path") or next_step.get("context_path"))
    set_summary_text(
        summary,
        "agent_step_view_path",
        next_step.get("agent_step_view_absolute_path") or next_step.get("agent_step_view_path"),
    )
    set_summary_text(
        summary,
        "step_contract_path",
        agent_native_step_contract_path_text(next_step, absolute=True),
    )
    set_summary_text(summary, "result_template", submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path"))
    set_summary_text(summary, "result_file_to_write", submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path"))
    set_summary_text(summary, "result_template_contract", submit_hint.get("result_file_contract"))
    if submit_hint.get("result_file_contract") or submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path"):
        summary["result_template_fill"] = (
            "open the template, save a filled copy to result_file_to_write, replace null placeholders in result, keep loopora_host_dispatch, then submit"
        )
    set_summary_text(summary, "result_outbox_dir", submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir"))
    set_summary_text(summary, "submit_command", submit_hint.get("command"))


def _attach_agent_next_step_evidence_summary(summary: dict[str, object], next_step: dict) -> None:
    known_count = non_bool_int(next_step.get("known_evidence_count"))
    if known_count is not None:
        summary["known_evidence_count"] = known_count
    known_ids = [str(item).strip() for item in list(next_step.get("known_evidence_ids") or []) if str(item).strip()]
    if known_ids:
        displayed_known_ids = known_ids[-8:]
        if len(known_ids) > len(displayed_known_ids):
            summary["known_evidence_ids_omitted"] = len(known_ids) - len(displayed_known_ids)
        summary["known_evidence_ids"] = displayed_known_ids
    known_refs = agent_known_evidence_ref_summaries(next_step.get("known_evidence_refs"), limit=5)
    if known_refs:
        summary["known_evidence_refs"] = known_refs
    set_summary_text(summary, "known_evidence_scope", agent_current_step_evidence_scope_summary(next_step))


def _attach_agent_next_step_coverage_summary(summary: dict[str, object], next_step: dict) -> None:
    required_coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    set_summary_text(summary, "required_coverage", required_coverage_summary(required_coverage))
    set_summary_text(summary, "coverage_classification_note", coverage_classification_note(next_step))
    top_gaps = coverage_gap_summaries(required_coverage.get("top_gaps"), limit=5)
    if top_gaps:
        summary["top_coverage_gaps"] = top_gaps
