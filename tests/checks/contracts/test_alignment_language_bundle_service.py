from __future__ import annotations

from pathlib import Path

from alignment_language_service_test_support import create_chinese_alignment_session
from alignment_test_support import _confirm_alignment_agreement, _wait_for_status


def test_alignment_service_blocks_chinese_bundle_with_english_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_bundle_for_chinese_user",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "需要使用中文" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_stage_blocked"
        and "agreement_summary" in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_service_rewrites_english_bundle_message_for_chinese_user(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_assistant_message_for_chinese_bundle",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    assert session["transcript"][-1]["content"] == "已整理成一个可导入的 Loopora bundle。"
    assert "I prepared" not in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_language_mismatch"
        and event["payload"].get("missing") == ["assistant_message"]
        for event in events
    )


def test_alignment_service_blocks_chinese_bundle_with_english_prose(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_bundle_prose_for_chinese_user",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field collaboration_summary must follow Chinese user language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "bundle field collaboration_summary" in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_service_blocks_chinese_bundle_with_english_visible_names(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_visible_bundle_names_for_chinese_user",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field metadata.name must follow Chinese user language" in session["error_message"]
    assert "bundle field loop.name must follow Chinese user language" in session["error_message"]
    assert "bundle role_definition builder.name must follow Chinese user language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "bundle role_definition builder.name" in event["payload"].get("error", "")
        for event in events
    )
