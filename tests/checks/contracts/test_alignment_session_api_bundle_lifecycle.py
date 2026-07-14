from __future__ import annotations

from http import HTTPStatus
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.executor import FakeCodexExecutor
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_alignment_failure_recovery import (
    ALIGNMENT_CANDIDATE_REPAIR,
    ALIGNMENT_GENERATION_RETRY,
    ALIGNMENT_USER_CANCELLED,
    ALIGNMENT_WORKER_INTERRUPTED,
    alignment_failure_recovery_projection,
)
from loopora.web import build_app
from loopora.web_home_attention import home_loop_sections

from alignment_test_support import _wait_for_status


def _assert_redirect_workdir(redirect_url: str, *, path: str, workdir: Path) -> None:
    redirect_parts = urlsplit(redirect_url)
    assert redirect_parts.path == path
    assert parse_qs(redirect_parts.query).get("workdir") == [str(workdir.resolve())]


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
    assert response.status_code == HTTPStatus.CREATED
    session_id = response.json()["session"]["id"]
    _wait_for_status(service, session_id, "waiting_user")
    confirm_response = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "确认"})
    assert confirm_response.status_code == HTTPStatus.OK
    _wait_for_status(service, session_id, "ready")

    session_response = client.get(f"/api/alignments/sessions/{session_id}")
    assert session_response.status_code == HTTPStatus.OK
    assert session_response.json()["session"]["status"] == "ready"

    events_response = client.get(f"/api/alignments/sessions/{session_id}/events")
    assert events_response.status_code == HTTPStatus.OK
    event_types = [event["event_type"] for event in events_response.json()]
    assert event_types[:2] == ["alignment_session_created", "alignment_user_message"]
    assert "alignment_ready" in event_types

    with client.stream("GET", f"/api/alignments/sessions/{session_id}/stream") as stream_response:
        assert stream_response.status_code == HTTPStatus.OK
        body = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in stream_response.iter_text())
    assert "alignment_ready" in body

    list_response = client.get("/api/alignments/sessions")
    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json()["sessions"][0]["id"] == session_id
    assert list_response.json()["sessions"][0]["native_resume_available"] is True

    bundle_response = client.get(f"/api/alignments/sessions/{session_id}/bundle")
    assert bundle_response.status_code == HTTPStatus.OK
    bundle_payload = bundle_response.json()
    assert bundle_payload["ok"] is True
    assert bundle_payload["workflow_preview"]["roles"][0]["archetype"] == "builder"

    bundle_path = Path(service.get_alignment_session(session_id)["bundle_path"])
    bundle_path.write_text(
        bundle_path.read_text(encoding="utf-8").replace("Aligned Starter Bundle", "Synced Starter Bundle", 1),
        encoding="utf-8",
    )
    sync_response = client.post(f"/api/alignments/sessions/{session_id}/bundle/sync")
    assert sync_response.status_code == HTTPStatus.OK
    sync_payload = sync_response.json()
    assert sync_payload["ok"] is True
    assert sync_payload["metadata"]["name"] == "Synced Starter Bundle"
    assert sync_payload["session"]["status"] == "ready"
    assert any(event["event_type"] == "alignment_bundle_synced" for event in service.list_alignment_events(session_id))

    import_response = client.post(
        f"/api/alignments/sessions/{session_id}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == HTTPStatus.CREATED
    import_payload = import_response.json()
    assert import_payload["bundle"]["id"]
    assert import_payload["session"]["status"] == "imported"
    _assert_redirect_workdir(import_payload["redirect_url"], path=f"/loops/{import_payload['loop']['id']}", workdir=sample_workdir)

    delete_response = client.delete(f"/api/alignments/sessions/{session_id}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/api/alignments/sessions/{session_id}").status_code == HTTPStatus.NOT_FOUND
    assert client.get("/api/alignments/sessions").json()["sessions"] == []


def test_alignment_api_retries_generation_without_inventing_plan_repair(
    service_factory,
    sample_workdir: Path,
) -> None:
    class FailBeforePlanExecutor(FakeCodexExecutor):
        def execute(self, request, emit_event, should_stop, set_child_pid):
            del request, emit_event, should_stop, set_child_pid
            raise OSError("simulated missing executor")

    service = service_factory(scenario="success")
    service.executor_factory = FailBeforePlanExecutor
    client = TestClient(build_app(service=service))
    task = "Migrate payment callbacks and prove idempotency, retries, and rollback."

    create_response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": task},
    )
    session_id = create_response.json()["session"]["id"]
    failed = _wait_for_status(service, session_id, "failed")

    assert failed["failure_recovery"] == {
        "kind": "retry_alignment_generation",
        "failure_domain": "execution",
        "candidate_plan_available": False,
        "retry_generation_available": True,
        "needs_attention": True,
    }
    assert not Path(failed["bundle_path"]).exists()

    service.executor_factory = lambda: FakeCodexExecutor(scenario="success")
    retry_response = client.post(f"/api/alignments/sessions/{session_id}/retry-generation", json={})

    assert retry_response.status_code == HTTPStatus.OK
    waiting = _wait_for_status(service, session_id, "waiting_user")
    assert [entry["content"] for entry in waiting["transcript"] if entry["role"] == "user"] == [task]
    event_types = [event["event_type"] for event in service.list_alignment_events(session_id)]
    assert "alignment_generation_retry_requested" in event_types
    assert event_types.count("alignment_user_message") == 1


def test_failed_alignment_recovery_follows_real_candidate_availability(tmp_path: Path) -> None:
    bundle_path = tmp_path / "alignment" / "artifacts" / "bundle.yml"
    failed = {
        "status": "failed",
        "bundle_path": str(bundle_path),
        "validation": {},
        "stop_requested": False,
    }

    generation = alignment_failure_recovery_projection(failed)

    assert generation == {
        "kind": ALIGNMENT_GENERATION_RETRY,
        "failure_domain": "execution",
        "candidate_plan_available": False,
        "retry_generation_available": True,
        "needs_attention": True,
    }

    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    candidate = alignment_failure_recovery_projection(failed)

    assert candidate["kind"] == ALIGNMENT_CANDIDATE_REPAIR
    assert candidate["failure_domain"] == "candidate_plan"
    assert candidate["candidate_plan_available"] is True
    assert candidate["retry_generation_available"] is False


def test_cancelled_alignment_failure_does_not_become_home_attention(tmp_path: Path) -> None:
    recovery = alignment_failure_recovery_projection(
        {
            "status": "failed",
            "bundle_path": str(tmp_path / "cancelled" / "bundle.yml"),
            "stop_requested": True,
        }
    )

    assert recovery["kind"] == ALIGNMENT_USER_CANCELLED
    assert recovery["needs_attention"] is False


def test_home_surfaces_failed_alignment_by_real_recovery_domain(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    sessions = [
        _failed_attention_session(
            "align_execution_failed",
            workdir,
            candidate=False,
            updated_at="2026-06-16T08:00:00+00:00",
        ),
        _failed_attention_session(
            "align_candidate_failed",
            workdir,
            candidate=True,
            updated_at="2026-06-16T07:00:00+00:00",
        ),
        _failed_attention_session(
            "align_worker_interrupted",
            workdir,
            candidate=False,
            kind=ALIGNMENT_WORKER_INTERRUPTED,
            updated_at="2026-06-16T06:00:00+00:00",
        ),
    ]

    sections = home_loop_sections(_AlignmentAttentionService(sessions), workdir_context=str(workdir))

    assert [item["id"] for item in sections["active_loops"]] == [
        "align_execution_failed",
        "align_candidate_failed",
        "align_worker_interrupted",
    ]
    assert [item["attention_reason_kind"] for item in sections["active_loops"]] == [
        "alignment_generation_failed",
        "alignment_candidate_failed",
        "alignment_worker_interrupted",
    ]
    assert [item["attention_action_kind"] for item in sections["active_loops"]] == [
        "retry_alignment_generation",
        "repair_alignment_bundle",
        "retry_alignment_generation",
    ]
    assert sections["active_loops"][2]["attention_action_en"] == "Resume planning"
    assert sections["active_loops"][2]["status_label"] == "interrupted"


class _AlignmentAttentionService:
    repository = None

    def __init__(self, sessions: list[dict]) -> None:
        self.sessions = sessions

    def list_loops(self) -> list[dict]:
        return []

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        return self.sessions[:limit]


def _failed_attention_session(
    session_id: str,
    workdir: Path,
    *,
    candidate: bool,
    updated_at: str,
    kind: str = "",
) -> dict:
    return {
        "id": session_id,
        "status": "failed",
        "status_label": "interrupted" if kind == ALIGNMENT_WORKER_INTERRUPTED else "failed",
        "workdir": str(workdir),
        "title": session_id,
        "last_message": "Preserve this task.",
        "failure_recovery": {
            "kind": kind or ("repair_candidate_plan" if candidate else "retry_alignment_generation"),
            "candidate_plan_available": candidate,
            "needs_attention": True,
        },
        "updated_at": updated_at,
    }


def test_alignment_api_rejects_relative_web_workdir_without_service_cwd_fallback(
    service_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    relative_workdir = Path("relative-project")
    relative_workdir.mkdir()
    client = TestClient(build_app(service=service_factory(scenario="success")))

    context_response = client.post("/api/alignments/workdir-context", json={"workdir": str(relative_workdir)})
    session_response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(relative_workdir), "message": "Create a target-scoped Web conversation."},
    )

    for response, action in (
        (context_response, "workdir_context"),
        (session_response, "create_alignment_session"),
    ):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert (payload["loop_recovery"], payload["status"], payload["action"]) == (
            "target_workdir_unavailable",
            "blocked_by_workdir",
            action,
        )
        assert (payload["workdir"], payload["workdir_state"]["status"], payload["workdir_state"]["usable_for_web_alignment"]) == (
            "",
            "absolute_required",
            False,
        )
        assert [item["kind"] for item in payload["next_actions"]] == ["choose_workdir", "confirm_readiness", "retry_web_compose"]
        encoded = json.dumps(payload, ensure_ascii=False)
        assert str(relative_workdir) not in encoded
        assert str(tmp_path.resolve()) not in encoded


def test_alignment_import_api_redirects_to_failed_run_when_worker_cannot_start(
    monkeypatch,
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    session_id = _ready_alignment_session(client, service, sample_workdir)
    private_path = tmp_path / "private" / "thread-start"
    monkeypatch.setattr(service, "_build_run_thread", lambda _run_id: _failing_run_thread(private_path))

    response = client.post(
        f"/api/alignments/sessions/{session_id}/import",
        json={"start_immediately": True},
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.json()
    assert "error" not in payload
    assert payload["run_start_error"] == BACKGROUND_WORKER_START_ERROR
    assert payload["run_recovery"] == "retry_run_start"
    assert payload["next_actions"] == [
        {
            "kind": "retry_web_run_start",
            "target": "web_loop_start",
            "action": "start_run",
            "loop_id": payload["loop"]["id"],
        }
    ]
    assert payload["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["next_action_ready_after_actions"] == {}
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["status_label"] == "run_start_failed"
    assert payload["run"]["run_recovery"] == "retry_run_start"
    assert payload["run"]["next_actions"] == payload["next_actions"]
    assert payload["run"]["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    assert payload["run"]["error_message"] == BACKGROUND_WORKER_START_ERROR
    parts = urlsplit(payload["redirect_url"])
    assert parts.path == f"/runs/{payload['run']['id']}"
    assert parse_qs(parts.query)["run_action_error"] == [BACKGROUND_WORKER_START_ERROR]
    assert parse_qs(parts.query).get("workdir") == [str(sample_workdir.resolve())]
    session = service.get_alignment_session(session_id)
    assert session["status"] == "imported"
    assert session["linked_run_id"] == payload["run"]["id"]
    events = service.list_alignment_events(session_id)
    failed_event = next(event for event in events if event["event_type"] == "alignment_run_start_failed")
    assert failed_event["payload"]["run_id"] == payload["run"]["id"]
    assert failed_event["payload"]["run_start_error"] == BACKGROUND_WORKER_START_ERROR
    assert failed_event["payload"]["run_recovery"] == "retry_run_start"
    assert failed_event["payload"]["next_actions"] == payload["next_actions"]
    assert failed_event["payload"]["next_action_ready_now_kinds"] == ["retry_web_run_start"]
    encoded = response.text
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded


def _ready_alignment_session(client: TestClient, service, sample_workdir: Path) -> str:
    response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(sample_workdir), "message": "Create a runnable bundle."},
    )
    assert response.status_code == HTTPStatus.CREATED
    session_id = response.json()["session"]["id"]
    _wait_for_status(service, session_id, "waiting_user")
    confirm_response = client.post(f"/api/alignments/sessions/{session_id}/messages", json={"message": "确认"})
    assert confirm_response.status_code == HTTPStatus.OK
    _wait_for_status(service, session_id, "ready")
    return session_id


def _failing_run_thread(private_path: Path):
    class FailingRunThread:
        name = "run-start-failure"

        def start(self) -> None:
            raise OSError(f"permission denied: {private_path}")

    return FailingRunThread()
