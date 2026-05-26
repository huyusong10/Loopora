from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

AGENT_NATIVE_V3_SCHEMA_VERSION = 3

AgentV3Kind = Literal[
    "agent_plan",
    "agent_run",
    "agent_next",
    "agent_submit",
    "agent_submit_repair",
    "agent_check",
    "agent_recovery",
]


class AgentWorkPanelV3(TypedDict):
    state: str
    run_id: str
    task_proven: bool
    task_outcome: str
    current_role: str
    current_step_id: str
    next_action: str
    evidence_focus: str
    top_gaps: list[dict[str, Any]]
    ask_user: str
    todo_items: list[str]
    run_url: str


class AgentNativeSurfaceV3(TypedDict, total=False):
    activation: str
    host_dispatch: str
    proof_boundary: str
    experience_capabilities: dict[str, Any]


class AgentSubmitRepairV3(TypedDict, total=False):
    auto_repair_attempted: bool
    auto_repair_actions: list[str]
    core_blocker_preserved: bool
    core_blocker_kind: str
    repair_focus: list[str]
    next_repair_step: str


class ExperienceHealthV3(TypedDict):
    agent_work_panel_seen: bool
    agent_work_panel_sources: list[str]
    agent_work_panel_artifact_exposed: bool
    agent_work_panel_artifact_sources: list[str]
    todo_guidance_seen: bool
    todo_not_evidence_confirmed: bool
    user_question_guidance_available: bool
    role_dispatch_guidance_seen: bool
    native_trace_observed: bool
    auto_repair_events: list[dict[str, Any]]
    experience_notes: list[str]


class CurrentStepHandoffV3(TypedDict, total=False):
    step_id: str
    role: str
    target_agent: str
    context_path: str
    capsule_path: str
    result_template: str
    submit_command: str
    dispatch_unavailable: dict[str, Any]


class AgentV3Envelope(TypedDict):
    schema_version: int
    kind: AgentV3Kind
    status: str
    summary: dict[str, Any]
    technical_handoff: dict[str, Any]
    diagnostics: dict[str, Any]
    raw: NotRequired[dict[str, Any]]


class AgentV3EnvelopeExtras(TypedDict, total=False):
    technical_handoff: dict[str, Any]
    diagnostics: dict[str, Any]
    raw: dict[str, Any]


def agent_v3_envelope(
    *,
    kind: AgentV3Kind,
    status: str,
    summary: dict[str, Any],
    extras: AgentV3EnvelopeExtras | None = None,
) -> AgentV3Envelope:
    extra_fields = extras or {}
    envelope: AgentV3Envelope = {
        "schema_version": AGENT_NATIVE_V3_SCHEMA_VERSION,
        "kind": kind,
        "status": str(status or "").strip() or "unknown",
        "summary": summary,
        "technical_handoff": extra_fields.get("technical_handoff") or {},
        "diagnostics": extra_fields.get("diagnostics") or {},
    }
    if "raw" in extra_fields:
        envelope["raw"] = extra_fields["raw"]
    return envelope


def agent_v3_status(*, ready: object = None, complete: object = None, error: object = None) -> str:
    if error:
        return "blocked"
    if ready is True:
        return "ready"
    if ready is False:
        return "not_ready"
    if complete is True:
        return "complete"
    if complete is False:
        return "active"
    return "unknown"


def agent_v3_technical_handoff(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_url",
        "preview_url",
        "context_path",
        "capsule_path",
        "result_template",
        "submit_command",
        "next_context_path",
        "next_capsule_path",
        "next_result_template",
        "next_submit_command",
        "schema_lookup",
        "result_file_to_repair",
    )
    return {key: summary[key] for key in keys if summary.get(key) not in ("", [], {}, None)}


def agent_v3_legacy_raw(*, summary_key: str, summary: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    legacy = dict(payload)
    legacy.pop("agent_v3_envelope", None)
    legacy.pop("agent_v2_envelope", None)
    legacy[summary_key] = summary
    return {"legacy": legacy}
