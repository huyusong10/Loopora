from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


def create_snapshot_loop(service, sample_spec_file: Path, sample_workdir: Path, *, name: str) -> dict:
    return service.create_loop(
        name=name,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )


def observation_client(service) -> TestClient:
    return TestClient(build_app(service=service))
