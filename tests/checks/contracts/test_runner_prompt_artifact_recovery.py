from __future__ import annotations

from pathlib import Path

import pytest

from loopora.branding import state_dir_for_workdir
from loopora.service import LooporaError
from loopora.strategy_source import strategy_prompt_asset_path

from runner_helpers import (
    _corrupt_loop_prompt_artifact,
    _corrupt_run_prompt_artifact,
    _create_loop,
)


def test_loop_projection_degrades_when_prompt_artifact_is_corrupt(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Corrupt Prompt Projection Loop")
    prompt_ref = next(iter(loop["prompt_files"]))
    _corrupt_loop_prompt_artifact(loop, prompt_ref)

    listed_loop = next(item for item in service.list_loops() if item["id"] == loop["id"])
    hydrated_loop = service.get_loop(loop["id"])

    assert listed_loop["prompt_files"] == {}
    assert hydrated_loop["prompt_files"] == {}


def test_loop_projection_uses_normalized_saved_workdir_for_prompt_artifacts(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Relative Prompt Projection Loop")
    prompt_ref = next(iter(loop["prompt_files"]))
    prompt_path = strategy_prompt_asset_path(
        state_dir_for_workdir(sample_workdir) / "loops" / loop["id"] / "prompts",
        prompt_ref,
    )
    prompt_path.write_text(f"{prompt_path.read_text(encoding='utf-8')}\n\nRELATIVE WORKDIR SIDECAR\n", encoding="utf-8")
    monkeypatch.chdir(sample_workdir.parent)
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", (sample_workdir.name, loop["id"]))

    listed_loop = next(item for item in service.list_loops() if item["id"] == loop["id"])
    hydrated_loop = service.get_loop(loop["id"])

    assert "RELATIVE WORKDIR SIDECAR" in listed_loop["prompt_files"][prompt_ref]
    assert "RELATIVE WORKDIR SIDECAR" in hydrated_loop["prompt_files"][prompt_ref]


def test_loop_projection_does_not_read_current_directory_for_blank_saved_workdir(
    monkeypatch,
    tmp_path: Path,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Blank Prompt Projection Loop")
    prompt_ref = next(iter(loop["prompt_files"]))
    wrong_cwd = tmp_path / "wrong-cwd"
    wrong_cwd.mkdir()
    fake_prompt_path = strategy_prompt_asset_path(
        state_dir_for_workdir(wrong_cwd) / "loops" / loop["id"] / "prompts",
        prompt_ref,
    )
    fake_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    fake_prompt_path.write_text(
        f"{loop['prompt_files'][prompt_ref]}\n\nUNEXPECTED CWD SIDECAR\n",
        encoding="utf-8",
    )
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", ("", loop["id"]))
    monkeypatch.chdir(wrong_cwd)

    hydrated_loop = service.get_loop(loop["id"])

    assert all("UNEXPECTED CWD SIDECAR" not in markdown for markdown in hydrated_loop["prompt_files"].values())


def test_start_run_reports_corrupt_loop_prompt_artifact_as_domain_error(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Corrupt Prompt Start Loop")
    prompt_ref = next(iter(loop["prompt_files"]))
    _corrupt_loop_prompt_artifact(loop, prompt_ref)
    runs_root = state_dir_for_workdir(sample_workdir) / "runs"

    with pytest.raises(LooporaError, match="UTF-8 encoded Markdown"):
        service.start_run(loop["id"])
    assert not runs_root.exists() or not list(runs_root.iterdir())


def test_execute_run_fails_readably_when_run_prompt_artifact_is_corrupt(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Corrupt Run Prompt Loop")
    run = service.start_run(loop["id"])
    prompt_ref = next(iter(run["prompt_files"]))
    _corrupt_run_prompt_artifact(run, prompt_ref)

    failed_run = service.execute_run(run["id"])

    assert failed_run["status"] == "failed"
    assert "UTF-8 encoded Markdown" in failed_run["error_message"]
    assert failed_run["prompt_files"] == {}
