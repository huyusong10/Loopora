from __future__ import annotations

from urllib.parse import quote

from loopora.action_readiness_projection import project_next_action_readiness_contract


_WEB_DELETE_RESOURCES = {
    "loop": ("delete_loop", "/api/loops"),
    "bundle": ("delete_bundle", "/api/bundles"),
    "role_definition": ("delete_role_definition", "/api/role-definitions"),
    "orchestration": ("delete_orchestration", "/api/orchestrations"),
}


def web_delete_preview_payload(
    payload: dict[str, object],
    *,
    resource_kind: str,
    resource_id: str,
) -> dict[str, object]:
    projected = dict(payload)
    projected["next_actions"] = _web_delete_preview_next_actions(
        resource_kind,
        resource_id,
        delete_allowed=projected.get("delete_allowed") is True,
    )
    return project_next_action_readiness_contract(projected)


def _web_delete_preview_next_actions(
    resource_kind: str,
    resource_id: str,
    *,
    delete_allowed: bool,
) -> list[dict[str, object]]:
    if not delete_allowed:
        return []
    action_kind, endpoint_prefix = _WEB_DELETE_RESOURCES[resource_kind]
    return [
        {
            "kind": action_kind,
            "target": "web_api",
            "method": "DELETE",
            "endpoint": f"{endpoint_prefix}/{quote(str(resource_id), safe='')}",
            "note": "Call this only after reviewing the preview scope.",
        }
    ]
