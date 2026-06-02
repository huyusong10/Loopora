from __future__ import annotations

from pathlib import Path

from alignment_test_support import (
    _confirm_alignment_agreement,
    _wait_for_status,
)


MIN_READY_REVIEW_PROMPT_COUNT = 2


def test_alignment_ready_preview_feedback_recompiles_from_current_bundle(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=(
            "Create a focused starter Loop with project-owned evidence, fake-done protection, "
            "and conservative GateKeeper closure."
        ),
    )
    ready = _confirm_alignment_agreement(service, created["id"])
    bundle_before = Path(ready["bundle_path"]).read_text(encoding="utf-8")
    agreement_before = dict(ready["working_agreement"])
    feedback = (
        "审查后请调整这份 Loop 预览：primary user flow、project-owned evidence、"
        "happy-path claim 和 GateKeeper weak proof 必须继续作为阻断判断。"
    )

    service.append_alignment_message(ready["id"], feedback)
    reviewed = _wait_for_status(service, ready["id"], "ready")

    assert reviewed["alignment_stage"] == "ready"
    assert reviewed["working_agreement"]["summary"] == agreement_before["summary"]
    assert reviewed["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is True
    assert reviewed["working_agreement"]["ready_review"]["feedback"] == feedback
    assert Path(reviewed["bundle_path"]).read_text(encoding="utf-8").strip()
    transcript_log = Path(reviewed["artifact_dir"]) / "conversation" / "transcript.jsonl"
    assert feedback in transcript_log.read_text(encoding="utf-8")
    events = service.list_alignment_events(ready["id"])
    assert any(event["event_type"] == "alignment_ready_review_started" for event in events)
    assert any(event["event_type"] == "alignment_bundle_written" for event in events)
    prompt_paths = sorted((Path(reviewed["artifact_dir"]) / "invocations").glob("*/prompt.md"))
    assert len(prompt_paths) >= MIN_READY_REVIEW_PROMPT_COUNT
    prompt_text = prompt_paths[-1].read_text(encoding="utf-8")
    assert "Current compiler gate: ready preview review" in prompt_text
    assert "The session already has a READY candidate bundle" in prompt_text
    assert "## Current Bundle" in prompt_text
    assert bundle_before.splitlines()[0] in prompt_text
    assert feedback in prompt_text
