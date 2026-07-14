from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import loopora.service_run_registration as run_registration_module
import loopora.service_run_start as run_start_module
from loopora.branding import state_dir_for_workdir
from loopora.service_run_registration import LOOP_ARTIFACT_PREPARE_ERROR
from loopora.service_run_start import RUN_ARTIFACT_PREPARE_ERROR
from loopora.service_types import (
    ACTIVE_WORKDIR_CONFLICT_MESSAGE,
    LooporaConflictError,
    LooporaError,
    LooporaWorkdirUnavailableError,
)

from runner_helpers import _create_loop


def test_create_loop_cleans_prepared_loop_dir_when_artifact_preparation_fails(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    private_path = tmp_path / "private" / "prompt.md"
    loop_dir = state_dir_for_workdir(sample_workdir) / "loops" / "loop_fixed"

    def fail_prompt_artifacts(*_args, **_kwargs) -> None:
        raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(run_registration_module, "make_id", lambda _prefix: "loop_fixed")
    monkeypatch.setattr(service, "_persist_prompt_files", fail_prompt_artifacts)

    with pytest.raises(LooporaError, match=LOOP_ARTIFACT_PREPARE_ERROR) as exc_info:
        _create_loop(service, sample_spec_file, sample_workdir, name="Loop Artifact Prep Failure")

    assert str(exc_info.value) == LOOP_ARTIFACT_PREPARE_ERROR
    assert "permission denied" not in str(exc_info.value)
    assert str(private_path) not in str(exc_info.value)
    assert not loop_dir.exists()
    assert service.list_loops() == []


def test_create_loop_cleans_prepared_loop_dir_when_registration_fails(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop_dir = state_dir_for_workdir(sample_workdir) / "loops" / "loop_fixed"

    def fail_create_loop(_payload: dict) -> dict:
        raise LooporaConflictError("forced loop registration conflict")

    monkeypatch.setattr(run_registration_module, "make_id", lambda _prefix: "loop_fixed")
    monkeypatch.setattr(service.repository, "create_loop", fail_create_loop)

    with pytest.raises(LooporaConflictError, match="forced loop registration conflict"):
        _create_loop(service, sample_spec_file, sample_workdir, name="Loop Registration Failure")

    assert not loop_dir.exists()
    assert service.list_loops() == []


def test_start_run_cleans_prepared_run_dir_when_registration_fails(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Registration Failure Cleanup Loop")
    captured: dict[str, Path] = {}

    def fail_create_run(payload: dict) -> dict:
        captured["run_dir"] = Path(payload["runs_dir"])
        raise LooporaConflictError("forced active run conflict")

    monkeypatch.setattr(service.repository, "create_run", fail_create_run)

    with pytest.raises(LooporaConflictError, match="forced active run conflict"):
        service.start_run(loop["id"])

    assert captured["run_dir"].parent == state_dir_for_workdir(sample_workdir) / "runs"
    assert not captured["run_dir"].exists()


def test_start_run_cleans_prepared_run_dir_when_artifact_preparation_fails(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Artifact Prep Failure Loop")
    private_path = tmp_path / "private" / "workspace_baseline.json"
    run_dir = state_dir_for_workdir(sample_workdir) / "runs" / "run_fixed"
    original_write_json_with_mirrors = run_start_module.write_json_with_mirrors

    def fail_workspace_baseline_write(path: Path, payload: dict, **kwargs) -> None:
        if path.name == "workspace_baseline.json":
            raise OSError(f"permission denied: {private_path}")
        original_write_json_with_mirrors(path, payload, **kwargs)

    monkeypatch.setattr(run_start_module, "make_id", lambda _prefix: "run_fixed")
    monkeypatch.setattr(run_start_module, "write_json_with_mirrors", fail_workspace_baseline_write)

    with pytest.raises(LooporaError, match=RUN_ARTIFACT_PREPARE_ERROR) as exc_info:
        service.start_run(loop["id"])

    assert str(exc_info.value) == RUN_ARTIFACT_PREPARE_ERROR
    assert "permission denied" not in str(exc_info.value)
    assert str(private_path) not in str(exc_info.value)
    assert not run_dir.exists()
    assert service.get_loop(loop["id"])["runs"] == []


def test_start_run_rejects_active_workdir_conflict_without_local_path(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Active Conflict Loop")
    service.start_run(loop["id"])

    with pytest.raises(LooporaConflictError, match="another active run is already using") as exc_info:
        service.start_run(loop["id"])
    assert str(exc_info.value) == ACTIVE_WORKDIR_CONFLICT_MESSAGE
    assert str(sample_workdir.resolve()) not in str(exc_info.value)


def test_start_run_uses_normalized_saved_workdir_for_active_conflict(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    first_loop = _create_loop(service, sample_spec_file, sample_workdir, name="Absolute Active Loop")
    legacy_loop = _create_loop(service, sample_spec_file, sample_workdir, name="Relative Legacy Loop")
    service.start_run(first_loop["id"])
    monkeypatch.chdir(sample_workdir.parent)
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", (sample_workdir.name, legacy_loop["id"]))

    with pytest.raises(LooporaConflictError, match="another active run is already using") as exc_info:
        service.start_run(legacy_loop["id"])

    assert str(exc_info.value) == ACTIVE_WORKDIR_CONFLICT_MESSAGE
    assert service.get_loop(legacy_loop["id"])["runs"] == []


def test_start_run_records_normalized_workdir_for_legacy_relative_saved_loop(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Relative Workdir Start Loop")
    monkeypatch.chdir(sample_workdir.parent)
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", (sample_workdir.name, loop["id"]))

    run = service.start_run(loop["id"])

    assert run["workdir"] == str(sample_workdir.resolve(strict=False))
    contract = json.loads((Path(run["runs_dir"]) / "contract" / "run_contract.json").read_text(encoding="utf-8"))
    assert contract["workdir"] == str(sample_workdir.resolve(strict=False))
    assert contract["workdir"] != sample_workdir.name


def test_start_run_rejects_missing_saved_workdir_without_recreating_project(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Missing Workdir Start Loop")
    shutil.rmtree(sample_workdir)

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        service.start_run(loop["id"])

    assert exc_info.value.workdir_state == "missing"
    assert str(exc_info.value) == f"target project is not ready for a run: {exc_info.value.summary}"
    assert str(sample_workdir.resolve(strict=False)) not in str(exc_info.value)
    assert not sample_workdir.exists()
    assert not state_dir_for_workdir(sample_workdir).exists()


def test_start_run_rejects_blank_saved_workdir_without_using_current_directory(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Blank Workdir Start Loop")
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", ("", loop["id"]))

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        service.start_run(loop["id"])

    assert exc_info.value.workdir == ""
    assert exc_info.value.workdir_state == "required"
    assert str(exc_info.value) == f"target project is not ready for a run: {exc_info.value.summary}"
    assert str(Path.cwd()) not in str(exc_info.value)
    assert service.get_loop(loop["id"])["runs"] == []


def test_start_run_rejects_non_directory_saved_workdir_without_recreating_project(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Non Directory Workdir Start Loop")
    shutil.rmtree(sample_workdir)
    sample_workdir.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        service.start_run(loop["id"])

    assert exc_info.value.workdir_state == "not_directory"
    assert str(exc_info.value) == f"target project is not ready for a run: {exc_info.value.summary}"
    assert str(sample_workdir.resolve(strict=False)) not in str(exc_info.value)
    assert sample_workdir.read_text(encoding="utf-8") == "not a directory\n"


def test_start_run_rejects_uninspectable_saved_workdir_without_os_error(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Uninspectable Workdir Start Loop")
    private_path = tmp_path / "private" / "blocked"
    sample_workdir_resolved = sample_workdir.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == sample_workdir_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
        service.start_run(loop["id"])

    assert exc_info.value.workdir_state == "unavailable"
    assert str(exc_info.value) == f"target project is not ready for a run: {exc_info.value.summary}"
    assert "permission denied" not in str(exc_info.value)
    assert str(private_path) not in str(exc_info.value)
    assert str(sample_workdir.resolve(strict=False)) not in str(exc_info.value)
    assert service.get_loop(loop["id"])["runs"] == []
