from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.run_artifacts import RunArtifactLayout


def build_contract_snapshot(tmp_path: Path, run_name: str, **request_overrides: Any) -> dict:
    layout = RunArtifactLayout(tmp_path / run_name)
    layout.initialize()
    request = {
        "run": {
            "id": run_name,
            "loop_id": f"loop_{run_name}",
            "workdir": str(tmp_path),
            "completion_mode": "gatekeeper",
            "max_iters": 4,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "iteration_interval_seconds": 0,
            "executor_kind": "codex",
            "executor_mode": "preset",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
        },
        "compiled_spec": {"checks": [], "raw_sections": {}},
        "strategy_source": {"preset": "custom", "roles": [], "steps": []},
        "prompt_files": {},
        "workspace_baseline": {"file_count": 0},
        "layout": layout,
    }
    request.update(request_overrides)
    return build_run_contract_snapshot(RunContractSnapshotRequest(**request))
