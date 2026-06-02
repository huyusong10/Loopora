from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_artifacts import (
    alignment_artifact_paths,
    alignment_artifact_paths_from_root,
    alignment_artifact_root_from_bundle_path,
    alignment_session_root,
    ensure_alignment_artifact_dirs,
)


def test_alignment_session_root_supports_modern_and_legacy_bundle_paths(tmp_path: Path) -> None:
    root = tmp_path / "align_1"

    assert alignment_artifact_root_from_bundle_path(root / "artifacts" / "bundle.yml") == root
    assert alignment_artifact_root_from_bundle_path(root / "bundle.yml") == root
    assert alignment_session_root({"bundle_path": str(root / "artifacts" / "bundle.yml")}) == root


def test_alignment_artifact_paths_and_directories_are_stable(tmp_path: Path) -> None:
    root = tmp_path / "align_1"
    paths = alignment_artifact_paths_from_root(root)

    assert paths["manifest"] == root / "manifest.json"
    assert paths["transcript"] == root / "conversation" / "transcript.jsonl"
    assert paths["agreement"] == root / "agreement" / "current.json"
    assert paths["bundle"] == root / "artifacts" / "bundle.yml"
    assert paths["validation"] == root / "artifacts" / "validation.json"
    assert paths["events"] == root / "events" / "events.jsonl"
    assert paths["legacy_dir"] == root / "legacy"
    assert alignment_artifact_paths({"bundle_path": str(root / "artifacts" / "bundle.yml")}) == paths

    ensure_alignment_artifact_dirs(root)

    assert paths["conversation_dir"].is_dir()
    assert paths["agreement_dir"].is_dir()
    assert paths["artifacts_dir"].is_dir()
    assert paths["events_dir"].is_dir()
    assert paths["invocations_dir"].is_dir()
    assert not paths["legacy_dir"].exists()
