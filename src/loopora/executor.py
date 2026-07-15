from __future__ import annotations

from loopora.executor_command_args import (
    COMMAND_PLACEHOLDERS,
    COMMAND_PLACEHOLDER_PATTERN,
    build_claude_exec_args,
    build_codex_exec_args,
    build_custom_exec_args,
    build_opencode_exec_args,
    coerce_reasoning_effort,
    normalize_reasoning_effort,
    parse_command_args_text,
    parse_extra_cli_args_text,
    validate_command_args_text,
    validate_extra_cli_args_text,
)
from loopora.executor_command_args import COMMAND_EVENT_PREVIEW_LIMIT, build_command_event_payload
from loopora.executor_real import RealCodexExecutor
from loopora.executor_command_args import EXECUTOR_OUTPUT_MAX_BYTES, read_executor_output_text
from loopora.executor_types import (
    CodexExecutor,
    ExecutionStopped,
    ExecutorError,
    ExecutorProcessRequest,
    RoleRequest,
)

import os

from loopora.branding import FAKE_DELAY_ENV, FAKE_EXECUTOR_ENV




import json

import time

from collections.abc import Callable

from loopora.executor_fake_payloads import (
    FakePayloadError,
    alignment_agreement_response,
    alignment_bundle_yaml,
    alignment_bundle_yaml_without_semantics,
    alignment_readiness_evidence,
    build_alignment_payload,
    build_fake_payload,
)


from loopora.utils import utc_now

class FakeCodexExecutor(CodexExecutor):
    def __init__(self, scenario: str = "success", role_delay: float = 0.0) -> None:
        self.scenario = scenario
        self.role_delay = role_delay

    def execute(
        self,
        request: RoleRequest,
        emit_event: Callable[[str, dict], None],
        should_stop: Callable[[], bool],
        set_child_pid: Callable[[int | None], None],
    ) -> dict:
        set_child_pid(None)
        try:
            emit_event("codex_event", {"type": "fake_start", "role": request.role, "scenario": self.scenario})
            if self.role_delay:
                deadline = time.time() + self.role_delay
                while time.time() < deadline:
                    if should_stop():
                        raise ExecutionStopped(f"run {request.run_id} stopped while {request.role} was running")
                    time.sleep(0.05)
            payload = self._build_payload(request)
            if request.inherit_session:
                current = request.extra_context.get("session_ref")
                session_ref = dict(current) if isinstance(current, dict) else {}
                session_ref.setdefault("session_id", request.resume_session_id or f"fake-{request.run_id}-{request.role}")
                request.extra_context["session_ref"] = session_ref
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            emit_event("codex_event", {"type": "fake_complete", "role": request.role, "at": utc_now()})
            return payload
        finally:
            set_child_pid(None)

    def _build_payload(self, request: RoleRequest) -> dict:
        try:
            return build_fake_payload(self.scenario, request)
        except FakePayloadError as exc:
            raise ExecutorError(str(exc)) from exc

    def _build_alignment_payload(self, request: RoleRequest) -> dict:
        try:
            return build_alignment_payload(self.scenario, request)
        except FakePayloadError as exc:
            raise ExecutorError(str(exc)) from exc

    @staticmethod
    def _alignment_agreement_response() -> dict:
        return alignment_agreement_response()

    @staticmethod
    def _alignment_readiness_evidence(*, open_questions: str = "") -> dict:
        return alignment_readiness_evidence(open_questions=open_questions)

    @staticmethod
    def _alignment_bundle_yaml(workdir: str) -> str:
        return alignment_bundle_yaml(workdir)

    @staticmethod
    def _alignment_bundle_yaml_without_semantics(workdir: str) -> str:
        return alignment_bundle_yaml_without_semantics(workdir)

def executor_from_environment() -> CodexExecutor:
    scenario = os.environ.get(FAKE_EXECUTOR_ENV, "").strip()
    if scenario:
        delay = float(os.environ.get(FAKE_DELAY_ENV, "0").strip())
        return FakeCodexExecutor(scenario=scenario, role_delay=delay)
    return RealCodexExecutor()


__all__ = (
    "COMMAND_EVENT_PREVIEW_LIMIT",
    "COMMAND_PLACEHOLDERS",
    "COMMAND_PLACEHOLDER_PATTERN",
    "EXECUTOR_OUTPUT_MAX_BYTES",
    "CodexExecutor",
    "ExecutionStopped",
    "ExecutorError",
    "ExecutorProcessRequest",
    "FakeCodexExecutor",
    "RealCodexExecutor",
    "RoleRequest",
    "build_claude_exec_args",
    "build_codex_exec_args",
    "build_command_event_payload",
    "build_custom_exec_args",
    "build_opencode_exec_args",
    "coerce_reasoning_effort",
    "executor_from_environment",
    "normalize_reasoning_effort",
    "parse_command_args_text",
    "parse_extra_cli_args_text",
    "read_executor_output_text",
    "validate_command_args_text",
    "validate_extra_cli_args_text",
)
