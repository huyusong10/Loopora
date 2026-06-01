from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loopora.alignment_readiness_rules import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.alignment_traceability_rules import ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS
from loopora.service_alignment_executor_settings import (
    AlignmentExecutorSettingsRequest as AlignmentExecutorSettingsRequest,
    alignment_executor_settings_from_raw as alignment_executor_settings_from_raw,
    default_alignment_executor_settings as default_alignment_executor_settings,
    normalize_alignment_executor_settings as normalize_alignment_executor_settings,
)

ALIGNMENT_READINESS_KEYS = [
    "loop_fit",
    "task_scope",
    "success_surface",
    "fake_done_risks",
    "evidence_preferences",
    "execution_strategy",
    "residual_risk_policy",
    "judgment_tradeoffs",
    "local_governance",
    "role_posture",
    "workflow_shape",
    "explicit_confirmation",
]
ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS = [
    "success_surface",
    "fake_done_risks",
    "evidence_preferences",
    "loop_fit",
    "execution_strategy",
    "judgment_tradeoffs",
    "residual_risk_policy",
    "local_governance",
]
ALIGNMENT_MISSING_ITEM_IDS = frozenset(
    [
        *ALIGNMENT_READINESS_KEYS,
        *ALIGNMENT_READINESS_EVIDENCE_KEYS,
        *ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS,
        *ALIGNMENT_AGENT_ENTRY_REVIEW_ITEM_IDS,
        "agreement_summary",
        "open_questions",
        "readiness_checklist",
        "readiness_evidence",
    ]
)
ALIGNMENT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {
            "type": "string",
            "enum": ["question", "bundle", "blocked"],
        },
        "assistant_message": {"type": "string"},
        "needs_user_input": {"type": "boolean"},
        "decision_options": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "recommended": {"type": "boolean"},
                    "user_reply": {"type": "string"},
                },
                "required": ["id", "label", "description", "recommended", "user_reply"],
            },
        },
        "bundle_yaml": {"type": "string"},
        "session_ref": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "session_id": {"type": "string"},
                "thread_id": {"type": "string"},
                "conversation_id": {"type": "string"},
                "provider": {"type": "string"},
                "raw_json": {"type": "string"},
            },
            "required": ["session_id", "thread_id", "conversation_id", "provider", "raw_json"],
        },
        "alignment_phase": {
            "type": "string",
            "enum": ["clarifying", "agreement", "confirmed", "bundle", "blocked"],
        },
        "agreement_summary": {"type": "string"},
        "readiness_checklist": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "task_scope": {"type": "boolean"},
                "loop_fit": {"type": "boolean"},
                "success_surface": {"type": "boolean"},
                "fake_done_risks": {"type": "boolean"},
                "evidence_preferences": {"type": "boolean"},
                "execution_strategy": {"type": "boolean"},
                "residual_risk_policy": {"type": "boolean"},
                "judgment_tradeoffs": {"type": "boolean"},
                "local_governance": {"type": "boolean"},
                "role_posture": {"type": "boolean"},
                "workflow_shape": {"type": "boolean"},
                "explicit_confirmation": {"type": "boolean"},
            },
            "required": ALIGNMENT_READINESS_KEYS,
        },
        "readiness_evidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "task_scope": {"type": "string"},
                "loop_fit": {"type": "string"},
                "success_surface": {"type": "string"},
                "fake_done_risks": {"type": "string"},
                "evidence_preferences": {"type": "string"},
                "execution_strategy": {"type": "string"},
                "residual_risk_policy": {"type": "string"},
                "judgment_tradeoffs": {"type": "string"},
                "local_governance": {"type": "string"},
                "role_posture": {"type": "string"},
                "workflow_shape": {"type": "string"},
                "workdir_facts": {"type": "string"},
                "open_questions": {"type": "string"},
            },
            "required": [*ALIGNMENT_READINESS_EVIDENCE_KEYS, "open_questions"],
        },
    },
    "required": [
        "status",
        "assistant_message",
        "needs_user_input",
        "decision_options",
        "bundle_yaml",
        "session_ref",
        "alignment_phase",
        "agreement_summary",
        "readiness_checklist",
        "readiness_evidence",
    ],
}


@dataclass(frozen=True)
class AlignmentSessionCreateRequest:
    workdir: Path
    message: str = ""
    start_immediately: bool = True
    source_option_id: str = ""
    executor_settings: AlignmentExecutorSettingsRequest = field(default_factory=default_alignment_executor_settings)


@dataclass(frozen=True)
class RevisionSessionOptions:
    message: str = ""
    start_immediately: bool = True
    executor_settings: AlignmentExecutorSettingsRequest = field(default_factory=default_alignment_executor_settings)


@dataclass(frozen=True)
class RevisionAlignmentSessionRequest:
    seed_bundle: dict
    message: str
    start_immediately: bool
    source_context: dict
    linked_bundle_id: str
    linked_run_id: str
    executor_settings: AlignmentExecutorSettingsRequest


def coerce_alignment_session_create_request(
    request: AlignmentSessionCreateRequest | None,
    raw_request: dict[str, object],
) -> AlignmentSessionCreateRequest:
    if request is not None:
        if raw_request:
            raise TypeError("create_alignment_session accepts either request or keyword fields, not both")
        return request
    workdir = raw_request.get("workdir")
    if workdir is None:
        raise TypeError("create_alignment_session requires workdir")
    return AlignmentSessionCreateRequest(
        workdir=workdir if isinstance(workdir, Path) else Path(str(workdir)),
        message=str(raw_request.get("message", "") or ""),
        start_immediately=coerce_alignment_start_immediately(raw_request.get("start_immediately", True)),
        source_option_id=str(raw_request.get("source_option_id", "") or "").strip(),
        executor_settings=alignment_executor_settings_from_raw(raw_request),
    )


def coerce_revision_session_options(
    request: RevisionSessionOptions | None,
    raw_request: dict[str, object],
) -> RevisionSessionOptions:
    if request is not None:
        if raw_request:
            raise TypeError("revision session creation accepts either request or keyword fields, not both")
        return request
    return RevisionSessionOptions(
        message=str(raw_request.get("message", "") or ""),
        start_immediately=coerce_alignment_start_immediately(raw_request.get("start_immediately", True)),
        executor_settings=alignment_executor_settings_from_raw(raw_request),
    )


def coerce_alignment_start_immediately(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
