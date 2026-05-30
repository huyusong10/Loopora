from __future__ import annotations

from loopora.utils import utc_now


def mark_run_started(repository, run_id: str) -> dict:
    return repository.update_run(run_id, status="running", started_at=utc_now())


def mark_run_succeeded(repository, run_id: str) -> dict:
    return repository.update_run(run_id, status="succeeded", finished_at=utc_now())
