from __future__ import annotations

import json
from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source

import pytest

from loopora.loop_run_progress import build_loop_run_progress
from loopora.run_continuation_progress import (
    continuation_action_mode,
    continuation_action_policy,
    normalize_continuation_progress_context,
)
from loopora.run_artifact_catalog import list_run_artifacts
from loopora.run_artifacts import (
    INITIAL_STAGNATION_STATE,
    RunArtifactLayout,
    append_jsonl_with_mirrors,
    read_jsonl,
    read_stagnation_state,
    write_json_with_mirrors,
    write_text_with_mirrors,
)
from loopora.utils import write_json


REPO_ROOT = Path(__file__).resolve().parents[3]


def _progress_run(tmp_path: Path, run_id: str, targets: list[dict], *, evidence_count: int = 0, status: str = "succeeded") -> dict:
    run_dir = tmp_path / run_id
    write_json(
        run_dir / "evidence" / "coverage.json",
        {
            "schema_version": 1,
            "status": "partial",
            "evidence_count": evidence_count,
            "targets": targets,
        },
    )
    return {"id": run_id, "status": status, "runs_dir": str(run_dir)}


def _source(module_name: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / f"{module_name}.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("relative_path", "payload", "expected"),
    [
        (Path("timeline/events.jsonl"), {"ok": True}, [{"ok": True}]),
        (Path("timeline/stagnation.json"), {"mode": "none"}, {"mode": "none"}),
        (Path("summary/summary.md"), "Summary\n", "Summary\n"),
    ],
)
def test_legacy_mirror_failure_does_not_block_canonical_write(
    tmp_path: Path, relative_path: Path, payload: object, expected: object
) -> None:
    canonical_path = tmp_path / relative_path
    mirror_path = tmp_path / relative_path.name
    mirror_path.mkdir(parents=True)

    if relative_path.suffix == ".jsonl":
        append_jsonl_with_mirrors(canonical_path, payload, mirror_paths=[mirror_path])
        actual = [json.loads(line) for line in canonical_path.read_text(encoding="utf-8").splitlines()]
    elif relative_path.suffix == ".json":
        write_json_with_mirrors(canonical_path, payload, mirror_paths=[mirror_path])
        actual = json.loads(canonical_path.read_text(encoding="utf-8"))
    else:
        write_text_with_mirrors(canonical_path, payload, mirror_paths=[mirror_path])
        actual = canonical_path.read_text(encoding="utf-8")

    assert actual == expected


def test_run_artifact_json_write_preserves_existing_canonical_on_replace_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    canonical_path = tmp_path / "timeline" / "state.json"
    canonical_path.parent.mkdir(parents=True)
    canonical_path.write_text('{"ok": false}\n', encoding="utf-8")
    private_path = tmp_path / "private" / "state.json"
    original_replace = Path.replace

    def fail_canonical_replace(path: Path, target: Path) -> Path:
        if Path(target) == canonical_path and Path(path).name.startswith(f".{canonical_path.name}.tmp."):
            raise OSError(f"permission denied: {private_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_canonical_replace)

    with pytest.raises(OSError, match="permission denied"):
        write_json_with_mirrors(canonical_path, {"ok": True})

    assert json.loads(canonical_path.read_text(encoding="utf-8")) == {"ok": False}
    assert not list(canonical_path.parent.glob(f".{canonical_path.name}.tmp.*"))


def test_read_jsonl_tolerates_invalid_utf8_artifacts(tmp_path: Path) -> None:
    artifact_path = tmp_path / "timeline" / "events.jsonl"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b'{"ok": true}\n\xff\n')

    assert read_jsonl(artifact_path) == []


def test_read_stagnation_state_recovers_corrupt_json(tmp_path: Path) -> None:
    artifact_path = tmp_path / "timeline" / "stagnation.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("{", encoding="utf-8")

    assert read_stagnation_state(artifact_path) == INITIAL_STAGNATION_STATE


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


def test_loop_run_progress_reports_mixed_target_change_without_using_evidence_count_as_proof(tmp_path: Path) -> None:
    previous = _progress_run(
        tmp_path,
        "run_previous",
        [
            {"id": "check.a", "kind": "done_when", "text": "A", "required": True, "status": "missing"},
            {"id": "check.b", "kind": "done_when", "text": "B", "required": True, "status": "covered"},
        ],
        evidence_count=2,
    )
    latest = _progress_run(
        tmp_path,
        "run_latest",
        [
            {"id": "check.a", "kind": "done_when", "text": "A", "required": True, "status": "covered"},
            {"id": "check.b", "kind": "done_when", "text": "B", "required": True, "status": "weak"},
        ],
        evidence_count=9,
    )

    progress = build_loop_run_progress([latest, previous])

    assert progress["status"] == "mixed"
    assert progress["comparable"] is True
    assert (progress["improved_target_count"], progress["regressed_target_count"]) == (1, 1)
    assert (progress["closed_gap_count"], progress["reopened_target_count"]) == (1, 1)
    assert progress["evidence_count_delta"] == 7


def test_loop_run_progress_treats_target_removal_or_rewrite_as_contract_change(tmp_path: Path) -> None:
    previous = _progress_run(
        tmp_path,
        "run_previous",
        [
            {"id": "check.a", "kind": "done_when", "text": "Original A", "required": True, "status": "missing"},
            {"id": "check.b", "kind": "done_when", "text": "B", "required": True, "status": "missing"},
        ],
    )
    latest = _progress_run(
        tmp_path,
        "run_latest",
        [{"id": "check.a", "kind": "done_when", "text": "Weaker A", "required": False, "status": "covered"}],
    )

    progress = build_loop_run_progress([latest, previous])

    assert (progress["status"], progress["comparable"]) == ("contract_changed", False)
    assert progress["removed_target_ids"] == ["check.b"]
    assert progress["changed_target_ids"] == ["check.a"]
    assert progress["improved_target_count"] == 0


def test_loop_run_progress_keeps_first_and_active_runs_out_of_terminal_comparison(tmp_path: Path) -> None:
    baseline = _progress_run(
        tmp_path,
        "run_baseline",
        [{"id": "check.a", "kind": "done_when", "text": "A", "required": True, "status": "covered"}],
    )
    active = _progress_run(
        tmp_path,
        "run_active",
        [{"id": "check.a", "kind": "done_when", "text": "A", "required": True, "status": "missing"}],
        status="running",
    )

    assert build_loop_run_progress([baseline])["status"] == "baseline"
    active_progress = build_loop_run_progress([active, baseline])
    assert (active_progress["status"], active_progress["reason"]) == ("active", "latest_run_active")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("baseline", "close_gaps"),
        ("progressed", "continue_progress"),
        ("mixed", "stabilize_mixed"),
        ("regressed", "repair_regression"),
        ("no_progress", "change_approach"),
        ("contract_changed", "review_contract_change"),
        ("unavailable", "close_gaps"),
    ],
)
def test_continuation_action_mode_changes_with_target_level_trajectory(status: str, expected: str) -> None:
    mode = continuation_action_mode(reason="terminal_task_verdict_requires_next_run", progress_status=status)

    assert mode == expected
    assert continuation_action_policy(mode)


def test_continuation_reason_overrides_cross_run_trajectory() -> None:
    assert (
        continuation_action_mode(reason="previous_lifecycle_failure_retry", progress_status="regressed")
        == "retry_lifecycle"
    )
    assert (
        continuation_action_mode(reason="recorded_advisory_follow_up", progress_status="no_progress")
        == "advisory_follow_up"
    )


def test_continuation_progress_normalization_is_bounded_and_path_free() -> None:
    normalized = normalize_continuation_progress_context(
        {
            "status": "regressed",
            "reason": "coverage_target_comparison",
            "comparable": True,
            "source_run_id": "run_current",
            "prior_run_id": "run_prior",
            "regressed_target_count": 12,
            "regressed_targets": [
                {"target_id": f"target_{index}", "private_path": f"/private/{index}"} for index in range(10)
            ],
            "changed_target_ids": [f"changed_{index}" for index in range(12)],
            "private_path": "/private/project",
        }
    )

    assert normalized["status"] == "regressed"
    assert normalized["regressed_target_count"] == 12
    assert len(normalized["regressed_targets"]) == 5
    assert all("private_path" not in item for item in normalized["regressed_targets"])
    assert len(normalized["changed_target_ids"]) == 8
    assert "private_path" not in normalized


def test_run_artifact_catalog_has_dedicated_boundary() -> None:
    facade_source = _source("run_artifacts")
    layout_source = _source("run_artifact_layout")
    io_source = _source("run_artifact_io")
    layout_setup_source = _source("run_artifact_layout_setup")
    catalog_source = _source("run_artifact_catalog")
    web_overviews_source = _source("web_overviews")
    web_run_artifact_api_source = _source("web_run_artifact_api")
    contracts_source = design_boundary_source()

    assert "from loopora.run_artifact_layout import" in facade_source
    assert "class RunArtifactLayout" in layout_source
    assert "def artifact_ref" in layout_source
    assert "from loopora.run_artifact_io import" in facade_source
    for marker in (
        "def read_stagnation_state",
        "def append_jsonl_with_mirrors",
        "def read_jsonl",
        "def _log_mirror_write_failure",
    ):
        assert marker in io_source
        assert marker not in facade_source
    assert "dict(INITIAL_LATEST_STATE)" not in layout_source
    for marker in ("def list_run_artifacts", "def artifact_slug", "builder_output.json"):
        assert marker not in facade_source
    for marker in ("def initialize_run_artifact_layout", "def legacy_role_output_alias_paths", "builder_output.json"):
        assert marker in layout_setup_source
    for marker in ("RUN_ARTIFACT_SPECS", "STEP_ARTIFACT_FILENAMES", "def list_run_artifacts"):
        assert marker in catalog_source
    assert "from loopora.run_artifact_catalog import list_run_artifacts" in web_overviews_source
    assert "from loopora.run_artifact_catalog import list_run_artifacts as _list_run_artifacts" in web_run_artifact_api_source
    assert "def register_run_artifact_api_routes" in web_run_artifact_api_source
    for module_name in (
        "run_artifact_layout.py",
        "run_artifact_layout_setup.py",
        "run_artifact_catalog.py",
        "run_artifact_io.py",
        "web_run_artifact_api.py",
    ):
        assert module_name in contracts_source
