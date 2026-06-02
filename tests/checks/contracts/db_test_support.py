from __future__ import annotations

import json
from pathlib import Path

from loopora.db import LooporaRepository
from loopora.settings import app_home


def _create_run(repository: LooporaRepository, tmp_path: Path, *, run_id: str = "run_test", status: str = "queued") -> dict:
    workdir = tmp_path / f"{run_id}-workdir"
    workdir.mkdir()
    spec_path = tmp_path / f"{run_id}-spec.md"
    spec_markdown = "# Task\n\nShip it.\n"
    spec_path.write_text(spec_markdown, encoding="utf-8")
    loop = repository.create_loop(
        {
            "id": f"loop_{run_id}",
            "name": f"Loop {run_id}",
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Ship it.", "checks": [], "constraints": "", "role_notes": {}},
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
    run_dir = workdir / ".loopora" / "runs" / run_id
    run_dir.mkdir(parents=True)
    return repository.create_run(
        {
            "id": run_id,
            "loop_id": loop["id"],
            "workdir": str(workdir),
            "spec_path": str(spec_path),
            "spec_markdown": spec_markdown,
            "compiled_spec": {"goal": "Ship it.", "checks": [], "constraints": "", "role_notes": {}},
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 1,
            "max_role_retries": 1,
            "delta_threshold": 0.1,
            "trigger_window": 1,
            "regression_window": 1,
            "role_models": {},
            "status": status,
            "runs_dir": str(run_dir),
            "summary_md": "# Loopora Run Summary\n\nQueued.\n",
        }
    )


def _read_service_log_records() -> list[dict]:
    return [
        json.loads(line)
        for line in (app_home() / "logs" / "service.log").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
