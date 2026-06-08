from __future__ import annotations

import signal
import subprocess
import time

from loopora.executor_command_events import build_command_event_payload
from loopora.executor_process_stream import (
    ProcessStreamCallbacks,
    ProcessStreamContext,
    ProcessStreamIdleTimeoutError,
    ProcessStreamStoppedError,
    stream_process,
)
from loopora.executor_types import ExecutionStopped, ExecutorError, ExecutorProcessRequest


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
