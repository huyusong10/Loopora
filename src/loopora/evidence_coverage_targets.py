from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def with_coverage_targets(compiled_spec: Mapping[str, Any], *, completion_mode: str = "gatekeeper") -> dict:
    spec = dict(compiled_spec)
    spec["coverage_targets"] = build_coverage_targets(spec, completion_mode=completion_mode)
    return spec


def build_coverage_targets(compiled_spec: Mapping[str, Any], *, completion_mode: str = "gatekeeper") -> list[dict]:
    targets: list[dict] = []
    for check in list(compiled_spec.get("checks") or []):
        if not isinstance(check, Mapping):
            continue
        check_id = str(check.get("id") or "").strip()
        if not check_id:
            continue
        title = str(check.get("title") or check_id).strip()
        text = str(check.get("details") or check.get("expect") or title).strip()
        targets.append(
            {
                "id": f"done_when.{check_id}",
                "kind": "done_when",
                "source_section": "Done When",
                "source_id": check_id,
                "label": title,
                "text": text,
                "required": True,
            }
        )

    for index, text in enumerate(_coverage_target_texts(compiled_spec.get("success_surface")), start=1):
        targets.append(
            {
                "id": f"success_surface.surface_{index:03d}",
                "kind": "success_surface",
                "source_section": "Success Surface",
                "source_id": f"surface_{index:03d}",
                "label": f"Success surface {index}",
                "text": text,
                "required": False,
            }
        )

    for index, text in enumerate(_coverage_target_texts(compiled_spec.get("fake_done_states")), start=1):
        targets.append(
            {
                "id": f"fake_done.risk_{index:03d}",
                "kind": "fake_done",
                "source_section": "Fake Done",
                "source_id": f"risk_{index:03d}",
                "label": f"Fake Done risk {index}",
                "text": text,
                "required": False,
            }
        )

    for index, text in enumerate(_coverage_target_texts(compiled_spec.get("evidence_preferences")), start=1):
        targets.append(
            {
                "id": f"evidence_preference.pref_{index:03d}",
                "kind": "evidence_preference",
                "source_section": "Evidence Preferences",
                "source_id": f"pref_{index:03d}",
                "label": f"Evidence preference {index}",
                "text": text,
                "required": False,
            }
        )

    if str(completion_mode or "gatekeeper").strip().lower() == "gatekeeper":
        targets.append(
            {
                "id": "gatekeeper.finish",
                "kind": "gatekeeper",
                "source_section": "Workflow",
                "source_id": "finish",
                "label": "GateKeeper finish",
                "text": "GateKeeper may finish only after citing supporting upstream evidence refs or measured self evidence.",
                "required": True,
            }
        )
    return targets


def parse_target_verify_ref(value: object) -> tuple[str, str] | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("target:"):
        parts = text.split(":", 2)
        if len(parts) == 3 and parts[1].strip():
            return parts[1].strip(), parts[2].strip() or "unknown"
    if text.startswith("check_results:"):
        parts = text.split(":", 2)
        if len(parts) >= 2 and parts[1].strip():
            return f"done_when.{parts[1].strip()}", parts[2].strip() if len(parts) == 3 else "unknown"
    if text.startswith("check:"):
        check_id = text.split(":", 1)[1].strip()
        if check_id:
            return f"done_when.{check_id}", "failed"
    return None


def _coverage_target_texts(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
