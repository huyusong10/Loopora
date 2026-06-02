from __future__ import annotations

from pathlib import Path


def create_manual_loop(
    service,
    *,
    spec_path: Path,
    workdir: Path,
    name: str = "Manual Loop",
    orchestration_id: str = "builtin:build_first",
) -> dict:
    return service.create_loop(
        name=name,
        spec_path=spec_path,
        workdir=workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id=orchestration_id,
    )
