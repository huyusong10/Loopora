from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.db import LooporaRepository


def create_loop(repository: LooporaRepository, tmp_path: Path, loop_spec: dict[str, Any]) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    spec_path = tmp_path / "spec.md"
    task = loop_spec["task"]
    spec_path.write_text(f"# Task\n\n{task}\n", encoding="utf-8")
    return repository.create_loop(
        {
            "id": loop_spec["id"],
            "name": loop_spec["name"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_path.read_text(encoding="utf-8"),
            "compiled_spec": loop_spec.get("compiled_spec", {"goal": task, "checks": []}),
            "workflow": loop_spec.get("workflow", {"roles": [], "steps": []}),
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": loop_spec.get("max_iters", 1),
            "max_role_retries": loop_spec.get("max_role_retries", 1),
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )


def gatekeeper_loop_spec(*, loop_id: str, name: str, task: str) -> dict[str, Any]:
    return {
        "id": loop_id,
        "name": name,
        "task": task,
        "compiled_spec": {
            "goal": task,
            "checks": [{"id": "proof", "title": "Proof"}],
            "coverage_targets": [{"id": "done_when.proof"}],
        },
        "workflow": {
            "roles": [{"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"}],
            "steps": [
                {
                    "id": "judge",
                    "role_id": "gatekeeper",
                    "action_policy": {"can_finish_run": True},
                }
            ],
        },
        "max_iters": 2,
    }
