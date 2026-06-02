from __future__ import annotations

import re

from loopora.alignment_semantics import trace_text_units


def preview_list_items(markdown_text: str, *, limit: int = 4) -> list[str]:
    items = []
    for line in str(markdown_text or "").splitlines():
        cleaned = re.sub(r"^\s*[-*]\s+", "", line).strip()
        cleaned = re.sub(r"^\s*\d+[.)]\s+", "", cleaned).strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        items.append(cleaned)
        if len(items) >= limit:
            break
    if items:
        return items
    compact = re.sub(r"\s+", " ", str(markdown_text or "")).strip()
    return [compact[:180]] if compact else []


def build_role_posture_trace(roles: list[dict]) -> list[str]:
    traces: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        role_name = str(role.get("name") or role.get("key") or "").strip()
        archetype = str(role.get("archetype") or "").strip()
        posture = role_posture_preview(role)
        if posture and (role_name or archetype):
            base = f"{role_name or 'Role'} ({archetype or 'custom'})"
            traces.append(f"{base}: {posture}")
    return traces[:4]


def role_posture_preview(role: dict) -> str:
    for field in ("posture_notes", "description", "prompt_markdown"):
        for unit in trace_text_units(str(role.get(field) or "")):
            compact = re.sub(r"\s+", " ", unit).strip()
            if not compact or _role_prompt_mechanics_unit(compact):
                continue
            return compact[:180].rstrip() + ("..." if len(compact) > 180 else "")
    return ""


def _role_prompt_mechanics_unit(text: str) -> bool:
    return bool(re.fullmatch(r"(?:version|archetype)\s*:\s*.+", text.strip(), re.IGNORECASE))
