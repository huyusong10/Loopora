from __future__ import annotations

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
from loopora.executor_types import CodexExecutor, ExecutionStopped, ExecutorError, RoleRequest
from loopora.utils import utc_now


class FakeCodexExecutor(CodexExecutor):
    def __init__(
        self,
        scenario: str = "success",
        role_delay: float = 0.0,
        display_language: str = "en",
    ) -> None:
        self.scenario = scenario
        self.role_delay = role_delay
        self.display_language = "zh" if str(display_language or "").strip().lower() == "zh" else "en"

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
                deadline = time.monotonic() + self.role_delay
                while time.monotonic() < deadline:
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
            return build_fake_payload(self.scenario, request, display_language=self.display_language)
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
