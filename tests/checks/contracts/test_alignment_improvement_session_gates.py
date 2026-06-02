from __future__ import annotations

from pathlib import Path

from alignment_test_support import (
    _confirm_alignment_agreement,
    _create_alignment_improvement_source_bundle,
    _wait_for_status,
)


def test_alignment_improvement_session_blocks_generic_final_bundle(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_generic_bundle")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "feedback-driven governance delta" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "improvement bundle must state the feedback-driven governance delta" in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_improvement_session_blocks_vague_improvement_agreement(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_missing_delta")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_improvement_incomplete"
        and "improvement_delta" in event["payload"].get("missing", [])
        for event in events
    )


def test_alignment_improvement_session_requires_completion_mode_delta_for_rounds_source(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(
        service,
        sample_spec_file,
        sample_workdir,
        completion_mode="rounds",
    )

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert session["working_agreement"]["source"]["source_completion_mode"] == "rounds"
    assert "improvement_completion_mode_delta" in session["transcript"][-1]["content"]
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")
    assert "Source completion mode: rounds" in prompt_text
    assert "conversion to evidence-backed GateKeeper task verdicts" in prompt_text
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_improvement_incomplete"
        and "improvement_completion_mode_delta" in event["payload"].get("missing", [])
        for event in events
    )
