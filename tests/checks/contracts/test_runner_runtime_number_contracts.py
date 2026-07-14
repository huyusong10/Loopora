from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary
from loopora.context_step_results import StepEvidenceEntryRequest, StepResultContext, build_step_evidence_entry, build_step_handoff
from loopora.run_artifacts import RunArtifactLayout
from loopora.service import LooporaError
from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.workdir_inputs import (
    normalize_existing_spec_path,
    normalize_existing_workdir,
    normalize_recoverable_workdir,
    restricted_workdir_scope,
    same_workdir_identity,
    spec_path_state,
    workdir_path_state,
)

from runner_helpers import _create_loop


def test_run_contract_snapshot_rejects_bool_numeric_limits(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_contract_bool_limits")
    layout.initialize()

    snapshot = build_run_contract_snapshot(
        RunContractSnapshotRequest(
            run={
                "id": "run_bool_limits",
                "runs_dir": str(tmp_path),
                "compiled_spec_json": {},
                "completion_mode": "gatekeeper",
                "max_iters": True,
                "max_role_retries": True,
                "delta_threshold": 0.0,
                "trigger_window": True,
                "regression_window": True,
                "iteration_interval_seconds": 0.0,
            },
            compiled_spec={},
            strategy_source={"roles": [], "steps": []},
            prompt_files={},
            workspace_baseline={"file_count": True},
            layout=layout,
        )
    )

    assert (
        snapshot["max_iters"],
        snapshot["max_role_retries"],
        snapshot["trigger_window"],
        snapshot["regression_window"],
        snapshot["workspace_baseline"]["file_count"],
    ) == (0, 0, 0, 0, 0)


def test_step_artifact_contexts_reject_bool_identity(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "step_artifact_bool_identity")
    step = {"id": "builder_step"}
    role = {"id": "builder", "name": "Builder", "archetype": "builder"}
    result = StepResultContext(
        layout=layout,
        iter_id=True,
        step=step,
        step_order=True,
        role=role,
        runtime_role="builder",
        output={"summary": "Built the slice.", "changed_files": [], "proof_files": []},
    )

    handoff = build_step_handoff(result)
    evidence = build_step_evidence_entry(StepEvidenceEntryRequest(result=result, handoff=handoff))
    summary = build_iteration_summary(
        IterationSummaryContext(
            layout=layout,
            iter_id=True,
            step_results=[{"step": step, "step_order": True, "role": role, "runtime_role": "builder", "handoff": handoff, "output": {}}],
            stagnation={},
            previous_composite=None,
            timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert handoff["source"]["iter"] == 0
    assert handoff["source"]["step_order"] == 0
    assert handoff["artifact_refs"][0]["relative_path"] == "iterations/iter_000/steps/00__builder_step/output.raw.json"
    assert (evidence["id"], evidence["iter"], evidence["step_order"]) == ("ev_000_00_builder_step", 0, 0)
    assert summary["iter"] == 0
    assert summary["latest_refs"]["latest_by_step"]["builder_step"] == "iterations/iter_000/steps/00__builder_step/handoff.json"


@pytest.mark.parametrize(
    "case",
    [
        ("iteration_interval_seconds", math.nan, "iteration_interval_seconds must be a finite number"),
        ("delta_threshold", math.inf, "delta_threshold must be a finite number"),
        ("max_iters", math.inf, "max_iters must be a finite number"),
        ("max_iters", False, "max_iters must be a finite number"),
        ("max_iters", 1.5, "max_iters must be an integer"),
        ("trigger_window", 1.5, "trigger_window must be an integer"),
        ("delta_threshold", -0.1, "delta_threshold must be >= 0"),
    ],
)
def test_create_loop_rejects_invalid_runtime_numbers(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    case: tuple[str, object, str],
) -> None:
    service = service_factory(scenario="success")
    field_name, value, error_text = case

    with pytest.raises(LooporaError, match=error_text):
        _create_loop(service, sample_spec_file, sample_workdir, **{field_name: value})


def test_create_loop_rejects_invalid_compose_options_before_input_paths(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    missing_workdir = tmp_path / "missing-workdir"
    missing_spec = tmp_path / "missing-spec.md"
    cases = [
        (
            {"workdir": missing_workdir, "executor_kind": "bogus"},
            "invalid executor_kind: unsupported executor kind: 'bogus'. Expected one of: codex, claude, opencode, custom",
        ),
        (
            {"workdir": missing_workdir, "executor_kind": "custom"},
            "invalid executor_mode: Custom Command only supports command mode",
        ),
        (
            {"spec_path": missing_spec, "completion_mode": "banana"},
            "invalid completion_mode: unsupported completion mode: banana",
        ),
        (
            {"spec_path": missing_spec, "executor_mode": "command", "command_args_text": "{schema_path}"},
            "invalid command_args_text: custom command is missing required placeholders: {prompt}, {output_path}",
        ),
        (
            {"spec_path": missing_spec, "role_models": {"builder": ""}},
            "invalid role_models: invalid role model override: builder=",
        ),
        (
            {"spec_path": missing_spec, "trigger_window": 0},
            "trigger_window must be >= 1",
        ),
    ]

    for overrides, expected_error in cases:
        with pytest.raises(LooporaError) as exc_info:
            _create_loop(service, sample_spec_file, sample_workdir, **overrides)
        assert str(exc_info.value) == expected_error
        assert "workdir does not exist" not in str(exc_info.value)
        assert "spec does not exist" not in str(exc_info.value)

    assert not missing_workdir.exists()
    assert not missing_spec.exists()
    assert service.list_loops() == []


def test_create_loop_rejects_unusable_input_paths_without_local_path(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    blank_workdir = ""
    blank_spec = ""
    missing_workdir = tmp_path / "missing-workdir"
    file_workdir = tmp_path / "not-a-workdir"
    missing_spec = tmp_path / "missing-spec.md"
    directory_spec = tmp_path / "spec-dir"
    file_workdir.write_text("not a directory\n", encoding="utf-8")
    directory_spec.mkdir()

    workdir_cases = [
        (blank_workdir, "required", blank_workdir),
        (missing_workdir, "missing", missing_workdir),
        (file_workdir, "not_directory", file_workdir),
    ]
    for workdir, state, local_path in workdir_cases:
        with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
            _create_loop(service, sample_spec_file, workdir)
        assert exc_info.value.action == "compose"
        assert exc_info.value.workdir_state == state
        assert str(exc_info.value) == f"target project is not ready for Loop compose: {exc_info.value.summary}"
        if isinstance(local_path, Path):
            assert str(local_path.resolve(strict=False)) not in str(exc_info.value)

    spec_cases = [
        (blank_spec, sample_workdir, "spec path is required", blank_spec),
        (missing_spec, sample_workdir, "spec does not exist", missing_spec),
        (directory_spec, sample_workdir, "spec path is not a file", directory_spec),
    ]
    for spec_path, workdir, error_text, local_path in spec_cases:
        with pytest.raises(LooporaError, match=error_text) as exc_info:
            _create_loop(service, spec_path, workdir)
        assert str(exc_info.value) == error_text
        if isinstance(local_path, Path):
            assert str(local_path.resolve(strict=False)) not in str(exc_info.value)
    assert service.list_loops() == []
    assert file_workdir.read_text(encoding="utf-8") == "not a directory\n"


def test_create_loop_rejects_uninspectable_input_paths_without_os_error(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    blocked_workdir = tmp_path / "blocked-workdir"
    blocked_spec = tmp_path / "blocked-spec.md"
    private_path = tmp_path / "private" / "blocked"
    blocked_workdir_resolved = blocked_workdir.resolve(strict=False)
    blocked_spec_resolved = blocked_spec.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path in {blocked_workdir_resolved, blocked_spec_resolved}:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    with pytest.raises(LooporaWorkdirUnavailableError) as workdir_error:
        _create_loop(service, sample_spec_file, blocked_workdir)
    assert workdir_error.value.action == "compose"
    assert workdir_error.value.workdir_state == "unavailable"
    assert "permission denied" not in str(workdir_error.value)
    assert str(private_path) not in str(workdir_error.value)

    with pytest.raises(LooporaError, match="spec path could not be inspected") as spec_error:
        _create_loop(service, blocked_spec, sample_workdir)
    assert str(spec_error.value) == "spec path could not be inspected"
    assert "permission denied" not in str(spec_error.value)
    assert str(private_path) not in str(spec_error.value)


def test_workdir_path_state_projects_shared_loop_compose_statuses(tmp_path: Path) -> None:
    missing_workdir = tmp_path / "missing-workdir"
    file_workdir = tmp_path / "not-a-workdir"
    ready_workdir = tmp_path / "workdir"
    file_workdir.write_text("not a directory\n", encoding="utf-8")
    ready_workdir.mkdir()

    for blank_input in (None, ""):
        assert workdir_path_state(blank_input) == {
            "status": "required",
            "workdir": "",
            "error": "workdir is required",
        }
        with pytest.raises(LooporaError, match="workdir is required"):
            normalize_existing_workdir(blank_input)

    assert workdir_path_state(missing_workdir) == {
        "status": "missing",
        "workdir": str(missing_workdir.resolve(strict=False)),
    }
    assert workdir_path_state(file_workdir) == {
        "status": "not_directory",
        "workdir": str(file_workdir.resolve(strict=False)),
    }
    assert workdir_path_state(ready_workdir) == {
        "status": "ready",
        "workdir": str(ready_workdir.resolve(strict=False)),
    }
    assert normalize_existing_workdir(ready_workdir) == ready_workdir.resolve(strict=False)

    with pytest.raises(LooporaError, match="workdir does not exist") as missing_error:
        normalize_existing_workdir(missing_workdir)
    assert str(missing_workdir.resolve(strict=False)) not in str(missing_error.value)

    with pytest.raises(LooporaError, match="workdir path is not a directory") as file_error:
        normalize_existing_workdir(file_workdir)
    assert str(file_workdir.resolve(strict=False)) not in str(file_error.value)


def test_restricted_workdir_scope_rejects_external_and_symlink_targets_then_restores(tmp_path: Path) -> None:
    isolated_root = tmp_path / "isolated"
    playground = isolated_root / "playground"
    outside = tmp_path / "real-project"
    playground.mkdir(parents=True)
    outside.mkdir()
    escape = isolated_root / "escape"
    escape.symlink_to(outside, target_is_directory=True)

    assert normalize_existing_workdir(outside) == outside.resolve()
    with restricted_workdir_scope(isolated_root):
        assert normalize_recoverable_workdir(playground, action="compose") == playground.resolve()
        for candidate in (outside, escape):
            state = workdir_path_state(candidate)
            assert state["status"] == "unavailable"
            assert state["error"] == "workdir is outside the active isolated workspace"
            with pytest.raises(LooporaError, match="outside the active isolated workspace"):
                normalize_recoverable_workdir(candidate, action="compose")
    assert normalize_existing_workdir(outside) == outside.resolve()


def test_workdir_path_state_redacts_uninspectable_low_level_errors(monkeypatch, tmp_path: Path) -> None:
    blocked_workdir = tmp_path / "blocked-workdir"
    private_path = tmp_path / "private" / "blocked-workdir"
    blocked_resolved = blocked_workdir.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    state = workdir_path_state(blocked_workdir)
    encoded_state = json.dumps(state, ensure_ascii=False)
    assert state == {
        "status": "unavailable",
        "workdir": str(blocked_resolved),
        "error": "workdir could not be inspected",
    }
    assert "exception" not in state
    assert "permission denied" not in encoded_state
    assert str(private_path) not in encoded_state
    with pytest.raises(LooporaError, match="workdir could not be inspected") as error:
        normalize_existing_workdir(blocked_workdir)
    assert "permission denied" not in str(error.value)
    assert str(private_path) not in str(error.value)


def test_workdir_path_state_handles_path_normalization_failures_without_current_directory() -> None:
    state = workdir_path_state("bad\0workdir")

    assert state == {
        "status": "unavailable",
        "workdir": "",
        "error": "workdir could not be inspected",
    }
    assert same_workdir_identity("bad\0workdir", Path.cwd()) is False
    with pytest.raises(LooporaError, match="workdir could not be inspected") as error:
        normalize_existing_workdir("bad\0workdir")
    assert "embedded null" not in str(error.value)
    assert str(Path.cwd()) not in str(error.value)


def test_spec_path_state_projects_shared_loop_compose_statuses(monkeypatch, tmp_path: Path) -> None:
    missing_spec = tmp_path / "missing-spec.md"
    directory_spec = tmp_path / "spec-dir"
    ready_spec = tmp_path / "spec.md"
    directory_spec.mkdir()
    ready_spec.write_text("# Task\n\nKeep going.\n", encoding="utf-8")

    for blank_input in (None, ""):
        assert spec_path_state(blank_input) == {
            "status": "required",
            "spec_path": "",
            "error": "spec path is required",
        }
        with pytest.raises(LooporaError, match="spec path is required"):
            normalize_existing_spec_path(blank_input)

    assert spec_path_state(missing_spec) == {
        "status": "missing",
        "spec_path": str(missing_spec.resolve(strict=False)),
    }
    assert spec_path_state(directory_spec) == {
        "status": "not_file",
        "spec_path": str(directory_spec.resolve(strict=False)),
    }
    assert spec_path_state(ready_spec) == {
        "status": "ready",
        "spec_path": str(ready_spec.resolve(strict=False)),
    }
    assert normalize_existing_spec_path(ready_spec) == ready_spec.resolve(strict=False)

    with pytest.raises(LooporaError, match="spec does not exist") as missing_error:
        normalize_existing_spec_path(missing_spec)
    assert str(missing_spec.resolve(strict=False)) not in str(missing_error.value)

    with pytest.raises(LooporaError, match="spec path is not a file") as directory_error:
        normalize_existing_spec_path(directory_spec)
    assert str(directory_spec.resolve(strict=False)) not in str(directory_error.value)

    other_spec = tmp_path / "socket-shaped-spec"
    other_resolved = other_spec.resolve(strict=False)
    original_exists = Path.exists
    original_is_dir = Path.is_dir
    original_is_file = Path.is_file

    def exists(path: Path) -> bool:
        if path == other_resolved:
            return True
        return original_exists(path)

    def is_dir(path: Path) -> bool:
        if path == other_resolved:
            return False
        return original_is_dir(path)

    def is_file(path: Path) -> bool:
        if path == other_resolved:
            return False
        return original_is_file(path)

    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(Path, "is_dir", is_dir)
    monkeypatch.setattr(Path, "is_file", is_file)

    assert spec_path_state(other_spec) == {
        "status": "not_file",
        "spec_path": str(other_resolved),
    }
    with pytest.raises(LooporaError, match="spec path is not a file") as other_error:
        normalize_existing_spec_path(other_spec)
    assert str(other_resolved) not in str(other_error.value)


def test_spec_path_state_redacts_uninspectable_low_level_errors(monkeypatch, tmp_path: Path) -> None:
    blocked_spec = tmp_path / "blocked-spec.md"
    private_path = tmp_path / "private" / "blocked-spec.md"
    blocked_resolved = blocked_spec.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    state = spec_path_state(blocked_spec)
    encoded_state = json.dumps(state, ensure_ascii=False)
    assert state == {
        "status": "unavailable",
        "spec_path": str(blocked_resolved),
        "error": "spec path could not be inspected",
    }
    assert "exception" not in state
    assert "permission denied" not in encoded_state
    assert str(private_path) not in encoded_state
    with pytest.raises(LooporaError, match="spec path could not be inspected") as error:
        normalize_existing_spec_path(blocked_spec)
    assert "permission denied" not in str(error.value)
    assert str(private_path) not in str(error.value)


def test_spec_path_state_handles_path_normalization_failures_without_current_directory() -> None:
    state = spec_path_state("bad\0spec.md")

    assert state == {
        "status": "unavailable",
        "spec_path": "",
        "error": "spec path could not be inspected",
    }
    with pytest.raises(LooporaError, match="spec path could not be inspected") as error:
        normalize_existing_spec_path("bad\0spec.md")
    assert "embedded null" not in str(error.value)
    assert str(Path.cwd()) not in str(error.value)
