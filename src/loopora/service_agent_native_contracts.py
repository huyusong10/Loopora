from __future__ import annotations

import re
from typing import Any

from loopora.agent_native_evidence_contracts import _agent_native_string_list
from loopora.agent_native_guidance import actionable_blocking_item as _shared_actionable_blocking_item
from loopora.agent_native_guidance import actionable_next_action as _shared_actionable_next_action


def _agent_native_previous_blocked_handoff(previous_summary: dict[str, Any]) -> dict[str, Any]:
    handoffs = previous_summary.get("step_handoffs")
    if not isinstance(handoffs, list):
        return {}
    for handoff in reversed(handoffs):
        if not isinstance(handoff, dict):
            continue
        status = str(handoff.get("status") or "").strip()
        if status == "blocked" or _agent_native_string_list(handoff.get("blocking_items")):
            return handoff
    return {}


def agent_native_actionable_blocking_item(item: str) -> str:
    return _shared_actionable_blocking_item(item)


def agent_native_actionable_repair_next_action(action: str, blocking_items: list[str]) -> str:
    return _shared_actionable_next_action(action, blocking_items)


_REPAIR_TARGET_TOKEN_RE = re.compile(
    r"\b(?:check_\d+|done_when\.check_\d+|fake_done\.risk_\d+|evidence_preference\.pref_\d+|success_surface\.surface_\d+|gatekeeper\.finish)\b"
)


def _agent_native_repair_target_tokens(top_gaps: list[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for gap in top_gaps:
        target_id = str(gap.get("target_id") or "").strip().lower()
        if not target_id:
            continue
        tokens.add(target_id)
        if "." in target_id:
            tokens.add(target_id.rsplit(".", 1)[-1])
    return tokens


def _agent_native_blocking_target_tokens(blocking_items: list[str]) -> set[str]:
    tokens: set[str] = set()
    for item in blocking_items:
        for match in _REPAIR_TARGET_TOKEN_RE.findall(str(item or "").lower()):
            tokens.add(match)
            if "." in match:
                tokens.add(match.rsplit(".", 1)[-1])
    return tokens


def _agent_native_repair_blockers_still_current(blocking_items: list[str], top_gaps: list[dict[str, Any]]) -> bool:
    blocker_tokens = _agent_native_blocking_target_tokens(blocking_items)
    if not blocker_tokens:
        return True
    return bool(blocker_tokens & _agent_native_repair_target_tokens(top_gaps))


def _agent_native_current_gap_repair_next_action(top_gaps: list[dict[str, Any]]) -> str:
    if not top_gaps:
        return "Continue with the newly supporting evidence before asking GateKeeper to pass again."
    return "Continue from the current coverage gaps instead of repeating the resolved previous blocker before asking GateKeeper to pass again."


def _agent_native_role_posture_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    postures: list[str] = []
    for item in value:
        if isinstance(item, dict):
            posture = str(item.get("posture_notes") or "").strip()
            if not posture:
                continue
            role_name = str(item.get("role_name") or item.get("name") or "").strip()
            archetype = str(item.get("archetype") or "").strip()
            label = role_name or archetype
            if label and archetype and archetype not in label.lower():
                label = f"{label} ({archetype})"
            postures.append(f"{label}: {posture}" if label else posture)
            continue
        text = str(item or "").strip()
        if text:
            postures.append(text)
    return postures
