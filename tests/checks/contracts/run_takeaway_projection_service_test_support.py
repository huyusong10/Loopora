from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


def create_takeaway_loop(service, sample_spec_file: Path, sample_workdir: Path, **overrides):
    payload = {
        "name": "Takeaway Projection Loop",
        "spec_path": sample_spec_file,
        "workdir": sample_workdir,
        "model": "gpt-5.4",
        "reasoning_effort": "medium",
        "max_iters": 3,
        "max_role_retries": 1,
        "delta_threshold": 0.005,
        "trigger_window": 2,
        "regression_window": 2,
        "role_models": {},
    }
    payload.update(overrides)
    return service.create_loop(**payload)


def rerun_takeaway_loop(service, sample_spec_file: Path, sample_workdir: Path, **overrides) -> dict:
    loop = create_takeaway_loop(service, sample_spec_file, sample_workdir, **overrides)
    return service.rerun(loop["id"])


def takeaway_client(service) -> TestClient:
    return TestClient(build_app(service=service))


def set_first_handoff_summary(run: dict, summary: str) -> None:
    handoff_path = next(Path(run["runs_dir"]).glob("iterations/iter_*/steps/*/handoff.json"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["summary"] = summary
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")


def restarted_service(service):
    return service.__class__(
        repository=service.repository,
        settings=service.settings,
        executor_factory=service.executor_factory,
    )
