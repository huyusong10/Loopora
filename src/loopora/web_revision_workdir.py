from __future__ import annotations

from urllib.parse import quote

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.asset_errors import asset_mutation_error_message
from loopora.service_alignment_revision import REVISION_SESSION_CREATE_ERROR
from loopora.web_start_context import workdir_context_href
from loopora.web_workdir_recovery import web_alignment_workdir_ready, web_alignment_workdir_recovery_payload


def bundle_revision_workdir_recovery_payload(service, bundle_id: str) -> dict[str, object] | None:
    workdir = _bundle_source_workdir(service, bundle_id)
    if web_alignment_workdir_ready(workdir):
        return None
    recovery = web_alignment_workdir_recovery_payload(workdir, action="revise_bundle")
    recovery["source_bundle_id"] = bundle_id
    return recovery


def run_revision_workdir_recovery_payload(service, run_id: str) -> dict[str, object] | None:
    workdir = _run_source_workdir(service, run_id)
    if web_alignment_workdir_ready(workdir):
        return None
    recovery = web_alignment_workdir_recovery_payload(workdir, action="revise_run")
    recovery["source_run_id"] = run_id
    return recovery


def revision_session_creation_recovery_payload(
    source_kind: str,
    source_id: str,
    exc: BaseException,
    *,
    workdir_context: str = "",
) -> dict[str, object]:
    action = "revise_run" if source_kind == "run" else "revise_bundle"
    actions = _revision_session_creation_recovery_actions(source_kind, source_id, workdir_context=workdir_context)
    summary: dict[str, object] = {
        "ready": False,
        "status": "blocked_by_revision_session_creation",
        "surface": "web_revision",
        "resource": "revision session",
        "action": action,
        "next_action_kinds": _revision_action_kinds(actions),
    }
    payload: dict[str, object] = {
        "ok": False,
        "error": asset_mutation_error_message(exc, asset_label="revision session", action="created"),
        "resource_recovery": "revision_session_creation_failed",
        "status": "blocked_by_revision_session_creation",
        "surface": "web_revision",
        "resource": "revision session",
        "action": action,
        "web_revision_recovery_summary": summary,
        "next_actions": actions,
    }
    payload[f"source_{source_kind}_id"] = source_id
    summary[f"source_{source_kind}_id"] = source_id
    return project_next_action_readiness_contract(payload, summary_key="web_revision_recovery_summary")


def browser_revision_session_creation_recovery_payload(
    source_kind: str,
    source_id: str,
    exc: BaseException,
    *,
    retry_url: str,
    workdir_context: str = "",
) -> dict[str, object]:
    payload = revision_session_creation_recovery_payload(
        source_kind,
        source_id,
        exc,
        workdir_context=workdir_context,
    )
    for action in payload.get("next_actions") or []:
        if isinstance(action, dict) and action.get("kind") == "retry_revision_session":
            action.pop("endpoint", None)
            action["form_action"] = retry_url
            action["form_method"] = "POST"
    return project_next_action_readiness_contract(payload, summary_key="web_revision_recovery_summary")


def is_revision_session_creation_recovery_error(exc: BaseException) -> bool:
    return isinstance(exc, OSError | UnicodeError) or str(exc) == REVISION_SESSION_CREATE_ERROR


def revision_source_workdir_context(service, source_kind: str, source_id: str) -> str:
    return _run_source_workdir(service, source_id) if source_kind == "run" else _bundle_source_workdir(service, source_id)


def _revision_session_creation_recovery_actions(
    source_kind: str,
    source_id: str,
    *,
    workdir_context: str = "",
) -> list[dict[str, object]]:
    encoded_source_id = quote(source_id, safe="")
    if source_kind == "run":
        review_kind = "review_source_run"
        review_target = "web_run_detail"
        review_url = f"/runs/{encoded_source_id}"
        retry_target = "web_run_revision"
        retry_endpoint = f"/api/runs/{encoded_source_id}/revise"
    else:
        review_kind = "review_source_bundle"
        review_target = "web_bundle_detail"
        review_url = f"/bundles/{encoded_source_id}"
        retry_target = "web_bundle_revision"
        retry_endpoint = f"/api/bundles/{encoded_source_id}/revise"
    return [
        {
            "kind": review_kind,
            "target": review_target,
            "source_id": source_id,
            "redirect_url": workdir_context_href(review_url, workdir_context),
        },
        {
            "kind": "retry_revision_session",
            "target": retry_target,
            "method": "POST",
            "source_id": source_id,
            "endpoint": retry_endpoint,
            "after_action": review_kind,
        },
        {
            "kind": "open_support",
            "target": "web_support",
            "redirect_url": workdir_context_href("/support", workdir_context),
        },
    ]


def _revision_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]


def _bundle_source_workdir(service, bundle_id: str) -> str:
    bundle = service.get_bundle(bundle_id)
    loop = service.get_loop(str(bundle.get("loop_id") or ""))
    return str(loop.get("workdir") or "")


def _run_source_workdir(service, run_id: str) -> str:
    run = service.get_run(run_id)
    loop = service.get_loop(str(run.get("loop_id") or ""))
    return str(loop.get("workdir") or "")
