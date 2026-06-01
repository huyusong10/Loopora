from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from loopora.bundle_semantic_workflow_support import _parallel_review_role_text


def _lint_alignment_role_semantics(
    role_by_key: Mapping[str, Mapping[str, Any]],
    *,
    used_role_keys: list[object],
) -> list[str]:
    issues: list[str] = []
    for role_key in used_role_keys:
        role = role_by_key.get(str(role_key))
        if role is None:
            continue
        if _alignment_role_name_is_generic(role):
            issues.append(f"role_definition {role['key']} must use a task-specific role name")
        if not str(role.get("posture_notes", "") or "").strip():
            issues.append(f"role_definition {role['key']} must include task-scoped posture_notes")
    return issues


def _lint_alignment_duplicate_role_responsibilities(
    role_by_key: Mapping[str, Mapping[str, Any]],
    *,
    used_role_keys: list[object],
) -> list[str]:
    responsibilities: dict[tuple[str, str], list[str]] = {}
    for raw_key in dict.fromkeys(str(key) for key in used_role_keys):
        role = role_by_key.get(raw_key)
        if not role:
            continue
        archetype = str(role.get("archetype") or "").strip()
        role_text = _parallel_review_role_text(role)
        if not archetype or not role_text:
            continue
        responsibilities.setdefault((archetype, role_text), []).append(raw_key)
    return [
        "role_definitions must have distinct task evidence responsibilities: " + ", ".join(role_keys)
        for role_keys in responsibilities.values()
        if len(role_keys) > 1
    ]


def _alignment_role_name_is_generic(role: Mapping[str, Any]) -> bool:
    name = re.sub(r"\s+", " ", str(role.get("name", "") or "")).strip().lower()
    if name in {
        "builder",
        "generator",
        "inspector",
        "tester",
        "gatekeeper",
        "gate keeper",
        "verifier",
        "guide",
        "challenger",
        "custom",
    }:
        return True
    return bool(
        re.fullmatch(
            r"(?:builder|generator|inspector|tester|gatekeeper|gate keeper|verifier|guide|challenger|agent|role)[\s#_-]*\d+",
            name,
        )
    )
