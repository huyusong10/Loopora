from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.db import LooporaRepository
from loopora.kernel import ActorRef

from kernel_event_test_support import create_kernel_run


def create_run_engine_evidence_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_event_core",
            "loop_id": "loop_event_core",
            "loop_name": "Event Core Loop",
            "task": "Prove it.",
        },
    )


def headless_runner_actor() -> ActorRef:
    return ActorRef(kind="runner", id="headless")


def covered_projection() -> dict[str, Any]:
    return {
        "status": "covered",
        "target_count": 1,
        "covered_target_count": 1,
        "top_gaps": [],
    }
