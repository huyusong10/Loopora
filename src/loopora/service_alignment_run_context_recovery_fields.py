from __future__ import annotations

from loopora.event_redaction import redact_sensitive_value
from loopora.run_projection_fields import task_verdict_from_run
from loopora.system_prompt_assets import load_system_prompt_asset


AGENT_CONTEXT_BINDING_RECOVERY_KEYS = {
    "path",
    "alignment_session_id",
    "alignment_status",
    "linked_run_id",
    "linked_loop_id",
    "linked_bundle_id",
    "workdir",
    "host_context_id",
    "context_source",
    "updated_at",
    "requires_web_alignment",
    "requires_candidate_repair",
    "loopora_fit_contradiction",
    "preview_path",
    "run_path",
}

RECOVERABLE_CONTEXT_REPAIR_NEXT_STEP = load_system_prompt_asset(
    "agent_native/recoverable-context-repair-next-step.md"
).strip()


def agent_exact_binding_recovery_action(choice: dict) -> str:
    if choice.get("linked_run_id"):
        return "resume_run"
    if choice.get("alignment_status") in {"ready", "imported"}:
        return "start_ready_preview"
    return "blocked"


def agent_failed_preview_choice_repair_fields(
    session: dict,
    *,
    payload: dict | None = None,
    failed_payload: dict | None = None,
) -> dict:
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    failed_payload = failed_payload if isinstance(failed_payload, dict) else {}
    validation_error = str(
        validation.get("error") or session.get("error_message") or failed_payload.get("error") or ""
    ).strip()
    source_path = str((payload or {}).get("source_path") or "").strip()
    preview_plan_copy = str(
        session.get("bundle_path") or validation.get("bundle_path") or failed_payload.get("bundle_path") or ""
    ).strip()
    summary = {
        "validation_error": validation_error,
        "plan_file_to_repair": source_path or preview_plan_copy,
        "preview_plan_copy": preview_plan_copy,
        "next_repair_step": RECOVERABLE_CONTEXT_REPAIR_NEXT_STEP,
    }
    return {key: value for key, value in summary.items() if value not in ("", [], {})}


def agent_redacted_context_binding(binding: dict) -> dict:
    return {
        key: redact_sensitive_value(key, value)
        for key, value in binding.items()
        if key in AGENT_CONTEXT_BINDING_RECOVERY_KEYS
    }


def agent_run_context_task_verdict(run: dict) -> dict:
    return task_verdict_from_run(run)
