from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loopora.executor_types import RoleRequest


ALIGNMENT_NATIVE_RESUME_FALLBACK_EXECUTORS = frozenset({"codex", "claude", "opencode"})
AlignmentExecutorOutputAction = Literal["bundle", "waiting_user", "failed"]
AlignmentBundleCandidateAction = Literal["ready", "repair", "failed"]
AlignmentSessionTransitionAction = Literal["waiting_user", "ready", "repair"]


@dataclass(frozen=True)
class AlignmentExecutionState:
    mode: str = "normal"
    validation_error: str = ""
    invalid_yaml: str = ""


@dataclass(frozen=True)
class AlignmentBundleCandidateOutcome:
    action: AlignmentBundleCandidateAction
    error: str = ""
    next_state: AlignmentExecutionState | None = None
    next_repair_attempts: int = 0


@dataclass(frozen=True)
class AlignmentSessionTransitionPlan:
    action: AlignmentSessionTransitionAction
    update_fields: dict[str, object]
    event_type: str
    event_payload: dict[str, object]
    finish_session: bool = False
    clear_active_child_pid: bool = False


def alignment_bundle_executor_settings_issues(session: dict, bundle: dict) -> list[str]:
    expected_kind = str(session.get("executor_kind", "") or "").strip()
    expected_mode = str(session.get("executor_mode", "") or "").strip()
    if expected_kind != "custom" and expected_mode != "command":
        return []
    expected = {
        "executor_kind": expected_kind,
        "executor_mode": expected_mode,
        "command_cli": str(session.get("command_cli", "") or ""),
        "command_args_text": str(session.get("command_args_text", "") or ""),
        "model": str(session.get("model", "") or "").strip(),
        "reasoning_effort": str(session.get("reasoning_effort", "") or "").strip(),
    }
    mismatches: list[str] = []
    runtime_surfaces: list[tuple[str, dict]] = []
    if isinstance(bundle.get("loop"), dict):
        runtime_surfaces.append(("loop", bundle["loop"]))
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        role_key = str(role.get("key", "") or "role")
        runtime_surfaces.append((f"role_definition {role_key}", role))
    for surface_name, surface in runtime_surfaces:
        for field_name, expected_value in expected.items():
            actual_value = str(surface.get(field_name, "") or "")
            if field_name in {"model", "reasoning_effort"}:
                actual_value = actual_value.strip()
            if actual_value != expected_value:
                mismatches.append(f"{surface_name}.{field_name}")
    if not mismatches:
        return []
    return ["alignment bundle must preserve selected Web executor settings for command/custom sessions: " + ", ".join(mismatches[:8])]


def alignment_bundle_candidate_outcome(
    *,
    ok: bool,
    error: str,
    repair_attempts: int,
    bundle_yaml: str,
) -> AlignmentBundleCandidateOutcome:
    if ok:
        return AlignmentBundleCandidateOutcome(action="ready")
    if repair_attempts >= 1:
        return AlignmentBundleCandidateOutcome(action="failed", error=error)
    return AlignmentBundleCandidateOutcome(
        action="repair",
        error=error,
        next_state=AlignmentExecutionState(
            mode="repair",
            validation_error=error,
            invalid_yaml=bundle_yaml,
        ),
        next_repair_attempts=repair_attempts + 1,
    )


def alignment_waiting_user_transition_plan() -> AlignmentSessionTransitionPlan:
    return AlignmentSessionTransitionPlan(
        action="waiting_user",
        update_fields={"status": "waiting_user", "error_message": ""},
        event_type="alignment_waiting_user",
        event_payload={"status": "waiting_user"},
        finish_session=True,
        clear_active_child_pid=True,
    )


def alignment_bundle_ready_transition_plan(*, bundle_path: str) -> AlignmentSessionTransitionPlan:
    return AlignmentSessionTransitionPlan(
        action="ready",
        update_fields={"status": "ready", "alignment_stage": "ready", "error_message": ""},
        event_type="alignment_ready",
        event_payload={"status": "ready", "bundle_path": bundle_path},
        finish_session=True,
        clear_active_child_pid=True,
    )


def alignment_bundle_repair_transition_plan(outcome: AlignmentBundleCandidateOutcome) -> AlignmentSessionTransitionPlan:
    return AlignmentSessionTransitionPlan(
        action="repair",
        update_fields={
            "status": "repairing",
            "repair_attempts": outcome.next_repair_attempts,
            "error_message": outcome.error,
        },
        event_type="alignment_repair_started",
        event_payload={"status": "repairing", "error": outcome.error},
    )


def alignment_executor_session_ref(session: dict) -> dict:
    value = session.get("executor_session_ref") if isinstance(session.get("executor_session_ref"), dict) else {}
    return dict(value)


def alignment_resume_session_id(session_ref: dict) -> str:
    return str((session_ref or {}).get("session_id", "") or "").strip()


def alignment_native_resume_id_for_request(session: dict, session_ref: dict) -> str:
    executor_kind = str(session.get("executor_kind", "codex") or "codex").strip().lower()
    executor_mode = str(session.get("executor_mode", "preset") or "preset").strip().lower()
    if executor_kind == "codex" and executor_mode != "command":
        return ""
    return alignment_resume_session_id(session_ref)


def alignment_executor_role_request(  # noqa: PLR0913 - executor request construction exposes the full runtime boundary.
    session_id: str,
    session: dict,
    *,
    mode: str,
    prompt: str,
    invocation_dir: Path,
    output_schema: dict,
    idle_timeout_seconds: float | None,
    validation_error: str = "",
    prefers_chinese: bool = False,
    display_language: str = "",
) -> RoleRequest:
    executor_session_ref = alignment_executor_session_ref(session)
    resume_session_id = alignment_native_resume_id_for_request(session, executor_session_ref)
    return RoleRequest(
        run_id=f"alignment:{session_id}",
        role="alignment",
        role_archetype="alignment",
        role_name="Bundle Alignment",
        prompt=prompt,
        workdir=Path(session["workdir"]),
        model=str(session.get("model", "") or ""),
        reasoning_effort=str(session.get("reasoning_effort", "") or ""),
        output_schema=output_schema,
        output_path=invocation_dir / "output.json",
        run_dir=invocation_dir,
        executor_kind=session.get("executor_kind", "codex"),
        executor_mode=session.get("executor_mode", "preset"),
        command_cli=session.get("command_cli", ""),
        command_args_text=session.get("command_args_text", ""),
        inherit_session=True,
        resume_session_id=resume_session_id,
        sandbox="read-only",
        idle_timeout_seconds=idle_timeout_seconds,
        extra_context={
            "target_workdir": session["workdir"],
            "alignment_session_id": session_id,
            "alignment_mode": mode,
            "alignment_stage": session.get("alignment_stage", "clarifying"),
            "working_agreement": session.get("working_agreement") or {},
            "validation_error": validation_error,
            "session_ref": executor_session_ref,
            "invocation_id": invocation_dir.name,
            "prefers_chinese": prefers_chinese,
            "display_language": display_language,
        },
    )


def alignment_request_can_native_resume_fallback(request: RoleRequest) -> bool:
    return bool(request.resume_session_id.strip()) and request.executor_kind in ALIGNMENT_NATIVE_RESUME_FALLBACK_EXECUTORS


def apply_alignment_native_resume_fallback(request: RoleRequest) -> None:
    request.inherit_session = False
    request.resume_session_id = ""
    request.extra_context["session_ref"] = {}


def alignment_native_resume_fallback_event_payload(request: RoleRequest) -> dict[str, object]:
    return {
        "executor_kind": request.executor_kind,
        "resume_session_id": request.resume_session_id,
        "message": "Native CLI session resume failed; retrying with Loopora transcript context.",
    }


def alignment_executor_session_ref_from_output(request: RoleRequest, output: dict) -> dict:
    current = request.extra_context.get("session_ref")
    session_ref = dict(current) if isinstance(current, dict) else {}
    output_ref = output.get("session_ref") if isinstance(output, dict) else None
    if isinstance(output_ref, dict):
        session_ref.update({str(key): str(value) for key, value in output_ref.items() if str(value).strip()})
    return session_ref


def alignment_executor_session_ref_event_payload(request: RoleRequest, session_ref: dict) -> dict[str, object]:
    return {
        "executor_kind": request.executor_kind,
        "session_ref": session_ref,
        "native_resume_available": bool(session_ref.get("session_id")),
    }


def alignment_executor_output_action(
    output: dict,
    *,
    assistant_message: str,
    bundle_yaml: str,
) -> AlignmentExecutorOutputAction:
    if bundle_yaml:
        return "bundle"
    if alignment_executor_output_waits_for_user(output, assistant_message=assistant_message):
        return "waiting_user"
    return "failed"


def alignment_executor_output_waits_for_user(output: dict, *, assistant_message: str) -> bool:
    if output.get("needs_user_input") is True:
        return True
    if not assistant_message.strip():
        return False
    status = str(output.get("status", "") or "").strip().lower()
    phase = str(output.get("alignment_phase", "") or "").strip().lower()
    return status == "blocked" or phase == "blocked"


def alignment_executor_output_failure_message(assistant_message: str) -> str:
    return assistant_message or "Agent finished without a bundle or a clarifying question."
