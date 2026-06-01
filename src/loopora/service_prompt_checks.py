from __future__ import annotations

import json
from collections.abc import Mapping


def normalize_generated_checks(checks: object) -> list[dict]:
    if not isinstance(checks, list):
        return []
    normalized = []
    for raw_check in checks:
        if not isinstance(raw_check, Mapping):
            continue
        index = len(normalized) + 1
        title = str(raw_check.get("title", "")).strip() or f"Exploratory check {index}"
        when = str(raw_check.get("when", "")).strip()
        expect = str(raw_check.get("expect", "")).strip()
        fail_if = str(raw_check.get("fail_if", "")).strip()
        details = str(raw_check.get("details", "")).strip()
        if not details:
            parts = []
            if when:
                parts.append(f"When: {when}")
            if expect:
                parts.append(f"Expect: {expect}")
            if fail_if:
                parts.append(f"Fail if: {fail_if}")
            details = "\n".join(parts).strip()
        normalized.append(
            {
                "id": f"check_{index:03d}",
                "title": title,
                "details": details or "Auto-generated exploratory check.",
                "when": when,
                "expect": expect,
                "fail_if": fail_if,
                "source": "auto_generated",
            }
        )
    return normalized


def render_checks(checks: list[dict]) -> str:
    return json.dumps(checks, ensure_ascii=False, indent=2)
