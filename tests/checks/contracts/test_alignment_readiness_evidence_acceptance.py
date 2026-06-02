from __future__ import annotations

from pathlib import Path

import pytest

from alignment_test_support import _confirm_alignment_agreement, _wait_for_status


def test_alignment_service_accepts_nonempty_loop_fit_readiness_evidence_without_keyword_gate(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_vague_loop_fit_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a complex but possibly one-pass starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "ready")

    assert Path(session["bundle_path"]).exists()
    assert session["validation"]["ok"] is True


@pytest.mark.parametrize(
    ("scenario", "missing_key"),
    [
        ("alignment_vague_task_scope_readiness_evidence", "task_scope"),
        ("alignment_vague_judgment_tradeoffs_readiness_evidence", "judgment_tradeoffs"),
        ("alignment_vague_execution_strategy_readiness_evidence", "execution_strategy"),
        ("alignment_workflow_shape_without_gatekeeper_readiness_evidence", "workflow_shape"),
    ],
)
def test_alignment_service_accepts_nonempty_bundle_shaping_readiness_evidence_without_keyword_gate(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    missing_key: str,
) -> None:
    service = service_factory(scenario=scenario)

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=f"Build a starter experience with weak {missing_key} evidence.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "ready")

    assert Path(session["bundle_path"]).exists()
    assert session["validation"]["ok"] is True
    assert session["working_agreement"]["readiness_evidence"][missing_key]


def test_alignment_service_accepts_chinese_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_chinese_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请用中文对齐这个需要多轮证据判断的任务。",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    assert Path(session["bundle_path"]).exists()
    bundle_text = Path(session["bundle_path"]).read_text(encoding="utf-8")
    assert "将工作协议投影到 spec" in bundle_text
    assert "name: 对齐 Starter Bundle" in bundle_text
    assert "name: 聚焦 Builder" in bundle_text
    assert "中文整理" in session["transcript"][-1]["content"]
    assert not any(
        event["event_type"] == "alignment_stage_blocked"
        for event in service.list_alignment_events(created["id"])
    )


def test_alignment_service_accepts_survive_chat_as_loop_fit_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_survive_chat_loop_fit_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a task whose judgment should survive the current chat.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    assert Path(session["bundle_path"]).exists()
    assert "survive one chat" in session["working_agreement"]["readiness_evidence"]["loop_fit"]
    assert not any(
        event["event_type"] == "alignment_stage_blocked"
        for event in service.list_alignment_events(created["id"])
    )
