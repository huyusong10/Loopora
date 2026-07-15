from __future__ import annotations

from collections.abc import Iterable

from loopora.db_event_records import RunObservationSnapshotRowsRequest
from loopora.run_observation_events import PROGRESS_EVENT_TYPES, TIMELINE_EVENT_TYPES
from loopora.run_takeaways import build_minimal_run_takeaway_projection, normalize_run_takeaway_projection_shape
from loopora.service_types import LooporaNotFoundError
from loopora.settings import app_home
from loopora.utils import structured_non_negative_int

import json

from pathlib import Path

from loopora.agent_native_evidence_contracts import agent_native_active_step_view

from loopora.agent_native_step_view_paths import (
    agent_native_step_contract_path_text,
    agent_native_step_view_path_text,
)

from loopora.service_types import ACTIVE_RUN_STATUSES


def current_agent_step_projection(run: dict) -> dict:
    if str(run.get("status") or run.get("run_status") or "") not in ACTIVE_RUN_STATUSES:
        return {}
    runs_dir = _text(run.get("runs_dir"), limit=2000)
    if not runs_dir:
        return {}
    state_path = Path(runs_dir) / "agent_native" / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    active = _dict(state.get("active_step"))
    step_view = agent_native_active_step_view(active)
    if not step_view:
        return {}
    role = _dict(step_view.get("role"))
    dispatch = _dict(step_view.get("role_dispatch"))
    coverage = _dict(step_view.get("required_coverage"))
    submit_hint = _dict(step_view.get("submit_hint"))
    known_evidence_ids = step_view.get("known_evidence_ids")
    top_gaps = _list_of_dicts(coverage.get("top_gaps"))
    return {
        "step_id": _text(step_view.get("step_id")),
        "iter": structured_non_negative_int(step_view.get("iter")),
        "step_order": structured_non_negative_int(step_view.get("step_order")),
        "parallel_group": _text(step_view.get("parallel_group")),
        "claimed_at": _text(active.get("claimed_at")),
        "role": {
            "id": _text(role.get("id")),
            "name": _text(role.get("name")),
            "archetype": _text(role.get("archetype")),
            "runtime_role": _text(role.get("runtime_role")),
            "posture_notes": _text(role.get("posture_notes")),
        },
        "target_agent": _text(dispatch.get("target_agent")),
        "target_agent_config_path": _text(dispatch.get("target_agent_config_path"), limit=1000),
        "target_agent_config_absolute_path": _text(dispatch.get("target_agent_config_absolute_path"), limit=2000),
        "target_agent_config_exists": dispatch.get("target_agent_config_exists") is True,
        "role_dispatch": {
            "target_agent": _text(dispatch.get("target_agent")),
            "target_agent_config_path": _text(dispatch.get("target_agent_config_path"), limit=1000),
            "target_agent_config_absolute_path": _text(dispatch.get("target_agent_config_absolute_path"), limit=2000),
            "target_agent_config_exists": dispatch.get("target_agent_config_exists") is True,
            "inline_allowed": dispatch.get("inline_allowed") is True,
            "dispatch_contract": _text(dispatch.get("dispatch_contract")),
        },
        "inputs": _dict(step_view.get("inputs")),
        "action_policy": _dict(step_view.get("action_policy")),
        "required_coverage": {
            "status": _text(coverage.get("status")),
            "evidence_progress_mode": _text(coverage.get("evidence_progress_mode")),
            "covered_check_count": structured_non_negative_int(coverage.get("covered_check_count")),
            "missing_check_count": structured_non_negative_int(coverage.get("missing_check_count")),
            "covered_check_ids": [str(item) for item in coverage.get("covered_check_ids", []) if isinstance(item, str)][:20]
            if isinstance(coverage.get("covered_check_ids"), list)
            else [],
            "missing_check_ids": [str(item) for item in coverage.get("missing_check_ids", []) if isinstance(item, str)][:20]
            if isinstance(coverage.get("missing_check_ids"), list)
            else [],
            "top_gaps": top_gaps,
        },
        "continuation": _current_agent_step_continuation_projection(step_view),
        "iteration_repair": _current_agent_step_iteration_repair_projection(step_view),
        "context_path": _text(step_view.get("context_path"), limit=1000),
        "context_absolute_path": _text(step_view.get("context_absolute_path"), limit=2000),
        "agent_step_view_path": _text(agent_native_step_view_path_text(step_view), limit=1000),
        "agent_step_view_absolute_path": _text(
            agent_native_step_view_path_text(step_view, absolute=True),
            limit=2000,
        ),
        "step_contract_path": _text(agent_native_step_contract_path_text(step_view), limit=1000),
        "step_contract_absolute_path": _text(agent_native_step_contract_path_text(step_view, absolute=True), limit=2000),
        "submit_hint": {
            "command": _text(submit_hint.get("command"), limit=1000),
            "result_file_contract": _text(submit_hint.get("result_file_contract"), limit=1000),
            "result_outbox_dir": _text(submit_hint.get("result_outbox_dir"), limit=1000),
            "result_outbox_absolute_dir": _text(submit_hint.get("result_outbox_absolute_dir"), limit=2000),
            "result_file_path": _text(submit_hint.get("result_file_path"), limit=1000),
            "result_file_absolute_path": _text(submit_hint.get("result_file_absolute_path"), limit=2000),
            "result_template_path": _text(submit_hint.get("result_template_path"), limit=1000),
            "result_template_absolute_path": _text(submit_hint.get("result_template_absolute_path"), limit=2000),
        },
        "known_evidence_count": len(known_evidence_ids) if isinstance(known_evidence_ids, list) else 0,
    }

def _current_agent_step_continuation_projection(step_view: dict) -> dict:
    continuation = _dict(step_view.get("continuation"))
    if continuation.get("active") is not True:
        return {}
    verdict = _dict(continuation.get("previous_task_verdict"))
    coverage = _dict(continuation.get("coverage"))
    return {
        "active": True,
        "reason": _text(continuation.get("reason")),
        "previous_run_id": _text(continuation.get("previous_run_id")),
        "previous_run_path": _text(continuation.get("previous_run_path"), limit=1000),
        "previous_run_status": _text(continuation.get("previous_run_status")),
        "previous_task_verdict": {
            "status": _text(verdict.get("status")),
            "source": _text(verdict.get("source")),
            "summary": _text(verdict.get("summary"), limit=600),
        },
        "previous_task_verdict_path": _text(continuation.get("previous_task_verdict_path"), limit=2000),
        "previous_evidence_coverage_path": _text(continuation.get("previous_evidence_coverage_path"), limit=2000),
        "coverage": {
            "status": _text(coverage.get("status")),
            "covered_check_count": structured_non_negative_int(coverage.get("covered_check_count")),
            "missing_check_count": structured_non_negative_int(coverage.get("missing_check_count")),
            "target_count": structured_non_negative_int(coverage.get("target_count")),
            "covered_target_count": structured_non_negative_int(coverage.get("covered_target_count")),
            "weak_target_count": structured_non_negative_int(coverage.get("weak_target_count")),
            "missing_target_count": structured_non_negative_int(coverage.get("missing_target_count")),
            "blocked_target_count": structured_non_negative_int(coverage.get("blocked_target_count")),
            "covered_check_ids": _list_of_strings(coverage.get("covered_check_ids"), limit=20),
            "missing_check_ids": _list_of_strings(coverage.get("missing_check_ids"), limit=20),
            "top_gaps": _list_of_dicts(coverage.get("top_gaps"), limit=5),
        },
        "next_focus": _list_of_strings(continuation.get("next_focus"), limit=8),
    }

def _current_agent_step_iteration_repair_projection(step_view: dict) -> dict:
    repair = _dict(step_view.get("iteration_repair"))
    if repair.get("active") is not True:
        return {}
    return {
        "active": True,
        "previous_iteration": structured_non_negative_int(repair.get("previous_iteration")),
        "source_step_id": _text(repair.get("source_step_id")),
        "source_role": _text(repair.get("source_role")),
        "status": _text(repair.get("status")),
        "summary": _text(repair.get("summary"), limit=600),
        "blocking_items": _list_of_strings(repair.get("blocking_items"), limit=8),
        "recommended_next_action": _text(repair.get("recommended_next_action"), limit=600),
        "evidence_refs": _list_of_strings(repair.get("evidence_refs"), limit=8),
        "top_gaps": _list_of_dicts(repair.get("top_gaps"), limit=5),
    }

def _text(value: object, *, limit: int = 400) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:limit]

def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}

def _list_of_dicts(value: object, *, limit: int = 5) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)][:limit]

def _list_of_strings(value: object, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()][:limit]


class ServiceRunObservationMixin:
    def recent_run_events(
        self,
        run_id: str,
        *,
        event_types: Iterable[str] | None = None,
        max_event_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.list_recent_events(
            run_id,
            event_types=event_types,
            max_event_id=max_event_id,
            limit=limit,
        )

    def latest_run_event_id(self, run_id: str) -> int:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.latest_event_id(run_id)

    def run_observation_snapshot(self, run_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        snapshot = self.repository.run_observation_snapshot_rows(
            RunObservationSnapshotRowsRequest(
                run_id=run_id,
                timeline_event_types=TIMELINE_EVENT_TYPES,
                progress_event_types=PROGRESS_EVENT_TYPES,
                timeline_limit=40,
                console_limit=160,
                progress_limit=2000,
            )
        )
        if snapshot is None:
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        run = self._hydrate_run_files(snapshot["run"])
        key_takeaways = snapshot.get("key_takeaway_projection")
        if not isinstance(key_takeaways, dict) or not key_takeaways:
            key_takeaways = build_minimal_run_takeaway_projection(run, source_event_id=snapshot["latest_event_id"])
        else:
            key_takeaways = normalize_run_takeaway_projection_shape(run, key_takeaways)
        key_takeaways["source_event_id"] = min(
            structured_non_negative_int(key_takeaways.get("source_event_id")),
            structured_non_negative_int(snapshot["latest_event_id"]),
        )
        current_agent_step = current_agent_step_projection(run)
        snapshot.pop("key_takeaway_projection", None)
        return {**snapshot, "run": run, "key_takeaways": key_takeaways, "current_agent_step": current_agent_step}

    def get_runtime_activity(self) -> dict:
        self._reconcile_local_orphaned_runs()
        active_runs = self.repository.list_active_runs()
        loop_name_by_id = {loop["id"]: loop["name"] for loop in self.repository.list_loops()}
        running_count = 0
        queued_count = 0
        awaiting_agent_count = 0
        runs = []
        for run in active_runs:
            status = str(run.get("status") or "").strip()
            if status == "running":
                running_count += 1
            elif status == "queued":
                queued_count += 1
            elif status == "awaiting_agent":
                awaiting_agent_count += 1
            runs.append(
                {
                    "id": run["id"],
                    "loop_id": run["loop_id"],
                    "loop_name": loop_name_by_id.get(run["loop_id"]) or run["loop_id"],
                    "status": status or "queued",
                    "active_role": run.get("active_role"),
                    "current_iter": run.get("current_iter"),
                    "workdir": run.get("workdir"),
                    "updated_at": run.get("updated_at"),
                }
            )
        return {
            "app_home": str(app_home().resolve()),
            "running_count": running_count,
            "queued_count": queued_count,
            "awaiting_agent_count": awaiting_agent_count,
            "has_running_runs": running_count > 0,
            "has_active_runs": bool(active_runs),
            "runs": runs,
        }

    def stream_events(self, run_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
        self._reconcile_local_orphaned_runs()
        if not self.repository.get_run(run_id):
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        return self.repository.list_events(run_id, after_id=after_id, limit=limit)
