from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import (
    agent_adapter_status,
    check_agent_adapter,
    install_agent_adapter,
    list_agent_adapter_statuses,
    uninstall_agent_adapter,
)
from loopora.agent_entry_run_projection import (
    agent_entry_loop_command as agent_entry_loop_command,
)
from loopora.service_agent_bundle_candidates import (
    AgentBundleCandidateRequest as AgentBundleCandidateRequest,
    ServiceAgentBundleCandidateMixin,
)
from loopora.service_agent_loop_start import ServiceAgentLoopStartMixin



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


from loopora.agent_adapters import normalize_agent_adapter_kind

from loopora.agent_entry_continuation import agent_entry_continuation_summary

from loopora.agent_entry_run_projection import (
    agent_entry_loop_json_command,
    agent_entry_loop_projection_messages,
)

from loopora.service_alignment_run_recovery import agent_recovery_agent_entry_candidate_event

from loopora.service_types import LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES

class ServiceAgentEntryProjectionMixin:
    def agent_entry_loop_start_projection(self, loop_id: str) -> dict[str, Any]:
        normalized_loop_id = str(loop_id or "").strip()
        if not normalized_loop_id:
            return {}
        loop = self.get_loop(normalized_loop_id)
        for session in self._agent_entry_sessions_for_loop(normalized_loop_id):
            candidate_event = agent_recovery_agent_entry_candidate_event(self.repository, str(session.get("id") or ""))
            if not candidate_event:
                continue
            payload = candidate_event.get("payload") if isinstance(candidate_event.get("payload"), dict) else {}
            adapter = self._agent_entry_projection_adapter(payload, session)
            if not adapter:
                continue
            workdir = str(session.get("workdir") or loop.get("workdir") or "").strip()
            entry_source = str(payload.get("entry_source") or "").strip()
            host_context_id = str(payload.get("host_context_id") or "").strip()
            linked_state = self._agent_entry_projection_linked_run_state(session)
            messages = agent_entry_loop_projection_messages(linked_state["next_loop_action"])
            return {
                "schema_version": 1,
                "source": "agent_entry",
                "requires_agent_native": True,
                "execution_plane": "agent_native",
                "slash_command": "/loopora-run",
                "adapter": adapter,
                "entry_source": entry_source,
                "host_context_id": host_context_id,
                "workdir": workdir,
                "loop_command": agent_entry_loop_json_command(
                    adapter,
                    workdir,
                    entry_source,
                    context_id=host_context_id,
                ),
                "alignment_session_id": str(session.get("id") or "").strip(),
                "alignment_status": str(session.get("status") or "").strip(),
                **linked_state,
                **messages,
            }
        return {}

    def _agent_entry_projection_adapter(self, payload: dict[str, Any], session: dict[str, Any]) -> str:
        adapter = str(payload.get("adapter") or session.get("executor_kind") or "").strip()
        if not adapter:
            return ""
        try:
            return normalize_agent_adapter_kind(adapter)
        except LooporaError:
            return ""

    def _agent_entry_projection_linked_run_state(self, session: dict[str, Any]) -> dict[str, Any]:
        linked_run_id = str(session.get("linked_run_id") or "").strip()
        state: dict[str, Any] = {
            "linked_run_id": linked_run_id,
            "linked_run_status": "",
            "linked_task_verdict_status": "",
            "next_loop_action": "start_or_continue",
            "continuation_summary": {},
        }
        if not linked_run_id:
            return state
        try:
            linked_run = self.get_run(linked_run_id)
        except LooporaNotFoundError:
            return state
        state["linked_run_status"] = str(linked_run.get("status") or "")
        state["linked_task_verdict_status"] = self._task_verdict_status_for_run(linked_run)
        if self._terminal_agent_run_needs_next_pass(linked_run):
            state["next_loop_action"] = "start_next_run_for_unproven_verdict"
            state["continuation_summary"] = self._agent_entry_continuation_summary(linked_run)
        elif state["linked_run_status"] in TERMINAL_RUN_STATUSES:
            state["next_loop_action"] = "replay_terminal_pass"
        else:
            state["next_loop_action"] = "continue_active_run"
        return state

    def _agent_entry_continuation_summary(self, run: dict) -> dict[str, Any]:
        continuation = self._agent_native_continuation_context_for_terminal_run(run)
        return agent_entry_continuation_summary(continuation)

    def _agent_entry_sessions_for_loop(self, loop_id: str) -> list[dict[str, Any]]:
        list_sessions = getattr(self.repository, "list_all_alignment_sessions", None)
        if not callable(list_sessions):
            return []
        normalized_loop_id = str(loop_id or "").strip()
        return [
            session
            for session in list_sessions()
            if str(session.get("linked_loop_id") or "").strip() == normalized_loop_id
        ]

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


class ServiceAgentAdapterMixin(
    ServiceAgentLoopStartMixin,
    ServiceAgentContinuationMixin,
    ServiceAgentBundleCandidateMixin,
    ServiceAgentEntryProjectionMixin,
):
    def list_agent_adapters(self, *, workdir: Path | str | None = None) -> list[dict[str, Any]]:
        return list_agent_adapter_statuses(workdir or Path.cwd())

    def get_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return agent_adapter_status(adapter, workdir or Path.cwd())

    def check_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return check_agent_adapter(adapter, workdir or Path.cwd())

    def install_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return install_agent_adapter(adapter, workdir or Path.cwd())

    def uninstall_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return uninstall_agent_adapter(adapter, workdir or Path.cwd())
