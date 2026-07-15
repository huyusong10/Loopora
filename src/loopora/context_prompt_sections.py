from __future__ import annotations

import json

from loopora.context_prompt_evidence_sections import (
    _evidence_item_prompt_coverage_results as _evidence_item_prompt_coverage_results,
)
from loopora.context_prompt_evidence_sections import render_artifact_refs as _render_artifact_refs
from loopora.context_prompt_evidence_sections import render_evidence_section as _render_evidence_section
from loopora.context_value_helpers import clean_text as _clean_text
from loopora.context_value_helpers import normalize_coverage_gap_rows as _normalize_coverage_gap_rows
from loopora.context_value_helpers import string_list as _string_list
from loopora.utils import coerced_non_negative_int


def render_continuation_section(continuation: dict) -> str:
    if not isinstance(continuation, dict) or continuation.get("active") is not True:
        return ""
    verdict = continuation.get("previous_task_verdict") if isinstance(continuation.get("previous_task_verdict"), dict) else {}
    coverage = continuation.get("coverage") if isinstance(continuation.get("coverage"), dict) else {}
    lines = [
        "Continuation from previous terminal run:",
        f"- Reason: {continuation.get('reason') or 'previous terminal verdict requires another evidence pass'}",
        f"- Previous run id: {continuation.get('previous_run_id') or '-'}",
        f"- Previous run status: {continuation.get('previous_run_status') or '-'}",
        f"- Previous task verdict: {verdict.get('status') or '-'} :: {verdict.get('summary') or '-'}",
        f"- Previous task verdict file: {continuation.get('previous_task_verdict_path') or '-'}",
        f"- Previous coverage file: {continuation.get('previous_evidence_coverage_path') or '-'}",
        f"- Previous required coverage: {coverage.get('covered_check_count', 0)} covered, {coverage.get('missing_check_count', 0)} missing",
        (
            f"- Previous coverage targets: {coverage.get('covered_target_count', 0)}/{coverage.get('target_count', 0)} covered, "
            f"{coverage.get('weak_target_count', 0)} weak, {coverage.get('missing_target_count', 0)} missing, "
            f"{coverage.get('blocked_target_count', 0)} blocked"
        ),
    ]
    missing_check_ids = _string_list(coverage.get("missing_check_ids"))[:8]
    if missing_check_ids:
        lines.append(f"- Previous missing required check ids: {json.dumps(missing_check_ids, ensure_ascii=False)}")
    top_gaps = _normalize_coverage_gap_rows(coverage.get("top_gaps"))[:5]
    if top_gaps:
        lines.append(f"- Previous top coverage gaps: {json.dumps(top_gaps, ensure_ascii=False)}")
    next_focus = _contract_string_list(continuation.get("next_focus"))[:8]
    if next_focus:
        lines.append(f"- Next focus: {json.dumps(next_focus, ensure_ascii=False)}")
    return "\n".join(lines)


def render_iteration_section(packet: dict) -> str:
    iteration = packet["iteration"]
    current_step = packet["current_step"]
    iter_display = coerced_non_negative_int(iteration["iter_index"]) + 1
    step_display = coerced_non_negative_int(current_step["step_order"]) + 1
    if iteration["is_first_iteration"]:
        previous_line = "This is the first iteration, so there is no previous iteration result."
    else:
        previous_line = (
            f"This is iteration {iter_display}. Reference the previous iteration result before continuing. "
            f"Previous composite score: {iteration['previous_composite']}."
        )
    control = current_step.get("control") if isinstance(current_step.get("control"), dict) else {}
    action_policy = current_step.get("action_policy") if isinstance(current_step.get("action_policy"), dict) else {}
    control_lines = ""
    if control:
        trigger_refs = [str(item).strip() for item in list(control.get("trigger_evidence_refs") or []) if str(item).strip()]
        control_lines = (
            f"- Control trigger: {control.get('signal') or 'unknown'}\n"
            f"- Control mode: {control.get('mode') or 'advisory'}\n"
            f"- Control reason: {control.get('reason') or 'runtime control check'}\n"
            f"- Control evidence refs: {json.dumps(trigger_refs, ensure_ascii=False)}\n"
        )
    top_gaps = list(iteration.get("coverage_top_gaps") or [])[:5]
    missing_check_ids = _string_list(iteration.get("missing_check_ids"))[:8]
    coverage_gap_lines = (
        f"- Missing required check ids: {json.dumps(missing_check_ids, ensure_ascii=False)}\n"
        f"- Top coverage gaps: {json.dumps(top_gaps, ensure_ascii=False)}\n"
        if missing_check_ids or top_gaps
        else ""
    )
    return (
        "Current execution frame:\n"
        f"- Iteration: {iter_display}\n"
        f"- Step: {step_display}\n"
        f"- Step id: {current_step['step_id']}\n"
        f"- Role: {current_step['role_name']} ({current_step['archetype']})\n"
        f"- Model: {current_step['model'] or 'default'}\n"
        f"- Executor: {current_step['executor_kind']} / {current_step['executor_mode']}\n"
        f"- Parallel group: {current_step.get('parallel_group') or 'none'}\n"
        f"- Input policy: {json.dumps(current_step.get('inputs') or {}, ensure_ascii=False)}\n"
        f"- Action policy: {json.dumps(action_policy, ensure_ascii=False)}\n"
        f"{control_lines}"
        f"- Stagnation mode: {iteration['stagnation_mode']}\n"
        f"- Evidence progress mode: {iteration['evidence_progress_mode']}\n"
        f"- Coverage status: {iteration.get('coverage_status', 'pending')}\n"
        f"- Required coverage: {iteration['covered_check_count']} covered, {iteration['missing_check_count']} missing\n"
        f"{coverage_gap_lines}"
        f"- Consecutive iterations without required coverage delta: {iteration['consecutive_no_required_coverage_delta']}\n\n"
        f"{previous_line}"
    )


def render_handoff_section(title: str, handoff: dict | None, *, empty_text: str) -> str:
    if not handoff:
        return f"{title}:\n- {empty_text}"
    source = handoff["source"]
    return (
        f"{title}:\n"
        f"- From: {source['role_name']} ({source['archetype']})\n"
        f"- Step: {source['step_id']}\n"
        f"- Status: {handoff['status']}\n"
        f"- Summary: {handoff['summary']}\n"
        f"- Blocking items: {json.dumps(handoff['blocking_items'], ensure_ascii=False)}\n"
        f"- Evidence refs: {json.dumps(handoff.get('evidence_refs', []), ensure_ascii=False)}\n"
        f"- Recommended next action: {handoff['recommended_next_action']}"
    )


def render_handoff_list_section(title: str, handoffs: list[dict], *, empty_text: str) -> str:
    if not handoffs:
        return f"{title}:\n- {empty_text}"
    lines = [f"{title}:"]
    for handoff in handoffs:
        source = handoff["source"]
        lines.append(
            f"- {coerced_non_negative_int(source['step_order']) + 1}. {source['role_name']} ({source['archetype']}) :: {handoff['status']} :: {handoff['summary']}"
            f" :: blocking={json.dumps(handoff.get('blocking_items', []), ensure_ascii=False)}"
            f" :: evidence={json.dumps(handoff.get('evidence_refs', []), ensure_ascii=False)}"
            f" :: next={handoff.get('recommended_next_action', '-')}"
        )
    return "\n".join(lines)


def render_previous_iteration_summary(summary: dict | None) -> str:
    if not summary:
        return "Previous iteration summary:\n- No previous iteration summary is available yet."
    gatekeeper_verdict = summary.get("gatekeeper_verdict") if isinstance(summary.get("gatekeeper_verdict"), dict) else {}
    lines = [
        "Previous iteration summary:\n"
        f"- Iteration: {coerced_non_negative_int(summary['iter']) + 1}\n"
        f"- Composite score: {summary['score']['composite']}\n"
        f"- Score delta: {summary['score']['delta']}\n"
        f"- Passed: {summary['score']['passed']}\n"
        f"- Stagnation mode: {summary['stagnation']['mode']}\n"
        f"- Evidence progress mode: {summary['stagnation']['evidence_progress_mode']}\n"
        f"- Coverage status: {summary['stagnation'].get('coverage_status', 'pending')}\n"
        f"- Required coverage: {summary['stagnation']['covered_check_count']} covered, {summary['stagnation']['missing_check_count']} missing\n"
        f"- Consecutive iterations without required coverage delta: {summary['stagnation']['consecutive_no_required_coverage_delta']}\n"
        f"- Step count: {len(summary['workflow'])}"
    ]
    lines.extend(_previous_iteration_coverage_gap_lines(summary["stagnation"]))
    if gatekeeper_verdict:
        lines.append(
            "- GateKeeper verdict: "
            f"passed={gatekeeper_verdict.get('passed')} :: "
            f"{gatekeeper_verdict.get('decision_summary') or '-'}"
        )
        blockers = _string_list(gatekeeper_verdict.get("blocking_issues"))
        if blockers:
            lines.append(f"- GateKeeper blockers: {json.dumps(blockers, ensure_ascii=False)}")
        feedback = _clean_text(gatekeeper_verdict.get("feedback_to_builder"))
        if feedback:
            lines.append(f"- GateKeeper next repair: {feedback}")
        residual_risks = _string_list(gatekeeper_verdict.get("residual_risks"))
        if residual_risks:
            lines.append(f"- GateKeeper residual risks: {json.dumps(residual_risks, ensure_ascii=False)}")
        evidence_refs = _string_list(gatekeeper_verdict.get("evidence_refs"))
        if evidence_refs:
            lines.append(f"- GateKeeper evidence refs: {json.dumps(evidence_refs, ensure_ascii=False)}")
        coverage_results = _evidence_item_prompt_coverage_results(gatekeeper_verdict.get("coverage_results"))
        if coverage_results:
            lines.append(f"- GateKeeper coverage results: {json.dumps(coverage_results, ensure_ascii=False)}")
    for handoff in list(summary.get("step_handoffs", []))[:6]:
        source = handoff.get("source", {})
        lines.append(
            f"- Previous step {coerced_non_negative_int(source.get('step_order')) + 1} :: {source.get('role_name', '-')}"
            f" :: {handoff.get('status', '-')}"
            f" :: {handoff.get('summary', '-')}"
            f" :: blocking={json.dumps(handoff.get('blocking_items', []), ensure_ascii=False)}"
            f" :: evidence={json.dumps(handoff.get('evidence_refs', []), ensure_ascii=False)}"
            f" :: next={handoff.get('recommended_next_action', '-')}"
        )
    return "\n".join(lines)


def _previous_iteration_coverage_gap_lines(stagnation: dict) -> list[str]:
    lines: list[str] = []
    missing_check_ids = _string_list(stagnation.get("missing_check_ids"))[:8]
    if missing_check_ids:
        lines.append(f"- Missing required check ids: {json.dumps(missing_check_ids, ensure_ascii=False)}")
    coverage_top_gaps = _normalize_coverage_gap_rows(stagnation.get("coverage_top_gaps"))
    if coverage_top_gaps:
        lines.append(f"- Top coverage gaps: {json.dumps(coverage_top_gaps, ensure_ascii=False)}")
    return lines


def render_evidence_section(evidence: dict) -> str:
    return _render_evidence_section(evidence)


def render_artifact_refs(refs: list[dict]) -> str:
    return _render_artifact_refs(refs)


def _contract_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
