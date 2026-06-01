from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_artifacts import alignment_bundle_content_fingerprint


def alignment_bundle_validation_success(
    bundle_path: Path,
    *,
    checked_at: str,
    normalized_yaml: str = "",
) -> dict:
    validation: dict = {
        "ok": True,
        "error": "",
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": True, "issues": []},
    }
    if normalized_yaml:
        validation.update(alignment_bundle_content_fingerprint(normalized_yaml))
    return validation


def alignment_bundle_validation_failure(
    bundle_path: Path,
    *,
    error: str,
    semantic_issues: list[str],
    checked_at: str,
) -> dict:
    return {
        "ok": False,
        "error": error,
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": not semantic_issues, "issues": list(semantic_issues)},
    }


def alignment_bundle_missing_file_validation(bundle_path: Path, *, checked_at: str) -> dict:
    error = f"alignment bundle does not exist: {bundle_path}"
    return {
        "ok": False,
        "error": error,
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": False, "issues": [error]},
    }
