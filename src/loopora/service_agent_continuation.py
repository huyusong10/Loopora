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
from loopora.utils import write_json


class ServiceAgentContinuationMixin:
    def _seed_agent_native_continuation_context(self, run: dict, previous_run: dict) -> None:
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        continuation = self._agent_native_continuation_context_for_terminal_run(previous_run)
        continuation_path = layout.context_dir / "continuation_context.json"
        write_json(continuation_path, continuation)

        run_contract = self._read_json_object(layout.run_contract_path)
        if run_contract:
            run_contract["continuation_context"] = continuation
            write_json(layout.run_contract_path, run_contract)

        self.append_run_event(
            run["id"],
            "run_continuation_context_seeded",
            {
                "previous_run_id": continuation["previous_run_id"],
                "previous_run_status": continuation["previous_run_status"],
                "previous_task_verdict_status": continuation["previous_task_verdict"]["status"],
                "missing_check_count": continuation["coverage"]["missing_check_count"],
                "top_gap_count": len(continuation["coverage"]["top_gaps"]),
                "continuation_context_path": layout.relative(continuation_path),
            },
        )

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
