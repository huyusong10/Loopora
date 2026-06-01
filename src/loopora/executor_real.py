from __future__ import annotations

import json
from collections.abc import Callable

from loopora.executor_output_parsing import parse_structured_output_from_text
from loopora.executor_opencode_stream import handle_opencode_record
from loopora.executor_claude_stream import (
    handle_claude_record,
    summarize_claude_tool_result,
    summarize_claude_tool_use,
    truncate_claude_console_preview,
)
from loopora.executor_process_runner import run_executor_process, terminate_executor_process
from loopora.executor_provider_flows import RealExecutorProviderFlowMixin
from loopora.executor_session_refs import (
    extract_session_ref,
    infer_codex_session_ref_from_rollouts,
    merge_session_ref,
    normalize_session_key,
)
from loopora.executor_types import (
    CodexExecutor,
    ExecutorError,
    ExecutorProcessRequest,
    RoleRequest,
)
from loopora.providers import (
    normalize_executor_kind,
    normalize_executor_mode,
)


class RealCodexExecutor(RealExecutorProviderFlowMixin, CodexExecutor):
    def execute(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        executor_kind = normalize_executor_kind(request.executor_kind)
        request.executor_mode = normalize_executor_mode(request.executor_mode)
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        if executor_kind == "codex":
            return self._execute_codex(request, emit_event, should_stop, set_child_pid)
        if executor_kind == "claude":
            return self._execute_claude(request, emit_event, should_stop, set_child_pid)
        if executor_kind == "opencode":
            return self._execute_opencode(request, emit_event, should_stop, set_child_pid)
        if executor_kind == "custom":
            return self._execute_custom(request, emit_event, should_stop, set_child_pid)
        raise ExecutorError(f"unsupported executor kind: {executor_kind}")

    @staticmethod
    def _normalize_session_key(value: object) -> str:
        return normalize_session_key(value)

    @classmethod
    def _extract_session_ref(cls, payload: object) -> dict[str, str]:
        return extract_session_ref(payload)

    def _capture_session_ref(self, request: RoleRequest, payload: object) -> None:
        if not request.inherit_session:
            return
        ref = self._extract_session_ref(payload)
        if not ref:
            return
        request.extra_context["session_ref"] = merge_session_ref(request.extra_context.get("session_ref"), ref)

    def _infer_codex_session_ref(self, request: RoleRequest) -> None:
        if not request.inherit_session:
            return
        current = request.extra_context.get("session_ref")
        started_at = float(request.extra_context.get("_executor_started_at") or 0.0)
        ref = infer_codex_session_ref_from_rollouts(
            workdir=request.workdir,
            current_ref=current,
            started_at=started_at,
        )
        if ref:
            request.extra_context["session_ref"] = merge_session_ref(current, ref)

    def _stream_process(self, process_request: ExecutorProcessRequest) -> int:
        return run_executor_process(process_request)

    def _handle_codex_line(
        self,
        line: str,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
    ) -> None:
        record = self._decode_json_line(line)
        self._capture_session_ref(request, record)
        emit_event("codex_event", record)

    @staticmethod
    def _decode_json_line(line: str) -> dict:
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"type": "stdout", "message": line}

    def _handle_claude_line(
        self,
        line: str,
        state: dict,
        emit_event: Callable[[str, dict], None],
        request: RoleRequest | None = None,
    ) -> None:
        record = self._decode_json_line(line)
        if request is not None:
            self._capture_session_ref(request, record)
        handle_claude_record(record, state, emit_event)

    @staticmethod
    def _summarize_claude_tool_use(name: object, raw_input: object) -> str:
        return summarize_claude_tool_use(name, raw_input)

    @staticmethod
    def _summarize_claude_tool_result(record: dict) -> str:
        return summarize_claude_tool_result(record)

    @staticmethod
    def _truncate_claude_console_preview(text: str, *, max_chars: int = 1200, max_lines: int = 24) -> str:
        return truncate_claude_console_preview(text, max_chars=max_chars, max_lines=max_lines)

    def _handle_opencode_line(
        self,
        line: str,
        state: dict,
        emit_event: Callable[[str, dict], None],
        request: RoleRequest | None = None,
    ) -> None:
        record = self._decode_json_line(line)
        if request is not None:
            self._capture_session_ref(request, record)
        handle_opencode_record(record, state, emit_event, request)

    @staticmethod
    def _parse_structured_output_from_text(text: str) -> dict | None:
        return parse_structured_output_from_text(text)

    @staticmethod
    def _terminate_process(process) -> None:
        terminate_executor_process(process)
