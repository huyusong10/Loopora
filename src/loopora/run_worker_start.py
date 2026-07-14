from __future__ import annotations

from loopora.branding import RUN_SUMMARY_TITLE

BACKGROUND_WORKER_START_ERROR = "background worker could not be started"


def background_worker_start_failure_summary() -> str:
    return (
        f"# {RUN_SUMMARY_TITLE}\n\n"
        "Background execution failed before the worker could start.\n\n"
        f"Reason: `{BACKGROUND_WORKER_START_ERROR}`.\n"
    )
