from __future__ import annotations

from pathlib import Path

from alignment_test_support import _assert_run_succeeds_and_joins, _wait_for_status


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


def test_alignment_service_accepts_refund_agreement_as_guide_repair_workflow(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_refund_agreement_repair_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a governed refund self-service flow.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "confirm")
    session = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = preview["bundle"]
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}

    assert session["validation"]["ok"] is True
    assert preview["control_summary"]["traceability"]["mapped_count"] == preview["control_summary"]["traceability"]["required_count"]
    assert [step["id"] for step in bundle["workflow"]["steps"]] == [
        "builder_step",
        "refund_inspection_step",
        "repair_guide_step",
        "builder_repair_step",
        "gatekeeper_step",
    ]
    assert bundle["role_definitions"][2]["archetype"] == "guide"
    assert steps_by_id["repair_guide_step"]["inputs"]["handoffs_from"] == ["refund_inspection_step"]
    assert steps_by_id["builder_repair_step"]["inputs"]["handoffs_from"] == ["refund_inspection_step", "repair_guide_step"]
    assert steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] == [
        "builder_step",
        "refund_inspection_step",
        "repair_guide_step",
        "builder_repair_step",
    ]
    assert "guide" in steps_by_id["gatekeeper_step"]["inputs"]["evidence_query"]["archetypes"]
    assert "double-refund" in bundle["collaboration_summary"]
    assert "support or finance follow-up" in bundle["spec"]["markdown"]

    imported = service.import_alignment_bundle(created["id"], start_immediately=True)
    _assert_run_succeeds_and_joins(service, imported["run"]["id"])


def test_alignment_service_accepts_chinese_refund_agreement_as_guide_repair_workflow(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_chinese_refund_agreement_repair_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请编排一个受治理的退款自助流程。",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认，采用这份工作协议。")
    session = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = preview["bundle"]
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}

    assert session["validation"]["ok"] is True
    assert preview["control_summary"]["traceability"]["mapped_count"] == preview["control_summary"]["traceability"]["required_count"]
    assert bundle["metadata"]["name"] == "退款安全修复 Bundle"
    assert bundle["role_definitions"][2]["archetype"] == "guide"
    assert steps_by_id["repair_guide_step"]["inputs"]["handoffs_from"] == ["refund_inspection_step"]
    assert steps_by_id["builder_repair_step"]["inputs"]["handoffs_from"] == ["refund_inspection_step", "repair_guide_step"]
    assert steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] == [
        "builder_step",
        "refund_inspection_step",
        "repair_guide_step",
        "builder_repair_step",
    ]
    assert "退款" in bundle["collaboration_summary"]
    assert "客服或财务 follow-up" in bundle["spec"]["markdown"]
