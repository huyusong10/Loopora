from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_unavailable_summary as _adapter_unavailable_summary
from loopora.agent_adapters import (
    normalize_agent_adapter_kind,
    resolve_adapter_project_root,
)
from loopora.agent_entry_continuation import task_verdict_status_for_run, terminal_agent_run_needs_next_pass
from loopora.agent_entry_run_projection import (
    adapter_label_for_error,
    agent_loop_unready_error,
)
from loopora.run_result_recording import run_result_is_lifecycle_failure
from loopora.service_agent_loop_start_bindings import (
    AgentLoopStartContext,
    agent_loop_result_from_native,
    write_agent_loop_running_binding,
)
from loopora.service_agent_run_context_binding import (
    AgentRunContextBindingContext,
    AgentRunContextBindingRequest,
    assert_agent_binding_matches_workdir,
    selected_agent_run_binding,
)
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES


class ServiceAgentLoopStartMixin:
    def start_agent_loop(  # noqa: PLR0913 - public CLI/service bridge keeps explicit recovery option.
        self,
        adapter: str,
        *,
        workdir: Path | str,
        context_id: str = "",
        entry_source: str = "",
        source_option_id: str = "",
        execute_async: bool = True,
    ) -> dict[str, Any]:
        execute_async = bool(execute_async)
        adapter = normalize_agent_adapter_kind(adapter)
        if adapter not in {"codex", "claude", "opencode"}:
            raise LooporaError(_adapter_unavailable_summary(adapter))
        root = resolve_adapter_project_root(workdir)
        binding = selected_agent_run_binding(
            AgentRunContextBindingContext(
                repository=self.repository,
                get_session=self.get_alignment_session,
                get_run=self.get_run,
            ),
            AgentRunContextBindingRequest(
                adapter=adapter,
                root=root,
                context_id=context_id,
                entry_source=entry_source,
                source_option_id=source_option_id,
            ),
        )
        if not binding:
            context_resolution = self.resolve_loopora_context(root, intent="run", adapter=adapter, context_id=context_id)
            if context_resolution.get("requires_user_choice"):
                raise LooporaConflictError(
                    f"no exact Loopora context card is associated with this {adapter_label_for_error(adapter)} session/workdir; "
                    "choose a recoverable context before /loopora-run can start"
                )
            raise LooporaConflictError(
                f"no ready Loop preview is associated with this {adapter_label_for_error(adapter)} session/workdir; run /loopora-plan first"
            )

        session_id = str(binding.get("alignment_session_id") or "").strip()
        if not session_id:
            raise LooporaConflictError("agent context card does not reference a ready Loop preview; run /loopora-plan first")
        session = self.get_alignment_session(session_id)
        assert_agent_binding_matches_workdir(binding, session, expected_workdir=root)
        start_context = AgentLoopStartContext(
            adapter=adapter,
            root=root,
            session_id=session_id,
            context_id=context_id,
            entry_source=entry_source,
        )
        run = self._agent_bound_run(session)
        if run is not None:
            return self._start_agent_loop_from_existing_run(start_context, session, binding, run)

        if session["status"] == "ready":
            return self._start_agent_loop_from_ready_session(start_context, binding)

        if session["status"] == "imported" and session.get("linked_loop_id"):
            return self._start_agent_loop_from_imported_session(start_context, session, binding)

        unready_error = agent_loop_unready_error(adapter, binding, session)
        if unready_error:
            raise LooporaConflictError(unready_error)
        raise LooporaConflictError(
            f"{adapter_label_for_error(adapter)} session has no ready Loop preview (current status: {session['status']}); run /loopora-plan first"
        )

    def _start_agent_loop_from_existing_run(
        self,
        start_context: AgentLoopStartContext,
        session: dict[str, Any],
        binding: dict[str, Any],
        run: dict[str, Any],
    ) -> dict[str, Any]:
        started_new_run = False
        if self._terminal_agent_run_needs_next_pass(run):
            native, session = self._start_next_agent_native_run(start_context, session, run)
            started_new_run = True
        else:
            native = self._agent_native_projection_for_run(start_context, run)
            session = self.repository.update_alignment_session(
                start_context.session_id,
                status="running_loop",
                linked_run_id=run["id"],
                error_message="",
            )
        binding = self._write_agent_loop_running_binding(start_context, binding, session, native)
        return agent_loop_result_from_native(start_context, session, binding, native, started_new_run=started_new_run)

    def _start_agent_loop_from_ready_session(
        self,
        start_context: AgentLoopStartContext,
        binding: dict[str, Any],
    ) -> dict[str, Any]:
        imported = self.import_alignment_bundle(start_context.session_id, start_immediately=True, execute_async=False)
        session = imported["session"]
        run = imported.get("run")
        if not isinstance(run, dict):
            raise LooporaError("Loopora did not return a run for the ready Loop preview")
        native = self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)
        ready_context = AgentLoopStartContext(
            adapter=start_context.adapter,
            root=start_context.root,
            session_id=start_context.session_id,
            context_id=start_context.context_id,
            entry_source=start_context.entry_source,
            binding_extra={"linked_bundle_id": imported["bundle"]["id"], "linked_loop_id": imported["bundle"].get("loop_id", "")},
        )
        binding = self._write_agent_loop_running_binding(ready_context, binding, session, native)
        return agent_loop_result_from_native(start_context, session, binding, native, started_new_run=True)

    def _start_agent_loop_from_imported_session(
        self,
        start_context: AgentLoopStartContext,
        session: dict[str, Any],
        binding: dict[str, Any],
    ) -> dict[str, Any]:
        run = self.start_run(str(session["linked_loop_id"]))
        native = self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)
        self.repository.update_alignment_session(
            start_context.session_id,
            status="running_loop",
            linked_run_id=native["run"]["id"],
            error_message="",
        )
        self.repository.append_alignment_event(start_context.session_id, "alignment_run_started", {"loop_id": session.get("linked_loop_id", ""), "run_id": run["id"]})
        session = self.get_alignment_session(start_context.session_id)
        binding = self._write_agent_loop_running_binding(start_context, binding, session, native)
        return agent_loop_result_from_native(start_context, session, binding, native, started_new_run=True)

    def _write_agent_loop_running_binding(
        self,
        start_context: AgentLoopStartContext,
        binding: dict[str, Any],
        session: dict[str, Any],
        native: dict[str, Any],
    ) -> dict[str, Any]:
        updated_binding = write_agent_loop_running_binding(start_context, binding, session, native)
        context_binding_error = str(updated_binding.get("context_binding_error") or "").strip()
        if context_binding_error:
            self.repository.append_alignment_event(
                start_context.session_id,
                "agent_context_card_save_failed",
                {
                    "status": "warning",
                    "error": context_binding_error,
                    "run_id": native["run"]["id"],
                },
            )
        return updated_binding

    def _start_next_agent_native_run(
        self,
        start_context: AgentLoopStartContext,
        session: dict[str, Any],
        previous_run: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        loop_id = str(session.get("linked_loop_id") or previous_run.get("loop_id") or "").strip()
        if not loop_id:
            raise LooporaConflictError("agent context card has no linked Loop for the next /loopora-run run")
        run = self.start_run(loop_id)
        self._seed_agent_native_continuation_context(run, previous_run)
        native = self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)
        continuation_reason = (
            "previous_lifecycle_failure_retry"
            if run_result_is_lifecycle_failure(previous_run)
            else "terminal_task_verdict_requires_next_run"
        )
        self.repository.update_alignment_session(
            start_context.session_id,
            status="running_loop",
            linked_run_id=native["run"]["id"],
            error_message="",
        )
        self.repository.append_alignment_event(
            start_context.session_id,
            "alignment_run_started",
            {
                "loop_id": loop_id,
                "run_id": native["run"]["id"],
                "reason": continuation_reason,
                "previous_run_id": previous_run["id"],
                "previous_task_verdict_status": self._task_verdict_status_for_run(previous_run),
            },
        )
        return native, self.get_alignment_session(start_context.session_id)

    def _agent_native_projection_for_run(self, start_context: AgentLoopStartContext, run: dict[str, Any]) -> dict[str, Any]:
        if run["status"] in TERMINAL_RUN_STATUSES:
            return self._with_agent_native_judgment_contract({"run": run, "next_step": None, "complete": True})
        return self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)

    def _agent_bound_run(self, session: dict) -> dict | None:
        run_id = str(session.get("linked_run_id") or "").strip()
        if not run_id:
            return None
        try:
            run = self.get_run(run_id)
        except LooporaNotFoundError:
            return None
        if run["status"] not in TERMINAL_RUN_STATUSES:
            return run
        return run

    @staticmethod
    def _task_verdict_status_for_run(run: dict) -> str:
        return task_verdict_status_for_run(run)

    @staticmethod
    def _terminal_agent_run_needs_next_pass(run: dict) -> bool:
        return terminal_agent_run_needs_next_pass(run)
