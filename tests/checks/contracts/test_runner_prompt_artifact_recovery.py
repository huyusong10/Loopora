from __future__ import annotations

from pathlib import Path

import pytest

from loopora.branding import state_dir_for_workdir
from loopora.service import LooporaError

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
