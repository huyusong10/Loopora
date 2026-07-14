from __future__ import annotations

from collections.abc import Callable

from loopora.executor_command_args import (
    build_claude_exec_args,
    build_codex_exec_args,
    build_custom_exec_args,
    build_opencode_exec_args,
)
from loopora.executor_output_parsing import parse_structured_output_from_text
from loopora.executor_opencode_stream import initial_opencode_stream_state
from loopora.executor_result_files import (
    read_executor_json_object_output,
    write_executor_json_output,
    write_executor_schema_file,
)
from loopora.executor_session_refs import ensure_resume_session_ref
from loopora.executor_types import ExecutionStopped, ExecutorError, ExecutorProcessRequest, RoleRequest


class RealExecutorProviderFlowMixin:
    def _execute_codex(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        schema_path = write_executor_schema_file(request)
        args = (
            build_custom_exec_args(request, schema_path)
            if request.executor_mode == "command"
            else build_codex_exec_args(request, schema_path)
        )
        stdin_text = None if request.executor_mode == "command" else request.prompt
        if request.inherit_session:
            request.extra_context.setdefault("session_ref", {})
        return_code = self._stream_process(
            ExecutorProcessRequest(
                request=request,
                args=args,
                emit_event=emit_event,
                should_stop=should_stop,
                set_child_pid=set_child_pid,
                line_handler=lambda line: self._handle_codex_line(line, request, emit_event),
                stdin_text=stdin_text,
            )
        )

        self._raise_for_unsuccessful_process(
            return_code,
            request=request,
            should_stop=should_stop,
            failure_label="codex exec failed",
        )

        if not request.output_path.exists():
            raise ExecutorError(f"codex exec did not produce an output file for role={request.role}")

        self._infer_codex_session_ref(request)
        ensure_resume_session_ref(request)

        return read_executor_json_object_output(
            request,
            executor_label="codex exec",
            invalid_json_message=f"role={request.role} produced invalid JSON output",
            non_object_message=f"codex exec did not produce a JSON object for role={request.role}",
            allow_text_fallback=True,
        )

    def _execute_claude(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        schema_path = write_executor_schema_file(request)
        args = (
            build_custom_exec_args(request, schema_path)
            if request.executor_mode == "command"
            else build_claude_exec_args(request)
        )
        if request.inherit_session:
            request.extra_context.setdefault("session_ref", {})
        state = {
            "blocks": {},
            "structured_output": None,
        }
        return_code = self._stream_process(
            ExecutorProcessRequest(
                request=request,
                args=args,
                emit_event=emit_event,
                should_stop=should_stop,
                set_child_pid=set_child_pid,
                line_handler=lambda line: self._handle_claude_line(line, state, emit_event, request),
            )
        )
        self._raise_for_unsuccessful_process(
            return_code,
            request=request,
            should_stop=should_stop,
            failure_label="claude print failed",
        )
        payload = state.get("structured_output")
        if not isinstance(payload, dict):
            raise ExecutorError(f"claude did not produce structured output for role={request.role}")
        ensure_resume_session_ref(request)
        write_executor_json_output(request, payload)
        return payload

    def _execute_opencode(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        schema_path = write_executor_schema_file(request)
        args = (
            build_custom_exec_args(request, schema_path)
            if request.executor_mode == "command"
            else build_opencode_exec_args(request)
        )
        if request.inherit_session:
            request.extra_context.setdefault("session_ref", {})
        state = initial_opencode_stream_state()
        return_code = self._stream_process(
            ExecutorProcessRequest(
                request=request,
                args=args,
                emit_event=emit_event,
                should_stop=should_stop,
                set_child_pid=set_child_pid,
                line_handler=lambda line: self._handle_opencode_line(line, state, emit_event, request),
            )
        )
        self._raise_for_unsuccessful_process(
            return_code,
            request=request,
            should_stop=should_stop,
            failure_label="opencode run failed",
        )
        payload = parse_structured_output_from_text(state.get("latest_text") or "\n".join(state["text_parts"]))
        if not isinstance(payload, dict):
            raise ExecutorError(f"opencode did not produce a valid JSON object for role={request.role}")
        ensure_resume_session_ref(request)
        write_executor_json_output(request, payload)
        return payload

    def _execute_custom(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        if request.executor_mode != "command":
            raise ExecutorError("custom executor only supports command mode")
        schema_path = write_executor_schema_file(request)
        args = build_custom_exec_args(request, schema_path)
        return_code = self._stream_process(
            ExecutorProcessRequest(
                request=request,
                args=args,
                emit_event=emit_event,
                should_stop=should_stop,
                set_child_pid=set_child_pid,
                line_handler=lambda line: emit_event("codex_event", self._decode_json_line(line)),
            )
        )
        self._raise_for_unsuccessful_process(
            return_code,
            request=request,
            should_stop=should_stop,
            failure_label="custom exec failed",
        )
        if not request.output_path.exists():
            raise ExecutorError(f"custom exec did not produce an output file for role={request.role}")
        payload = read_executor_json_object_output(
            request,
            executor_label="custom exec",
            invalid_json_message=f"role={request.role} produced invalid JSON output",
            non_object_message=f"custom exec did not produce a JSON object for role={request.role}",
        )
        if request.inherit_session:
            self._capture_session_ref(request, payload)
            ensure_resume_session_ref(request)
        return payload

    @staticmethod
    def _raise_for_unsuccessful_process(
        return_code: int,
        *,
        request: RoleRequest,
        should_stop: Callable[[], bool],
        failure_label: str,
    ) -> None:
        if return_code == 0:
            return
        if should_stop():
            raise ExecutionStopped(f"run {request.run_id} stopped while {request.role} was running")
        raise ExecutorError(f"{failure_label} for role={request.role} exit_code={return_code}")
