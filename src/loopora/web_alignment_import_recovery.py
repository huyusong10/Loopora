from __future__ import annotations

from urllib.parse import quote

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.agent_entry_run_projection import AGENT_NATIVE_PREVIEW_ASYNC_START_ERROR
from loopora.asset_errors import asset_mutation_error_message
from loopora.service_alignment_bundle_validation_payloads import ALIGNMENT_BUNDLE_MISSING_FILE_ERROR
from loopora.service_types import LooporaError
from loopora.web_start_context import workdir_context_href
from loopora.web_url_utils import with_query_params

ALIGNMENT_SESSION_NOT_READY_PREFIX = "alignment session is not READY:"


def alignment_import_recovery_payload(
    session_id: str,
    exc: BaseException,
    *,
    workdir_context: str = "",
) -> dict[str, object]:
    actions = _alignment_bundle_recovery_actions(session_id, workdir_context=workdir_context)
    summary: dict[str, object] = {
        "ready": False,
        "status": "blocked_by_alignment_import",
        "surface": "web_alignment_import",
        "resource": "alignment bundle",
        "action": "import_alignment_bundle",
        "session_id": session_id,
        "next_action_kinds": _alignment_action_kinds(actions),
    }
    payload: dict[str, object] = {
        "ok": False,
        "error": asset_mutation_error_message(exc, asset_label="alignment bundle", action="imported"),
        "resource_recovery": "alignment_import_failed",
        "status": "blocked_by_alignment_import",
        "surface": "web_alignment_import",
        "resource": "alignment bundle",
        "action": "import_alignment_bundle",
        "session_id": session_id,
        "web_alignment_import_recovery_summary": summary,
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_alignment_import_recovery_summary")


def alignment_bundle_sync_recovery_payload(session_id: str, result: dict, *, workdir_context: str = "") -> dict[str, object]:
    actions = _alignment_bundle_recovery_actions(
        session_id,
        retry_import_after_action="sync_alignment_bundle",
        workdir_context=workdir_context,
    )
    error = _alignment_sync_error(result)
    summary: dict[str, object] = {
        "ready": False,
        "status": "blocked_by_alignment_bundle_sync",
        "surface": "web_alignment_bundle_sync",
        "resource": "alignment bundle",
        "action": "sync_alignment_bundle",
        "session_id": session_id,
        "next_action_kinds": _alignment_action_kinds(actions),
    }
    payload: dict[str, object] = {
        **result,
        "ok": False,
        "error": error,
        "resource_recovery": "alignment_bundle_sync_failed",
        "status": "blocked_by_alignment_bundle_sync",
        "surface": "web_alignment_bundle_sync",
        "resource": "alignment bundle",
        "action": "sync_alignment_bundle",
        "session_id": session_id,
        "web_alignment_bundle_sync_recovery_summary": summary,
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_alignment_bundle_sync_recovery_summary")


def alignment_bundle_preview_recovery_payload(session_id: str, result: dict, *, workdir_context: str = "") -> dict[str, object]:
    actions = _alignment_bundle_preview_recovery_actions(session_id, workdir_context=workdir_context)
    error = _alignment_sync_error(result)
    summary: dict[str, object] = {
        "ready": False,
        "status": "blocked_by_alignment_bundle_preview",
        "surface": "web_alignment_bundle_preview",
        "resource": "alignment bundle",
        "action": "preview_alignment_bundle",
        "session_id": session_id,
        "next_action_kinds": _alignment_action_kinds(actions),
    }
    payload: dict[str, object] = {
        **result,
        "ok": False,
        "error": error,
        "resource_recovery": "alignment_bundle_preview_failed",
        "status": "blocked_by_alignment_bundle_preview",
        "surface": "web_alignment_bundle_preview",
        "resource": "alignment bundle",
        "action": "preview_alignment_bundle",
        "session_id": session_id,
        "web_alignment_bundle_preview_recovery_summary": summary,
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_alignment_bundle_preview_recovery_summary")


def is_alignment_import_recovery_error(exc: BaseException) -> bool:
    if isinstance(exc, OSError | UnicodeError):
        return True
    if not isinstance(exc, LooporaError):
        return False
    message = str(exc)
    if message == AGENT_NATIVE_PREVIEW_ASYNC_START_ERROR:
        return False
    return not message.startswith(ALIGNMENT_SESSION_NOT_READY_PREFIX)


def _alignment_bundle_recovery_actions(
    session_id: str,
    *,
    retry_import_after_action: str = "review_alignment_bundle",
    workdir_context: str = "",
) -> list[dict[str, object]]:
    encoded_session_id = quote(session_id, safe="")
    return [
        {
            "kind": "review_alignment_bundle",
            "target": "web_alignment_bundle",
            "session_id": session_id,
            "redirect_url": workdir_context_href(
                f"/loops/new/bundle?alignment_session_id={encoded_session_id}",
                workdir_context,
            ),
        },
        {
            "kind": "sync_alignment_bundle",
            "target": "web_alignment_bundle_sync",
            "method": "POST",
            "session_id": session_id,
            "endpoint": f"/api/alignments/sessions/{encoded_session_id}/bundle/sync",
            "after_action": "review_alignment_bundle",
        },
        {
            "kind": "retry_alignment_import",
            "target": "web_alignment_import",
            "method": "POST",
            "session_id": session_id,
            "endpoint": f"/api/alignments/sessions/{encoded_session_id}/import",
            "after_action": retry_import_after_action,
        },
        {
            "kind": "open_support",
            "target": "web_support",
            "redirect_url": workdir_context_href(
                with_query_params("/support", alignment_session_id=session_id),
                workdir_context,
            ),
        },
    ]


def _alignment_bundle_preview_recovery_actions(session_id: str, *, workdir_context: str = "") -> list[dict[str, object]]:
    encoded_session_id = quote(session_id, safe="")
    return [
        {
            "kind": "review_alignment_bundle",
            "target": "web_alignment_bundle",
            "session_id": session_id,
            "redirect_url": workdir_context_href(
                f"/loops/new/bundle?alignment_session_id={encoded_session_id}",
                workdir_context,
            ),
        },
        {
            "kind": "sync_alignment_bundle",
            "target": "web_alignment_bundle_sync",
            "method": "POST",
            "session_id": session_id,
            "endpoint": f"/api/alignments/sessions/{encoded_session_id}/bundle/sync",
            "after_action": "review_alignment_bundle",
        },
        {
            "kind": "retry_alignment_bundle_preview",
            "target": "web_alignment_bundle_preview",
            "method": "GET",
            "session_id": session_id,
            "endpoint": f"/api/alignments/sessions/{encoded_session_id}/bundle",
            "after_action": "sync_alignment_bundle",
        },
        {
            "kind": "open_support",
            "target": "web_support",
            "redirect_url": workdir_context_href(
                with_query_params("/support", alignment_session_id=session_id),
                workdir_context,
            ),
        },
    ]


def _alignment_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _alignment_sync_error(result: dict) -> str:
    validation = result.get("validation")
    if isinstance(validation, dict):
        error = str(validation.get("error") or "").strip()
        if error:
            return error
    session = result.get("session")
    if isinstance(session, dict):
        error = str(session.get("error_message") or "").strip()
        if error:
            return error
    if result.get("ok") is False and result.get("bundle") is None and not str(result.get("yaml") or "").strip():
        return ALIGNMENT_BUNDLE_MISSING_FILE_ERROR
    return "alignment bundle could not be synced"
