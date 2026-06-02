from __future__ import annotations

from pathlib import Path

import pytest

from loopora.branding import state_dir_for_workdir
from loopora.service_types import LooporaConflictError

from runner_helpers import _create_loop


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
