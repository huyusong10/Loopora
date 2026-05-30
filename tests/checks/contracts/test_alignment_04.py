from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from loopora.alignment_readiness_rules import alignment_improvement_readiness_issues
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_stage import alignment_improvement_bundle_issues
from loopora.web import build_app
from loopora.web_streaming import MAX_EVENT_CURSOR_ID

from alignment_test_support import (
    _wait_for_status,
    _confirm_alignment_agreement,
    _create_alignment_improvement_source_bundle,
)

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
        event["event_type"] == "alignment_validation_failed" and "confirmed working agreement evidence" in event["payload"].get("error", "") for event in events
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

def test_alignment_service_blocks_global_persona_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_global_persona_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without turning task judgment into memory.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "task_scoped_judgment" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] in {"alignment_evidence_incomplete", "alignment_stage_blocked"}
        and ("task_scoped_judgment" in event["payload"].get("missing", []) or "task_scoped_judgment" in event["payload"].get("error", ""))
        for event in events
    )

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
    assert not any(event["event_type"] == "alignment_stage_blocked" for event in service.list_alignment_events(created["id"]))

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
    assert not any(event["event_type"] == "alignment_stage_blocked" for event in service.list_alignment_events(created["id"]))

def test_alignment_service_reuses_executor_session_ref_between_turns(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_question")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="I need help shaping this task.",
    )
    first = _wait_for_status(service, created["id"], "waiting_user")
    first_session_id = first["executor_session_ref"]["session_id"]

    service.append_alignment_message(created["id"], "更怕做糙。")
    second = _wait_for_status(service, created["id"], "waiting_user")

    assert second["executor_session_ref"]["session_id"] == first_session_id
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_executor_session_ref" for event in events)

def test_alignment_service_falls_back_when_native_resume_fails(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_resume_failure")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle after resume trouble.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], executor_session_ref={"session_id": "stale-session"})
    service.start_alignment_session_async(session["id"])
    _wait_for_status(service, session["id"], "waiting_user")
    service.repository.update_alignment_session(
        session["id"],
        alignment_stage="confirmed",
        working_agreement={"summary": "Confirmed test agreement.", "confirmed_at": "test"},
    )
    service.start_alignment_session_async(session["id"])
    ready = _wait_for_status(service, session["id"], "ready")

    assert ready["validation"]["ok"] is True
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_native_resume_fallback" for event in events)

def test_alignment_service_repairs_invalid_bundle_once(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_invalid_then_valid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle, and recover if the first draft is malformed.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is True
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_repair_started" for event in events)

def test_alignment_service_repairs_semantically_incomplete_bundle_once(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_semantic_invalid_then_valid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a semantically complete bundle.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is True
    failed_events = [event for event in service.list_alignment_events(created["id"]) if event["event_type"] == "alignment_validation_failed"]
    assert failed_events
    assert "semantic lint" in failed_events[0]["payload"]["error"]

def test_alignment_service_fails_after_invalid_repair(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_invalid")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle that remains invalid.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["repair_attempts"] == 1
    assert session["validation"]["ok"] is False
    assert "collaboration_summary" in session["error_message"]

def test_alignment_service_normalizes_custom_command_settings(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        executor_kind="custom",
        executor_mode="preset",
        command_cli="my-aligner",
        command_args_text="{prompt}\n--output\n{output_path}",
        start_immediately=False,
    )

    assert session["executor_kind"] == "custom"
    assert session["executor_mode"] == "command"
    assert session["command_cli"] == "my-aligner"
    assert session["model"] == ""
    assert session["reasoning_effort"] == ""

def test_alignment_service_blocks_custom_executor_bundle_that_drops_session_settings(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle that preserves the selected runtime.",
        executor_kind="custom",
        executor_mode="preset",
        command_cli="my-aligner",
        command_args_text="{prompt}\n--output\n{output_path}",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must preserve selected Web executor settings" in session["error_message"]
    assert "loop.executor_kind" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_validation_failed" and "command/custom sessions" in event["payload"].get("error", "") for event in events)

def test_alignment_api_covers_session_events_bundle_and_import(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "Create a runnable bundle."},
    )
    assert response.status_code == 201
    session_id = response.json()["session"]["id"]
    _wait_for_status(service, session_id, "waiting_user")
    confirm_response = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "确认"})
    assert confirm_response.status_code == 200
    _wait_for_status(service, session_id, "ready")

    session_response = client.get(f"/api/alignments/sessions/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["session"]["status"] == "ready"

    events_response = client.get(f"/api/alignments/sessions/{session_id}/events")
    assert events_response.status_code == 200
    assert any(event["event_type"] == "alignment_ready" for event in events_response.json())

    with client.stream("GET", f"/api/alignments/sessions/{session_id}/stream") as stream_response:
        assert stream_response.status_code == 200
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in stream_response.iter_text())
    assert "alignment_ready" in body

    list_response = client.get("/api/alignments/sessions")
    assert list_response.status_code == 200
    assert list_response.json()["sessions"][0]["id"] == session_id
    assert list_response.json()["sessions"][0]["native_resume_available"] is True

    bundle_response = client.get(f"/api/alignments/sessions/{session_id}/bundle")
    assert bundle_response.status_code == 200
    bundle_payload = bundle_response.json()
    assert bundle_payload["ok"] is True
    assert bundle_payload["workflow_preview"]["roles"][0]["archetype"] == "builder"

    bundle_path = Path(service.get_alignment_session(session_id)["bundle_path"])
    bundle_path.write_text(
        bundle_path.read_text(encoding="utf-8").replace("Aligned Starter Bundle", "Synced Starter Bundle", 1),
        encoding="utf-8",
    )
    sync_response = client.post(f"/api/alignments/sessions/{session_id}/bundle/sync")
    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert sync_payload["ok"] is True
    assert sync_payload["metadata"]["name"] == "Synced Starter Bundle"
    assert sync_payload["session"]["status"] == "ready"
    assert any(event["event_type"] == "alignment_bundle_synced" for event in service.list_alignment_events(session_id))

    import_response = client.post(
        f"/api/alignments/sessions/{session_id}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == 201
    assert import_response.json()["bundle"]["id"]
    assert import_response.json()["session"]["status"] == "imported"

    delete_response = client.delete(f"/api/alignments/sessions/{session_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/api/alignments/sessions/{session_id}").status_code == 404
    assert client.get("/api/alignments/sessions").json()["sessions"] == []

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
    assert len(prompt_paths) >= 2
    prompt_text = prompt_paths[-1].read_text(encoding="utf-8")
    assert "Current compiler gate: ready preview review" in prompt_text
    assert "The session already has a READY candidate bundle" in prompt_text
    assert "## Current Bundle" in prompt_text
    assert bundle_before.splitlines()[0] in prompt_text
    assert feedback in prompt_text

def test_alignment_api_start_immediately_false_keeps_new_session_idle(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/alignments/sessions",
        json={
            "workdir": str(sample_workdir),
            "message": "Create a bundle later.",
            "start_immediately": "false",
        },
    )

    assert response.status_code == 201
    session_id = response.json()["session"]["id"]
    session = service.get_alignment_session(session_id)
    assert session["status"] == "idle"
    assert session["transcript"][-1]["content"] == "Create a bundle later."
    assert not any(event["event_type"] == "alignment_started" for event in service.list_alignment_events(session_id))

def test_alignment_stream_emits_redacted_stream_error_on_backend_failure(caplog) -> None:
    class FlakyService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "running"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return 9

        def list_alignment_events(self, session_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
            assert session_id == "session_test"
            assert after_id == 9
            assert limit == 200
            raise RuntimeError("alignment database unavailable")

    client = TestClient(build_app(service=FlakyService()))

    with caplog.at_level(logging.ERROR, logger="loopora.web"), client.stream("GET", "/api/alignments/sessions/session_test/stream?after_id=9") as response:
        assert response.status_code == 200
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text())

    assert "event: stream_error" in body
    assert "alignment database unavailable" not in body
    payload = json.loads(next(line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")))
    assert payload == {
        "session_id": "session_test",
        "after_id": 9,
        "error": "stream_unavailable",
        "retryable": True,
    }
    assert any(
        getattr(record, "event", "") == "web.alignment_stream.failed" and record.exc_info and "alignment database unavailable" in str(record.exc_info[1])
        for record in caplog.records
    )

def test_alignment_event_api_rejects_out_of_range_query_params(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for path in (
        "/api/alignments/sessions?limit=0",
        "/api/alignments/sessions?limit=101",
        "/api/alignments/sessions/session_test/events?after_id=-1",
        f"/api/alignments/sessions/session_test/events?after_id={MAX_EVENT_CURSOR_ID + 1}",
        "/api/alignments/sessions/session_test/events?limit=0",
        "/api/alignments/sessions/session_test/events?limit=5001",
        "/api/alignments/sessions/session_test/stream?after_id=-1",
        f"/api/alignments/sessions/session_test/stream?after_id={MAX_EVENT_CURSOR_ID + 1}",
    ):
        response = client.get(path)
        assert response.status_code == 400
        assert response.json()["error"] == "request validation failed"

def test_alignment_event_api_rejects_cursor_beyond_current_events() -> None:
    class CursorAwareService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "ready"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return 10

    client = TestClient(build_app(service=CursorAwareService()))

    response = client.get("/api/alignments/sessions/session_test/events?after_id=11")

    assert response.status_code == 400
    assert response.json()["error"] == "event cursor is out of range"

def test_alignment_stream_logs_invalid_resume_cursor_and_keeps_request_cursor(caplog) -> None:
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_alignment_session(self, session_id: str) -> dict:
            return {"id": session_id, "status": "ready"}

        def latest_alignment_event_id(self, session_id: str) -> int:
            assert session_id == "session_test"
            return 10

        def list_alignment_events(self, session_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
            assert session_id == "session_test"
            assert limit == 200
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with (
        caplog.at_level(logging.WARNING, logger="loopora.web"),
        client.stream(
            "GET",
            "/api/alignments/sessions/session_test/stream?after_id=7",
            headers={"Last-Event-ID": "11"},
        ) as response,
    ):
        assert response.status_code == 200
        assert "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text()) == ""

    assert captured["after_id"] == 7
    assert any(
        getattr(record, "event", "") == "web.alignment_stream.resume_cursor_invalid"
        and getattr(record, "context", {}).get("session_id") == "session_test"
        and getattr(record, "context", {}).get("after_id") == 7
        and getattr(record, "context", {}).get("latest_event_id") == 10
        and getattr(record, "context", {}).get("invalid_last_event_id") == "11"
        for record in caplog.records
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
        event["event_type"] == "alignment_improvement_incomplete" and "improvement_completion_mode_delta" in event["payload"].get("missing", [])
        for event in events
    )

def test_alignment_improvement_bundle_requires_completion_mode_delta_for_rounds_source(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] = (
        "Preserve the source Loop stable intent, source workdir, and useful source posture while applying "
        "a feedback-driven governance delta that maps to spec, roles, workflow, evidence expectations, "
        "and GateKeeper strictness."
    )
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert "improvement bundle must state the source completion-mode governance delta" in issues

def test_alignment_improvement_bundle_accepts_loop_verdict_marker_for_completion_mode_delta(
) -> None:
    bundle = {
        "metadata": {},
        "collaboration_summary": (
            "保留来源 Loop 的稳定意图；基于反馈变化，新的方案把 rounds completion mode 的"
            "运行生命周期与 Loop 裁决分开，并把证据放回治理面。"
        ),
        "loop": {},
        "spec": {},
        "workflow": {},
        "role_definitions": [],
    }
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert "improvement bundle must state the source completion-mode governance delta" not in issues

def test_alignment_improvement_readiness_accepts_loop_verdict_marker_for_completion_mode_delta() -> None:
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }
    output = {
        "agreement_summary": (
            "保留既有意图，基于反馈调整治理面；原完成模式是 rounds，新的运行生命周期"
            "与 Loop 裁决分开。"
        ),
        "readiness_evidence": {},
    }

    issues = alignment_improvement_readiness_issues(session, output)

    assert "improvement_completion_mode_delta" not in issues

def test_alignment_improvement_bundle_rejects_reusing_source_bundle_id(
    sample_workdir: Path,
) -> None:
    source_bundle_id = "bundle_source"
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["metadata"]["bundle_id"] = source_bundle_id
    bundle["collaboration_summary"] = (
        "Preserve the source Loop stable intent, source workdir, and useful source posture while applying "
        "a feedback-driven governance delta that maps to spec, roles, workflow, evidence expectations, "
        "and GateKeeper strictness."
    )
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_bundle_id": source_bundle_id,
                "source_completion_mode": "gatekeeper",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert (
        "improvement bundle must not reuse the source bundle id as metadata.bundle_id; leave bundle_id empty or choose a new standalone candidate id"
    ) in issues
