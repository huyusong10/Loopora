from __future__ import annotations

from loopora.diagnostics import get_logger, log_exception
from loopora.run_observation_events import TAKEAWAY_PROJECTION_EVENT_TYPES, TIMELINE_EVENT_TYPES
from loopora.run_takeaways import build_run_key_takeaways
from loopora.service_types import LooporaConflictError, TERMINAL_RUN_STATUSES
from loopora.utils import structured_non_negative_int

from loopora.run_takeaway_judgment import empty_judgment_contract


ACCEPTANCE_EVIDENCE_BUCKETS = ("proven", "weak", "unproven", "blocking", "residual_risk")

def recorded_verdict_kind_for_task_status(task_verdict_status: object) -> str:
    status = str(task_verdict_status or "").strip().lower()
    return {
        "passed": "passed_verdict_recorded",
        "passed_with_residual_risk": "passed_with_residual_risk_recorded",
        "insufficient_evidence": "unproven_verdict_recorded",
        "failed": "failed_verdict_recorded",
        "not_evaluated": "not_evaluated_verdict_recorded",
    }.get(status, "evidence_verdict_recorded")

def run_acceptance_evidence_payload_from_takeaways(takeaways: dict, *, evidence_source_event_id: int) -> dict:
    evidence_coverage = takeaways.get("evidence_coverage") if isinstance(takeaways.get("evidence_coverage"), dict) else {}
    evidence_manifest = takeaways.get("evidence_manifest") if isinstance(takeaways.get("evidence_manifest"), dict) else {}
    judgment_contract = takeaways.get("judgment_contract") if isinstance(takeaways.get("judgment_contract"), dict) else empty_judgment_contract()
    source_bundle = judgment_contract.get("source_bundle") if isinstance(judgment_contract.get("source_bundle"), dict) else {}
    buckets = takeaways.get("evidence_buckets") if isinstance(takeaways.get("evidence_buckets"), dict) else {}
    bucket_counts = dict.fromkeys(ACCEPTANCE_EVIDENCE_BUCKETS, 0)
    bucket_counts.update({bucket: len(items) for bucket, items in buckets.items() if isinstance(bucket, str) and isinstance(items, list)})
    return {
        "evidence_source_event_id": structured_non_negative_int(evidence_source_event_id),
        "evidence_available": True,
        "judgment_contract": dict(judgment_contract),
        "source_bundle": dict(source_bundle),
        "run_contract_path": _acceptance_text(judgment_contract.get("contract_path")),
        "judgment_contract_summary": _acceptance_judgment_summary(judgment_contract),
        "check_mode": _acceptance_text(judgment_contract.get("check_mode")),
        "check_count": structured_non_negative_int(judgment_contract.get("check_count")),
        "completion_mode": _acceptance_text(judgment_contract.get("completion_mode")),
        "strategy_preset": _acceptance_text(judgment_contract.get("strategy_preset")),
        "coverage_targets": _acceptance_coverage_targets(judgment_contract),
        "loop_fit_reasons": _acceptance_string_list(judgment_contract, "loop_fit_reasons"),
        "execution_strategy": _acceptance_string_list(judgment_contract, "execution_strategy"),
        "local_governance": _acceptance_string_list(judgment_contract, "local_governance"),
        "role_postures": _acceptance_string_list(judgment_contract, "role_postures", limit=6),
        "judgment_tradeoffs": _acceptance_string_list(judgment_contract, "judgment_tradeoffs"),
        "success_surface": _acceptance_string_list(judgment_contract, "success_surface"),
        "fake_done_states": _acceptance_string_list(judgment_contract, "fake_done_states"),
        "evidence_preferences": _acceptance_string_list(judgment_contract, "evidence_preferences"),
        "residual_risk": _acceptance_text(judgment_contract.get("residual_risk"), limit=600),
        "task_verdict_path": str(takeaways.get("task_verdict_path") or ""),
        "coverage_path": str(evidence_coverage.get("coverage_path") or ""),
        "coverage_status": str(evidence_coverage.get("status") or ""),
        "manifest_path": str(evidence_manifest.get("manifest_path") or ""),
        "evidence_count": structured_non_negative_int(takeaways.get("evidence_count")),
        "evidence_bucket_counts": bucket_counts,
    }

def empty_run_acceptance_evidence_payload(*, evidence_source_event_id: int, evidence_available: bool) -> dict:
    return {
        "evidence_source_event_id": structured_non_negative_int(evidence_source_event_id),
        "evidence_available": evidence_available,
        "evidence_error": "acceptance_evidence_unavailable",
        "judgment_contract": empty_judgment_contract(),
        "source_bundle": {},
        "run_contract_path": "",
        "judgment_contract_summary": "",
        "check_mode": "",
        "check_count": 0,
        "completion_mode": "",
        "strategy_preset": "",
        "coverage_targets": [],
        "loop_fit_reasons": [],
        "execution_strategy": [],
        "local_governance": [],
        "role_postures": [],
        "judgment_tradeoffs": [],
        "success_surface": [],
        "fake_done_states": [],
        "evidence_preferences": [],
        "residual_risk": "",
        "task_verdict_path": "",
        "coverage_path": "",
        "coverage_status": "",
        "manifest_path": "",
        "evidence_count": 0,
        "evidence_bucket_counts": dict.fromkeys(ACCEPTANCE_EVIDENCE_BUCKETS, 0),
    }

def _acceptance_text(value: object, *, limit: int | None = None) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if limit is not None:
        return text[:limit]
    return text

def _acceptance_string_list(judgment_contract: dict, field: str, *, limit: int = 4) -> list[str]:
    values = judgment_contract.get(field)
    if not isinstance(values, list):
        return []
    items = [value.strip() for value in values if isinstance(value, str) and value.strip()]
    return items[:limit]

def _acceptance_coverage_targets(judgment_contract: dict, *, limit: int = 40) -> list[dict]:
    values = judgment_contract.get("coverage_targets")
    if not isinstance(values, list):
        return []
    return [dict(value) for value in values if isinstance(value, dict)][:limit]

def _acceptance_judgment_summary(judgment_contract: dict) -> str:
    for field in (
        "collaboration_summary",
        "goal",
        "strategy_collaboration_intent",
        "residual_risk",
    ):
        value = _acceptance_text(judgment_contract.get(field), limit=240)
        if value:
            return value
    for field in (
        "loop_fit_reasons",
        "execution_strategy",
        "local_governance",
        "role_postures",
        "judgment_tradeoffs",
        "success_surface",
        "fake_done_states",
        "evidence_preferences",
    ):
        values = _acceptance_string_list(judgment_contract, field, limit=1)
        if values:
            return values[0][:240]
    return ""

logger = get_logger(__name__)


class ServiceRunAcceptanceMixin:
    def accept_run_result(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATUSES:
            raise LooporaConflictError(f"cannot accept run result in status {run['status']}")
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else {}
        evidence_source_event_id = self._run_acceptance_evidence_source_event_id(run_id)
        task_verdict_status = str(task_verdict.get("status") or "")
        existing_acceptance = self._latest_run_result_acceptance_for_source(
            run_id,
            evidence_source_event_id=evidence_source_event_id,
            task_verdict_status=task_verdict_status,
        )
        if existing_acceptance:
            return {
                "id": run_id,
                "status": run["status"],
                "task_verdict": task_verdict,
                "event_id": existing_acceptance.get("id"),
                "accepted": True,
                "reused_event": True,
                "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
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
        }

    def run_result_acceptance_state(self, run_id: str) -> dict:
        run = self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATUSES:
            return {"accepted": False, "event_id": 0, "evidence_source_event_id": 0, "task_verdict_status": ""}
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else {}
        task_verdict_status = str(task_verdict.get("status") or "")
        evidence_source_event_id = self._run_acceptance_evidence_source_event_id(run_id)
        accepted_event = self._latest_run_result_acceptance_for_source(
            run_id,
            evidence_source_event_id=evidence_source_event_id,
            task_verdict_status=task_verdict_status,
        )
        return {
            "accepted": bool(accepted_event),
            "event_id": int((accepted_event or {}).get("id") or 0),
            "evidence_source_event_id": evidence_source_event_id,
            "task_verdict_status": task_verdict_status,
            "recorded_verdict_kind": recorded_verdict_kind_for_task_status(task_verdict_status),
        }

    def _run_acceptance_evidence_source_event_id(self, run_id: str) -> int:
        return (
            self.repository.latest_event_id_for_types(run_id, TAKEAWAY_PROJECTION_EVENT_TYPES)
            or self.repository.latest_event_id_for_types(run_id, TIMELINE_EVENT_TYPES - {"run_result_accepted"})
            or self._latest_non_acceptance_event_id(run_id)
        )

    def _latest_non_acceptance_event_id(self, run_id: str) -> int:
        for event in reversed(self.repository.list_recent_events(run_id, limit=100)):
            if event.get("event_type") != "run_result_accepted":
                return structured_non_negative_int(event.get("id"))
        return 0

    def _latest_run_result_acceptance_for_source(
        self,
        run_id: str,
        *,
        evidence_source_event_id: int,
        task_verdict_status: str,
    ) -> dict:
        for event in reversed(self.repository.list_recent_events(run_id, event_types={"run_result_accepted"}, limit=20)):
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
