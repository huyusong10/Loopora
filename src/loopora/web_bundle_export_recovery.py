from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.asset_errors import asset_mutation_error_message
from loopora.web_start_context import workdir_context_href


def web_bundle_export_generation_recovery_payload(
    bundle_id: str,
    exc: BaseException,
    *,
    retry_surface: Literal["api", "page"] = "api",
    workdir_context: str = "",
) -> dict[str, object]:
    actions = web_bundle_export_generation_recovery_actions(
        bundle_id,
        retry_surface=retry_surface,
        workdir_context=workdir_context,
    )
    payload: dict[str, object] = {
        "ok": False,
        "error": asset_mutation_error_message(exc, asset_label="plan file", action="generated"),
        "resource_recovery": "plan_file_export_generation_failed",
        "status": "blocked_by_plan_file_generation",
        "surface": "web_bundle_export",
        "resource": "Plan File",
        "action": "export",
        "bundle_id": bundle_id,
        "web_bundle_export_recovery_summary": {
            "ready": False,
            "status": "blocked_by_plan_file_generation",
            "surface": "web_bundle_export",
            "resource": "Plan File",
            "action": "export",
            "bundle_id": bundle_id,
            "next_action_kinds": _web_bundle_export_action_kinds(actions),
        },
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_bundle_export_recovery_summary")


def web_bundle_export_generation_recovery_actions(
    bundle_id: str,
    *,
    retry_surface: Literal["api", "page"] = "api",
    workdir_context: str = "",
) -> list[dict[str, object]]:
    encoded_bundle_id = quote(bundle_id, safe="")
    retry_action: dict[str, object] = {
        "kind": "retry_plan_file_export",
        "target": "web_bundle_export",
        "method": "GET",
        "bundle_id": bundle_id,
        "after_action": "review_plan_file",
    }
    if retry_surface == "page":
        retry_action["redirect_url"] = workdir_context_href(f"/bundles/{encoded_bundle_id}/export", workdir_context)
    else:
        retry_action["endpoint"] = f"/api/bundles/{encoded_bundle_id}/export"
    return [
        {
            "kind": "review_plan_file",
            "target": "web_bundle_detail",
            "bundle_id": bundle_id,
            "redirect_url": workdir_context_href(f"/bundles/{encoded_bundle_id}", workdir_context),
        },
        retry_action,
        {
            "kind": "open_plan_file_library",
            "target": "web_bundle_library",
            "redirect_url": workdir_context_href("/bundles", workdir_context),
        },
    ]


def _web_bundle_export_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
