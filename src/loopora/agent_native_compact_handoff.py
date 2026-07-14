from __future__ import annotations

from typing import Any

from loopora.summary_projection_helpers import clip_inline


_NEXT_STEP_KEYS = (
    "step_id",
    "role",
    "target_agent",
    "target_agent_config_exists",
    "dispatch_next",
    "dispatch_unavailable",
    "action_policy",
    "known_evidence_count",
    "known_evidence_ids",
    "known_evidence_scope",
    "coverage_target_ids",
    "required_coverage",
    "coverage_classification_note",
    "iteration_repair",
    "continuation",
)

_WORK_PANEL_KEYS = (
    "state",
    "run_id",
    "task_proven",
    "task_outcome",
    "current_role",
    "current_step_id",
    "target_agent",
    "role_handoff_status",
    "role_handoff_owner",
    "next_action",
    "evidence_focus",
    "top_gaps",
    "ask_user",
    "run_url",
)


def compact_agent_next_step(summary: dict[str, Any]) -> dict[str, Any]:
    return _selected_values(summary, _NEXT_STEP_KEYS)


def compact_agent_work_panel(panel: dict[str, Any]) -> dict[str, Any]:
    compact = _selected_values(panel, _WORK_PANEL_KEYS)
    evidence_focus = str(compact.get("evidence_focus") or "").strip()
    if evidence_focus:
        compact["evidence_focus"] = clip_inline(evidence_focus, 180)
    top_gaps = _compact_work_panel_gaps(compact.get("top_gaps"))
    if top_gaps:
        compact["top_gaps"] = top_gaps
    else:
        compact.pop("top_gaps", None)
    return compact


def _selected_values(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: source[key] for key in keys if source.get(key) not in ("", [], {}, None)}


def _compact_work_panel_gaps(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    gaps: list[dict[str, str]] = []
    for item in [candidate for candidate in value if isinstance(candidate, dict)][:3]:
        gap: dict[str, str] = {}
        target_id = str(item.get("target_id") or item.get("id") or "").strip()
        status = str(item.get("status") or "").strip()
        if target_id:
            gap["target_id"] = target_id
        if status:
            gap["status"] = status
        if not target_id:
            summary = str(item.get("text") or item.get("reason") or item.get("summary") or "").strip()
            if summary:
                gap["summary"] = clip_inline(summary, 120)
        if gap:
            gaps.append(gap)
    return gaps
