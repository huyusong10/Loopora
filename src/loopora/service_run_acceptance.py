from __future__ import annotations

from loopora.diagnostics import get_logger, log_exception
from loopora.run_observation_events import TAKEAWAY_PROJECTION_EVENT_TYPES, TIMELINE_EVENT_TYPES
from loopora.run_result_recording import run_result_recording_blocked_reason
from loopora.run_takeaways import build_run_key_takeaways
from loopora.service_run_acceptance_evidence import (
    empty_acceptance_coverage_target_basis,
    empty_run_acceptance_evidence_payload,
    normalize_acceptance_coverage_target_basis,
    recorded_advisory_follow_up_available,
    recorded_verdict_kind_for_task_status,
    run_acceptance_evidence_payload_from_takeaways,
)
from loopora.service_types import LooporaConflictError, TERMINAL_RUN_STATUSES
from loopora.structured_numbers import structured_non_negative_int

logger = get_logger(__name__)

RUN_RESULT_ACCEPTANCE_EVENT_TYPES = {"run_result_accepted", "run_result_acceptance_reopened"}


class ServiceRunAcceptanceMixin:
    def accept_run_result(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(f"cannot accept run result in status {run['status']}")
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else {}
        task_verdict_status = str(task_verdict.get("status") or "")
        blocked_reason = run_result_recording_blocked_reason(run, task_verdict_status=task_verdict_status)
        if blocked_reason:
            raise LooporaConflictError(blocked_reason)
        evidence_source_event_id = self._run_acceptance_evidence_source_event_id(run_id)
        existing_acceptance = self._latest_run_result_acceptance_state_event_for_source(
            run_id,
            evidence_source_event_id=evidence_source_event_id,
            task_verdict_status=task_verdict_status,
        )
        if existing_acceptance.get("event_type") == "run_result_accepted":
            existing_payload = existing_acceptance.get("payload") if isinstance(existing_acceptance.get("payload"), dict) else {}
            recorded_basis = normalize_acceptance_coverage_target_basis(existing_payload.get("coverage_target_basis"))
            return {
                "id": run_id,
                "status": run["status"],
                "task_verdict": task_verdict,
                "event_id": existing_acceptance.get("id"),
                "accepted": True,
                "reused_event": True,
                "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
                "recorded_coverage_target_basis": recorded_basis,
                "recorded_advisory_follow_up_available": recorded_advisory_follow_up_available(
                    task_verdict_status,
                    recorded_basis,
                ),
            }
        acceptance_evidence = self._run_acceptance_evidence_payload(run, evidence_source_event_id=evidence_source_event_id)
        event = self.append_run_event(
            run_id,
            "run_result_accepted",
            {
                "status": run["status"],
                "task_verdict_status": task_verdict_status,
                "task_verdict_source": str(task_verdict.get("source") or ""),
                "task_verdict_summary": str(task_verdict.get("summary") or ""),
                "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
                **acceptance_evidence,
            },
        )
        return {
            "id": run_id,
            "status": run["status"],
            "task_verdict": task_verdict,
            "event_id": event.get("id"),
            "accepted": True,
            "reused_event": False,
            "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
            "recorded_coverage_target_basis": acceptance_evidence["coverage_target_basis"],
            "recorded_advisory_follow_up_available": recorded_advisory_follow_up_available(
                task_verdict_status,
                acceptance_evidence["coverage_target_basis"],
            ),
        }

    def reopen_run_result_acceptance(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(f"cannot reopen recorded run result in status {run['status']}")
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else {}
        task_verdict_status = str(task_verdict.get("status") or "")
        evidence_source_event_id = self._run_acceptance_evidence_source_event_id(run_id)
        latest_state_event = self._latest_run_result_acceptance_state_event_for_source(
            run_id,
            evidence_source_event_id=evidence_source_event_id,
            task_verdict_status=task_verdict_status,
        )
        if latest_state_event.get("event_type") != "run_result_accepted":
            return {
                "id": run_id,
                "status": run["status"],
                "task_verdict": task_verdict,
                "event_id": int(latest_state_event.get("id") or 0),
                "accepted": False,
                "reused_event": True,
                "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
                "recorded_coverage_target_basis": empty_acceptance_coverage_target_basis(),
                "recorded_advisory_follow_up_available": False,
            }
        event = self.append_run_event(
            run_id,
            "run_result_acceptance_reopened",
            {
                "status": run["status"],
                "task_verdict_status": task_verdict_status,
                "task_verdict_source": str(task_verdict.get("source") or ""),
                "task_verdict_summary": str(task_verdict.get("summary") or ""),
                "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
                "evidence_source_event_id": evidence_source_event_id,
                "recorded_event_id": structured_non_negative_int(latest_state_event.get("id")),
            },
        )
        return {
            "id": run_id,
            "status": run["status"],
            "task_verdict": task_verdict,
            "event_id": event.get("id"),
            "accepted": False,
            "reused_event": False,
            "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
            "recorded_coverage_target_basis": empty_acceptance_coverage_target_basis(),
            "recorded_advisory_follow_up_available": False,
        }

    def run_result_acceptance_state(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATUSES:
            return {
                "accepted": False,
                "event_id": 0,
                "evidence_source_event_id": 0,
                "task_verdict_status": "",
                "recordable": False,
                "recording_blocked_reason": "",
                "recorded_coverage_target_basis": empty_acceptance_coverage_target_basis(),
                "recorded_advisory_follow_up_available": False,
            }
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else {}
        task_verdict_status = str(task_verdict.get("status") or "")
        evidence_source_event_id = self._run_acceptance_evidence_source_event_id(run_id)
        state_event = self._latest_run_result_acceptance_state_event_for_source(
            run_id,
            evidence_source_event_id=evidence_source_event_id,
            task_verdict_status=task_verdict_status,
        )
        accepted = state_event.get("event_type") == "run_result_accepted"
        state_payload = state_event.get("payload") if isinstance(state_event.get("payload"), dict) else {}
        recorded_basis = normalize_acceptance_coverage_target_basis(
            state_payload.get("coverage_target_basis") if accepted else {}
        )
        blocked_reason = run_result_recording_blocked_reason(run, task_verdict_status=task_verdict_status)
        return {
            "accepted": accepted,
            "event_id": int((state_event or {}).get("id") or 0),
            "evidence_source_event_id": evidence_source_event_id,
            "task_verdict_status": task_verdict_status,
            "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
            "state_event_type": str((state_event or {}).get("event_type") or ""),
            "recordable": not blocked_reason,
            "recording_blocked_reason": blocked_reason,
            "recorded_coverage_target_basis": recorded_basis,
            "recorded_advisory_follow_up_available": recorded_advisory_follow_up_available(
                task_verdict_status,
                recorded_basis,
            ),
        }

    def _run_acceptance_evidence_source_event_id(self, run_id: str) -> int:
        return (
            self.repository.latest_event_id_for_types(run_id, TAKEAWAY_PROJECTION_EVENT_TYPES)
            or self.repository.latest_event_id_for_types(run_id, TIMELINE_EVENT_TYPES - RUN_RESULT_ACCEPTANCE_EVENT_TYPES)
            or self._latest_non_acceptance_event_id(run_id)
        )

    def _latest_non_acceptance_event_id(self, run_id: str) -> int:
        for event in reversed(self.repository.list_recent_events(run_id, limit=100)):
            if event.get("event_type") not in RUN_RESULT_ACCEPTANCE_EVENT_TYPES:
                return structured_non_negative_int(event.get("id"))
        return 0

    def _latest_run_result_acceptance_state_event_for_source(
        self,
        run_id: str,
        *,
        evidence_source_event_id: int,
        task_verdict_status: str,
    ) -> dict:
        for event in reversed(self.repository.list_recent_events(run_id, event_types=RUN_RESULT_ACCEPTANCE_EVENT_TYPES, limit=20)):
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            if structured_non_negative_int(payload.get("evidence_source_event_id")) != evidence_source_event_id:
                continue
            if str(payload.get("task_verdict_status") or "") != task_verdict_status:
                continue
            return event
        return {}

    def _run_acceptance_evidence_payload(self, run: dict, *, evidence_source_event_id: int) -> dict:
        try:
            takeaways = build_run_key_takeaways(self._hydrate_run_files(run))
        except Exception as exc:  # noqa: BLE001 - acceptance must still record the user action if artifacts are damaged.
            log_exception(
                logger,
                "service.run.acceptance_evidence_payload_failed",
                "Failed to build run acceptance evidence payload",
                error=exc,
                **self._run_log_context(run),
            )
            return empty_run_acceptance_evidence_payload(
                evidence_source_event_id=evidence_source_event_id,
                evidence_available=False,
            )
        return run_acceptance_evidence_payload_from_takeaways(takeaways, evidence_source_event_id=evidence_source_event_id)
