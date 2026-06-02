from __future__ import annotations

from pathlib import Path

from alignment_test_support import _wait_for_status


def test_alignment_service_blocks_bundle_that_drops_confirmed_agreement_specifics(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_refund_agreement_generic_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a governed refund self-service flow.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "confirmed working agreement evidence" in session["error_message"]
    assert "refund" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "confirmed working agreement evidence" in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_service_blocks_chinese_bundle_that_drops_confirmed_agreement_specifics(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_chinese_refund_agreement_generic_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请编排一个受治理的退款自助流程。",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "confirmed working agreement evidence" in session["error_message"]
    assert "退款" in session["error_message"]
