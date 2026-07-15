from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
from pathlib import Path
from typing import Any

from loopora.context_flow import evidence_entry_id
from loopora.run_artifacts import INITIAL_STAGNATION_STATE, read_jsonl
from loopora.service_types import LooporaError
from loopora.utils import read_json, write_json


def agent_native_state(layout: Any, *, adapter: str, run: dict[str, Any]) -> dict[str, Any]:
    path = agent_native_state_path(layout)
    if path.exists():
        try:
            payload = read_json(path)
        except (OSError, UnicodeError, ValueError) as exc:
            raise LooporaError(f"agent-native state is unreadable: {path}: {exc}") from exc
        if isinstance(payload, dict) and payload:
            return payload
    return {
        "version": 1,
        "execution_plane": "agent_native",
        "adapter": adapter,
        "run_id": run["id"],
        "status": "awaiting_agent",
        "iter_id": 0,
        "step_index": 0,
        "previous_composite": None,
        "stagnation": dict(INITIAL_STAGNATION_STATE),
        "previous_outputs_by_step": {},
        "previous_outputs_by_role": {},
        "previous_outputs_by_archetype": {},
        "previous_handoffs_by_step": {},
        "previous_handoffs_by_role": {},
        "previous_iteration_summary": None,
        "previous_session_refs_by_step": {},
        "current_outputs_by_step": {},
        "current_outputs_by_role": {},
        "current_outputs_by_archetype": {},
        "current_handoffs": [],
        "current_session_refs_by_step": {},
        "current_gatekeeper_result": None,
        "current_guide_result": None,
        "step_results": [],
        "control_fire_counts": {},
        "control_queue": [],
        "control_queue_index": 0,
        "control_queue_iter": None,
        "parallel_group_snapshot": {},
        "host_dispatches": [],
        "active_step": {},
    }


def write_agent_native_state(layout: Any, state: dict[str, Any]) -> None:
    write_json(agent_native_state_path(layout), state)


def agent_native_state_path(layout: Any) -> Path:
    return layout.run_dir / "agent_native" / "state.json"


@contextmanager
def agent_native_submit_lock(layout: Any) -> Iterator[None]:
    # Agent submits can arrive from separate CLI processes; evidence/state writes must be single-accept.
    lock_path = agent_native_submit_lock_path(layout)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def agent_native_submit_lock_path(layout: Any) -> Path:
    return layout.run_dir / "agent_native" / "submit.lock"


def agent_native_step_already_submitted(layout: Any, *, iter_id: int, step_order: int, step_id: str) -> bool:
    existing_id = evidence_entry_id(iter_id, step_order, step_id)
    return any(str(item.get("id") or "").strip() == existing_id for item in read_jsonl(layout.evidence_ledger_path))


def update_agent_native_parallel_group_snapshot_after_submit(
    state: dict[str, Any],
    *,
    strategy_steps: list[dict[str, Any]],
    step: dict[str, Any],
    step_order: int,
) -> None:
    parallel_group = str(step.get("parallel_group") or "").strip()
    if not parallel_group:
        state["parallel_group_snapshot"] = {}
        return
    next_step_order = step_order + 1
    if (
        next_step_order < len(strategy_steps)
        and str(strategy_steps[next_step_order].get("parallel_group") or "").strip() == parallel_group
    ):
        return
    state["parallel_group_snapshot"] = {}
