from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_adapters import (
    agent_adapter_status,
    check_agent_adapter,
    list_agent_adapter_statuses,
    install_agent_adapter,
    normalize_agent_adapter_kind,
    read_agent_binding,
    resolve_adapter_project_root,
    resolved_agent_context_id,
    uninstall_agent_adapter,
    write_agent_binding,
)
from loopora.agent_entry_candidate import (
    agent_ready_review_projection,
    candidate_yaml_provenance,
    normalized_candidate_yaml,
    ready_candidate_yaml_provenance,
    ready_candidate_yaml_provenance_from_validation,
)
from loopora.agent_entry_continuation import (
    agent_entry_continuation_summary,
    agent_native_continuation_context_for_terminal_run,
    agent_native_continuation_focus,
    bucket_focus_text,
    coverage_context_for_run,
    dedupe_strings,
    list_of_dicts,
    non_negative_int,
    read_json_object,
    string_list,
    task_verdict_context_for_run,
    task_verdict_status_for_run,
    terminal_agent_run_needs_next_pass,
)
from loopora.agent_entry_run_projection import (
    adapter_label_for_error as _adapter_label_for_error,
    agent_entry_loop_command as agent_entry_loop_command,
    agent_entry_loop_json_command as agent_entry_loop_json_command,
    agent_entry_loop_projection_messages as _agent_entry_loop_projection_messages,
    agent_loop_result,
    agent_loop_unready_error,
    append_agent_entry_invocation,
)
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.service_types import LooporaConflictError, LooporaError, LooporaNotFoundError, TERMINAL_RUN_STATUSES
from loopora.utils import write_json


@dataclass(frozen=True)
class AgentBundleCandidateRequest:
    adapter: str
    workdir: Path | str
    message: str = ""
    bundle_yaml: str = ""
    bundle_file: Path | str | None = None
    context_id: str = ""
    entry_source: str = ""


@dataclass(frozen=True)
class _AgentLoopStartContext:
    adapter: str
    root: Path
    session_id: str
    context_id: str
    entry_source: str
    binding_extra: dict[str, Any] | None = None


class ServiceAgentAdapterMixin:
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

    def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict[str, Any]:
        adapter = normalize_agent_adapter_kind(request.adapter)
        if adapter not in {"codex", "claude", "opencode"}:
            raise LooporaError(f"{adapter} adapter is not implemented yet")
        root = resolve_adapter_project_root(request.workdir)
        entry_source = str(request.entry_source or "").strip() or "direct_cli"
        raw_yaml = str(request.bundle_yaml or "")
        source_path = ""
        if not raw_yaml.strip() and request.bundle_file is not None:
            bundle_path = Path(request.bundle_file).expanduser().resolve()
            try:
                raw_yaml = read_bundle_file_text(bundle_path)
            except OSError as exc:
                raise LooporaError(str(exc)) from exc
            source_path = str(bundle_path)
        candidate_text = normalized_candidate_yaml(raw_yaml)
        candidate_provenance = candidate_yaml_provenance(candidate_text)
        task_message = str(request.message or "").strip()
        if not task_message:
            raise LooporaError("agent candidate requires --message task summary for traceability")
        loopora_fit_contradiction = text_mentions_loop_fit_contradiction(task_message)
        host_context_id = resolved_agent_context_id(adapter, context_id=request.context_id)

        session = self.create_alignment_session(
            workdir=root,
            message=task_message,
            start_immediately=False,
            executor_kind=adapter,
            executor_mode="preset",
            command_cli="",
            command_args_text="",
            model="",
            reasoning_effort="",
        )
        self.repository.append_alignment_event(
            session["id"],
            "agent_candidate_received",
            {
                "candidate_origin": "agent_entry",
                "adapter": adapter,
                "entry_source": entry_source,
                "host_context_id": host_context_id,
                "has_candidate_yaml": bool(candidate_text),
                "requires_web_alignment": not bool(candidate_text),
                "requires_candidate_repair": False,
                "loopora_fit_contradiction": loopora_fit_contradiction,
                "source_path": source_path,
                **candidate_provenance,
                "ready_candidate_sha256": "",
                "ready_candidate_bytes": 0,
            },
        )
        if candidate_text:
            candidate_path = Path(session["bundle_path"])
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(candidate_text, encoding="utf-8")
            preview = self.sync_alignment_bundle_from_file(session["id"])
            session = preview["session"]
        elif loopora_fit_contradiction:
            session = self._append_alignment_system_message(
                session["id"],
                zh=(
                    "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
                    "而任务摘要已经说明这更像一次性处理、直接回答、不需要后续新证据，"
                    "或稳定 benchmark / proof harness 已足够裁决的工作，"
                    "所以这里不会伪装成可运行 Loop。若你仍想把范围改成可治理的长期 Loop，"
                    "请先补充为什么需要后续证据、handoff 或 GateKeeper 裁决。"
                ),
                en=(
                    "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
                    "a candidate plan file, and the task summary says this is closer to a one-off fix, direct answer, "
                    "benchmark/test-harness-only path, or work where later rounds add no new evidence. This is not a runnable Loop yet. If you still "
                    "want to reshape it into a governed Loop, first explain what later evidence, handoffs, or "
                    "GateKeeper judgment would add."
                ),
            )
        else:
            session = self._append_alignment_system_message(
                session["id"],
                zh=(
                    "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
                    "所以这里不会伪装成可运行 Loop。请继续确认或补充成功标准、伪完成风险、证据预期、"
                    "Loopora fit、执行策略、判断取舍、残余风险和本地治理责任，然后再生成可审查的 Loop 预览。"
                ),
                en=(
                    "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
                    "a candidate plan file, so this is not a runnable Loop yet. Continue by confirming or filling "
                    "in the success criteria, fake-done risks, evidence expectations, Loopora fit, execution strategy, "
                    "judgment tradeoffs, residual-risk policy, and local governance responsibilities before "
                    "generating a reviewable Loop preview."
                ),
            )
        requires_candidate_repair = bool(candidate_text) and session["status"] != "ready"
        ready_candidate_provenance = ready_candidate_yaml_provenance(session)
        if ready_candidate_provenance["ready_candidate_sha256"]:
            self.repository.append_alignment_event(
                session["id"],
                "agent_candidate_ready_content",
                {
                    "candidate_origin": "agent_entry",
                    "adapter": adapter,
                    "entry_source": entry_source,
                    "host_context_id": host_context_id,
                    "source_path": source_path,
                    **candidate_provenance,
                    **ready_candidate_provenance,
                },
            )
            session = self.get_alignment_session(session["id"])
        existing_binding = read_agent_binding(adapter, root, context_id=request.context_id)
        binding = write_agent_binding(
            adapter,
            root,
            {
                "alignment_session_id": session["id"],
                "alignment_status": session["status"],
                "bundle_path": session.get("bundle_path", ""),
                "candidate_origin": "agent_entry",
                "candidate_adapter": adapter,
                "candidate_entry_source": entry_source,
                "host_context_id": host_context_id,
                "requires_web_alignment": not bool(candidate_text),
                "requires_candidate_repair": requires_candidate_repair,
                "loopora_fit_contradiction": loopora_fit_contradiction,
                "source_path": source_path,
                **candidate_provenance,
                **ready_candidate_provenance,
                "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
                "entry_invocations": append_agent_entry_invocation(
                    existing_binding,
                    action="plan",
                    entry_source=entry_source,
                ),
            },
            context_id=request.context_id,
        )
        return {
            "adapter": adapter,
            "workdir": str(root),
            "candidate_origin": "agent_entry",
            "candidate_entry_source": entry_source,
            "host_context_id": host_context_id,
            "requires_web_alignment": not bool(candidate_text),
            "requires_candidate_repair": requires_candidate_repair,
            "loopora_fit_contradiction": loopora_fit_contradiction,
            **candidate_provenance,
            **ready_candidate_provenance,
            "status": session["status"],
            "ready": session["status"] == "ready",
            "ready_review_projection": self._agent_ready_review_projection(session) if session["status"] == "ready" else {},
            "session": session,
            "binding": binding,
            "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
        }

    def _agent_ready_review_projection(self, session: dict) -> dict[str, Any]:
        try:
            preview = self.get_alignment_bundle(str(session.get("id") or ""))
        except (LooporaError, BundleError, OSError, ValueError):
            return {}
        return agent_ready_review_projection(preview)

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
        binding = self._selected_agent_run_binding(
            adapter,
            root,
            context_id=context_id,
            entry_source=entry_source,
            source_option_id=source_option_id,
        )
        if not binding:
            context_resolution = self.resolve_loopora_context(root, intent="run", adapter=adapter, context_id=context_id)
            if context_resolution.get("requires_user_choice"):
                raise LooporaConflictError(
                    f"no exact Loopora binding is associated with this {_adapter_label_for_error(adapter)} session/workdir; "
                    "choose a recoverable context before /loopora-run can start"
                )
            raise LooporaConflictError(
                f"no ready Loop preview is associated with this {_adapter_label_for_error(adapter)} session/workdir; run /loopora-plan first"
            )

        session_id = str(binding.get("alignment_session_id") or "").strip()
        if not session_id:
            raise LooporaConflictError("agent binding does not reference a ready Loop preview; run /loopora-plan first")
        session = self.get_alignment_session(session_id)
        self._assert_agent_binding_matches_workdir(binding, session, expected_workdir=root)
        start_context = _AgentLoopStartContext(
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
            f"{_adapter_label_for_error(adapter)} session has no ready Loop preview (current status: {session['status']}); run /loopora-plan first"
        )

    def _start_agent_loop_from_existing_run(
        self,
        start_context: _AgentLoopStartContext,
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
        return self._agent_loop_result_from_native(start_context, session, binding, native, started_new_run=started_new_run)

    def _start_agent_loop_from_ready_session(
        self,
        start_context: _AgentLoopStartContext,
        binding: dict[str, Any],
    ) -> dict[str, Any]:
        imported = self.import_alignment_bundle(start_context.session_id, start_immediately=True, execute_async=False)
        session = imported["session"]
        run = imported.get("run")
        if not isinstance(run, dict):
            raise LooporaError("Loopora did not return a run for the ready Loop preview")
        native = self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)
        ready_context = _AgentLoopStartContext(
            adapter=start_context.adapter,
            root=start_context.root,
            session_id=start_context.session_id,
            context_id=start_context.context_id,
            entry_source=start_context.entry_source,
            binding_extra={"linked_bundle_id": imported["bundle"]["id"], "linked_loop_id": imported["bundle"].get("loop_id", "")},
        )
        binding = self._write_agent_loop_running_binding(ready_context, binding, session, native)
        return self._agent_loop_result_from_native(start_context, session, binding, native, started_new_run=True)

    def _start_agent_loop_from_imported_session(
        self,
        start_context: _AgentLoopStartContext,
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
        return self._agent_loop_result_from_native(start_context, session, binding, native, started_new_run=True)

    def _start_next_agent_native_run(
        self,
        start_context: _AgentLoopStartContext,
        session: dict[str, Any],
        previous_run: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        loop_id = str(session.get("linked_loop_id") or previous_run.get("loop_id") or "").strip()
        if not loop_id:
            raise LooporaConflictError("agent binding has no linked Loop for the next /loopora-run run")
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

    def _agent_native_projection_for_run(self, start_context: _AgentLoopStartContext, run: dict[str, Any]) -> dict[str, Any]:
        if run["status"] in TERMINAL_RUN_STATUSES:
            return self._with_agent_native_judgment_contract({"run": run, "next_step": None, "complete": True})
        return self.prepare_agent_native_run(start_context.adapter, run["id"], entry_source=start_context.entry_source)

    def _write_agent_loop_running_binding(
        self,
        start_context: _AgentLoopStartContext,
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

    def _selected_agent_run_binding(
        self,
        adapter: str,
        root: Path,
        *,
        context_id: str,
        entry_source: str,
        source_option_id: str,
    ) -> dict[str, Any]:
        option_id = str(source_option_id or "").strip()
        if option_id:
            return self._bind_selected_agent_run_context(
                adapter,
                root,
                context_id=context_id,
                entry_source=entry_source,
                source_option_id=option_id,
            )
        try:
            return read_agent_binding(adapter, root, context_id=context_id)
        except LooporaError as exc:
            raise LooporaConflictError(f"agent binding is damaged before /loopora-run can start: {exc}") from exc

    def _bind_selected_agent_run_context(
        self,
        adapter: str,
        root: Path,
        *,
        context_id: str,
        entry_source: str,
        source_option_id: str,
    ) -> dict[str, Any]:
        choices = [choice for choice in self._agent_run_context_choices(root, adapter=adapter) if isinstance(choice, dict)]
        selected = next((choice for choice in choices if str(choice.get("option_id") or "") == source_option_id), None)
        if not selected:
            raise LooporaConflictError(
                f"selected recoverable context {source_option_id!r} is not available for /loopora-run in this workdir"
            )
        session_id = str(selected.get("alignment_session_id") or "").strip()
        if not session_id:
            raise LooporaConflictError("selected recoverable context does not reference a Loop preview; run /loopora-plan first")
        session = self.get_alignment_session(session_id)
        self._assert_agent_binding_matches_workdir({"workdir": str(root)}, session, expected_workdir=root)
        try:
            existing_binding = read_agent_binding(adapter, root, context_id=context_id)
        except LooporaError:
            existing_binding = {}
        return write_agent_binding(
            adapter,
            root,
            {
                **existing_binding,
                "alignment_session_id": session_id,
                "alignment_status": str(session.get("status") or ""),
                "bundle_path": session.get("bundle_path", ""),
                "candidate_origin": "agent_entry",
                "candidate_adapter": adapter,
                "candidate_entry_source": str(entry_source or selected.get("entry_source") or "").strip() or "direct_cli",
                "host_context_id": resolved_agent_context_id(adapter, context_id=context_id),
                "requires_web_alignment": str(session.get("status") or "") not in {"ready", "imported"},
                "requires_candidate_repair": False,
                "loopora_fit_contradiction": False,
                "selected_option_id": source_option_id,
                "linked_run_id": str(selected.get("linked_run_id") or ""),
                "preview_path": f"/loops/new/bundle?alignment_session_id={session_id}",
                "entry_invocations": append_agent_entry_invocation(
                    existing_binding,
                    action="run_select",
                    entry_source=entry_source,
                ),
            },
            context_id=context_id,
        )

    def _agent_loop_result_from_native(
        self,
        start_context: _AgentLoopStartContext,
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

    def agent_entry_loop_start_projection(self, loop_id: str) -> dict[str, Any]:
        normalized_loop_id = str(loop_id or "").strip()
        if not normalized_loop_id:
            return {}
        loop = self.get_loop(normalized_loop_id)
        for session in self._agent_entry_sessions_for_loop(normalized_loop_id):
            candidate_event = self._alignment_session_agent_entry_candidate_event(str(session.get("id") or ""))
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
            messages = _agent_entry_loop_projection_messages(linked_state["next_loop_action"])
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
    def _non_negative_int(value: object) -> int:
        return non_negative_int(value)

    @staticmethod
    def _dedupe_strings(values: list[str], *, limit: int) -> list[str]:
        return dedupe_strings(values, limit=limit)

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

    @staticmethod
    def _assert_agent_binding_matches_workdir(binding: dict, session: dict, *, expected_workdir: Path) -> None:
        expected = expected_workdir.expanduser().resolve()
        binding_workdir = str(binding.get("workdir") or "").strip()
        if binding_workdir and Path(binding_workdir).expanduser().resolve() != expected:
            raise LooporaConflictError("agent binding belongs to a different workdir; run /loopora-plan again")
        session_workdir = str(session.get("workdir") or "").strip()
        if not session_workdir or Path(session_workdir).expanduser().resolve() != expected:
            raise LooporaConflictError("agent binding references a Loop preview from a different workdir; run /loopora-plan again")
