from __future__ import annotations

from pathlib import Path

import pytest

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_ready_bundle_validation import (
    alignment_assert_bundle_workdir,
    alignment_bundle_file_has_ready_validation,
    alignment_bundle_file_is_valid_alignment_bundle,
)
from loopora.service_types import LooporaError


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(module_name: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / module_name).read_text(encoding="utf-8")


def test_alignment_ready_bundle_validation_has_dedicated_boundary() -> None:
    context_source = _loopora_source("service_alignment_context.py")
    ready_validation_source = _loopora_source("service_alignment_ready_bundle_validation.py")
    workdir_context_source = _loopora_source("service_alignment_workdir_context.py")
    validation_source = _loopora_source("service_alignment_validation.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_alignment_ready_bundle_validation import" in context_source
    for marker in (
        "def alignment_assert_bundle_workdir",
        "def alignment_bundle_file_is_valid_alignment_bundle",
        "def alignment_bundle_file_has_ready_validation",
        "def alignment_session_has_current_ready_bundle",
    ):
        assert marker in ready_validation_source
        assert marker not in context_source
    assert "from loopora.service_alignment_ready_bundle_validation import alignment_bundle_file_has_ready_validation" in workdir_context_source
    assert "from loopora.service_alignment_ready_bundle_validation import alignment_assert_bundle_workdir" in validation_source
    assert "service_alignment_ready_bundle_validation.py" in contracts_source


def test_alignment_bundle_file_ready_validation_requires_current_valid_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_ready" / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")

    assert alignment_bundle_file_is_valid_alignment_bundle(bundle_path, expected_workdir=workdir)
    assert not alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=workdir)

    (bundle_path.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")

    assert alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=workdir)
    assert not alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=tmp_path / "other")


def test_alignment_assert_bundle_workdir_fails_closed_on_mismatch(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))

    alignment_assert_bundle_workdir(bundle, expected_workdir=workdir)
    with pytest.raises(LooporaError):
        alignment_assert_bundle_workdir(bundle, expected_workdir=tmp_path / "other")
