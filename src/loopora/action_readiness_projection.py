from __future__ import annotations

from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)


def project_next_action_readiness_contract(
    payload: dict[str, object],
    *,
    summary_key: str = "",
) -> dict[str, object]:
    actions = _payload_actions(payload, "next_actions")
    action_kinds = [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    if summary_key:
        summary = payload.get(summary_key)
        if isinstance(summary, dict):
            summary["next_action_kinds"] = list(action_kinds)
            project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)
    return payload


def _payload_actions(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    actions = payload.get(key)
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]
