from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.event_redaction import redact_alignment_event_payload
from loopora.executor_types import ExecutorError, RoleRequest
from loopora.service_alignment_artifacts import (
    alignment_session_root,
    finalize_alignment_invocation_files,
    write_alignment_invocation_input_files,
)
from loopora.service_alignment_language import alignment_generation_prefers_chinese
from loopora.service_alignment_execution import (
    alignment_executor_role_request,
    alignment_executor_session_ref_event_payload,
    alignment_executor_session_ref_from_output,
    alignment_native_resume_fallback_event_payload,
    alignment_request_can_native_resume_fallback,
    apply_alignment_native_resume_fallback,
)


class AlignmentInvocationRepository(Protocol):
    def get_alignment_session(self, session_id: str) -> dict | None: ...

    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...

    def alignment_should_stop(self, session_id: str) -> bool: ...


class AlignmentPromptBuilder(Protocol):
    def __call__(
        self,
        session: dict,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> str: ...


class AlignmentNextInvocationDir(Protocol):
    def __call__(self, root: Path, attempt: int, *, repair: bool) -> Path: ...


class AlignmentRepairAttempts(Protocol):
    def __call__(self, session: dict | None, *, invalid_default: int = 0) -> int: ...


class AlignmentExecutor(Protocol):
    def execute(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], dict],
        should_stop: Callable[[], bool],
        update_child_pid: Callable[[int | None], dict],
    ) -> dict: ...


@dataclass(frozen=True)
class AlignmentExecutorInvocationConfig:
    output_schema: dict
    idle_timeout_seconds: float | None
    executor_factory: Callable[[], AlignmentExecutor]
    build_prompt: AlignmentPromptBuilder
    ensure_artifact_dirs: Callable[[Path], None]
    next_invocation_dir: AlignmentNextInvocationDir
    repair_attempts: AlignmentRepairAttempts


@dataclass(frozen=True)
class AlignmentExecutorInvocationContext:
    repository: AlignmentInvocationRepository
    session_id: str
    session: dict
    config: AlignmentExecutorInvocationConfig


@dataclass(frozen=True)
class AlignmentExecutorRunContext:
    repository: AlignmentInvocationRepository
    get_session: Callable[[str], dict]
    config: AlignmentExecutorInvocationConfig


def run_alignment_executor(
    context: AlignmentExecutorRunContext,
    session_id: str,
    *,
    mode: str,
    validation_error: str = "",
    invalid_yaml: str = "",
) -> dict:
    session = context.get_session(session_id)
    return run_alignment_executor_invocation(
        AlignmentExecutorInvocationContext(
            repository=context.repository,
            session_id=session_id,
            session=session,
            config=context.config,
        ),
        mode=mode,
        validation_error=validation_error,
        invalid_yaml=invalid_yaml,
    )


def run_alignment_executor_invocation(
    context: AlignmentExecutorInvocationContext,
    *,
    mode: str,
    validation_error: str = "",
    invalid_yaml: str = "",
) -> dict:
    repository = context.repository
    session_id = context.session_id
    session = context.session
    config = context.config
    root = alignment_session_root(session)
    config.ensure_artifact_dirs(root)
    attempt = config.repair_attempts(session)
    invocation_dir = config.next_invocation_dir(root, attempt, repair=mode == "repair")
    invocation_dir.mkdir(parents=True, exist_ok=True)
    prompt = config.build_prompt(
        session,
        mode=mode,
        validation_error=validation_error,
        invalid_yaml=invalid_yaml,
    )
    write_alignment_invocation_input_files(
        invocation_dir,
        prompt=prompt,
        output_schema=config.output_schema,
    )
    request = alignment_executor_role_request(
        session_id,
        session,
        mode=mode,
        prompt=prompt,
        invocation_dir=invocation_dir,
        output_schema=config.output_schema,
        idle_timeout_seconds=config.idle_timeout_seconds,
        validation_error=validation_error,
        prefers_chinese=alignment_generation_prefers_chinese(session),
    )
    executor = config.executor_factory()
    output = execute_alignment_request_with_resume_fallback(repository, session_id, executor, request)
    finalize_alignment_invocation_files(invocation_dir, output, Path(session["bundle_path"]))
    persist_alignment_executor_session_ref(repository, session_id, request, output)
    return output


def execute_alignment_request_with_resume_fallback(
    repository: AlignmentInvocationRepository,
    session_id: str,
    executor: AlignmentExecutor,
    request: RoleRequest,
) -> dict:
    try:
        return execute_alignment_request(repository, session_id, executor, request)
    except ExecutorError:
        if not alignment_request_can_native_resume_fallback(request):
            raise
        repository.append_alignment_event(
            session_id,
            "alignment_native_resume_fallback",
            alignment_native_resume_fallback_event_payload(request),
        )
        apply_alignment_native_resume_fallback(request)
        return execute_alignment_request(repository, session_id, executor, request)


def execute_alignment_request(
    repository: AlignmentInvocationRepository,
    session_id: str,
    executor: AlignmentExecutor,
    request: RoleRequest,
) -> dict:
    invocation_id = str(request.extra_context.get("invocation_id", "") or "")
    stdout_path = request.run_dir / "stdout.log"

    def emit_alignment_event(event_type: str, payload: dict) -> dict:
        sanitized = sanitize_alignment_invocation_event_payload(event_type, payload, invocation_id=invocation_id)
        if event_type == "codex_event":
            message = str(sanitized.get("message", "") or "").strip()
            if message:
                with stdout_path.open("a", encoding="utf-8") as handle:
                    handle.write(message + "\n")
        session = repository.get_alignment_session(session_id) or {}
        return repository.append_alignment_event(
            session_id,
            event_type,
            {
                **sanitized,
                "alignment_status": session.get("status", ""),
            },
        )

    return executor.execute(
        request,
        emit_alignment_event,
        lambda: repository.alignment_should_stop(session_id),
        lambda pid: set_alignment_active_child_pid(repository, session_id, pid),
    )


def persist_alignment_executor_session_ref(
    repository: AlignmentInvocationRepository,
    session_id: str,
    request: RoleRequest,
    output: dict,
) -> None:
    session_ref = alignment_executor_session_ref_from_output(request, output)
    if not session_ref:
        return
    repository.update_alignment_session(session_id, executor_session_ref=session_ref)
    repository.append_alignment_event(
        session_id,
        "alignment_executor_session_ref",
        alignment_executor_session_ref_event_payload(request, session_ref),
    )


def set_alignment_active_child_pid(
    repository: AlignmentInvocationRepository,
    session_id: str,
    pid: int | None,
) -> dict:
    if pid is not None:
        return repository.update_alignment_session(session_id, active_child_pid=pid)
    return repository.update_alignment_session(session_id, clear_active_child_pid=True)


def sanitize_alignment_invocation_event_payload(event_type: str, payload: dict, *, invocation_id: str = "") -> dict:
    sanitized = redact_alignment_event_payload(event_type, payload)
    if invocation_id:
        sanitized.setdefault("invocation_id", invocation_id)
    return sanitized
