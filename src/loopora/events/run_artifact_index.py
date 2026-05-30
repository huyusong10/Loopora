from __future__ import annotations

from loopora.kernel import StepResult


def step_result_artifact_index_entries(result: StepResult, *, loop_id: str, created_by_event_id: str) -> list[dict]:
    return [
        {
            "run_id": result.run_id,
            "loop_id": loop_id,
            "kind": artifact_ref.kind,
            "uri": artifact_ref.uri,
            "content_hash": artifact_ref.content_hash or "",
            "created_by_event_id": created_by_event_id,
        }
        for artifact_ref in result.artifact_refs
    ]
