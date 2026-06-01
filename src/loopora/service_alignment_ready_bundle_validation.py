from __future__ import annotations

import json
from pathlib import Path

from loopora.bundles import (
    BundleError,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
    load_bundle_text,
    read_bundle_file_text,
)
from loopora.service_types import LooporaError


def alignment_assert_bundle_workdir(bundle: dict, *, expected_workdir: Path) -> None:
    actual = Path(str(bundle["loop"]["workdir"])).expanduser().resolve()
    expected = expected_workdir.expanduser().resolve()
    if actual != expected:
        raise LooporaError(f"bundle loop.workdir must be {expected}, got {actual}")


def alignment_bundle_file_is_valid_alignment_bundle(
    bundle_path: Path,
    *,
    expected_workdir: Path | None = None,
) -> bool:
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        generation_issues = lint_alignment_bundle_generation_text(raw_yaml)
        bundle = load_bundle_text(raw_yaml)
        if expected_workdir is not None:
            alignment_assert_bundle_workdir(bundle, expected_workdir=expected_workdir)
        semantic_issues = lint_alignment_bundle_semantics(bundle)
    except (BundleError, LooporaError, OSError):
        return False
    return not generation_issues and not semantic_issues


def alignment_bundle_file_has_ready_validation(bundle_path: Path, *, expected_workdir: Path | None = None) -> bool:
    validation_path = bundle_path.parent / "validation.json"
    try:
        payload = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    return alignment_bundle_file_is_valid_alignment_bundle(
        bundle_path,
        expected_workdir=expected_workdir,
    )


def alignment_session_has_current_ready_bundle(session: dict, bundle_path: Path) -> bool:
    expected_workdir = Path(session["workdir"]) if session.get("workdir") else None
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    if validation.get("ok") is True:
        return alignment_bundle_file_is_valid_alignment_bundle(
            bundle_path,
            expected_workdir=expected_workdir,
        )
    return alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=expected_workdir)
