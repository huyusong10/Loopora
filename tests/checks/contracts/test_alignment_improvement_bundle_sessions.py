from __future__ import annotations

from pathlib import Path

from alignment_test_support import (
    _confirm_alignment_agreement,
    _create_alignment_improvement_source_bundle,
    _wait_for_status,
)


def test_alignment_improvement_session_can_start_from_existing_bundle(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    session = service.create_bundle_revision_session(source["id"], start_immediately=False)

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "bundle"
    assert agreement["source"]["source_bundle_id"] == source["id"]
    assert agreement["source"]["source_run_id"] == ""
    assert agreement["source"]["source_completion_mode"] == "gatekeeper"
    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["metadata"]["source_bundle_id"] == ""
    assert preview["bundle"]["metadata"]["revision"] == 1
    assert "source_bundle_id" not in preview["yaml"]
    assert "revision:" not in preview["yaml"]
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_bundle_improvement_seeded" for event in events)


def test_alignment_improvement_session_materializes_preservation_and_delta(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "agreement_ready"
    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    evidence = agreement["readiness_evidence"]
    assert "Preserve" in evidence["task_scope"]
    assert "change" in evidence["task_scope"]
    assert "evidence" in evidence["workflow_shape"]
    visible_agreement = session["transcript"][-1]["content"]
    assert "Preserve" in visible_agreement
    assert "source bundle" in evidence["task_scope"]


def test_alignment_improvement_session_validates_feedback_driven_bundle_delta(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    bundle_text = Path(session["bundle_path"]).read_text(encoding="utf-8")
    assert "Preserve the source Loop" in bundle_text
    assert "feedback-driven governance delta" in bundle_text
    assert "spec" in bundle_text
    assert "roles" in bundle_text
    assert "workflow" in bundle_text
