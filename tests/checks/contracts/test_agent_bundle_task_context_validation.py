from __future__ import annotations

from http import HTTPStatus

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    TestClient,
    alignment_bundle_yaml,
    build_app,
)


def test_agent_bundle_candidate_rejects_task_context_mismatch(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_web_alignment"] is False
    assert generated["requires_candidate_repair"] is True
    assert generated["ready_candidate_sha256"] == ""
    assert generated["ready_candidate_bytes"] == 0
    assert generated["binding"]["requires_web_alignment"] is False
    assert generated["binding"]["requires_candidate_repair"] is True
    assert generated["binding"]["ready_candidate_sha256"] == ""
    assert generated["binding"]["ready_candidate_bytes"] == 0
    assert generated["session"].get("agent_entry_review", {}) == {}
    assert "host Agent task context" in generated["session"]["error_message"]
    assert "refund" in generated["session"]["error_message"]
    assert "audit" in generated["session"]["error_message"]
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["requires_candidate_repair"] is False
    assert candidate_event["payload"]["ready_candidate_sha256"] == ""
    assert candidate_event["payload"]["ready_candidate_bytes"] == 0
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "host Agent task context" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )


def test_agent_bundle_candidate_repair_session_keeps_web_plan_previewable(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["requires_candidate_repair"] is True
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/alignments/sessions/{generated['session']['id']}/bundle")

    assert response.status_code == HTTPStatus.OK
    preview = response.json()
    assert preview["ok"] is True
    assert preview["session"]["status"] == "failed"
    assert preview["source_path"] == generated["session"]["bundle_path"]
    assert preview["validation"]["ok"] is False
    assert "host Agent task context" in preview["validation"]["error"]
    assert preview["control_summary"]["coverage"]["target_count"] >= preview["control_summary"]["coverage"]["check_count"]
    assert preview["traceability"] == preview["control_summary"]["traceability"]
