from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopora.run_artifact_catalog import list_run_artifacts
from loopora.run_artifacts import (
    RunArtifactLayout,
    append_jsonl_with_mirrors,
    read_jsonl,
    read_stagnation_state,
    write_json_with_mirrors,
    write_text_with_mirrors,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_jsonl_legacy_mirror_failure_does_not_block_canonical_write(tmp_path: Path) -> None:
    canonical_path = tmp_path / "timeline" / "events.jsonl"
    mirror_path = tmp_path / "events.jsonl"
    mirror_path.mkdir(parents=True)

    append_jsonl_with_mirrors(canonical_path, {"ok": True}, mirror_paths=[mirror_path])

    assert [json.loads(line) for line in canonical_path.read_text(encoding="utf-8").splitlines()] == [{"ok": True}]


def test_json_legacy_mirror_failure_does_not_block_canonical_write(tmp_path: Path) -> None:
    canonical_path = tmp_path / "timeline" / "stagnation.json"
    mirror_path = tmp_path / "stagnation.json"
    mirror_path.mkdir(parents=True)

    write_json_with_mirrors(canonical_path, {"mode": "none"}, mirror_paths=[mirror_path])

    assert json.loads(canonical_path.read_text(encoding="utf-8")) == {"mode": "none"}


def test_text_legacy_mirror_failure_does_not_block_canonical_write(tmp_path: Path) -> None:
    canonical_path = tmp_path / "summary" / "summary.md"
    mirror_path = tmp_path / "summary.md"
    mirror_path.mkdir(parents=True)

    write_text_with_mirrors(canonical_path, "Summary\n", mirror_paths=[mirror_path])

    assert canonical_path.read_text(encoding="utf-8") == "Summary\n"


def test_read_jsonl_tolerates_invalid_utf8_artifacts(tmp_path: Path) -> None:
    artifact_path = tmp_path / "timeline" / "events.jsonl"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b'{"ok": true}\n\xff\n')

    assert read_jsonl(artifact_path) == []


def test_read_stagnation_state_recovers_corrupt_json(tmp_path: Path) -> None:
    artifact_path = tmp_path / "timeline" / "stagnation.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{", encoding="utf-8")

    assert read_stagnation_state(artifact_path) == {
        "stagnation_mode": "none",
        "recent_composites": [],
        "recent_deltas": [],
        "consecutive_low_delta": 0,
    }


def test_run_artifact_layout_rejects_bool_iteration_and_step_identity(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    bool_iter_id = True
    bool_step_order = True

    assert layout.step_output_raw_path(bool_iter_id, bool_step_order, "builder").relative_to(layout.run_dir).as_posix() == (
        "iterations/iter_000/steps/00__builder/output.raw.json"
    )


def test_list_run_artifacts_does_not_mark_symlink_escaping_run_dir_available(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    outside_artifact = tmp_path / "outside.md"
    outside_artifact.write_text("outside secret", encoding="utf-8")

    summary_path = run_dir / "summary.md"
    prompt_path = run_dir / "contract" / "prompts" / "builder.md"
    step_path = run_dir / "iterations" / "iter_001" / "steps" / "01__builder" / "prompt.md"
    for artifact_path in (summary_path, prompt_path, step_path):
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            artifact_path.symlink_to(outside_artifact)
        except OSError as exc:
            pytest.skip(f"symlinks are not available in this environment: {exc}")

    artifacts = list_run_artifacts({"runs_dir": str(run_dir)})
    artifacts_by_id = {artifact["id"]: artifact for artifact in artifacts}

    assert artifacts_by_id["summary"]["available"] is False
    assert all(artifact.get("relative_path") != "contract/prompts/builder.md" for artifact in artifacts)
    assert all(artifact.get("relative_path") != "iterations/iter_001/steps/01__builder/prompt.md" for artifact in artifacts)


def test_run_artifact_catalog_has_dedicated_boundary() -> None:
    facade_source = (REPO_ROOT / "src" / "loopora" / "run_artifacts.py").read_text(encoding="utf-8")
    layout_source = (REPO_ROOT / "src" / "loopora" / "run_artifact_layout.py").read_text(encoding="utf-8")
    io_source = (REPO_ROOT / "src" / "loopora" / "run_artifact_io.py").read_text(encoding="utf-8")
    layout_setup_source = (REPO_ROOT / "src" / "loopora" / "run_artifact_layout_setup.py").read_text(encoding="utf-8")
    catalog_source = (REPO_ROOT / "src" / "loopora" / "run_artifact_catalog.py").read_text(encoding="utf-8")
    web_overviews_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    web_run_artifact_api_source = (REPO_ROOT / "src" / "loopora" / "web_run_artifact_api.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.run_artifact_layout import" in facade_source
    assert "class RunArtifactLayout" in layout_source
    assert "def artifact_ref" in layout_source
    assert "def list_run_artifacts" not in facade_source
    assert "def artifact_slug" not in facade_source
    assert "from loopora.run_artifact_io import" in facade_source
    for marker in (
        "def read_stagnation_state",
        "def append_jsonl_with_mirrors",
        "def read_jsonl",
        "def _log_mirror_write_failure",
    ):
        assert marker in io_source
        assert marker not in facade_source
    assert "def initialize_run_artifact_layout" in layout_setup_source
    assert "def legacy_role_output_alias_paths" in layout_setup_source
    assert "builder_output.json" in layout_setup_source
    assert "dict(INITIAL_LATEST_STATE)" not in layout_source
    assert "builder_output.json" not in facade_source
    assert "RUN_ARTIFACT_SPECS" in catalog_source
    assert "STEP_ARTIFACT_FILENAMES" in catalog_source
    assert "def list_run_artifacts" in catalog_source
    assert "from loopora.run_artifact_catalog import list_run_artifacts" in web_overviews_source
    assert "from loopora.run_artifact_catalog import list_run_artifacts as _list_run_artifacts" in web_run_artifact_api_source
    assert "def register_run_artifact_api_routes" in web_run_artifact_api_source
    assert "run_artifact_layout.py" in contracts_source
    assert "run_artifact_layout_setup.py" in contracts_source
    assert "run_artifact_catalog.py" in contracts_source
    assert "run_artifact_io.py" in contracts_source
    assert "web_run_artifact_api.py" in contracts_source
