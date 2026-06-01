from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.branding import state_dir_for_workdir
from loopora.settings import app_home, configure_logging
import loopora.web as web_module
from loopora.web import build_app

from web_api_test_support import (
    _read_service_log_records,
    _start_agent_first_loop,
    _accept_run_result_and_assert_observation_event,
    _expected_recorded_verdict_title,
    _expected_recorded_verdict_page_text,
    _assert_run_detail_terminal_actions_page,
    _wait_for_run_terminal_status,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_system_api_guard_has_dedicated_route_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    system_source = (REPO_ROOT / "src" / "loopora" / "web_system_api.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_system_api import register_system_api_routes" in editor_source
    assert "register_system_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _guard_system_api_request",
        "def _system_request_is_same_origin",
        '"/api/system/pick-directory"',
        '"/api/system/reveal-path"',
    ):
        assert marker in system_source
        assert marker not in editor_source
    assert "web_system_api.py" in design_source


def test_api_run_observation_snapshot_uses_consistent_event_cutoff(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Snapshot Cutoff Loop",
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
    service.repository.append_event(run["id"], "run_started", {"status": "running"})
    service.repository.append_event(
        run["id"],
        "role_started",
        {"role": "generator", "step_id": "initial_step", "iter": 0},
        role="generator",
    )
    service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "visible before cutoff"},
        role="generator",
    )

    original_recent_rows = service.repository._recent_event_rows_for_connection
    captured: dict[str, int] = {}

    def recent_rows_with_concurrent_append(connection, run_id: str, **kwargs):
        captured.setdefault("cutoff", int(kwargs.get("max_event_id") or 0))
        if "late_id" not in captured:
            late_event = service.repository.append_event(
                run_id,
                "role_started",
                {"role": "generator", "step_id": "late_step", "iter": 1},
                role="generator",
            )
            captured["late_id"] = late_event["id"]
        return original_recent_rows(connection, run_id, **kwargs)

    monkeypatch.setattr(service.repository, "_recent_event_rows_for_connection", recent_rows_with_concurrent_append)
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_event_id"] == captured["cutoff"]
    assert payload["key_takeaways"]["source_event_id"] == captured["cutoff"]
    for event in payload["timeline_events"] + payload["console_events"] + payload["progress_events"]:
        assert event["id"] <= payload["latest_event_id"]
        assert event["id"] != captured["late_id"]

    events_response = client.get(f"/api/runs/{run['id']}/events?after_id={payload['latest_event_id']}")
    assert events_response.status_code == 200
    assert any(event["id"] == captured["late_id"] for event in events_response.json())

def test_api_reveal_path_uses_native_host_shortcut(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_reveal(path: str) -> str:
        called.append(path)
        return path

    monkeypatch.setattr(web_module, "reveal_path", fake_reveal)
    response = client.post("/api/system/reveal-path", json={"path": str(sample_workdir)})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called == [str(sample_workdir)]

def test_system_picker_requires_post_and_same_origin(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_pick_directory(start_path: str | None = None) -> str:
        called.append(start_path or "")
        return str(sample_workdir)

    monkeypatch.setattr(web_module, "pick_directory", fake_pick_directory)

    old_get = client.get(f"/api/system/pick-directory?start_path={sample_workdir}")
    assert old_get.status_code == 405
    assert called == []

    cross_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://evil.example"},
    )
    assert cross_origin.status_code == 403
    assert "same origin" in cross_origin.json()["error"]
    assert called == []

    malformed_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://testserver:bad"},
    )
    assert malformed_origin.status_code == 403
    assert "same origin" in malformed_origin.json()["error"]
    assert called == []

    same_origin = client.post(
        "/api/system/pick-directory",
        json={"start_path": str(sample_workdir)},
        headers={"Origin": "http://testserver"},
    )
    assert same_origin.status_code == 200
    assert same_origin.json()["path"] == str(sample_workdir)
    assert called == [str(sample_workdir)]

def test_system_reveal_rejects_cross_origin_before_callback(monkeypatch, service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    called: list[str] = []

    def fake_reveal(path: str) -> str:
        called.append(path)
        return path

    monkeypatch.setattr(web_module, "reveal_path", fake_reveal)
    response = client.post(
        "/api/system/reveal-path",
        json={"path": str(sample_workdir)},
        headers={"Referer": "http://evil.example/page"},
    )

    assert response.status_code == 403
    assert "same origin" in response.json()["error"]
    assert called == []

def test_api_json_endpoints_reject_invalid_json_body(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/markdown/render",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert "invalid JSON body" in response.json()["error"]

    invalid_utf8_response = client.post(
        "/api/markdown/render",
        content=b'{"markdown":"\xff"}',
        headers={"content-type": "application/json"},
    )

    assert invalid_utf8_response.status_code == 400
    assert "invalid JSON body" in invalid_utf8_response.json()["error"]
    assert "UTF-8" in invalid_utf8_response.json()["error"]

def test_api_json_endpoints_require_object_bodies(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post("/api/markdown/render", json=["not", "an", "object"])

    assert response.status_code == 400
    assert response.json()["error"] == "request body must be a JSON object"

def test_api_file_preview_reports_json_parse_errors(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="JSON Preview Loop",
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
    broken_json_path = sample_workdir / "broken.json"
    broken_json_path.write_text("{\n", encoding="utf-8")

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=broken.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "file"
    assert payload["content"] == "{\n"
    assert payload["parse_error"]

def test_api_file_preview_keeps_valid_jsonl_lines_when_some_are_broken(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="JSONL Preview Loop",
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
    log_path = sample_workdir / "events.jsonl"
    log_path.write_text('{"event":"good"}\n{\n{"event":"also-good"}\n', encoding="utf-8")

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=events.jsonl")

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "file"
    assert '"event": "good"' in payload["content"]
    assert '"event": "also-good"' in payload["content"]
    assert payload["jsonl_parse_errors"] == [{"line": 2, "error": "Expecting property name enclosed in double quotes"}]

def test_api_run_events_and_stream_require_a_real_run(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    events_response = client.get("/api/runs/missing-run/events")
    assert events_response.status_code == 404
    assert "unknown run" in events_response.json()["error"]

    snapshot_response = client.get("/api/runs/missing-run/observation-snapshot")
    assert snapshot_response.status_code == 404
    assert "unknown run" in snapshot_response.json()["error"]

    stream_response = client.get("/api/runs/missing-run/stream")
    assert stream_response.status_code == 404
    assert "unknown run" in stream_response.json()["error"]

def test_api_run_lifecycle_reports_not_found_and_conflict_status_codes(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    missing_loop_response = client.post("/api/loops/missing-loop/runs")
    assert missing_loop_response.status_code == 404
    assert "unknown loop" in missing_loop_response.json()["error"]

    loop = service.create_loop(
        name="Conflict Loop",
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
    service.start_run(loop["id"])

    conflict_response = client.post(f"/api/loops/{loop['id']}/runs")
    assert conflict_response.status_code == 409
    assert "active run" in conflict_response.json()["error"]

def test_api_run_lifecycle_rejects_web_headless_start_for_agent_first_loop(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    started = _start_agent_first_loop(service, tmp_path=tmp_path, workdir=sample_workdir)
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/loops/{started['run']['loop_id']}/runs")

    assert response.status_code == 409
    payload = response.json()
    assert "agent-first Loop runs" in payload["error"]
    assert payload["agent_entry_start"]["slash_command"] == "/loopora-run"
    assert payload["agent_entry_start"]["execution_plane"] == "agent_native"
    assert payload["agent_entry_start"]["linked_run_id"] == started["run"]["id"]
    assert payload["agent_entry_start"]["host_context_id"] == "web-api-agent-first"
    assert "loopora agent codex run" in payload["agent_entry_start"]["loop_command"]
    assert "--context-id web-api-agent-first" in payload["agent_entry_start"]["loop_command"]
    assert "--json" in payload["agent_entry_start"]["loop_command"]
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1

def test_api_runtime_activity_reports_running_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success", role_delay=0.4)
    loop = service.create_loop(
        name="Runtime Activity Loop",
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
    service.start_run_async(run["id"])

    deadline = time.time() + 5
    while time.time() < deadline:
        current = service.get_run(run["id"])
        if current["status"] == "running":
            break
        time.sleep(0.05)

    client = TestClient(build_app(service=service))
    response = client.get("/api/runtime/activity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_home"]
    assert payload["running_count"] >= 1
    assert payload["has_running_runs"] is True
    assert any(item["id"] == run["id"] and item["loop_name"] == "Runtime Activity Loop" for item in payload["runs"])

    service.stop_run(run["id"])

def test_api_local_asset_diagnostics_reports_orphans_and_missing_dirs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Diagnostics Workdir Loop",
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
    assert loop["id"]
    run = service.start_run(loop["id"])
    run_dir = Path(run["runs_dir"])
    if run_dir.exists():
        shutil.rmtree(run_dir)
    orphan_run_dir = state_dir_for_workdir(sample_workdir) / "runs" / "run_orphan"
    orphan_run_dir.mkdir(parents=True)
    orphan_alignment_dir = state_dir_for_workdir(sample_workdir) / "alignment_sessions" / "align_orphan"
    orphan_alignment_dir.mkdir(parents=True)
    orphan_bundle_dir = app_home() / "bundles" / "bundle_orphan"
    orphan_bundle_dir.mkdir(parents=True)
    service.repository.create_bundle(
        {
            "id": "bundle_missing_dir",
            "name": "Missing Dir Bundle",
            "description": "",
            "collaboration_summary": "",
            "workdir": str(sample_workdir),
            "loop_id": "",
            "orchestration_id": "",
            "role_definition_ids": [],
            "source_bundle_id": "",
            "revision": 1,
            "imported_from_path": "",
        }
    )
    missing_bundle_dir = service._bundle_dir("bundle_missing_dir")
    if missing_bundle_dir.exists():
        shutil.rmtree(missing_bundle_dir)
    missing_registry_run_dir = state_dir_for_workdir(sample_workdir) / "runs" / "run_registry_missing"
    service.repository.upsert_local_asset_root(
        resource_type="run",
        resource_id="run_registry_missing",
        path=missing_registry_run_dir,
        workdir=str(sample_workdir),
        state="active",
    )

    client = TestClient(build_app(service=service))
    response = client.get("/api/diagnostics/local-assets")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"orphan_alignment_dirs", "orphan_bundle_dirs", "orphan_run_dirs", "record_without_dir"}
    assert any(item["session_id"] == "align_orphan" for item in payload["orphan_alignment_dirs"])
    assert any(item["bundle_id"] == "bundle_orphan" for item in payload["orphan_bundle_dirs"])
    assert any(item["run_id"] == "run_orphan" and item["source"] == "recent_workdir" for item in payload["orphan_run_dirs"])
    assert any(item["resource_type"] == "bundle" and item["resource_id"] == "bundle_missing_dir" for item in payload["record_without_dir"])
    assert any(item["resource_type"] == "run" and item["resource_id"] == run["id"] for item in payload["record_without_dir"])
    assert any(item["resource_type"] == "run" and item["resource_id"] == "run_registry_missing" for item in payload["record_without_dir"])


def test_local_asset_diagnostics_delegate_orphan_dir_projection() -> None:
    diagnostics_source = (REPO_ROOT / "src" / "loopora" / "service_local_asset_diagnostics.py").read_text(
        encoding="utf-8"
    )
    orphans_source = (REPO_ROOT / "src" / "loopora" / "service_local_asset_orphans.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_local_asset_orphans import" in diagnostics_source
    for marker in ("def orphan_bundle_dirs", "def orphan_run_dirs", "def orphan_alignment_dirs"):
        assert marker in orphans_source
        assert marker not in diagnostics_source
    assert "def _records_without_dirs" in diagnostics_source
    assert "service_local_asset_orphans.py" in design_source


def test_api_run_stream_emits_redacted_stream_error_on_backend_failure() -> None:
    configure_logging()

    class FlakyService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "running", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return 42

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
            assert run_id == "run_test"
            assert after_id == 42
            assert limit == 200
            raise RuntimeError("database unavailable")

    client = TestClient(build_app(service=FlakyService()))

    with client.stream("GET", "/api/runs/run_test/stream?after_id=42") as response:
        assert response.status_code == 200
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text())

    assert "event: stream_error" in body
    assert "database unavailable" not in body
    payload = json.loads(next(line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")))
    assert payload == {
        "run_id": "run_test",
        "after_id": 42,
        "error": "stream_unavailable",
        "retryable": True,
    }
    assert any(
        record.get("event") == "web.run_stream.failed" and (record.get("error") or {}).get("message") == "database unavailable"
        for record in _read_service_log_records()
    )

def test_api_unhandled_error_returns_stable_json_and_logs_exception() -> None:
    configure_logging()
    raw_error = "database unavailable for api-internal-error-test"

    class FlakyService:
        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get("/api/runs/run_test/events")

    assert response.status_code == 500
    assert response.json() == {"error": "internal server error"}
    assert raw_error not in response.text
    assert any(
        record.get("event") == "web.request.failed"
        and (record.get("error") or {}).get("message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/api/runs/run_test/events"
        and (record.get("context") or {}).get("status_code") == 500
        for record in _read_service_log_records()
    )

def test_api_run_stream_logs_invalid_resume_cursor_and_keeps_request_cursor() -> None:
    configure_logging()
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "succeeded", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return 10

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
            assert run_id == "run_test"
            assert limit == 200
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with client.stream(
        "GET",
        "/api/runs/run_test/stream?after_id=7",
        headers={"Last-Event-ID": "not-a-number"},
    ) as response:
        assert response.status_code == 200
        assert "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text()) == ""

    assert captured["after_id"] == 7
    record = next(item for item in _read_service_log_records() if item["event"] == "web.run_stream.resume_cursor_invalid")
    assert record["run_id"] == "run_test"
    assert record["context"]["after_id"] == 7
    assert record["context"]["latest_event_id"] == 10
    assert record["context"]["invalid_last_event_id"] == "not-a-number"

def test_api_run_stream_ignores_resume_cursor_beyond_current_run_events() -> None:
    configure_logging()
    captured: dict[str, int] = {}

    class CursorAwareService:
        def get_run(self, run_id: str) -> dict:
            return {"id": run_id, "status": "succeeded", "loop_id": "loop_test"}

        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            return 10

        def stream_events(self, run_id: str, after_id: int = 0, limit: int = 200) -> list[dict]:
            assert run_id == "run_test"
            assert limit == 200
            captured["after_id"] = after_id
            return []

    client = TestClient(build_app(service=CursorAwareService()))

    with client.stream(
        "GET",
        "/api/runs/run_test/stream?after_id=7",
        headers={"Last-Event-ID": "11"},
    ) as response:
        assert response.status_code == 200
        assert "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text()) == ""

    assert captured["after_id"] == 7
    record = next(item for item in _read_service_log_records() if item["event"] == "web.run_stream.resume_cursor_invalid")
    assert record["run_id"] == "run_test"
    assert record["context"]["after_id"] == 7
    assert record["context"]["latest_event_id"] == 10
    assert record["context"]["invalid_last_event_id"] == "11"

def test_web_logs_completed_requests(service_factory) -> None:
    configure_logging()
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/tutorial")

    assert response.status_code == 200
    records = _read_service_log_records()
    record = next(item for item in records if item["event"] == "web.request.completed" and item["context"]["request_path"] == "/tutorial")
    assert record["context"]["status_code"] == 200
    assert record["context"]["duration_ms"] >= 0

def test_api_stop_run_rejects_finished_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Finished Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(f"/api/runs/{run['id']}/stop")

    assert response.status_code == 409
    assert "cannot stop run in status" in response.json()["error"]

def test_run_detail_separates_status_verdict_and_reruns_terminal_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Rerun From Detail Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    client = TestClient(build_app(service=service))

    _assert_run_detail_terminal_actions_page(client, run, loop)

    _accept_run_result_and_assert_observation_event(client, service, run, loop)
    accepted_events_after_first_post = service.recent_run_events(run["id"], event_types={"run_result_accepted"})
    first_accept_event_id = accepted_events_after_first_post[-1]["id"]
    accepted_task_verdict_status = accepted_events_after_first_post[-1]["payload"]["task_verdict_status"]
    page_after_accept = client.get(f"/runs/{run['id']}")
    assert page_after_accept.status_code == 200
    assert 'data-testid="run-accepted-result-state"' in page_after_accept.text
    assert _expected_recorded_verdict_page_text(accepted_task_verdict_status) in page_after_accept.text
    assert 'data-testid="run-accept-result-button"' not in page_after_accept.text
    duplicate_accept_response = client.post(f"/runs/{run['id']}/accept", follow_redirects=False)
    assert duplicate_accept_response.status_code == 303
    accepted_events_after_duplicate_post = service.recent_run_events(run["id"], event_types={"run_result_accepted"})
    assert [event["id"] for event in accepted_events_after_duplicate_post] == [first_accept_event_id]
    acceptance_state = service.run_result_acceptance_state(run["id"])
    assert acceptance_state["accepted"] is True
    assert acceptance_state["event_id"] == first_accept_event_id
    snapshot_response = client.get(f"/api/runs/{run['id']}/observation-snapshot")
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    accepted_timeline_events = [event for event in snapshot_payload["timeline_events"] if event["event_type"] == "run_result_accepted"]
    assert accepted_timeline_events
    assert accepted_timeline_events[-1]["title"] == _expected_recorded_verdict_title(accepted_task_verdict_status)
    assert snapshot_payload["key_takeaways"]["source_event_id"] <= snapshot_payload["latest_event_id"]

    rerun_response = client.post(f"/runs/{run['id']}/rerun", follow_redirects=False)

    assert rerun_response.status_code == 303
    new_run_id = rerun_response.headers["location"].removeprefix("/runs/")
    assert new_run_id
    assert new_run_id != run["id"]
    assert service.get_run(new_run_id)["loop_id"] == loop["id"]
    _wait_for_run_terminal_status(service, new_run_id)
