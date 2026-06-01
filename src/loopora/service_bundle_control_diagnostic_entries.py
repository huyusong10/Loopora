from __future__ import annotations

"""Shared bundle-control diagnostic entry shaping."""


def append_bundle_control_diagnostic(
    diagnostics: list[dict],
    spec: dict,
) -> None:
    code = str(spec.get("code") or "").strip()
    step_ids = [str(item).strip() for item in list(spec.get("step_ids") or []) if str(item).strip()]
    key = (code, tuple(step_ids or ()))
    existing_keys = {
        (str(item.get("code") or ""), tuple(item.get("step_ids") or ()))
        for item in diagnostics
        if isinstance(item, dict)
    }
    if key in existing_keys:
        return
    diagnostics.append(
        {
            "code": code,
            "severity": str(spec.get("severity") or "warning").strip(),
            "title": str(spec.get("title_en") or "").strip(),
            "title_zh": str(spec.get("title_zh") or spec.get("title_en") or "").strip(),
            "title_en": str(spec.get("title_en") or "").strip(),
            "message": str(spec.get("message_en") or "").strip(),
            "message_zh": str(spec.get("message_zh") or spec.get("message_en") or "").strip(),
            "message_en": str(spec.get("message_en") or "").strip(),
            "surfaces": [str(item).strip() for item in list(spec.get("surfaces") or []) if str(item).strip()],
            "step_ids": step_ids,
            "details": dict(spec.get("details") or {}),
        }
    )
