from __future__ import annotations

from collections.abc import Mapping


def first_use_action_readiness_summary(actions: list[dict[str, object]]) -> dict[str, object]:
    ready_kinds: list[str] = []
    ready_now_kinds: list[str] = []
    ready_after_actions: dict[str, str] = {}
    blocked_kinds: list[str] = []
    blockers_by_kind: dict[str, list[str]] = {}
    for action in actions:
        kind = str(action.get("kind") or "").strip()
        if not kind:
            continue
        readiness_key = "action_ready" if isinstance(action.get("action_ready"), bool) else "command_ready"
        blockers_key = "action_blockers" if readiness_key == "action_ready" else "command_blockers"
        blockers = [str(item) for item in list(action.get(blockers_key) or []) if str(item)]
        if action.get(readiness_key) is False:
            blocked_kinds.append(kind)
            blockers_by_kind[kind] = blockers
        else:
            ready_kinds.append(kind)
            after_action = str(action.get("after_action") or "").strip()
            if after_action:
                ready_after_actions[kind] = after_action
            else:
                ready_now_kinds.append(kind)
    return {
        "ready_kinds": ready_kinds,
        "ready_now_kinds": ready_now_kinds,
        "ready_after_actions": ready_after_actions,
        "blocked_kinds": blocked_kinds,
        "command_blockers": blockers_by_kind,
    }


def project_first_use_action_readiness_summary(
    target: dict[str, object],
    *,
    prefix: str,
    readiness: Mapping[str, object],
) -> None:
    target[f"{prefix}_ready_kinds"] = list(readiness.get("ready_kinds") or [])
    target[f"{prefix}_ready_now_kinds"] = list(readiness.get("ready_now_kinds") or [])
    target[f"{prefix}_ready_after_actions"] = dict(readiness.get("ready_after_actions") or {})
    target[f"{prefix}_blocked_kinds"] = list(readiness.get("blocked_kinds") or [])
    target[f"{prefix}_command_blockers"] = dict(readiness.get("command_blockers") or {})


def first_use_actions(payload: Mapping[str, object], key: str) -> list[dict[str, object]]:
    actions = payload.get(key)
    if not isinstance(actions, list):
        return []
    return [action for action in actions if isinstance(action, dict)]


def first_use_action_by_kind(actions: list[dict[str, object]], kind: str) -> dict[str, object]:
    for action in actions:
        if str(action.get("kind") or "") == kind:
            return action
    return {}
