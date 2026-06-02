from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from loopora.web import build_app


def loop_creation_client(service_factory) -> TestClient:
    return TestClient(build_app(service=service_factory(scenario="success")))


def loop_creation_payload(sample_spec_file: Path, sample_workdir: Path, **overrides: Any) -> dict[str, Any]:
    payload = {
        "name": "API Loop",
        "spec_path": str(sample_spec_file),
        "workdir": str(sample_workdir),
        "max_iters": 3,
        "max_role_retries": 1,
        "delta_threshold": 0.005,
        "trigger_window": 2,
        "regression_window": 2,
        "start_immediately": False,
    }
    payload.update(overrides)
    return payload


def post_loop_creation(client: TestClient, sample_spec_file: Path, sample_workdir: Path, **overrides: Any):
    return client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, **overrides),
    )


def loop_creation_workflow(
    *,
    roles: list[dict[str, str]] | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "roles": roles or [loop_creation_role("builder", "Builder", "builder")],
        "steps": steps or [loop_creation_step("builder_step", "builder")],
    }


def loop_creation_role(role_id: str, name: str, archetype: str) -> dict[str, str]:
    return {
        "id": role_id,
        "name": name,
        "archetype": archetype,
        "prompt_ref": f"{archetype}.md",
    }


def loop_creation_step(step_id: str, role_id: str, **overrides: Any) -> dict[str, Any]:
    step = {"id": step_id, "role_id": role_id}
    step.update(overrides)
    return step
