from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_bundle_preview import AlignmentBundlePreviewContext, alignment_bundle_preview
from loopora.service_types import LooporaError


def preview_payload(bundle: dict, *, source_path: str = "", validation: dict | None = None) -> dict:
    return {
        "ok": bool((validation or {}).get("ok", True)),
        "bundle": bundle,
        "source_path": source_path,
        "validation": validation or {},
    }


def never_load_validated(_session: dict, _raw_yaml: str, _semantic_issues: list[str]) -> tuple[dict, str]:
    raise AssertionError("ready validation should not run for this preview path")


def test_alignment_bundle_preview_reports_missing_bundle_without_building_preview(tmp_path: Path) -> None:
    session = {
        "id": "align_missing",
        "status": "ready",
        "bundle_path": str(tmp_path / "missing.yml"),
        "validation": {"ok": False, "error": "previous validation error"},
    }

    result = alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=never_load_validated,
            now=lambda: "2026-05-29T00:00:00Z",
        ),
        session,
    )

    assert result == {
        "ok": False,
        "session": session,
        "yaml": "",
        "bundle": None,
        "validation": {"ok": False, "error": "previous validation error"},
    }


def test_alignment_bundle_preview_normalizes_draft_bundle_without_ready_validation(tmp_path: Path) -> None:
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir()
    raw_yaml = alignment_bundle_yaml(str(tmp_path))
    bundle_path.write_text(raw_yaml, encoding="utf-8")
    session = {
        "id": "align_idle",
        "status": "idle",
        "bundle_path": str(bundle_path),
    }

    result = alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=never_load_validated,
            now=lambda: "2026-05-29T00:00:00Z",
        ),
        session,
    )

    assert result["ok"] is True
    assert result["session"] is session
    assert result["source_path"] == str(bundle_path)
    assert result["bundle"]["loop"]["workdir"] == str(tmp_path)
    assert result["validation"] == {"ok": True, "bundle_path": str(bundle_path)}
    assert result["yaml"].startswith("version: 1\n")


def test_alignment_bundle_preview_revalidates_ready_statuses(tmp_path: Path) -> None:
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir()
    raw_yaml = alignment_bundle_yaml(str(tmp_path))
    bundle_path.write_text(raw_yaml, encoding="utf-8")
    session = {
        "id": "align_ready",
        "status": "ready",
        "bundle_path": str(bundle_path),
    }

    def load_validated(session_arg: dict, raw_yaml_arg: str, semantic_issues: list[str]) -> tuple[dict, str]:
        assert session_arg is session
        assert raw_yaml_arg == raw_yaml
        assert semantic_issues == []
        return load_bundle_text(raw_yaml_arg), "version: 1\nmetadata:\n  name: Normalized\n"

    result = alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=load_validated,
            now=lambda: "2026-05-29T00:01:00Z",
        ),
        session,
    )

    assert result["ok"] is True
    assert result["validation"]["ok"] is True
    assert result["validation"]["checked_at"] == "2026-05-29T00:01:00Z"
    assert result["validation"]["semantic_lint"] == {"ok": True, "issues": []}
    assert result["yaml"] == "version: 1\nmetadata:\n  name: Normalized\n"


def test_alignment_bundle_preview_returns_failure_validation_with_raw_yaml(tmp_path: Path) -> None:
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir()
    raw_yaml = "version: 1\nmetadata:\n  name: [\n"
    bundle_path.write_text(raw_yaml, encoding="utf-8")
    session = {
        "id": "align_invalid",
        "status": "idle",
        "bundle_path": str(bundle_path),
    }

    result = alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=never_load_validated,
            now=lambda: "2026-05-29T00:02:00Z",
        ),
        session,
    )

    assert result["ok"] is False
    assert result["bundle"] is None
    assert result["yaml"] == raw_yaml
    assert result["validation"]["ok"] is False
    assert result["validation"]["checked_at"] == "2026-05-29T00:02:00Z"


def test_alignment_bundle_preview_preserves_semantic_issues_from_ready_validation(tmp_path: Path) -> None:
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir()
    raw_yaml = alignment_bundle_yaml(str(tmp_path))
    bundle_path.write_text(raw_yaml, encoding="utf-8")
    session = {
        "id": "align_ready_invalid",
        "status": "imported",
        "bundle_path": str(bundle_path),
    }

    def fail_validated(_session: dict, _raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        semantic_issues.append("spec.markdown")
        raise LooporaError("semantic lint failed")

    result = alignment_bundle_preview(
        AlignmentBundlePreviewContext(
            build_preview=preview_payload,
            load_validated_bundle_text=fail_validated,
            now=lambda: "2026-05-29T00:03:00Z",
        ),
        session,
    )

    assert result["ok"] is False
    assert result["validation"]["semantic_lint"] == {"ok": False, "issues": ["spec.markdown"]}
