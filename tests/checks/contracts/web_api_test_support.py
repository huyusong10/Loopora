from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.settings import app_home
from loopora.service_agent_adapters import AgentBundleCandidateRequest

def _read_service_log_records() -> list[dict]:
    return [json.loads(line) for line in (app_home() / "logs" / "service.log").read_text(encoding="utf-8").splitlines() if line.strip()]

def _start_agent_first_loop(service, *, tmp_path: Path, workdir: Path) -> dict:
    bundle_file = tmp_path / "agent-first-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message=(
                "Ship the focused starter experience. The primary user flow must work end to end, "
                "use project-owned evidence, avoid happy-path claim only, keep a clear handoff, "
                "and let GateKeeper reject weak proof."
            ),
            bundle_file=bundle_file,
            context_id="web-api-agent-first",
            entry_source="codex_project_skill",
        )
    )
    return service.start_agent_loop(
        "codex",
        workdir=workdir,
        context_id="web-api-agent-first",
        entry_source="codex_project_skill",
        execute_async=False,
    )

def _create_api_loop_run(client: TestClient, sample_spec_file: Path, sample_workdir: Path) -> str:
    response = client.post(
        "/api/loops",
        json={
            "name": "API Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": True,
        },
    )
    assert response.status_code == 201
    return response.json()["run"]["id"]

def _wait_for_run_success(client: TestClient, run_id: str) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        run_response = client.get(f"/api/runs/{run_id}")
        assert run_response.status_code == 200
        if run_response.json()["status"] == "succeeded":
            return
        time.sleep(0.05)
    raise AssertionError(f"run did not succeed before timeout: {run_id}")

def _assert_file_explorer_contract(client: TestClient, run_id: str) -> None:
    explorer = client.get(f"/api/files?run_id={run_id}&root=workdir")
    assert explorer.status_code == 200
    assert explorer.json()["kind"] == "directory"
    assert explorer.json()["entries_truncated"] is False

    loopora_dir = client.get(f"/api/files?run_id={run_id}&root=loopora")
    assert loopora_dir.status_code == 200
    assert loopora_dir.json()["kind"] == "directory"
    assert loopora_dir.json()["entries_truncated"] is False

    invalid_root = client.get(f"/api/files?run_id={run_id}&root=archive")
    assert invalid_root.status_code == 400
    assert "error" in invalid_root.json()

def _assert_run_artifact_catalog(client: TestClient, run_id: str) -> None:
    artifacts = client.get(f"/api/runs/{run_id}/artifacts")
    assert artifacts.status_code == 200
    artifact_payload = artifacts.json()
    assert any(item["id"] == "original-spec" and item["available"] for item in artifact_payload)
    assert any(item["id"] == "summary" and item["available"] for item in artifact_payload)
    assert any(item["id"] == "evidence-ledger" and item["available"] for item in artifact_payload)
    assert any(item["id"] == "evidence-coverage" and item["available"] for item in artifact_payload)
    assert any(item["id"] == "evidence-manifest" and item["available"] for item in artifact_payload)
    assert any(item["id"] == "task-verdict" and item["available"] for item in artifact_payload)

    artifacts_by_id = {item["id"]: item for item in artifact_payload}
    assert artifacts_by_id["original-spec"]["label_zh"] == "原始 Loop 契约"
    assert artifacts_by_id["compiled-spec"]["label_zh"] == "编译后契约"
    assert "假完成风险" in artifacts_by_id["compiled-spec"]["description_zh"]
    assert "执行策略" in artifacts_by_id["compiled-spec"]["description_zh"]
    assert "Evidence Preferences" in artifacts_by_id["compiled-spec"]["description_en"]
    assert "Execution Strategy" in artifacts_by_id["compiled-spec"]["description_en"]
    assert "Residual Risk" in artifacts_by_id["compiled-spec"]["description_en"]
    assert artifacts_by_id["workflow-manifest"]["label_zh"] == "流程清单"
    assert "规范证据账本" in artifacts_by_id["evidence-ledger"]["description_zh"]
    assert artifacts_by_id["task-verdict"]["label_zh"] == "Loop 裁决"
    assert "终态 Loop 裁决" in artifacts_by_id["task-verdict"]["description_zh"]
    for artifact_id in (
        "summary",
        "original-spec",
        "compiled-spec",
        "workflow-manifest",
        "run-contract",
        "latest-state",
        "timeline-events",
        "timeline-iterations",
        "timeline-metrics",
        "evidence-ledger",
        "evidence-coverage",
        "evidence-manifest",
        "task-verdict",
    ):
        zh_metadata = f"{artifacts_by_id[artifact_id]['label_zh']} {artifacts_by_id[artifact_id]['description_zh']}"
        assert "Spec" not in zh_metadata
        assert "workflow" not in zh_metadata
        assert "canonical" not in zh_metadata
        assert " run " not in f" {zh_metadata} "
        assert "任务裁决" not in zh_metadata

def _assert_artifact_file(
    client: TestClient,
    run_id: str,
    artifact_id: str,
    *,
    expected_content: str | None = None,
    content_fragment: str | None = None,
) -> None:
    artifact = client.get(f"/api/runs/{run_id}/artifacts/{artifact_id}")
    assert artifact.status_code == 200
    payload = artifact.json()
    assert payload["kind"] == "file"
    if expected_content is not None:
        assert payload["content"] == expected_content
    if content_fragment is not None:
        assert content_fragment in payload["content"]

def _assert_attachment_download(response, *, filename: str) -> None:
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert filename in response.headers["content-disposition"]

def _assert_acceptance_evidence_payload(payload: dict) -> None:
    assert payload["evidence_source_event_id"] > 0
    assert payload["evidence_available"] is True
    assert payload["task_verdict_summary"]
    _assert_key_takeaway_judgment_contract(payload["judgment_contract"])
    assert payload["run_contract_path"] == "contract/run_contract.json"
    assert payload["judgment_contract_summary"] == "Ship the requested behavior."
    assert payload["check_mode"] == "specified"
    assert payload["check_count"] == 2
    assert payload["completion_mode"] == "gatekeeper"
    assert payload["workflow_preset"]
    assert any(target["id"] == "done_when.check_001" for target in payload["coverage_targets"])
    assert any(target["id"] == "gatekeeper.finish" for target in payload["coverage_targets"])
    assert isinstance(payload["loop_fit_reasons"], list)
    assert isinstance(payload["execution_strategy"], list)
    assert payload["execution_strategy"]
    assert isinstance(payload["local_governance"], list)
    assert isinstance(payload["role_postures"], list)
    assert any("Prefer structured run artifacts" in item for item in payload["judgment_tradeoffs"])
    assert payload["success_surface"] == [
        "The result remains easy for the next role to verify.",
        "The surrounding contract stays clear enough to revise safely.",
    ]
    assert payload["fake_done_states"] == ["A happy-path-only result that leaves the edge path unverifiable."]
    assert payload["evidence_preferences"] == [
        "Prefer structured run artifacts and reproducible checks over role self-report."
    ]
    assert payload["residual_risk"] == "Minor copy polish can wait, but unverifiable completion should fail closed."
    assert payload["task_verdict_path"] == "evidence/task_verdict.json"
    assert payload["coverage_path"] == "evidence/coverage.json"
    assert payload["manifest_path"] == "evidence/manifest.json"
    assert payload["coverage_status"] in {"covered", "weak", "partial", "blocked", "pending"}
    assert payload["evidence_count"] > 0
    assert set(payload["evidence_bucket_counts"]) >= {"proven", "weak", "unproven", "blocking", "residual_risk"}

def _accept_run_result_and_assert_observation_event(client: TestClient, service, run: dict, loop: dict) -> list[dict]:
    run_before_accept = service.get_run(run["id"])
    loop_before_accept = service.get_loop(loop["id"])
    task_verdict_status = str((run_before_accept.get("task_verdict") or {}).get("status") or "")

    accept_response = client.post(f"/runs/{run['id']}/accept", follow_redirects=False)

    assert accept_response.status_code == 303
    assert accept_response.headers["location"] == f"/runs/{run['id']}"
    run_after_accept = service.get_run(run["id"])
    loop_after_accept = service.get_loop(loop["id"])
    assert run_after_accept["status"] == run_before_accept["status"]
    assert run_after_accept["task_verdict"] == run_before_accept["task_verdict"]
    assert loop_after_accept["workflow_json"] == loop_before_accept["workflow_json"]
    accepted_events = service.recent_run_events(run["id"], event_types={"run_result_accepted"})
    assert accepted_events
    assert accepted_events[-1]["payload"]["status"] == run["status"]
    assert accepted_events[-1]["payload"]["task_verdict_status"]
    assert accepted_events[-1]["payload"]["recorded_verdict_kind"] == _expected_recorded_verdict_kind(task_verdict_status)
    assert accepted_events[-1]["payload"]["evidence_source_event_id"] < accepted_events[-1]["id"]
    _assert_acceptance_evidence_payload(accepted_events[-1]["payload"])
    return accepted_events

def _expected_recorded_verdict_kind(task_verdict_status: str) -> str:
    return {
        "passed": "passed_verdict_recorded",
        "passed_with_residual_risk": "passed_with_residual_risk_recorded",
        "insufficient_evidence": "unproven_verdict_recorded",
        "failed": "failed_verdict_recorded",
        "not_evaluated": "not_evaluated_verdict_recorded",
    }.get(task_verdict_status, "evidence_verdict_recorded")

def _expected_recorded_verdict_title(task_verdict_status: str) -> str:
    return {
        "passed": "Passing evidence verdict recorded",
        "passed_with_residual_risk": "Pass-with-risk verdict recorded",
        "insufficient_evidence": "Unproven evidence verdict recorded",
        "failed": "Failed evidence verdict recorded",
        "not_evaluated": "Unevaluated evidence verdict recorded",
    }.get(task_verdict_status, "Evidence verdict recorded")

def _expected_recorded_verdict_page_text(task_verdict_status: str) -> str:
    return {
        "passed": "Passing verdict recorded",
        "passed_with_residual_risk": "Pass-with-risk verdict recorded",
        "insufficient_evidence": "Unproven verdict recorded",
        "failed": "Failed verdict recorded",
        "not_evaluated": "Unevaluated verdict recorded",
    }.get(task_verdict_status, "Evidence verdict recorded")

def _assert_run_artifact_previews(client: TestClient, run_id: str, sample_spec_text: str) -> None:
    missing_artifact = client.get(f"/api/runs/{run_id}/artifacts/missing-artifact/download")
    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["error"] == "unknown artifact"
    summary_download = client.get(f"/api/runs/{run_id}/artifacts/summary/download")
    _assert_attachment_download(summary_download, filename="summary.md")
    _assert_artifact_file(client, run_id, "original-spec", expected_content=sample_spec_text)
    _assert_artifact_file(client, run_id, "summary", content_fragment="Loopora Run Summary")
    _assert_artifact_file(client, run_id, "latest-state", content_fragment='"latest_iteration"')
    _assert_artifact_file(client, run_id, "evidence-ledger", content_fragment="gatekeeper")
    _assert_artifact_file(client, run_id, "evidence-coverage", content_fragment='"targets"')
    _assert_artifact_file(client, run_id, "evidence-manifest", content_fragment='"verification_status"')
    _assert_artifact_file(client, run_id, "task-verdict", content_fragment='"status"')

def _assert_file_preview_safety(client: TestClient, run_id: str, sample_workdir: Path) -> None:
    binary_path = sample_workdir / ".DS_Store"
    binary_path.write_bytes(b"\x00\x01\x02binary-data")
    binary_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=.DS_Store")
    assert binary_preview.status_code == 200
    assert binary_preview.json()["kind"] == "file"
    assert binary_preview.json()["is_binary"] is True

    bad_path = client.get(f"/api/files?run_id={run_id}&root=workdir&path=../secret.txt")
    assert bad_path.status_code == 400

    sibling_dir = sample_workdir.parent / "workdir-shadow"
    sibling_dir.mkdir()
    (sibling_dir / "secret.txt").write_text("nope", encoding="utf-8")
    sneaky_path = client.get(f"/api/files?run_id={run_id}&root=workdir&path=../workdir-shadow/secret.txt")
    assert sneaky_path.status_code == 400

    unsafe_md = sample_workdir / "unsafe.md"
    unsafe_md.write_text("# Title\n\n<script>alert('xss')</script>\n", encoding="utf-8")
    unsafe_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=unsafe.md")
    assert unsafe_preview.status_code == 200
    assert "<script>" not in unsafe_preview.json()["rendered_html"]
    assert "&lt;script&gt;alert" in unsafe_preview.json()["rendered_html"]

    large_path = sample_workdir / "large.txt"
    large_body = "x" * 1_000_001
    large_path.write_text(large_body, encoding="utf-8")
    large_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=large.txt")
    assert large_preview.status_code == 200
    large_payload = large_preview.json()
    assert large_payload["kind"] == "file"
    assert large_payload["preview_omitted"] is True
    assert large_payload["content"] == ""
    assert large_payload["size_bytes"] == len(large_body)
    assert "too large" in large_payload["preview_error"]

    large_download = client.get(f"/api/files/download?run_id={run_id}&root=workdir&path=large.txt")
    _assert_attachment_download(large_download, filename="large.txt")
    assert large_download.content == large_body.encode()

    html_download_path = sample_workdir / "untrusted.html"
    html_download_path.write_text("<script>alert('xss')</script>", encoding="utf-8")
    html_download = client.get(f"/api/files/download?run_id={run_id}&root=workdir&path=untrusted.html")
    _assert_attachment_download(html_download, filename="untrusted.html")

    crowded_dir = sample_workdir / "crowded"
    crowded_dir.mkdir()
    for index in range(1001):
        (crowded_dir / f"entry-{index:04d}.txt").write_text("", encoding="utf-8")
    crowded_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=crowded")
    assert crowded_preview.status_code == 200
    crowded_payload = crowded_preview.json()
    assert crowded_payload["kind"] == "directory"
    assert crowded_payload["entries_truncated"] is True
    assert len(crowded_payload["entries"]) == 1000

def _stream_body(stream_response) -> str:
    return "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in stream_response.iter_text())

def _assert_run_event_streaming(client: TestClient, run_id: str) -> None:
    events = client.get(f"/api/runs/{run_id}/events")
    assert events.status_code == 200
    event_payload = events.json()
    assert event_payload

    with client.stream("GET", f"/api/runs/{run_id}/stream") as stream_response:
        assert stream_response.status_code == 200
        body = _stream_body(stream_response)
    assert "run_finished" in body or "keep-alive" in body

    latest_event_id = event_payload[-1]["id"]
    with client.stream("GET", f"/api/runs/{run_id}/stream?after_id={latest_event_id}") as stream_response:
        assert stream_response.status_code == 200
        delta_body = _stream_body(stream_response)
    assert "run_started" not in delta_body

    reconnect_from = event_payload[0]["id"]
    with client.stream(
        "GET",
        f"/api/runs/{run_id}/stream",
        headers={"Last-Event-ID": str(reconnect_from)},
    ) as stream_response:
        assert stream_response.status_code == 200
        reconnect_body = _stream_body(stream_response)
    assert f"id: {reconnect_from}\n" not in reconnect_body

def _assert_key_takeaway_judgment_contract(judgment_contract: dict) -> None:
    assert judgment_contract["contract_path"] == "contract/run_contract.json"
    assert judgment_contract["goal"] == "Ship the requested behavior."
    assert judgment_contract["check_mode"] == "specified"
    assert judgment_contract["check_count"] == 2
    assert judgment_contract["completion_mode"] == "gatekeeper"
    assert judgment_contract["workflow_preset"]
    assert any(target["id"] == "done_when.check_001" for target in judgment_contract["coverage_targets"])
    assert any(target["id"] == "gatekeeper.finish" for target in judgment_contract["coverage_targets"])
    assert judgment_contract["success_surface"] == [
        "The result remains easy for the next role to verify.",
        "The surrounding contract stays clear enough to revise safely.",
    ]
    assert judgment_contract["fake_done_states"] == ["A happy-path-only result that leaves the edge path unverifiable."]
    assert judgment_contract["evidence_preferences"] == [
        "Prefer structured run artifacts and reproducible checks over role self-report."
    ]
    assert judgment_contract["execution_strategy"]
    assert isinstance(judgment_contract["local_governance"], list)
    assert "Prefer structured run artifacts and reproducible checks over role self-report." in judgment_contract["judgment_tradeoffs"]
    assert any("one coherent attempt that improves the main path" in item for item in judgment_contract["judgment_tradeoffs"])
    assert judgment_contract["residual_risk"] == "Minor copy polish can wait, but unverifiable completion should fail closed."

def _assert_run_detail_terminal_actions_page(client: TestClient, run: dict, loop: dict) -> None:
    page_response = client.get(f"/runs/{run['id']}")
    assert page_response.status_code == 200
    assert "Run status" in page_response.text
    assert "Task verdict" in page_response.text
    assert 'data-testid="run-status-card"' in page_response.text
    assert 'data-testid="run-task-verdict-card"' in page_response.text
    assert 'data-testid="run-latest-event-card"' in page_response.text
    assert 'data-testid="run-agent-handoff-card"' in page_response.text
    assert 'data-testid="run-export-loop-button"' in page_response.text
    assert f"/bundles/derive/export?loop_id={loop['id']}" in page_response.text
    assert 'data-testid="run-accept-result-button"' in page_response.text
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert "Run next evidence pass" in page_response.text
    assert '<span data-lang="en">Rerun</span>' not in page_response.text
    assert 'id="stop-run"' not in page_response.text

    export_response = client.get(f"/bundles/derive/export?loop_id={loop['id']}")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/yaml")
    assert "Rerun From Detail Loop" in export_response.text

def _wait_for_run_terminal_status(service, run_id: str) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        new_run = service.get_run(run_id)
        if new_run["status"] in {"succeeded", "failed", "stopped"}:
            break
        time.sleep(0.05)
    assert service.get_run(run_id)["status"] in {"succeeded", "failed", "stopped"}

def _assert_bundle_preview_control_summary(preview: dict) -> None:
    preview_control_summary = preview["control_summary"]
    assert preview_control_summary["gatekeeper"]["requires_evidence_refs"] is True
    assert preview_control_summary["coverage"]["check_count"] >= 1
    assert preview_control_summary["coverage"]["target_count"] >= preview_control_summary["coverage"]["check_count"]
    assert isinstance(preview_control_summary["loop_fit_reasons"], list)
    assert preview_control_summary["residual_risk_policy"] and preview_control_summary["role_postures"]
    assert "traceability" in preview_control_summary
    assert preview["traceability"] == preview_control_summary["traceability"]
    assert isinstance(preview["traceability"]["items"], list)
    assert preview["traceability"]["required_count"] >= preview["traceability"]["mapped_count"] >= 0
    assert preview["diagnostics"] == preview_control_summary["diagnostics"]
    assert isinstance(preview["diagnostics"], list)

__all__ = [
    '_accept_run_result_and_assert_observation_event',
    '_assert_acceptance_evidence_payload',
    '_assert_artifact_file',
    '_assert_attachment_download',
    '_assert_bundle_preview_control_summary',
    '_assert_file_explorer_contract',
    '_assert_file_preview_safety',
    '_assert_key_takeaway_judgment_contract',
    '_assert_run_artifact_catalog',
    '_assert_run_artifact_previews',
    '_assert_run_detail_terminal_actions_page',
    '_assert_run_event_streaming',
    '_create_api_loop_run',
    '_expected_recorded_verdict_kind',
    '_expected_recorded_verdict_page_text',
    '_expected_recorded_verdict_title',
    '_read_service_log_records',
    '_start_agent_first_loop',
    '_stream_body',
    '_wait_for_run_success',
    '_wait_for_run_terminal_status',
]
