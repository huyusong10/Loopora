from __future__ import annotations

import json
import time
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.settings import app_home
from loopora.service_agent_adapters import AgentBundleCandidateRequest

KEY_TAKEAWAY_CONTRACT_PATH = "contract/run_contract.json"
KEY_TAKEAWAY_GOAL = "Ship the requested behavior."
KEY_TAKEAWAY_TARGET_IDS = {"done_when.check_001", "gatekeeper.finish"}
KEY_TAKEAWAY_SUCCESS_SURFACE = [
    "The result remains easy for the next role to verify.",
    "The surrounding contract stays clear enough to revise safely.",
]
KEY_TAKEAWAY_FAKE_DONE_STATES = ["A happy-path-only result that leaves the edge path unverifiable."]
KEY_TAKEAWAY_EVIDENCE_SIGNAL = "Prefer structured run artifacts"
KEY_TAKEAWAY_EVIDENCE_PREFERENCE = "Prefer structured run artifacts and reproducible checks over role self-report."
KEY_TAKEAWAY_EVIDENCE_PREFERENCES = [KEY_TAKEAWAY_EVIDENCE_PREFERENCE]
KEY_TAKEAWAY_RESIDUAL_RISK = "Minor copy polish can wait, but unverifiable completion should fail closed."
KEY_TAKEAWAY_CHECK_COUNT = 2

CROWDED_DIRECTORY_CREATED_ENTRIES = 1001
CROWDED_DIRECTORY_PREVIEW_ENTRY_LIMIT = 1000

RECORDED_VERDICT_KIND_BY_STATUS = {
    "passed": "passed_verdict_recorded",
    "passed_with_residual_risk": "passed_with_residual_risk_recorded",
    "insufficient_evidence": "unproven_verdict_recorded",
    "failed": "failed_verdict_recorded",
    "not_evaluated": "not_evaluated_verdict_recorded",
}
RECORDED_VERDICT_TITLE_BY_STATUS = {
    "passed": "Passing evidence verdict recorded",
    "passed_with_residual_risk": "Pass-with-risk verdict recorded",
    "insufficient_evidence": "Unproven evidence verdict recorded",
    "failed": "Failed evidence verdict recorded",
    "not_evaluated": "Unevaluated evidence verdict recorded",
}
RECORDED_VERDICT_PAGE_TEXT_BY_STATUS = {
    "passed": "Passing verdict recorded",
    "passed_with_residual_risk": "Pass-with-risk verdict recorded",
    "insufficient_evidence": "Unproven verdict recorded",
    "failed": "Failed verdict recorded",
    "not_evaluated": "Unevaluated verdict recorded",
}


def _assert_recovery_summary_actions(
    payload: dict,
    *,
    summary_key: str,
    state_key: str,
    state: str,
    expected: list[str],
) -> None:
    actions = payload["next_actions"]
    action_kinds = [item["kind"] for item in actions]
    ready_after = {item["kind"]: item["after_action"] for item in actions if item.get("after_action")}
    ready_now = [item["kind"] for item in actions if not item.get("after_action")]
    assert (payload[summary_key]["next_action_kinds"], action_kinds, payload[summary_key][state_key]) == (expected, expected, state)
    assert (payload["next_action_ready_now_kinds"], payload[summary_key]["next_action_ready_after_actions"]) == (ready_now, ready_after)


def _assert_web_delete_preview_action_projection(
    payload: dict,
    *,
    expected_kind: str = "",
    expected_endpoint: str = "",
) -> None:
    if not expected_kind:
        assert (payload["next_actions"], payload["next_action_kinds"], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (
            [],
            [],
            [],
            {},
        )
        return
    action = payload["next_actions"][0]
    assert action["kind"] == expected_kind
    assert action["target"] == "web_api"
    assert action["method"] == "DELETE"
    assert action["endpoint"] == expected_endpoint
    assert (payload["next_action_kinds"], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (
        [expected_kind],
        [expected_kind],
        {},
    )


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
    assert response.status_code == HTTPStatus.CREATED
    return response.json()["run"]["id"]


def _wait_for_run_success(client: TestClient, run_id: str) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        run_response = client.get(f"/api/runs/{run_id}")
        assert run_response.status_code == HTTPStatus.OK
        if run_response.json()["status"] == "succeeded":
            return
        time.sleep(0.05)
    raise AssertionError(f"run did not succeed before timeout: {run_id}")


def _assert_file_explorer_contract(client: TestClient, run_id: str) -> None:
    explorer = client.get(f"/api/files?run_id={run_id}&root=workdir")
    assert explorer.status_code == HTTPStatus.OK
    assert explorer.json()["kind"] == "directory"
    assert explorer.json()["entries_truncated"] is False

    loopora_dir = client.get(f"/api/files?run_id={run_id}&root=loopora")
    assert loopora_dir.status_code == HTTPStatus.OK
    assert loopora_dir.json()["kind"] == "directory"
    assert loopora_dir.json()["entries_truncated"] is False

    invalid_root = client.get(f"/api/files?run_id={run_id}&root=archive")
    assert invalid_root.status_code == HTTPStatus.BAD_REQUEST
    assert "error" in invalid_root.json()


def _assert_run_artifact_catalog(client: TestClient, run_id: str) -> None:
    artifacts = client.get(f"/api/runs/{run_id}/artifacts")
    assert artifacts.status_code == HTTPStatus.OK
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
    assert artifact.status_code == HTTPStatus.OK
    payload = artifact.json()
    assert payload["kind"] == "file"
    if expected_content is not None:
        assert payload["content"] == expected_content
    if content_fragment is not None:
        assert content_fragment in payload["content"]


def _assert_attachment_download(response, *, filename: str) -> None:
    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert filename in response.headers["content-disposition"]


def _assert_acceptance_evidence_payload(payload: dict) -> None:
    assert payload["evidence_source_event_id"] > 0
    assert payload["evidence_available"] is True
    assert payload["task_verdict_summary"]
    _assert_key_takeaway_judgment_contract(payload["judgment_contract"])
    _assert_key_takeaway_contract_core(
        payload,
        path_key="run_contract_path",
        goal_key="judgment_contract_summary",
    )
    assert isinstance(payload["loop_fit_reasons"], list)
    assert isinstance(payload["execution_strategy"], list)
    assert isinstance(payload["role_postures"], list)
    assert any(KEY_TAKEAWAY_EVIDENCE_SIGNAL in item for item in payload["judgment_tradeoffs"])
    assert payload["task_verdict_path"] == "evidence/task_verdict.json"
    assert payload["coverage_path"] == "evidence/coverage.json"
    assert payload["manifest_path"] == "evidence/manifest.json"
    assert payload["coverage_status"] in {"covered", "weak", "partial", "blocked", "pending"}
    assert payload["evidence_count"] > 0
    assert set(payload["evidence_bucket_counts"]) >= {"proven", "weak", "unproven", "blocking", "residual_risk"}
    target_basis = payload["coverage_target_basis"]
    assert set(target_basis) == {"required", "advisory"}
    assert target_basis["required"]["total"] > 0
    for group in target_basis.values():
        assert set(group) == {"total", "covered", "weak", "unproven", "blocking", "open"}
        assert group["open"] == group["weak"] + group["unproven"] + group["blocking"]
        assert group["total"] >= group["covered"] + group["open"]


def _accept_run_result_and_assert_observation_event(client: TestClient, service, run: dict, loop: dict) -> list[dict]:
    run_before_accept = service.get_run(run["id"])
    loop_before_accept = service.get_loop(loop["id"])
    task_verdict_status = str((run_before_accept.get("task_verdict") or {}).get("status") or "")

    accept_response = client.post(f"/runs/{run['id']}/accept", follow_redirects=False)

    assert accept_response.status_code == HTTPStatus.SEE_OTHER
    redirect_parts = urlsplit(accept_response.headers["location"])
    assert redirect_parts.path == f"/runs/{run['id']}"
    assert parse_qs(redirect_parts.query)["workdir"] == [str(loop["workdir"])]
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
    acceptance_state = service.run_result_acceptance_state(run["id"])
    assert acceptance_state["recorded_coverage_target_basis"] == accepted_events[-1]["payload"][
        "coverage_target_basis"
    ]
    return accepted_events


def _expected_recorded_verdict_kind(task_verdict_status: str) -> str:
    return RECORDED_VERDICT_KIND_BY_STATUS.get(task_verdict_status, "evidence_verdict_recorded")


def _expected_recorded_verdict_title(task_verdict_status: str) -> str:
    return RECORDED_VERDICT_TITLE_BY_STATUS.get(task_verdict_status, "Evidence verdict recorded")


def _expected_recorded_verdict_page_text(task_verdict_status: str) -> str:
    return RECORDED_VERDICT_PAGE_TEXT_BY_STATUS.get(task_verdict_status, "Evidence verdict recorded")


def _assert_run_artifact_previews(client: TestClient, run_id: str, sample_spec_text: str) -> None:
    missing_artifact = client.get(f"/api/runs/{run_id}/artifacts/missing-artifact/download")
    assert missing_artifact.status_code == HTTPStatus.NOT_FOUND
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
    assert binary_preview.status_code == HTTPStatus.OK
    assert binary_preview.json()["kind"] == "file"
    assert binary_preview.json()["is_binary"] is True

    bad_path = client.get(f"/api/files?run_id={run_id}&root=workdir&path=../secret.txt")
    assert bad_path.status_code == HTTPStatus.BAD_REQUEST

    sibling_dir = sample_workdir.parent / "workdir-shadow"
    sibling_dir.mkdir()
    (sibling_dir / "secret.txt").write_text("nope", encoding="utf-8")
    sneaky_path = client.get(f"/api/files?run_id={run_id}&root=workdir&path=../workdir-shadow/secret.txt")
    assert sneaky_path.status_code == HTTPStatus.BAD_REQUEST

    unsafe_md = sample_workdir / "unsafe.md"
    unsafe_md.write_text("# Title\n\n<script>alert('xss')</script>\n", encoding="utf-8")
    unsafe_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=unsafe.md")
    assert unsafe_preview.status_code == HTTPStatus.OK
    assert "<script>" not in unsafe_preview.json()["rendered_html"]
    assert "&lt;script&gt;alert" in unsafe_preview.json()["rendered_html"]

    large_path = sample_workdir / "large.txt"
    large_body = "x" * 1_000_001
    large_path.write_text(large_body, encoding="utf-8")
    large_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=large.txt")
    assert large_preview.status_code == HTTPStatus.OK
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
    for index in range(CROWDED_DIRECTORY_CREATED_ENTRIES):
        (crowded_dir / f"entry-{index:04d}.txt").write_text("", encoding="utf-8")
    crowded_preview = client.get(f"/api/files?run_id={run_id}&root=workdir&path=crowded")
    assert crowded_preview.status_code == HTTPStatus.OK
    crowded_payload = crowded_preview.json()
    assert crowded_payload["kind"] == "directory"
    assert crowded_payload["entries_truncated"] is True
    assert len(crowded_payload["entries"]) == CROWDED_DIRECTORY_PREVIEW_ENTRY_LIMIT


def _stream_body(stream_response) -> str:
    return "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in stream_response.iter_text())


def _assert_run_event_streaming(client: TestClient, run_id: str) -> None:
    events = client.get(f"/api/runs/{run_id}/events")
    assert events.status_code == HTTPStatus.OK
    event_payload = events.json()
    assert event_payload

    with client.stream("GET", f"/api/runs/{run_id}/stream") as stream_response:
        assert stream_response.status_code == HTTPStatus.OK
        body = _stream_body(stream_response)
    assert "run_finished" in body or "keep-alive" in body

    latest_event_id = event_payload[-1]["id"]
    with client.stream("GET", f"/api/runs/{run_id}/stream?after_id={latest_event_id}") as stream_response:
        assert stream_response.status_code == HTTPStatus.OK
        delta_body = _stream_body(stream_response)
    assert "run_started" not in delta_body

    reconnect_from = event_payload[0]["id"]
    with client.stream(
        "GET",
        f"/api/runs/{run_id}/stream",
        headers={"Last-Event-ID": str(reconnect_from)},
    ) as stream_response:
        assert stream_response.status_code == HTTPStatus.OK
        reconnect_body = _stream_body(stream_response)
    assert f"id: {reconnect_from}\n" not in reconnect_body


def _assert_key_takeaway_judgment_contract(judgment_contract: dict) -> None:
    _assert_key_takeaway_contract_core(judgment_contract, path_key="contract_path", goal_key="goal")
    assert KEY_TAKEAWAY_EVIDENCE_PREFERENCE in judgment_contract["judgment_tradeoffs"]
    assert any("one coherent attempt that improves the main path" in item for item in judgment_contract["judgment_tradeoffs"])


def _assert_key_takeaway_contract_core(payload: dict, *, path_key: str, goal_key: str) -> None:
    assert payload[path_key] == KEY_TAKEAWAY_CONTRACT_PATH
    assert payload[goal_key] == KEY_TAKEAWAY_GOAL
    assert payload["check_mode"] == "specified"
    assert payload["check_count"] == KEY_TAKEAWAY_CHECK_COUNT
    assert payload["completion_mode"] == "gatekeeper"
    assert payload["strategy_preset"]
    assert "workflow_preset" not in payload
    assert {target["id"] for target in payload["coverage_targets"]} >= KEY_TAKEAWAY_TARGET_IDS
    assert payload["execution_strategy"]
    assert isinstance(payload["local_governance"], list)
    assert payload["success_surface"] == KEY_TAKEAWAY_SUCCESS_SURFACE
    assert payload["fake_done_states"] == KEY_TAKEAWAY_FAKE_DONE_STATES
    assert payload["evidence_preferences"] == KEY_TAKEAWAY_EVIDENCE_PREFERENCES
    assert payload["residual_risk"] == KEY_TAKEAWAY_RESIDUAL_RISK


def _assert_run_detail_terminal_actions_page(client: TestClient, run: dict, loop: dict) -> None:
    page_response = client.get(f"/runs/{run['id']}")
    assert page_response.status_code == HTTPStatus.OK
    assert "Run status" in page_response.text
    assert "Task verdict" in page_response.text
    assert 'data-testid="run-status-card"' in page_response.text
    assert 'data-testid="run-task-verdict-card"' in page_response.text
    assert 'data-testid="run-latest-event-card"' in page_response.text
    assert 'data-testid="run-agent-handoff-card"' in page_response.text
    assert 'data-testid="run-export-loop-button"' in page_response.text
    assert 'data-testid="run-export-evidence-button"' in page_response.text
    assert f"/bundles/derive/export?loop_id={loop['id']}" in page_response.text
    assert 'data-testid="run-accept-result-button"' in page_response.text
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert 'data-testid="run-result-decision"' in page_response.text
    assert page_response.text.count('data-testid="run-improve-chat-button"') == 1
    assert 'data-testid="run-evidence-improve-button"' not in page_response.text
    assert "Run next evidence pass" in page_response.text
    assert '<span data-lang="en">Rerun</span>' not in page_response.text
    assert 'id="stop-run"' not in page_response.text

    export_response = client.get(f"/bundles/derive/export?loop_id={loop['id']}")
    assert export_response.status_code == HTTPStatus.OK
    assert export_response.headers["content-type"].startswith("application/yaml")
    assert "Rerun From Detail Loop" in export_response.text


def _wait_for_run_terminal_status(service, run_id: str) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
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
    assert preview_control_summary["residual_risk_policy"]
    assert preview_control_summary["role_postures"]
    assert "traceability" in preview_control_summary
    assert preview["traceability"] == preview_control_summary["traceability"]
    assert isinstance(preview["traceability"]["items"], list)
    assert preview["traceability"]["required_count"] >= preview["traceability"]["mapped_count"] >= 0
    assert preview["diagnostics"] == preview_control_summary["diagnostics"]
    assert isinstance(preview["diagnostics"], list)


__all__ = [
    "_accept_run_result_and_assert_observation_event",
    "_assert_acceptance_evidence_payload",
    "_assert_artifact_file",
    "_assert_attachment_download",
    "_assert_bundle_preview_control_summary",
    "_assert_file_explorer_contract",
    "_assert_file_preview_safety",
    "_assert_key_takeaway_judgment_contract",
    "_assert_run_artifact_catalog",
    "_assert_run_artifact_previews",
    "_assert_run_detail_terminal_actions_page",
    "_assert_run_event_streaming",
    "_create_api_loop_run",
    "_expected_recorded_verdict_kind",
    "_expected_recorded_verdict_page_text",
    "_expected_recorded_verdict_title",
    "_read_service_log_records",
    "_start_agent_first_loop",
    "_stream_body",
    "_wait_for_run_success",
    "_wait_for_run_terminal_status",
]
