from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def create_file_preview_run(service, sample_spec_file: Path, sample_workdir: Path, *, name: str) -> dict:
    loop = service.create_loop(
        name=name,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=1,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    return service.start_run(loop["id"])
