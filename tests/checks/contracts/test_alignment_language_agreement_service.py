from __future__ import annotations

from pathlib import Path

from alignment_language_service_test_support import create_chinese_alignment_session
from alignment_test_support import _wait_for_status


def test_alignment_service_blocks_chinese_agreement_with_english_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_agreement_for_chinese_user",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    assert not session["working_agreement"]
    assert "需要使用中文" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_language_mismatch"
        and "agreement_summary" in event["payload"].get("missing", [])
        for event in events
    )


def test_alignment_service_rewrites_english_clarifying_message_for_chinese_user(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_clarifying_message_for_chinese_user",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assistant_message = session["transcript"][-1]["content"]
    assert "推荐判断" in assistant_message
    assert "What evidence" not in assistant_message
    events = service.list_alignment_events(created["id"])
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and "missing_recommended_decision_options" in event["payload"].get("issues", [])
        for event in events
    )
