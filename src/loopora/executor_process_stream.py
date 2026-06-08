from __future__ import annotations

import queue
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_NO_LINE = object()
_IDLE_PROGRESS_NOISE_MARKERS = (
    "WARN codex_core_plugins::manifest: ignoring interface.defaultPrompt",
    "WARN codex_core_skills::loader: ignoring interface.icon_small",
    "WARN codex_core_skills::loader: ignoring interface.icon_large",
    "WARN codex_core::thread_manager: failed to apply goal resume runtime effects",
    "WARN codex_app_server::request_processors::thread_lifecycle: failed to read thread goal",
    "WARN codex_core::goals: failed to read thread goal",
)


class ProcessStreamStoppedError(RuntimeError):
    """Raised when the caller requests stop while the child process is active."""


class ProcessStreamIdleTimeoutError(RuntimeError):
    """Raised when the child process produces no output before the idle deadline."""


ProcessStreamStopped = ProcessStreamStoppedError
ProcessStreamIdleTimeout = ProcessStreamIdleTimeoutError


@dataclass(slots=True)
class ProcessStreamContext:
    run_id: str
    role: str
    workdir: Path
    idle_timeout_seconds: float | None


@dataclass(slots=True)
class ProcessStreamCallbacks:
    emit_event: Callable[[str, dict], None]
    should_stop: Callable[[], bool]
    set_child_pid: Callable[[int | None], None]
    line_handler: Callable[[str], None]
    terminate_process: Callable[[subprocess.Popen[str]], None]


def stream_process(
    *,
    context: ProcessStreamContext,
    args: list[str],
    command_event_payload: dict,
    callbacks: ProcessStreamCallbacks,
    stdin_text: str | None = None,
) -> int:
    process = _open_stream_process(args, context=context, stdin_text=stdin_text)
    _ensure_stdout_pipe_configured(process, callbacks)

    output_queue = None
    stdin_writer = None
    child_pid_registered = False
    try:
        callbacks.set_child_pid(process.pid)
        child_pid_registered = True
        callbacks.emit_event("codex_event", command_event_payload)
        stdin_writer = _start_stdin_writer_if_needed(process, stdin_text, context.role)
        output_queue = _start_stdout_reader(process, context.role)
        idle_timeout_seconds = context.idle_timeout_seconds or 0.0
        last_output_at = time.monotonic()
        stream_closed = False
        while True:
            if callbacks.should_stop():
                callbacks.terminate_process(process)
                raise ProcessStreamStoppedError(f"run {context.run_id} stopped while {context.role} was running")

            raw_line = _next_stream_line(output_queue)
            if raw_line is None:
                stream_closed = True
            elif raw_line is not _NO_LINE and _stream_line_counts_as_idle_progress(
                raw_line,
                callbacks.line_handler,
            ):
                last_output_at = time.monotonic()

            _raise_if_idle_timeout_elapsed(
                process=process,
                context=context,
                idle_timeout_seconds=idle_timeout_seconds,
                last_output_at=last_output_at,
                terminate_process=callbacks.terminate_process,
            )

            if stream_closed and process.poll() is not None:
                break
        return process.wait()
    finally:
        if process.poll() is None:
            callbacks.terminate_process(process)
        if child_pid_registered:
            callbacks.set_child_pid(None)
        if stdin_writer is not None:
            stdin_writer.join(timeout=0.2)
        if output_queue is not None:
            output_queue.reader.join(timeout=0.2)
        _close_stdout_pipe(process.stdout)


@dataclass(slots=True)
class _OutputQueue:
    lines: queue.Queue[str | None]
    reader: threading.Thread


def _open_stream_process(
    args: list[str],
    *,
    context: ProcessStreamContext,
    stdin_text: str | None,
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        args,
        cwd=str(context.workdir),
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _ensure_stdout_pipe_configured(
    process: subprocess.Popen[str],
    callbacks: ProcessStreamCallbacks,
) -> None:
    if process.stdout is not None:
        return
    callbacks.terminate_process(process)
    raise RuntimeError("executor process stdout pipe was not configured")


def _start_stdout_reader(process: subprocess.Popen[str], role: str) -> _OutputQueue:
    output_queue: queue.Queue[str | None] = queue.Queue()
    stdout = process.stdout
    if stdout is None:
        raise RuntimeError("executor process stdout pipe was not configured")

    def pump_stdout() -> None:
        try:
            for raw_line in stdout:
                output_queue.put(raw_line)
        except (OSError, ValueError):
            pass
        finally:
            _close_stdout_pipe(stdout)
            output_queue.put(None)

    reader = threading.Thread(target=pump_stdout, daemon=True, name=f"{role}-stdout")
    reader.start()
    return _OutputQueue(lines=output_queue, reader=reader)


def _start_stdin_writer_if_needed(
    process: subprocess.Popen[str],
    stdin_text: str | None,
    role: str,
) -> threading.Thread | None:
    if stdin_text is None:
        return None
    return _start_stdin_writer(process, stdin_text, role)


def _start_stdin_writer(process: subprocess.Popen[str], stdin_text: str, role: str) -> threading.Thread:
    def write_stdin() -> None:
        stdin = process.stdin
        if stdin is None:
            return
        try:
            stdin.write(stdin_text)
            stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            return

    writer = threading.Thread(target=write_stdin, daemon=True, name=f"{role}-stdin")
    writer.start()
    return writer


def _close_stdout_pipe(stdout: TextIO | None) -> None:
    if stdout is None or stdout.closed:
        return
    try:
        stdout.close()
    except OSError:
        return


def _next_stream_line(output_queue: _OutputQueue) -> str | None | object:
    try:
        return output_queue.lines.get(timeout=0.2)
    except queue.Empty:
        return _NO_LINE


def _handle_stream_line(raw_line: str, line_handler: Callable[[str], None]) -> str:
    line = raw_line.strip()
    if line:
        line_handler(line)
    return line


def _stream_line_counts_as_idle_progress(raw_line: str, line_handler: Callable[[str], None]) -> bool:
    line = _handle_stream_line(raw_line, line_handler)
    return bool(line and _line_counts_as_idle_progress(line))


def _line_counts_as_idle_progress(line: str) -> bool:
    return not any(marker in line for marker in _IDLE_PROGRESS_NOISE_MARKERS)


def _raise_if_idle_timeout_elapsed(
    *,
    process: subprocess.Popen[str],
    context: ProcessStreamContext,
    idle_timeout_seconds: float,
    last_output_at: float,
    terminate_process: Callable[[subprocess.Popen[str]], None],
) -> None:
    if not idle_timeout_seconds or process.poll() is not None:
        return
    silence_duration = time.monotonic() - last_output_at
    if silence_duration < idle_timeout_seconds:
        return
    terminate_process(process)
    timeout_text = f"{idle_timeout_seconds:g}s"
    raise ProcessStreamIdleTimeoutError(
        f"role={context.role} produced no output for {timeout_text}; treating the role as stalled"
    )
