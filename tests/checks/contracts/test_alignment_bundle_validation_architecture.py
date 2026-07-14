from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_bundle_validation_payloads_have_dedicated_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_bundle_lifecycle.py").read_text(
        encoding="utf-8"
    )
    validation_payloads_source = (
        REPO_ROOT / "src" / "loopora" / "service_alignment_bundle_validation_payloads.py"
    ).read_text(encoding="utf-8")
    preview_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_bundle_preview.py").read_text(
        encoding="utf-8"
    )
    design_source = design_boundary_source()

    assert "from loopora.service_alignment_bundle_validation_payloads import" in lifecycle_source
    assert "from loopora.service_alignment_bundle_validation_payloads import" in preview_source
    for marker in (
        "def alignment_bundle_validation_success",
        "def alignment_bundle_validation_failure",
        "def alignment_bundle_missing_file_validation",
        "alignment_bundle_content_fingerprint",
    ):
        assert marker in validation_payloads_source
        assert marker not in lifecycle_source
    assert "service_alignment_bundle_validation_payloads.py" in design_source
