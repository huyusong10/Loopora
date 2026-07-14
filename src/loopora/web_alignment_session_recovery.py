from __future__ import annotations

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.asset_errors import asset_mutation_error_message
from loopora.service_alignment_session_creation import ALIGNMENT_SESSION_CREATE_ERROR
from loopora.web_url_utils import with_query_params


def alignment_session_creation_recovery_payload(
    *,
    workdir: str,
    source_option_id: str,
    exc: BaseException,
) -> dict[str, object]:
    actions = _alignment_session_creation_recovery_actions(workdir)
    summary: dict[str, object] = {
        "ready": False,
        "status": "blocked_by_alignment_session_creation",
        "surface": "web_alignment",
        "resource": "alignment session",
        "action": "create_alignment_session",
        "workdir": workdir,
        "source_option_id": source_option_id,
        "next_action_kinds": _alignment_action_kinds(actions),
    }
    payload: dict[str, object] = {
        "ok": False,
        "error": asset_mutation_error_message(exc, asset_label="alignment session", action="created"),
        "resource_recovery": "alignment_session_creation_failed",
        "status": "blocked_by_alignment_session_creation",
        "surface": "web_alignment",
        "resource": "alignment session",
        "action": "create_alignment_session",
        "workdir": workdir,
        "source_option_id": source_option_id,
        "web_alignment_session_recovery_summary": summary,
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_alignment_session_recovery_summary")


def is_alignment_session_creation_recovery_error(exc: BaseException) -> bool:
    return isinstance(exc, OSError | UnicodeError) or str(exc) == ALIGNMENT_SESSION_CREATE_ERROR


def _alignment_session_creation_recovery_actions(workdir: str) -> list[dict[str, object]]:
    return [
        {
            "kind": "review_alignment_source_context",
            "target": "web_alignment_source_context",
            "method": "POST",
            "endpoint": "/api/alignments/workdir-context",
            "workdir": workdir,
        },
        {
            "kind": "retry_alignment_session_create",
            "target": "web_alignment",
            "method": "POST",
            "endpoint": "/api/alignments/sessions",
            "after_action": "review_alignment_source_context",
        },
        {
            "kind": "open_support",
            "target": "web_support",
            "redirect_url": with_query_params("/support", workdir=workdir or None),
        },
    ]


def _alignment_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
