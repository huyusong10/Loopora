from __future__ import annotations

from collections.abc import Mapping

from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)


def _project_support_next_action_contract(payload: dict[str, object]) -> None:
    actions = _support_actions(payload)
    action_kinds = [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
    payload["next_action_kinds"] = action_kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="next_action", readiness=readiness)
    summary = payload.get("support_summary")
    if isinstance(summary, dict):
        summary["next_action_kinds"] = list(action_kinds)
        project_first_use_action_readiness_summary(summary, prefix="next_action", readiness=readiness)


def _support_actions(payload: Mapping[str, object]) -> list[dict[str, object]]:
    actions = payload.get("next_actions")
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]
