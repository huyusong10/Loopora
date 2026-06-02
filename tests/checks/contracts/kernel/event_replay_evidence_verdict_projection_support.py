from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository

from kernel_event_test_support import create_kernel_run


def create_event_projection_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_event_projection",
            "loop_id": "loop_event_projection",
            "loop_name": "Event Projection Loop",
            "task": "Prove replay.",
        },
    )
