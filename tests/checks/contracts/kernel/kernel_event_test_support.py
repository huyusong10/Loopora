from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.db import LooporaRepository


def create_kernel_run(repository: LooporaRepository, tmp_path: Path, run_spec: dict[str, Any]) -> dict:
    workdir = tmp_path / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)
    spec_path = tmp_path / "spec.md"
    task = run_spec["task"]
    spec_markdown = f"# Task\n\n{task}\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    compiled_spec = {"goal": task, "checks": [{"id": "proof", "title": "Proof"}]}
    loop = repository.create_loop(
        {
            "id": run_spec["loop_id"],
            "name": run_spec["loop_name"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": compiled_spec,
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
        }
    )
    run_dir = workdir / ".loopora" / "runs" / run_spec["run_id"]
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": run_spec["run_id"],
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": compiled_spec,
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
            "status": "queued",
            "runs_dir": str(run_dir),
        }
    )
