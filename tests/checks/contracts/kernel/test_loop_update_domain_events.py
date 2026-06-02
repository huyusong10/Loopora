from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id

from loop_event_core_test_support import create_loop


UPDATED_COVERAGE_TARGET_COUNT = 2
LOOP_UPDATE_MAX_ITERATIONS = 3
LOOP_UPDATE_MAX_STEP_RETRIES = 2
UPDATED_LOOP_SOURCE_SEQUENCE = 5


def test_loop_contract_updates_emit_compiler_domain_events_without_reactivation(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    create_loop(
        repository,
        tmp_path,
        {
            "id": "loop_update_events",
            "name": "Loop Update Events",
            "task": "Initial.",
            "max_iters": LOOP_UPDATE_MAX_ITERATIONS,
            "max_role_retries": LOOP_UPDATE_MAX_STEP_RETRIES,
        },
    )

    updated_spec_path = tmp_path / "updated.md"
    updated_spec_path.write_text("# Task\n\nUpdated.\n", encoding="utf-8")
    repository.update_loop_contract(
        "loop_update_events",
        {
            "spec_path": str(updated_spec_path),
            "spec_markdown": updated_spec_path.read_text(encoding="utf-8"),
            "compiled_spec": {
                "goal": "Updated.",
                "checks": [{"id": "updated", "title": "Updated"}],
                "coverage_targets": [{"id": "done_when.updated"}],
            },
            "workflow": {
                "roles": [{"id": "builder", "name": "Builder", "archetype": "builder"}],
                "steps": [{"id": "build", "role_id": "builder"}],
            },
        },
    )

    events = repository.list_domain_events(loop_stream_id("loop_update_events"))

    assert [event.event_type for event in events] == [
        "LoopContractCompiled",
        "LoopStrategyCompiled",
        "LoopActivated",
        "LoopContractCompiled",
        "LoopStrategyCompiled",
    ]
    assert events[-2].payload["task"] == "Updated."
    assert events[-2].payload["name"] == "Loop Update Events"
    assert events[-2].payload["coverage_target_count"] == UPDATED_COVERAGE_TARGET_COUNT
    assert events[-2].payload["reason"] == "updated"
    assert events[-1].payload["role_count"] == 1
    assert events[-1].payload["max_iterations"] == LOOP_UPDATE_MAX_ITERATIONS
    assert events[-1].payload["max_step_retries"] == LOOP_UPDATE_MAX_STEP_RETRIES
    assert events[-1].causation_id == events[-2].event_id
    cached = repository.get_projection_record("loop_definition", "loop_update_events")
    assert cached["source_sequence"] == UPDATED_LOOP_SOURCE_SEQUENCE
    assert cached["payload"]["name"] == "Loop Update Events"
    assert cached["payload"]["task"] == "Updated."
    assert cached["payload"]["step_count"] == 1
