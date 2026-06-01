from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


class ExecutorError(RuntimeError):
    """Raised when a role execution fails."""


class ExecutionStopped(BaseException):
    """Raised when a run is interrupted by the user."""


@dataclass(slots=True)
class RoleRequest:
    run_id: str
    role: str
    prompt: str
    workdir: Path
    model: str
    reasoning_effort: str
    output_schema: dict
    output_path: Path
    run_dir: Path
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    command_cli: str = ""
    command_args_text: str = ""
    inherit_session: bool = False
    resume_session_id: str = ""
    extra_cli_args_text: str = ""
    sandbox: str = "workspace-write"
    idle_timeout_seconds: float | None = None
    role_archetype: str = ""
    role_name: str = ""
    step_id: str = ""
    extra_context: dict = field(default_factory=dict)


class CodexExecutor:
    def execute(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ExecutorProcessRequest:
    request: RoleRequest
    args: list[str]
    emit_event: Callable[[str, dict], None]
    should_stop: Callable[[], bool]
    set_child_pid: Callable[[int | None], None]
    line_handler: Callable[[str], None]
