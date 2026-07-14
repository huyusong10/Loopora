from __future__ import annotations

from typing import Any

from loopora.agent_adapters import normalize_agent_adapter_kind
from loopora.agent_entry_continuation import agent_entry_continuation_summary
from loopora.agent_entry_run_projection import (
    agent_entry_loop_json_command,
    agent_entry_loop_projection_messages,
)
from loopora.run_result_recording import run_result_is_lifecycle_failure
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
            state["next_loop_action"] = (
                "retry_lifecycle_failure"
                if run_result_is_lifecycle_failure(linked_run)
                else "start_next_run_for_unproven_verdict"
            )
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
