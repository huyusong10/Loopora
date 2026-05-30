from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from loopora.file_previews import preview_existing_path
from loopora.run_takeaways import (
    build_minimal_run_takeaway_projection,
    empty_judgment_contract,
)
from loopora.web_streaming import MAX_EVENT_CURSOR_ID, parse_sse_last_event_id, stream_error_payload
from loopora.web_url_utils import safe_attachment_filename, safe_local_return_path, with_query_params
from loopora.web import build_app
from loopora.web_overviews import _build_run_summary_snapshot, _decorate_loop_overview, _format_timeline_event, _progress_stage_seed

from web_api_test_support import (
    _create_api_loop_run,
    _wait_for_run_success,
    _assert_file_explorer_contract,
    _assert_run_artifact_catalog,
    _assert_run_artifact_previews,
    _assert_file_preview_safety,
    _assert_run_event_streaming,
    _assert_key_takeaway_judgment_contract,
)

def test_streaming_cursor_helpers_require_strict_integer_boundaries() -> None:
    assert parse_sse_last_event_id("42") == 42
    assert parse_sse_last_event_id(" 42 ") == 42
    assert parse_sse_last_event_id("+42") is None
    assert parse_sse_last_event_id("42.0") is None
    assert parse_sse_last_event_id(str(MAX_EVENT_CURSOR_ID + 1)) is None

    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=42)["after_id"] == 42
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id="42")["after_id"] == 0
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=True)["after_id"] == 0
    assert stream_error_payload(owner_key="run_id", owner_id="run_test", after_id=MAX_EVENT_CURSOR_ID + 1)["after_id"] == 0

def test_progress_stage_seed_keeps_run_closure_language_neutral() -> None:
    stages = _progress_stage_seed({"workflow_json": {"roles": [], "steps": []}})

    assert stages[-1] == {"key": "finished", "label": "Run closed", "kind": "finished", "sequence": 2}
    assert all(stage["label"] != "Done" for stage in stages)

def test_timeline_event_formatter_keeps_stable_observation_titles() -> None:
    role_summary = _format_timeline_event(
        {
            "id": 1,
            "event_type": "role_execution_summary",
            "created_at": "2026-05-05T00:00:00Z",
            "role": "Builder",
            "payload": {"ok": True, "attempts": 2, "degraded": True, "duration_ms": 12},
        }
    )
    string_ok_role_summary = _format_timeline_event(
        {
            "id": 6,
            "event_type": "role_execution_summary",
            "created_at": "2026-05-05T00:00:00Z",
            "role": "Builder",
            "payload": {"ok": "false", "error": "failed as string", "duration_ms": 12},
        }
    )
    control_event = _format_timeline_event(
        {
            "id": 2,
            "event_type": "control_triggered",
            "created_at": "2026-05-05T00:00:01Z",
            "payload": {"signal": "no_evidence_progress", "role_id": "inspector"},
        }
    )
    parallel_event = _format_timeline_event(
        {
            "id": 5,
            "event_type": "parallel_group_started",
            "created_at": "2026-05-05T00:00:01Z",
            "payload": {"parallel_group": "inspection_pack", "step_ids": ["review_a", "review_b"]},
        }
    )
    run_finished = _format_timeline_event(
        {
            "id": 3,
            "event_type": "run_finished",
            "created_at": "2026-05-05T00:00:02Z",
            "payload": {
                "status": "succeeded",
                "reason": "rounds_completed",
                "task_verdict_status": "insufficient_evidence",
                "task_verdict_summary": "Required coverage still lacks direct evidence.",
            },
        }
    )
    accepted = _format_timeline_event(
        {
            "id": 4,
            "event_type": "run_result_accepted",
            "created_at": "2026-05-05T00:00:03Z",
            "payload": {"status": "succeeded", "task_verdict_status": "passed"},
        }
    )
    accepted_with_judgment = _format_timeline_event(
        {
            "id": 5,
            "event_type": "run_result_accepted",
            "created_at": "2026-05-05T00:00:04Z",
            "payload": {
                "status": "succeeded",
                "task_verdict_status": "passed",
                "run_contract_path": "contract/run_contract.json",
                "judgment_contract_summary": "Prefer proof before closure.",
                "loop_fit_reasons": ["Future rounds keep proof alive."],
                "execution_strategy": ["Prove the contract before polish."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md obligations as Blocking."],
                "role_postures": ["GateKeeper: Fail closed when evidence is weak."],
                "judgment_tradeoffs": ["Proof beats polish."],
                "success_surface": ["Support admin can approve a refund."],
                "fake_done_states": ["CSV export without permission audit is fake done."],
                "evidence_preferences": ["Use browser journey and audit log evidence."],
                "residual_risk": "No residual risk is acceptable.",
            },
        }
    )
    malformed_role_summary = _format_timeline_event(
        {
            "id": 7,
            "event_type": "role_execution_summary",
            "created_at": "2026-05-05T00:00:04Z",
            "role": "Builder",
            "payload": {"ok": True, "attempts": "2", "degraded": "false", "duration_ms": "not-a-duration"},
        }
    )
    malformed_checks = _format_timeline_event(
        {
            "id": 11,
            "event_type": "checks_resolved",
            "created_at": "2026-05-05T00:00:04Z",
            "payload": {"count": "7", "source": "auto_generated"},
        }
    )
    malformed_wait = _format_timeline_event(
        {
            "id": 12,
            "event_type": "iteration_wait_started",
            "created_at": "2026-05-05T00:00:04Z",
            "payload": {"duration_seconds": "30"},
        }
    )
    malformed_abort = _format_timeline_event(
        {
            "id": 13,
            "event_type": "run_aborted",
            "created_at": "2026-05-05T00:00:04Z",
            "payload": {"role": "Builder", "attempts": "2"},
        }
    )
    malformed_guard = _format_timeline_event(
        {
            "id": 14,
            "event_type": "workspace_guard_triggered",
            "created_at": "2026-05-05T00:00:04Z",
            "payload": {"deleted_original_count": "3"},
        }
    )
    malformed_failure_summary = _format_timeline_event(
        {
            "id": 8,
            "event_type": "role_execution_summary",
            "created_at": "2026-05-05T00:00:05Z",
            "role": "Builder",
            "payload": {"ok": "false", "error": "failed as string", "duration_ms": "not-a-duration"},
        }
    )
    list_payload_summary = _format_timeline_event(
        {
            "id": 9,
            "event_type": "role_execution_summary",
            "created_at": "2026-05-05T00:00:06Z",
            "role": "Builder",
            "payload": ["not", "a", "mapping"],
        }
    )
    overflow_iter_finished = _format_timeline_event(
        {
            "id": 10,
            "event_type": "run_finished",
            "created_at": "2026-05-05T00:00:07Z",
            "payload": {"status": "succeeded", "iter": float("inf")},
        }
    )
    legacy_missing_verdict_finished = _format_timeline_event(
        {
            "id": 11,
            "event_type": "run_finished",
            "created_at": "2026-05-05T00:00:08Z",
            "payload": {"status": "succeeded", "reason": "legacy_terminal_event"},
        }
    )

    assert role_summary["title"] == "Builder completed"
    assert role_summary["detail"] == "attempts=2, degraded, 12ms"
    assert string_ok_role_summary["title"] == "Builder failed"
    assert string_ok_role_summary["detail"] == "failed as string, 12ms"
    assert malformed_role_summary["title"] == "Builder completed"
    assert malformed_role_summary["detail"] == "ok"
    assert malformed_checks["detail"] == "0 checks, auto-generated"
    assert malformed_wait["detail"] == "0s"
    assert malformed_abort["detail"] == ""
    assert malformed_guard["detail"] == "deleted=0"
    assert malformed_failure_summary["title"] == "Builder failed"
    assert malformed_failure_summary["detail"] == "failed as string"
    assert list_payload_summary["title"] == "Builder failed"
    assert list_payload_summary["detail"] == ""
    assert overflow_iter_finished["title"] == "Run finished"
    assert overflow_iter_finished["detail"] == "task_verdict_status=not_evaluated"
    assert legacy_missing_verdict_finished["title"] == "Run finished"
    assert legacy_missing_verdict_finished["detail"] == "legacy_terminal_event, task_verdict_status=not_evaluated"
    assert control_event["title"] == "Control triggered"
    assert control_event["detail"] == "no_evidence_progress -> inspector"
    assert parallel_event["title"] == "Parallel review started"
    assert parallel_event["detail"] == "inspection_pack, steps=2"
    assert run_finished["title"] == "Run finished"
    assert (
        run_finished["detail"]
        == "planned rounds completed, task_verdict_status=insufficient_evidence, task_verdict_summary=Required coverage still lacks direct evidence."
    )
    assert accepted["title"] == "Passing evidence verdict recorded"
    assert accepted["detail"] == "status=succeeded, task_verdict_status=passed"
    assert accepted_with_judgment["detail"] == (
        "status=succeeded, task_verdict_status=passed, judgment=Prefer proof before closure., "
        "loop_fit=Future rounds keep proof alive., strategy=Prove the contract before polish., "
        "local_governance=GateKeeper treats skipped AGENTS.md obligations as Blocking., "
        "role_posture=GateKeeper: Fail closed when evidence is weak., "
        "tradeoff=Proof beats polish., success=Support admin can approve a refund., "
        "fake_done=CSV export without permission audit is fake done., "
        "evidence=Use browser journey and audit log evidence., residual_risk=No residual risk is acceptable."
    )

def test_loop_overview_preserves_residual_risk_task_verdict() -> None:
    decorated = _decorate_loop_overview(
        {
            "id": "loop_1",
            "latest_run_id": "run_1",
            "latest_status": "succeeded",
            "latest_task_verdict_json": {
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Accepted a visible follow-up risk.",
                "buckets": {"residual_risk": [{"label": "follow-up"}]},
            },
            "workflow_json": {},
        }
    )

    assert decorated["card_hint_en"] == "The latest task verdict passed with residual risk."
    assert decorated["card_hint_zh"] == "最近一次 Loop 裁决带残余风险通过。"

    summary = _build_run_summary_snapshot(
        {
            "status": "succeeded",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {},
            "task_verdict": {
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "",
                "buckets": {"residual_risk": [{"label": "follow-up"}]},
            },
        }
    )

    assert summary["verdict_title_en"] == "Task verdict: passed with residual risk"
    assert summary["verdict_title_zh"] == "Loop 裁决：有残余风险地通过"
    assert summary["verdict_note_en"] == "follow-up"
    assert "Loop verdict" in summary["status_note_en"]
    assert "任务是否通过" in summary["status_note_zh"]

def test_loop_overview_surfaces_unproven_terminal_task_verdicts() -> None:
    insufficient = _decorate_loop_overview(
        {
            "id": "loop_1",
            "latest_run_id": "run_1",
            "latest_status": "succeeded",
            "latest_task_verdict_json": {
                "status": "insufficient_evidence",
                "source": "gatekeeper",
                "summary": "Missing proof.",
            },
            "latest_summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "workflow_json": {},
        }
    )
    failed = _decorate_loop_overview(
        {
            "id": "loop_2",
            "latest_run_id": "run_2",
            "latest_status": "failed",
            "latest_task_verdict_json": {
                "status": "failed",
                "source": "run_status",
                "summary": "Blocked.",
            },
            "workflow_json": {},
        }
    )

    assert insufficient["card_hint_en"] == "The latest task verdict has insufficient evidence."
    assert insufficient["card_hint_zh"] == "最近一次 Loop 裁决证据不足。"
    assert insufficient["card_excerpt_en"] == "Task verdict still insufficient: Missing proof."
    assert insufficient["card_excerpt_zh"] == "Loop 裁决证据不足：Missing proof."
    assert "All done" not in insufficient["card_excerpt_en"]
    assert failed["card_hint_en"] == "The latest task verdict failed."
    assert failed["card_hint_zh"] == "最近一次 Loop 裁决未通过。"

    summary = _build_run_summary_snapshot(
        {
            "status": "succeeded",
            "current_iter": 0,
            "summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "last_verdict_json": {},
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "gatekeeper",
                "summary": "Missing proof.",
            },
        }
    )
    assert summary["summary_excerpt_en"] == "Task verdict still insufficient: Missing proof."
    assert summary["summary_excerpt_zh"] == "Loop 裁决证据不足：Missing proof."
    assert "All done" not in summary["summary_excerpt_en"]

def test_web_url_helpers_keep_redirects_and_filenames_local() -> None:
    assert safe_local_return_path("/bundles/bundle-1?tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("/bundles/bundle-1?token=secret&tab=roles#surface") == "/bundles/bundle-1?tab=roles#surface"
    assert safe_local_return_path("https://example.test/bundles/1") is None
    assert safe_local_return_path("//example.test/bundles/1") is None
    assert safe_local_return_path("bundles/1") is None
    assert safe_local_return_path("/bundles\\example.test") is None
    assert safe_local_return_path("/bundles/1\r\nLocation: https://example.test") is None
    assert with_query_params("/bundles/bundle-1?tab=roles#surface", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow#surface"
    )
    assert with_query_params("/bundles/bundle-1?token=secret&tab=roles", surface_updated="workflow") == (
        "/bundles/bundle-1?tab=roles&surface_updated=workflow"
    )
    assert safe_attachment_filename('Bad/Name" \r\n injected.yml') == "Bad-Name-injected.yml"

def test_api_run_detail_includes_v4_web_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    payload = client.get(f"/api/runs/{run_id}").json()
    projection = payload["web_projection"]

    assert projection["schema_version"] == 4
    assert projection["kind"] == "web_run_detail"
    assert projection["summary"]["run_id"] == run_id
    assert projection["summary"]["run_status"] == payload["status"]
    assert projection["lifecycle"]["run_id"] == run_id
    assert projection["task_verdict"]["status"] in {"passed", "passed_with_residual_risk", "insufficient_evidence", "not_evaluated"}
    assert "summary_md" in projection["display"]
    assert {"queued_at", "started_at", "finished_at", "updated_at", "created_at"} <= set(projection["timing"])
    assert projection["technical_handoff"]["run_url"] == f"/runs/{run_id}"
    assert projection["diagnostics"]["source_shape"] == "run_record"
    assert "raw" not in projection

def test_run_artifact_download_rejects_symlink_escaping_loopora_root(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    run = client.get(f"/api/runs/{run_id}").json()

    outside_artifact = sample_workdir.parent / "outside-summary.md"
    outside_artifact.write_text("outside secret", encoding="utf-8")
    summary_path = Path(run["runs_dir"]) / "summary.md"
    summary_path.unlink()
    try:
        summary_path.symlink_to(outside_artifact)
    except OSError as exc:
        pytest.skip(f"symlinks are not available in this environment: {exc}")

    artifacts = client.get(f"/api/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    summary_artifact = next(item for item in artifacts.json() if item["id"] == "summary")
    assert summary_artifact["available"] is False

    preview = client.get(f"/api/runs/{run_id}/artifacts/summary")
    assert preview.status_code == 400

    download = client.get(f"/api/runs/{run_id}/artifacts/summary/download")
    assert download.status_code == 400
    assert "outside secret" not in download.text

def test_api_file_preview_reports_unreadable_file_without_500(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Unreadable File Preview Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=1,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    unreadable_path = sample_workdir / "unreadable.txt"
    unreadable_path.write_text("hidden", encoding="utf-8")
    unreadable_resolved = unreadable_path.resolve()
    original_read_bytes = Path.read_bytes

    def fail_target_read(path: Path) -> bytes:
        if path == unreadable_resolved:
            raise OSError("forced unreadable file")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", fail_target_read)
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=unreadable.txt")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "file"
    assert payload["content"] == ""
    assert payload["preview_error"] == "file could not be read"

def test_file_preview_reports_unreadable_directory(monkeypatch, tmp_path: Path) -> None:
    directory = tmp_path / "blocked"
    directory.mkdir()
    original_iterdir = Path.iterdir

    def fail_target_iterdir(path: Path):
        if path == directory:
            raise OSError("forced unreadable directory")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", fail_target_iterdir)
    payload = preview_existing_path(base=tmp_path, relative_path="blocked", resolved=directory)

    assert payload["kind"] == "directory"
    assert payload["entries"] == []
    assert payload["preview_error"] == "directory could not be read"

def test_run_event_api_rejects_out_of_range_query_params(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for path in (
        "/api/runs/run_test/events?after_id=-1",
        f"/api/runs/run_test/events?after_id={MAX_EVENT_CURSOR_ID + 1}",
        "/api/runs/run_test/events?limit=0",
        "/api/runs/run_test/events?limit=5001",
        "/api/runs/run_test/stream?after_id=-1",
        f"/api/runs/run_test/stream?after_id={MAX_EVENT_CURSOR_ID + 1}",
    ):
        response = client.get(path)
        assert response.status_code == 400
        assert response.json()["error"] == "request validation failed"

def test_run_event_api_rejects_cursor_beyond_current_run_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Cursor Boundary Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    latest_event = service.repository.append_event(run["id"], "run_started", {"status": "running"})
    future_cursor = latest_event["id"] + 1
    client = TestClient(build_app(service=service))

    for path in (
        f"/api/runs/{run['id']}/events?after_id={future_cursor}",
        f"/api/runs/{run['id']}/stream?after_id={future_cursor}",
    ):
        response = client.get(path)
        assert response.status_code == 400
        assert response.json()["error"] == "event cursor is out of range"

def test_api_loop_creation_run_preview_and_stream(
    service_factory,
    sample_spec_file: Path,
    sample_spec_text: str,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    _assert_file_explorer_contract(client, run_id)
    _assert_run_artifact_catalog(client, run_id)
    _assert_run_artifact_previews(client, run_id, sample_spec_text)
    _assert_file_preview_safety(client, run_id, sample_workdir)
    _assert_run_event_streaming(client, run_id)

def test_api_run_key_takeaways_returns_iteration_role_conclusions(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Takeaway Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert response.status_code == 200
    payload = response.json()
    assert payload["build_dir"] == str(sample_workdir.resolve())
    assert payload["log_dir"].endswith(f"/.loopora/runs/{run['id']}")
    assert payload["run_status"] == "succeeded"
    assert payload["task_verdict"]["status"] == "passed"
    assert payload["task_verdict"]["source"] == "gatekeeper"
    assert payload["task_verdict_path"] == "evidence/task_verdict.json"
    _assert_key_takeaway_judgment_contract(payload["judgment_contract"])
    assert set(payload["evidence_buckets"]) == {"proven", "weak", "unproven", "blocking", "residual_risk"}
    assert payload["iteration_count"] >= 1
    assert payload["role_conclusion_count"] >= 2
    latest_iteration = payload["iterations"][0]
    assert latest_iteration["display_iter"] >= 1
    assert latest_iteration["summary"]
    role_names = {item["role_name"] for item in latest_iteration["roles"]}
    assert "Builder" in role_names
    assert "GateKeeper" in role_names
    gatekeeper = next(item for item in latest_iteration["roles"] if item["role_name"] == "GateKeeper")
    assert gatekeeper["composite_score"] is not None
    coverage = payload["evidence_coverage"]
    assert coverage["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage["coverage_path"] == "evidence/coverage.json"
    assert coverage["evidence_count"] == payload["evidence_count"]
    assert coverage["status"] == "weak"
    assert coverage["summary"]["reason"]
    assert coverage["check_count"] == 2
    assert coverage["covered_check_count"] == 2
    assert coverage["missing_check_count"] == 0
    assert set(coverage["covered_check_ids"]) == {"check_001", "check_002"}
    assert coverage["target_count"] >= 5
    assert coverage["missing_target_count"] >= 1
    assert coverage["top_gaps"]
    assert coverage["latest_gatekeeper"]["evidence_refs"]
    assert coverage["evidence_kind_counts"]["inspection"] >= 1
    assert coverage["evidence_kind_counts"]["verdict"] >= 1
    manifest = payload["evidence_manifest"]
    assert manifest["manifest_path"] == "evidence/manifest.json"
    assert manifest["claim_count"] == payload["evidence_count"]
    assert manifest["artifact_backed_claim_count"] == manifest["claim_count"]
    assert manifest["run_artifact_claim_count"] >= 1
    assert set(manifest) >= {
        "direct_proof_claim_count",
        "workspace_artifact_claim_count",
        "ledger_only_claim_count",
        "unverified_claim_count",
        "problem_count",
    }

def test_api_run_key_takeaways_tolerates_invalid_utf8_json_artifacts(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Corrupt Artifact Takeaway Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    (run_dir / "contract" / "compiled_spec.json").write_bytes(b"\xff")
    (run_dir / "contract" / "run_contract.json").write_bytes(b"\xff")
    (run_dir / "evidence" / "ledger.jsonl").write_bytes(b"\xff")
    for handoff_path in run_dir.glob("iterations/iter_*/steps/*/handoff.json"):
        handoff_path.write_bytes(b"\xff")
        break

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_count"] == 0
    assert payload["run_status"] == "succeeded"
    assert payload["judgment_contract"] == empty_judgment_contract()

def test_minimal_run_takeaway_projection_keeps_status_verdict_and_empty_evidence_shape(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    runs_dir = workdir / ".loopora" / "runs" / "run_minimal"
    task_verdict = {
        "status": "insufficient_evidence",
        "source": "rounds_completion",
        "summary": "Evidence did not cross the bar.",
        "buckets": {
            "proven": [],
            "weak": [],
            "unproven": [{"label": "manual review"}],
            "blocking": [],
            "residual_risk": [],
        },
    }

    projection = build_minimal_run_takeaway_projection(
        {
            "id": "run_minimal",
            "status": "succeeded",
            "run_status": "succeeded",
            "task_verdict": task_verdict,
            "workdir": str(workdir),
            "runs_dir": str(runs_dir),
            "summary_md": "# Loopora Run Summary\n\nEvidence did not cross the bar.",
        },
        source_event_id=42,
    )

    assert projection["run_status"] == "succeeded"
    assert projection["task_verdict"]["status"] == "insufficient_evidence"
    assert projection["task_verdict_path"] == ""
    assert projection["evidence_buckets"]["unproven"] == [{"label": "manual review"}]
    assert projection["build_dir"] == str(workdir.resolve())
    assert projection["log_dir"] == str(runs_dir.resolve())
    assert projection["evidence_coverage"]["status"] == "pending"
    assert projection["evidence_manifest"]["claim_count"] == 0
    assert projection["evidence_manifest"]["manifest_path"] == ""
    assert projection["evidence_count"] == 0
    assert projection["iteration_count"] == 0
    assert projection["source_event_id"] == 42
