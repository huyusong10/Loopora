from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaError

from runner_helpers import _create_loop


def test_destructive_generator_is_blocked_by_workspace_guard(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    (sample_workdir / "notes.txt").write_text("keep me\n", encoding="utf-8")
    (sample_workdir / "src").mkdir()
    (sample_workdir / "src" / "app.js").write_text("console.log('hi')\n", encoding="utf-8")

    service = service_factory(scenario="destructive_generator")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Guarded Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    guard = json.loads((run_dir / "workspace_guard.json").read_text(encoding="utf-8"))

    assert run["status"] == "failed"
    assert "workspace safety guard" in (run["error_message"] or "")
    assert guard["baseline_file_count"] == 3
    assert guard["remaining_original_file_count"] == 0
    assert guard["deleted_original_count"] == 3
    assert "progress.md" in guard["deleted_original_paths"]
    assert "Execution stopped by the workspace safety guard." in (run_dir / "summary.md").read_text(encoding="utf-8")
    events = service.stream_events(run["id"], limit=200)
    assert any(event["event_type"] == "run_aborted" for event in events)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "failed"
        and event["payload"]["reason"] == "workspace_safety_guard"
        and event["payload"]["task_verdict_status"] == "failed"
        and event["payload"].get("task_verdict_summary")
        for event in events
    )


def test_workspace_guard_ignores_generated_cache_deletions(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    (sample_workdir / "src").mkdir()
    (sample_workdir / "src" / "app.py").write_text("print('keep')\n", encoding="utf-8")
    (sample_workdir / ".pytest_cache" / "v" / "cache").mkdir(parents=True)
    (sample_workdir / ".pytest_cache" / "v" / "cache" / "nodeids").write_text("[]\n", encoding="utf-8")
    (sample_workdir / ".ruff_cache").mkdir()
    (sample_workdir / ".ruff_cache" / "metadata.json").write_text("{}\n", encoding="utf-8")
    (sample_workdir / ".coverage").write_text("coverage data\n", encoding="utf-8")

    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Cache Cleanup Loop")
    run = service.start_run(loop["id"])
    run_dir = Path(run["runs_dir"])
    baseline = json.loads((run_dir / "contract" / "workspace_baseline.json").read_text(encoding="utf-8"))

    assert "src/app.py" in baseline["files"]
    assert "progress.md" in baseline["files"]
    assert not any(path.startswith(".pytest_cache/") for path in baseline["files"])
    assert not any(path.startswith(".ruff_cache/") for path in baseline["files"])
    assert ".coverage" not in baseline["files"]

    shutil.rmtree(sample_workdir / ".pytest_cache")
    shutil.rmtree(sample_workdir / ".ruff_cache")
    (sample_workdir / ".coverage").unlink()

    service._enforce_workspace_safety(run, run_dir, 0, role="builder")

    assert not (run_dir / "workspace_guard.json").exists()
    assert not (run_dir / "timeline" / "workspace_guard.json").exists()
    assert not any(event["event_type"] == "workspace_guard_triggered" for event in service.stream_events(run["id"], limit=10))


def test_workspace_guard_fails_closed_when_baseline_is_missing_or_malformed(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    (sample_workdir / "src").mkdir()
    (sample_workdir / "src" / "app.py").write_text("print('keep')\n", encoding="utf-8")

    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Missing Baseline Loop")
    run = service.start_run(loop["id"])
    run_dir = Path(run["runs_dir"])
    baseline_path = RunArtifactLayout(run_dir).workspace_baseline_path

    baseline_path.unlink()
    with pytest.raises(LooporaError, match="workspace safety baseline"):
        service._enforce_workspace_safety(run, run_dir, 0, role="builder")

    baseline_path.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(LooporaError, match="workspace safety baseline"):
        service._enforce_workspace_safety(run, run_dir, 0, role="builder")

    baseline_path.write_text('{"files": [42]}\n', encoding="utf-8")
    with pytest.raises(LooporaError, match="workspace safety baseline"):
        service._enforce_workspace_safety(run, run_dir, 0, role="builder")


def test_destructive_tester_is_blocked_by_workspace_guard(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    (sample_workdir / "notes.txt").write_text("keep me\n", encoding="utf-8")
    (sample_workdir / "src").mkdir()
    (sample_workdir / "src" / "app.js").write_text("console.log('hi')\n", encoding="utf-8")

    service = service_factory(scenario="destructive_tester")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Guarded Tester Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    guard = json.loads((run_dir / "workspace_guard.json").read_text(encoding="utf-8"))

    assert run["status"] == "failed"
    assert "workspace safety guard" in (run["error_message"] or "")
    assert guard["role"] in {"tester", "inspector"}
    assert guard["deleted_original_count"] == 3
