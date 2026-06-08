from __future__ import annotations

import shlex

from loopora.agent_adapters import prefix_loopora_command
from loopora.agent_native_coverage_summary import (
    coverage_gap_summaries,
    evidence_scope_items,
)
from loopora.agent_native_guidance import actionable_blocking_item as _actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _actionable_next_action
from loopora.summary_projection_helpers import (
    clip_inline,
    non_bool_int,
    set_summary_list,
    set_summary_text,
)
from loopora.system_prompt_assets import load_system_prompt_asset, render_system_prompt_asset


def agent_dispatch_next_summary(role_dispatch: dict) -> str:
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if not target_agent or role_dispatch.get("target_agent_config_exists") is False:
        return ""
    return render_system_prompt_asset("agent_native/dispatch-next-summary.md", {"target_agent": target_agent}).strip()


def agent_dispatch_unavailable_summary(*, adapter: str, workdir: str, role_dispatch: dict) -> dict[str, object]:
    target_agent = str(role_dispatch.get("target_agent") or "").strip()
    if not target_agent or role_dispatch.get("target_agent_config_exists") is not False:
        return {}
    target_config = str(
        role_dispatch.get("target_agent_config_absolute_path") or role_dispatch.get("target_agent_config_path") or ""
    ).strip()
    normalized_adapter = str(adapter or "").strip() or "codex"
    workdir_arg = _quoted_workdir_arg(workdir)
    return {
        "reason": "target_agent_config_missing",
        "target_agent": target_agent,
        "target_agent_config": target_config,
        "check_command": prefix_loopora_command(f"loopora agent {normalized_adapter} check --workdir {workdir_arg}"),
        "repair_command": prefix_loopora_command(f"loopora init {normalized_adapter} --workdir {workdir_arg}"),
        "next": load_system_prompt_asset("agent_native/dispatch-unavailable-next.md").strip(),
    }


def agent_next_step_continuation_summary(next_step: dict) -> dict[str, object]:
    continuation = next_step.get("continuation") if isinstance(next_step.get("continuation"), dict) else {}
    if not continuation or continuation.get("active") is not True:
        return {}
    previous_verdict = (
        continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    )
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    summary: dict[str, object] = {"active": True}
    set_summary_text(summary, "previous_run_id", continuation.get("previous_run_id"))
    set_summary_text(summary, "previous_task_verdict_status", previous_verdict.get("status"))
    set_summary_text(summary, "previous_task_verdict_summary", clip_inline(str(previous_verdict.get("summary") or ""), 220))
    missing_required_check_count = non_bool_int(coverage.get("missing_check_count"))
    if missing_required_check_count is not None:
        summary["missing_required_check_count"] = missing_required_check_count
    missing_target_count = non_bool_int(coverage.get("missing_target_count"))
    if missing_target_count is not None:
        summary["missing_target_count"] = missing_target_count
    raw_next_focus = continuation.get("next_focus")
    next_focus = (
        [clip_inline(str(item), 220) for item in list(raw_next_focus or []) if str(item).strip()]
        if isinstance(raw_next_focus, list)
        else []
    )
    if next_focus:
        summary["next_focus"] = next_focus[:6]
    return {"continuation": {key: value for key, value in summary.items() if value not in ("", [], {})}}


def agent_current_step_evidence_scope_summary(next_step: dict) -> str:
    inputs = next_step.get("inputs") if isinstance(next_step.get("inputs"), dict) else {}
    evidence_query = inputs.get("evidence_query") if isinstance(inputs.get("evidence_query"), dict) else {}
    if not evidence_query:
        return ""
    parts: list[str] = []
    archetypes = evidence_scope_items(evidence_query.get("archetypes"))
    if archetypes:
        parts.append(f"archetypes={','.join(archetypes[:6])}")
    role_ids = evidence_scope_items(evidence_query.get("role_ids"))
    if role_ids:
        parts.append(f"role_ids={','.join(role_ids[:6])}")
    step_ids = evidence_scope_items(evidence_query.get("step_ids"))
    if step_ids:
        parts.append(f"step_ids={','.join(step_ids[:6])}")
    limit = non_bool_int(evidence_query.get("limit"))
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


def action_policy_summary(action_policy: dict) -> str:
    workspace = str(action_policy.get("workspace") or "").strip()
    bits = [workspace] if workspace else []
    if action_policy.get("can_block") is True:
        bits.append("can_block")
    if action_policy.get("can_finish_run") is True:
        bits.append("can_finish_run")
    return ", ".join(bits)


def agent_native_todo_summary(native_todo: dict) -> dict[str, object]:
    summary: dict[str, object] = {
        "recommended": native_todo.get("recommended") is True,
        "not_evidence": native_todo.get("not_evidence") is True,
    }
    set_summary_text(summary, "host_policy", native_todo.get("host_policy"))
    set_summary_list(summary, "items", native_todo.get("items"))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def agent_iteration_repair_summary(repair: object) -> dict[str, object]:
    if not isinstance(repair, dict) or repair.get("active") is not True:
        return {}
    summary: dict[str, object] = {"active": True}
    set_summary_text(summary, "source_step_id", repair.get("source_step_id"))
    set_summary_text(summary, "source_role", repair.get("source_role"))
    set_summary_text(summary, "status", repair.get("status"))
    set_summary_text(summary, "summary", clip_inline(str(repair.get("summary") or ""), 220))
    blocking_items = evidence_scope_items(repair.get("blocking_items"))
    actionable_blockers = [_actionable_blocking_item(item) for item in blocking_items]
    if actionable_blockers:
        summary["blocking_items"] = [clip_inline(item, 220) for item in actionable_blockers[:5]]
    next_action = _actionable_next_action(str(repair.get("recommended_next_action") or "").strip(), actionable_blockers)
    set_summary_text(summary, "recommended_next_action", clip_inline(next_action, 220))
    evidence_refs = evidence_scope_items(repair.get("evidence_refs"))
    if evidence_refs:
        summary["evidence_refs"] = evidence_refs[:5]
    top_gaps = coverage_gap_summaries(repair.get("top_gaps"), limit=5)
    if top_gaps:
        summary["top_gaps"] = top_gaps
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _quoted_workdir_arg(workdir: str) -> str:
    normalized_workdir = str(workdir or "").strip() or "$PWD"
    if normalized_workdir == "$PWD":
        return '"$PWD"'
    return shlex.quote(normalized_workdir)


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
