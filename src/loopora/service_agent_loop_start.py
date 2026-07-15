from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import (
    normalize_agent_adapter_kind,
    resolve_adapter_project_root,
)
from loopora.agent_entry_continuation import task_verdict_status_for_run, terminal_agent_run_needs_next_pass
from loopora.agent_entry_run_projection import (
    adapter_label_for_error,
    agent_loop_unready_error,
)
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES

from dataclasses import dataclass



from loopora.agent_adapters import write_agent_binding

from loopora.agent_entry_candidate import ready_candidate_yaml_provenance_from_validation

from loopora.agent_entry_run_projection import agent_loop_result, append_agent_entry_invocation

from collections.abc import Callable




from loopora.agent_adapters import read_agent_binding, resolved_agent_context_id


from loopora.service_alignment_run_recovery import agent_run_context_choices

from loopora.service_alignment_workdir_snapshot import alignment_same_workdir


@dataclass(frozen=True)
class AgentRunContextBindingContext:
    repository: object
    get_session: Callable[[str], dict[str, Any]]
    get_run: Callable[[str], dict[str, Any]]

@dataclass(frozen=True)
class AgentRunContextBindingRequest:
    adapter: str
    root: Path
    context_id: str
    entry_source: str
    source_option_id: str

def selected_agent_run_binding(
    context: AgentRunContextBindingContext,
    request: AgentRunContextBindingRequest,
) -> dict[str, Any]:
    option_id = str(request.source_option_id or "").strip()
    if option_id:
        return bind_selected_agent_run_context(
            context,
            AgentRunContextBindingRequest(
                adapter=request.adapter,
                root=request.root,
                context_id=request.context_id,
                entry_source=request.entry_source,
                source_option_id=option_id,
            ),
        )
    try:
        return read_agent_binding(request.adapter, request.root, context_id=request.context_id)
    except LooporaError as exc:
        raise LooporaConflictError(f"agent context card is damaged before /loopora-run can start: {exc}") from exc

def bind_selected_agent_run_context(
    context: AgentRunContextBindingContext,
    request: AgentRunContextBindingRequest,
) -> dict[str, Any]:
    choices = [
        choice
        for choice in agent_run_context_choices(
            context.repository,
            root=request.root,
            adapter=request.adapter,
            same_workdir=alignment_same_workdir,
            get_run=context.get_run,
        )
        if isinstance(choice, dict)
    ]
    selected = next((choice for choice in choices if str(choice.get("option_id") or "") == request.source_option_id), None)
    if not selected:
        raise LooporaConflictError(
            f"selected recoverable context {request.source_option_id!r} is not available for /loopora-run in this workdir"
        )
    session_id = str(selected.get("alignment_session_id") or "").strip()
    if not session_id:
        raise LooporaConflictError("selected recoverable context does not reference a Loop preview; run /loopora-plan first")
    session = context.get_session(session_id)
    assert_agent_binding_matches_workdir({"workdir": str(request.root)}, session, expected_workdir=request.root)
    try:
        existing_binding = read_agent_binding(request.adapter, request.root, context_id=request.context_id)
    except LooporaError:
        existing_binding = {}
    return write_agent_binding(
        request.adapter,
        request.root,
        {
            **existing_binding,
            "alignment_session_id": session_id,
            "alignment_status": str(session.get("status") or ""),
            "bundle_path": session.get("bundle_path", ""),
            "candidate_origin": "agent_entry",
            "candidate_adapter": request.adapter,
            "candidate_entry_source": str(request.entry_source or selected.get("entry_source") or "").strip() or "direct_cli",
            "host_context_id": resolved_agent_context_id(request.adapter, context_id=request.context_id),
            "requires_web_alignment": str(session.get("status") or "") not in {"ready", "imported"},
            "requires_candidate_repair": False,
            "loopora_fit_contradiction": False,
            "selected_option_id": request.source_option_id,
            "linked_run_id": str(selected.get("linked_run_id") or ""),
            "preview_path": f"/loops/new/bundle?alignment_session_id={session_id}",
            "entry_invocations": append_agent_entry_invocation(
                existing_binding,
                action="run_select",
                entry_source=request.entry_source,
            ),
        },
        context_id=request.context_id,
    )

def assert_agent_binding_matches_workdir(binding: dict, session: dict, *, expected_workdir: Path) -> None:
    expected = expected_workdir.expanduser().resolve()
    binding_workdir = str(binding.get("workdir") or "").strip()
    if binding_workdir and Path(binding_workdir).expanduser().resolve() != expected:
        raise LooporaConflictError("agent context card belongs to a different workdir; run /loopora-plan again")
    session_workdir = str(session.get("workdir") or "").strip()
    if not session_workdir or Path(session_workdir).expanduser().resolve() != expected:
        raise LooporaConflictError("agent context card references a Loop preview from a different workdir; run /loopora-plan again")

@dataclass(frozen=True)
class AgentLoopStartContext:
    adapter: str
    root: Path
    session_id: str
    context_id: str
    entry_source: str
    binding_extra: dict[str, Any] | None = None

def write_agent_loop_running_binding(
    start_context: AgentLoopStartContext,
    binding: dict[str, Any],
    session: dict[str, Any],
    native: dict[str, Any],
) -> dict[str, Any]:
    ready_candidate_provenance = ready_candidate_yaml_provenance_from_validation(session)
    return write_agent_binding(
        start_context.adapter,
        start_context.root,
        {
            **binding,
            **ready_candidate_provenance,
            **(start_context.binding_extra or {}),
            "alignment_status": session["status"],
            "requires_web_alignment": False,
            "requires_candidate_repair": False,
            "loopora_fit_contradiction": False,
            "linked_run_id": native["run"]["id"],
            "run_path": f"/runs/{native['run']['id']}",
            "execution_plane": "agent_native",
            "entry_invocations": append_agent_entry_invocation(
                binding,
                action="run",
                entry_source=start_context.entry_source,
            ),
        },
        context_id=start_context.context_id,
    )

def agent_loop_result_from_native(
    start_context: AgentLoopStartContext,
    session: dict[str, Any],
    binding: dict[str, Any],
    native: dict[str, Any],
    *,
    started_new_run: bool,
) -> dict[str, Any]:
    return agent_loop_result(
        start_context.adapter,
        start_context.root,
        session,
        binding,
        {
            "run": native["run"],
            "started_new_run": started_new_run,
            "next_step": native.get("next_step"),
            "complete": native.get("complete", False),
            "task_next_action": native.get("task_next_action"),
        },
    )


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
            raise LooporaError(f"{adapter} adapter is not implemented yet")
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
        binding = write_agent_loop_running_binding(start_context, binding, session, native)
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
        binding = write_agent_loop_running_binding(ready_context, binding, session, native)
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
        binding = write_agent_loop_running_binding(start_context, binding, session, native)
        return agent_loop_result_from_native(start_context, session, binding, native, started_new_run=True)

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
                "reason": "terminal_task_verdict_requires_next_run",
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
