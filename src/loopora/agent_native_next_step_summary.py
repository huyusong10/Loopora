from __future__ import annotations

from pathlib import Path

from loopora.agent_native_coverage_summary import (
    coverage_classification_note,
    coverage_gap_summaries,
    required_coverage_summary,
)
from loopora.agent_native_step_view import agent_known_evidence_ref_summaries
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
    clip_inline,
    non_bool_int,
    set_summary_text,
)
from loopora.system_prompt_assets import load_system_prompt_asset

ROLE_DISPATCH_MESSAGE_LIMIT = 1000
ROLE_DISPATCH_LIST_ITEM_LIMIT = 8


def agent_next_step_summary(next_step: dict, *, adapter: str = "", workdir: str = "", compact: bool = False) -> dict:
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
    _attach_agent_next_step_evidence_summary(summary, next_step, compact=compact)
    _attach_agent_next_step_coverage_summary(summary, next_step, compact=compact)
    set_summary_text(summary, "role_dispatch_message", _role_dispatch_message(summary, workdir=workdir))
    iteration_repair = agent_iteration_repair_summary(next_step.get("iteration_repair"))
    if iteration_repair:
        summary["iteration_repair"] = iteration_repair
    summary.update(agent_next_step_continuation_summary(next_step))
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def _role_dispatch_message(summary: dict[str, object], *, workdir: str = "") -> str:
    target = str(summary.get("target_agent") or "").strip()
    if not target:
        return ""
    is_gatekeeper = "gatekeeper" in target.lower()
    prefix_asset = (
        "agent_native/role-dispatch-message-gatekeeper-prefix.md"
        if is_gatekeeper
        else "agent_native/role-dispatch-message-standard-prefix.md"
    )
    prefix = load_system_prompt_asset(prefix_asset).strip() + " "
    anchors = [f"target_agent={target}"]
    for label, key in (
        ("context_path", "context_path"),
        ("step_contract_path", "step_contract_path"),
        ("result_template", "result_template"),
    ):
        value = str(summary.get(key) or "").strip()
        if value:
            anchors.append(f"{label}={_dispatch_path_text(value, workdir=workdir)}")
    known_ids = [str(item).strip() for item in list(summary.get("known_evidence_ids") or []) if str(item).strip()]
    coverage_ids = [str(item).strip() for item in list(summary.get("coverage_target_ids") or []) if str(item).strip()]
    value = str(summary.get("action_policy") or "").strip()
    if is_gatekeeper:
        _append_bounded_list_anchor(anchors, "known_evidence_ids", known_ids, prefix=prefix, max_items=1)
        if value:
            _append_optional_anchor(anchors, f"action_policy={value}", prefix=prefix)
        _append_bounded_list_anchor(anchors, "coverage_target_ids", coverage_ids, prefix=prefix)
    else:
        _append_bounded_list_anchor(anchors, "coverage_target_ids", coverage_ids, prefix=prefix)
        _append_bounded_list_anchor(anchors, "known_evidence_ids", known_ids, prefix=prefix)
        if value:
            _append_optional_anchor(anchors, f"action_policy={value}", prefix=prefix)
    for label, key in (
        ("required_coverage", "required_coverage"),
    ):
        value = str(summary.get(key) or "").strip()
        if not value:
            continue
        _append_optional_anchor(anchors, f"{label}={_dispatch_path_text(value, workdir=workdir)}", prefix=prefix)
    return clip_inline(prefix + "; ".join(anchors) + ".", ROLE_DISPATCH_MESSAGE_LIMIT)


def _append_bounded_list_anchor(
    anchors: list[str],
    label: str,
    values: list[str],
    *,
    prefix: str,
    max_items: int | None = None,
) -> None:
    if not values:
        return
    max_count = min(ROLE_DISPATCH_LIST_ITEM_LIMIT, len(values), max_items or len(values))
    for count in range(max_count, 0, -1):
        omitted = len(values) - count
        anchor = f"{label}={', '.join(values[:count])}"
        if omitted:
            anchor = f"{anchor} (+{omitted} omitted)"
        if _inline_dispatch_length(prefix, [*anchors, anchor]) <= ROLE_DISPATCH_MESSAGE_LIMIT:
            anchors.append(anchor)
            return


def _append_optional_anchor(anchors: list[str], anchor: str, *, prefix: str) -> None:
    if _inline_dispatch_length(prefix, [*anchors, anchor]) <= ROLE_DISPATCH_MESSAGE_LIMIT:
        anchors.append(anchor)


def _inline_dispatch_length(prefix: str, anchors: list[str]) -> int:
    return len(" ".join((prefix + "; ".join(anchors) + ".").split()))


def _dispatch_path_text(value: str, *, workdir: str = "") -> str:
    text = str(value or "").strip()
    if not text or not workdir:
        return text
    try:
        path = Path(text).expanduser()
    except (OSError, ValueError):
        return text
    if not path.is_absolute():
        return text
    try:
        relative = path.resolve().relative_to(Path(workdir).expanduser().resolve())
    except (OSError, ValueError):
        return text
    return str(relative)


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
        summary["result_template_fill"] = load_system_prompt_asset("agent_native/result-template-fill-save-copy.md").strip()
    set_summary_text(summary, "result_outbox_dir", submit_hint.get("result_outbox_absolute_dir") or submit_hint.get("result_outbox_dir"))
    set_summary_text(summary, "submit_command", submit_hint.get("command"))


def _attach_agent_next_step_evidence_summary(summary: dict[str, object], next_step: dict, *, compact: bool) -> None:
    known_count = non_bool_int(next_step.get("known_evidence_count"))
    if known_count is not None:
        summary["known_evidence_count"] = known_count
    known_ids = [str(item).strip() for item in list(next_step.get("known_evidence_ids") or []) if str(item).strip()]
    if known_ids:
        displayed_known_ids = known_ids[-8:]
        if len(known_ids) > len(displayed_known_ids):
            summary["known_evidence_ids_omitted"] = len(known_ids) - len(displayed_known_ids)
        summary["known_evidence_ids"] = displayed_known_ids
    known_refs = agent_known_evidence_ref_summaries(next_step.get("known_evidence_refs"), limit=3 if compact else 5)
    if known_refs:
        summary["known_evidence_refs"] = known_refs
    set_summary_text(summary, "known_evidence_scope", agent_current_step_evidence_scope_summary(next_step))


def _attach_agent_next_step_coverage_summary(summary: dict[str, object], next_step: dict, *, compact: bool) -> None:
    required_coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    coverage_target_ids = _coverage_target_ids(next_step)
    if coverage_target_ids:
        summary["coverage_target_ids"] = coverage_target_ids
    coverage_targets = _coverage_targets(next_step, compact=False)
    if coverage_targets and compact:
        coverage_preview = _coverage_targets(next_step, compact=True)
        summary["coverage_targets_preview"] = coverage_preview
        if len(coverage_targets) > len(coverage_preview):
            summary["coverage_targets_omitted"] = len(coverage_targets) - len(coverage_preview)
    elif coverage_targets:
        summary["coverage_targets"] = coverage_targets
    set_summary_text(summary, "required_coverage", required_coverage_summary(required_coverage))
    set_summary_text(summary, "coverage_classification_note", coverage_classification_note(next_step))
    top_gaps = coverage_gap_summaries(required_coverage.get("top_gaps"), limit=3 if compact else 5)
    if top_gaps:
        summary["top_coverage_gaps"] = top_gaps


def _coverage_target_ids(next_step: dict) -> list[str]:
    target_ids = [str(item).strip() for item in list(next_step.get("coverage_target_ids") or []) if str(item).strip()]
    if target_ids:
        return list(dict.fromkeys(target_ids))
    target_ids = []
    for item in list(next_step.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return list(dict.fromkeys(target_ids))


def _coverage_targets(next_step: dict, *, compact: bool = False) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    for item in list(next_step.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if not target_id:
            continue
        target: dict[str, object] = {"id": target_id}
        kind = str(item.get("kind") or "").strip()
        if kind:
            target["kind"] = kind
        if "required" in item:
            target["required"] = bool(item.get("required"))
        text = str(item.get("text") or item.get("label") or "").strip()
        if text:
            target["text"] = text if not compact else text[:157].rstrip() + ("..." if len(text) > 160 else "")
        targets.append(target)
        if compact and len(targets) >= 3:
            break
    return targets
