from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_entry_continuation import (
    agent_native_continuation_context_for_terminal_run,
    agent_native_continuation_focus,
    bucket_focus_text,
    coverage_context_for_run,
    dedupe_strings,
    list_of_dicts,
    read_json_object,
    string_list,
    task_verdict_context_for_run,
)


class ServiceAgentContinuationMixin:
    def _seed_agent_native_continuation_context(self, run: dict, previous_run: dict) -> None:
        self._seed_run_continuation_context(run, previous_run)

    def _agent_native_continuation_context_for_terminal_run(self, previous_run: dict) -> dict[str, Any]:
        previous_layout = self._run_artifact_layout(Path(previous_run["runs_dir"]))
        return agent_native_continuation_context_for_terminal_run(previous_run, previous_layout)

    def _task_verdict_context_for_run(self, run: dict, layout) -> dict[str, Any]:
        return task_verdict_context_for_run(run, layout)

    def _coverage_context_for_run(self, layout) -> dict[str, Any]:
        return coverage_context_for_run(layout)

    @staticmethod
    def _agent_native_continuation_focus(task_verdict: dict, coverage: dict) -> list[str]:
        return agent_native_continuation_focus(task_verdict, coverage)

    @staticmethod
    def _bucket_focus_text(item: dict) -> str:
        return bucket_focus_text(item)

    @staticmethod
    def _read_json_object(path: Path) -> dict:
        return read_json_object(path)

    @staticmethod
    def _string_list(value: object, *, limit: int | None = None) -> list[str]:
        return string_list(value, limit=limit)

    @staticmethod
    def _list_of_dicts(value: object, *, limit: int | None = None) -> list[dict]:
        return list_of_dicts(value, limit=limit)

    @staticmethod
    def _dedupe_strings(values: list[str], *, limit: int) -> list[str]:
        return dedupe_strings(values, limit=limit)
