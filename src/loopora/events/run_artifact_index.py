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


def evidence_artifact_index_entries(payload: dict, *, created_by_event_id: str, loop_id: str = "") -> list[dict]:
    entries: list[dict] = []
    for artifact_ref in list(payload.get("artifact_refs") or []):
        if not isinstance(artifact_ref, dict):
            continue
        uri = str(artifact_ref.get("uri") or "")
        if not uri:
            continue
        entries.append(
            {
                "run_id": str(payload.get("run_id") or ""),
                "loop_id": loop_id,
                "kind": str(artifact_ref.get("kind") or "artifact"),
                "uri": uri,
                "content_hash": str(artifact_ref.get("content_hash") or ""),
                "created_by_event_id": created_by_event_id,
            }
        )
    return entries
