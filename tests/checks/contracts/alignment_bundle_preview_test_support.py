from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_bundle_preview import AlignmentBundlePreviewContext, alignment_bundle_preview


def preview_payload(bundle: dict, *, source_path: str = "", validation: dict | None = None) -> dict:
    return {
        "ok": bool((validation or {}).get("ok", True)),
        "bundle": bundle,
        "source_path": source_path,
        "validation": validation or {},
    }


def never_load_validated(_session: dict, _raw_yaml: str, _semantic_issues: list[str]) -> tuple[dict, str]:
    raise AssertionError("ready validation should not run for this preview path")


def preview_alignment_bundle(
    session: dict,
    *,
    load_validated_bundle_text: Any = never_load_validated,
    now: str = "2026-05-29T00:00:00Z",
) -> dict:
    return alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=load_validated_bundle_text,
            now=lambda: now,
        ),
        session,
    )


def write_alignment_bundle(tmp_path: Path, raw_yaml: str | None = None) -> tuple[Path, str]:
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir()
    yaml_text = raw_yaml if raw_yaml is not None else alignment_bundle_yaml(str(tmp_path))
    bundle_path.write_text(yaml_text, encoding="utf-8")
    return bundle_path, yaml_text


def bundle_session(session_id: str, status: str, bundle_path: Path, validation: dict | None = None) -> dict:
    session = {"id": session_id, "status": status, "bundle_path": str(bundle_path)}
    if validation is not None:
        session["validation"] = validation
    return session
