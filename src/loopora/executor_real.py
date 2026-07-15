from __future__ import annotations

import json
from collections.abc import Callable

from loopora.executor_command_args import parse_structured_output_from_text
from loopora.executor_claude_stream import (
    handle_claude_record,
    summarize_claude_tool_result,
    summarize_claude_tool_use,
    truncate_claude_console_preview,
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

import signal

import subprocess

import time

from loopora.executor_command_args import build_command_event_payload

from loopora.executor_process_stream import (
    ProcessStreamCallbacks,
    ProcessStreamContext,
    ProcessStreamIdleTimeoutError,
    ProcessStreamStoppedError,
    stream_process,
)

from loopora.executor_types import ExecutionStopped


from loopora.executor_command_args import (
    build_claude_exec_args,
    build_codex_exec_args,
    build_custom_exec_args,
    build_opencode_exec_args,
)



from loopora.executor_command_args import (
    read_executor_json_object_output,
    write_executor_json_output,
    write_executor_schema_file,
)




from loopora.executor_command_args import EXECUTOR_OUTPUT_MAX_BYTES



import os

import re

from pathlib import Path

_ROLLOUT_SESSION_ID_PATTERN = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
    re.IGNORECASE,
)

def normalize_session_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())

def extract_session_ref(payload: object) -> dict[str, str]:
    session_id = ""
    rollout_path = ""

    for key, child in _iter_payload_fields(payload):
        normalized_key = normalize_session_key(key)
        if normalized_key == "sessionid":
            session_id = _session_id_from_value(child) or session_id
        elif normalized_key == "rolloutpath" and isinstance(child, str) and child.strip():
            rollout_path = child.strip()
        if session_id and rollout_path:
            break

    if not session_id and rollout_path:
        session_id = _session_id_from_rollout_path(rollout_path)
    return _session_ref_payload(session_id=session_id, rollout_path=rollout_path)

def _iter_payload_fields(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _iter_payload_fields(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_payload_fields(child)

def _session_id_from_value(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        uuid_value = value.get("uuid")
        if isinstance(uuid_value, str) and uuid_value.strip():
            return uuid_value.strip()
    return ""

def _session_id_from_rollout_path(rollout_path: str) -> str:
    match = _ROLLOUT_SESSION_ID_PATTERN.search(rollout_path)
    return match.group(1) if match else ""

def _session_ref_payload(*, session_id: str, rollout_path: str) -> dict[str, str]:
    ref: dict[str, str] = {}
    if session_id:
        ref["session_id"] = session_id
    if rollout_path:
        ref["rollout_path"] = rollout_path
    return ref

def merge_session_ref(current: object, ref: dict[str, str]) -> dict:
    merged = dict(current) if isinstance(current, dict) else {}
    merged.update(ref)
    return merged

def ensure_resume_session_ref(request: object) -> None:
    if not getattr(request, "inherit_session", False):
        return
    resume_session_id = str(getattr(request, "resume_session_id", "") or "").strip()
    if not resume_session_id:
        return
    extra_context = getattr(request, "extra_context", None)
    if not isinstance(extra_context, dict):
        return
    current = extra_context.get("session_ref")
    if not isinstance(current, dict) or not current.get("session_id"):
        extra_context["session_ref"] = {"session_id": resume_session_id}

def infer_codex_session_ref_from_rollouts(
    *,
    workdir: Path,
    current_ref: object,
    started_at: float = 0.0,
    codex_home: Path | None = None,
) -> dict[str, str]:
    if isinstance(current_ref, dict) and current_ref.get("session_id"):
        return {}

    sessions_dir = (codex_home or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))) / "sessions"
    if not sessions_dir.exists():
        return {}

    resolved_workdir = workdir.expanduser().resolve().as_posix()
    for path in _recent_rollout_paths(sessions_dir):
        try:
            stat = path.stat()
            if started_at and stat.st_mtime + 1 < started_at:
                break
            payload = _read_first_json_line(path)
        except (OSError, json.JSONDecodeError):
            continue

        if not _payload_matches_workdir(payload, resolved_workdir):
            continue
        ref = extract_session_ref(payload) or extract_session_ref({"rollout_path": str(path)})
        if ref:
            return ref
    return {}

def _recent_rollout_paths(sessions_dir: Path) -> list[Path]:
    candidates: list[tuple[float, Path]] = []
    for path in sessions_dir.rglob("rollout-*.jsonl"):
        try:
            candidates.append((path.stat().st_mtime, path))
        except OSError:
            continue
    return [path for _, path in sorted(candidates, reverse=True)[:50]]

def _read_first_json_line(path: Path) -> object:
    with path.open(encoding="utf-8") as file:
        first_line = file.readline()
    if not first_line:
        raise json.JSONDecodeError("empty rollout file", "", 0)
    return json.loads(first_line)

def _payload_matches_workdir(payload: object, resolved_workdir: str) -> bool:
    cwd = ""
    if isinstance(payload, dict):
        session_meta = payload.get("session_meta")
        cwd = str(payload.get("cwd") or (session_meta.get("cwd") if isinstance(session_meta, dict) else "") or "").strip()
    if not cwd:
        return True
    return Path(cwd).expanduser().resolve().as_posix() == resolved_workdir

EmitEvent = Callable[[str, dict], None]

def initial_opencode_stream_state() -> dict:
    return {
        "latest_text": "",
        "text_parts": [],
        "text_size_bytes": 0,
    }

def handle_opencode_record(
    record: dict,
    state: dict,
    emit_event: EmitEvent,
    request: RoleRequest | None = None,
) -> None:
    if record.get("type") == "stdout":
        emit_event("codex_event", record)
        return
    event_type = record.get("type")
    if event_type == "step_start":
        emit_event("codex_event", {"type": "stdout", "message": "OpenCode step started"})
        return
    if event_type == "text":
        _handle_text_record(record, state, emit_event, request)
        return
    if event_type == "step_finish":
        _handle_step_finish_record(record, emit_event)

def _handle_text_record(
    record: dict,
    state: dict,
    emit_event: EmitEvent,
    request: RoleRequest | None,
) -> None:
    text = str((record.get("part") or {}).get("text") or "").strip()
    if not text:
        return
    text_size = len(text.encode("utf-8"))
    next_size = int(state.get("text_size_bytes") or 0) + text_size
    if next_size > EXECUTOR_OUTPUT_MAX_BYTES:
        role = request.role if request is not None else "unknown"
        raise ExecutorError(
            f"opencode output is too large for role={role}: "
            f"{next_size} bytes exceeds {EXECUTOR_OUTPUT_MAX_BYTES} bytes"
        )
    state["text_size_bytes"] = next_size
    state["latest_text"] = text
    state["text_parts"].append(text)
    emit_event("codex_event", {"type": "stdout", "message": text})

def _handle_step_finish_record(record: dict, emit_event: EmitEvent) -> None:
    tokens = ((record.get("part") or {}).get("tokens") or {})
    total = tokens.get("total")
    if total is not None:
        emit_event("codex_event", {"type": "stdout", "message": f"OpenCode step finished · tokens={total}"})

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

        if return_code != 0:
            raise ExecutorError(f"codex exec failed for role={request.role} exit_code={return_code}")

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
        if return_code != 0:
            raise ExecutorError(f"claude print failed for role={request.role} exit_code={return_code}")
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
        if return_code != 0:
            raise ExecutorError(f"opencode run failed for role={request.role} exit_code={return_code}")
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
        if return_code != 0:
            raise ExecutorError(f"custom exec failed for role={request.role} exit_code={return_code}")
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

def run_executor_process(process_request: ExecutorProcessRequest) -> int:
    request = process_request.request
    request.extra_context["_executor_started_at"] = time.time()
    try:
        return stream_process(
            context=ProcessStreamContext(
                run_id=request.run_id,
                role=request.role,
                workdir=request.workdir,
                idle_timeout_seconds=request.idle_timeout_seconds,
            ),
            args=process_request.args,
            command_event_payload=build_command_event_payload(request, process_request.args),
            callbacks=ProcessStreamCallbacks(
                emit_event=process_request.emit_event,
                should_stop=process_request.should_stop,
                set_child_pid=process_request.set_child_pid,
                line_handler=process_request.line_handler,
                terminate_process=terminate_executor_process,
            ),
            stdin_text=process_request.stdin_text,
        )
    except ProcessStreamStoppedError as exc:
        raise ExecutionStopped(str(exc)) from exc
    except ProcessStreamIdleTimeoutError as exc:
        raise ExecutorError(str(exc)) from exc

def terminate_executor_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


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
