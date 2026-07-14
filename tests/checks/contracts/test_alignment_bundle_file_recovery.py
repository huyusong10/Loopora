from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_bundle_validation_payloads import ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
from loopora.web import build_app

from alignment_test_support import (
    _bundle_invocation_dir,
    _confirm_alignment_agreement,
    _wait_for_status,
)


def test_alignment_bundle_source_file_rejects_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")

    preview = service.get_alignment_bundle(preview_session["id"])
    assert preview["ok"] is False
    assert preview["yaml"] == ""
    assert "UTF-8 encoded YAML" in preview["validation"]["error"]

    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False
    assert "UTF-8 encoded YAML" in sync_result["validation"]["error"]
    synced_session = service.get_alignment_session(preview_session["id"])
    assert synced_session["status"] == "failed"
    assert "UTF-8 encoded YAML" in synced_session["error_message"]
    assert any(event["event_type"] == "alignment_bundle_sync_failed" for event in service.list_alignment_events(preview_session["id"]))

    Path(preview_session["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    recovered = service.sync_alignment_bundle_from_file(preview_session["id"])
    recovered_session = service.get_alignment_session(preview_session["id"])
    assert recovered["ok"] is True
    assert recovered_session["status"] == "ready"
    assert recovered_session["error_message"] == ""
    assert recovered_session["finished_at"] is None


def test_alignment_bundle_preview_revalidates_current_file_without_mutating_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    bundle_path = Path(session["bundle_path"])
    ready_bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    ready_bundle["spec"]["markdown"] = ready_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps or residual risks only when they are explicitly named, visible, tracked, and owned as a follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    bundle_path.write_text(bundle_to_yaml(ready_bundle), encoding="utf-8")

    preview = service.get_alignment_bundle(session["id"])

    assert preview["ok"] is False
    assert preview["validation"]["ok"] is False
    assert "Residual Risk guidance" in preview["validation"]["error"]
    assert service.get_alignment_session(session["id"])["status"] == "ready"


def test_alignment_bundle_source_file_recovers_after_invalid_utf8(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    preview_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a previewable Loop.")["id"],
    )
    Path(preview_session["bundle_path"]).write_bytes(b"\xff")
    sync_result = service.sync_alignment_bundle_from_file(preview_session["id"])
    assert sync_result["ok"] is False

    import_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create an importable Loop.")["id"],
    )
    Path(import_session["bundle_path"]).write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    import_response = client.post(
        f"/api/alignments/sessions/{import_session['id']}/import",
        json={"start_immediately": False},
    )
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert "UTF-8 encoded YAML" in import_response.json()["error"]
    import_failed_session = service.get_alignment_session(import_session["id"])
    assert import_failed_session["status"] == "ready"
    assert "UTF-8 encoded YAML" in import_failed_session["error_message"]
    assert any(event["event_type"] == "alignment_import_failed" for event in service.list_alignment_events(import_session["id"]))


def test_alignment_import_api_projects_storage_failure_as_recovery(
    monkeypatch,
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    import_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create an importable Loop.")["id"],
    )
    bundle_path = Path(import_session["bundle_path"])
    original_yaml = bundle_path.read_text(encoding="utf-8")
    private_path = tmp_path / "private" / "ready-bundle.yml"

    def fail_import_bundle_text(*_args: object, **_kwargs: object) -> dict:
        raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(service, "import_bundle_text", fail_import_bundle_text)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.post(
        f"/api/alignments/sessions/{import_session['id']}/import",
        json={"start_immediately": False},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert_alignment_import_recovery(
        payload,
        import_session["id"],
        expected_error=ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR,
        workdir=sample_workdir,
    )
    assert "permission denied" not in response.text
    assert str(private_path) not in response.text
    assert str(bundle_path) not in response.text
    assert bundle_path.read_text(encoding="utf-8") == original_yaml
    failed_session = service.get_alignment_session(import_session["id"])
    assert failed_session["status"] == "ready"
    assert failed_session["error_message"] == ALIGNMENT_BUNDLE_SAVE_FAILED_ERROR
    assert any(event["event_type"] == "alignment_import_failed" for event in service.list_alignment_events(import_session["id"]))


def test_alignment_bundle_missing_file_errors_use_stable_user_message(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    sync_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a reloadable Loop.")["id"],
    )
    sync_path = Path(sync_session["bundle_path"])
    sync_path.unlink()

    sync_response = client.post(f"/api/alignments/sessions/{sync_session['id']}/bundle/sync")

    assert sync_response.status_code == HTTPStatus.OK
    sync_payload = sync_response.json()
    assert sync_payload["ok"] is False
    assert sync_payload["validation"]["error"] == "alignment bundle does not exist"
    assert sync_payload["validation"]["semantic_lint"]["issues"] == ["alignment bundle does not exist"]
    assert sync_payload["session"]["error_message"] == "alignment bundle does not exist"
    assert_alignment_bundle_recovery(
        sync_payload,
        sync_session["id"],
        {
            "error": "alignment bundle does not exist",
            "resource_recovery": "alignment_bundle_sync_failed",
            "status": "blocked_by_alignment_bundle_sync",
            "surface": "web_alignment_bundle_sync",
            "action": "sync_alignment_bundle",
            "summary_key": "web_alignment_bundle_sync_recovery_summary",
            "action_kinds": "review_alignment_bundle,sync_alignment_bundle,retry_alignment_import,open_support",
            "retry_after": "sync_alignment_bundle",
            "workdir": str(sample_workdir.resolve()),
        },
    )
    assert str(sync_path) not in sync_payload["validation"]["error"]
    assert str(sync_path) not in sync_payload["validation"]["semantic_lint"]["issues"][0]
    assert str(sync_path) not in sync_payload["session"]["error_message"]
    assert str(sync_path) not in sync_payload["session"]["transcript"][-1]["content"]

    import_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create an importable Loop.")["id"],
    )
    import_path = Path(import_session["bundle_path"])
    import_path.unlink()

    preview_response = client.get(f"/api/alignments/sessions/{import_session['id']}/bundle")

    assert preview_response.status_code == HTTPStatus.OK
    preview_payload = preview_response.json()
    assert preview_payload["validation"]["error"] == "alignment bundle does not exist"
    assert preview_payload["validation"]["semantic_lint"]["issues"] == ["alignment bundle does not exist"]
    assert_alignment_bundle_recovery(
        preview_payload,
        import_session["id"],
        {
            "error": "alignment bundle does not exist",
            "resource_recovery": "alignment_bundle_preview_failed",
            "status": "blocked_by_alignment_bundle_preview",
            "surface": "web_alignment_bundle_preview",
            "action": "preview_alignment_bundle",
            "summary_key": "web_alignment_bundle_preview_recovery_summary",
            "action_kinds": "review_alignment_bundle,sync_alignment_bundle,retry_alignment_bundle_preview,open_support",
            "retry_after": "sync_alignment_bundle",
            "workdir": str(sample_workdir.resolve()),
        },
    )
    assert str(import_path) not in preview_payload["error"]
    assert str(import_path) not in preview_payload["validation"].get("error", "")
    assert str(import_path) not in str(preview_payload["next_actions"])

    import_response = client.post(
        f"/api/alignments/sessions/{import_session['id']}/import",
        json={"start_immediately": False},
    )

    assert import_response.status_code == HTTPStatus.NOT_FOUND
    assert_alignment_import_recovery(
        import_response.json(),
        import_session["id"],
        expected_error="alignment bundle does not exist",
        workdir=sample_workdir,
    )
    assert str(import_path) not in import_response.text
    assert service.get_alignment_session(import_session["id"])["status"] == "ready"


def test_alignment_message_after_corrupt_ready_bundle_keeps_session_usable(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a recoverable Loop.")["id"],
    )
    Path(session["bundle_path"]).write_bytes(b"\xff")

    service.append_alignment_message(session["id"], "请根据对话重新整理方案。")

    continued = _wait_for_status(service, session["id"], "ready")
    assert continued["error_message"] == ""
    assert continued["validation"]["ok"] is True
    assert continued["transcript"][-1]["role"] == "assistant"
    prompt_text = (_bundle_invocation_dir(Path(continued["artifact_dir"])) / "prompt.md").read_text(encoding="utf-8")
    assert "Current bundle file could not be read" in prompt_text


def assert_alignment_import_recovery(payload: dict, session_id: str, *, expected_error: str, workdir: Path) -> None:
    assert_alignment_bundle_recovery(
        payload,
        session_id,
        {
            "error": expected_error,
            "resource_recovery": "alignment_import_failed",
            "status": "blocked_by_alignment_import",
            "surface": "web_alignment_import",
            "action": "import_alignment_bundle",
            "summary_key": "web_alignment_import_recovery_summary",
            "action_kinds": "review_alignment_bundle,sync_alignment_bundle,retry_alignment_import,open_support",
            "retry_after": "review_alignment_bundle",
            "workdir": str(workdir.resolve()),
        },
    )


def assert_alignment_bundle_recovery(payload: dict, session_id: str, expected: dict[str, str]) -> None:
    expected_actions = expected["action_kinds"].split(",")
    retry_kind = expected_actions[2]
    expected_ready_after = {
        "sync_alignment_bundle": "review_alignment_bundle",
        retry_kind: expected["retry_after"],
    }
    assert payload["ok"] is False
    assert payload["error"] == expected["error"]
    assert payload["resource_recovery"] == expected["resource_recovery"]
    assert payload["status"] == expected["status"]
    assert payload["surface"] == expected["surface"]
    assert payload["resource"] == "alignment bundle"
    assert payload["action"] == expected["action"]
    assert payload["session_id"] == session_id
    assert [item["kind"] for item in payload["next_actions"]] == expected_actions
    review_parts = urlsplit(payload["next_actions"][0]["redirect_url"])
    assert review_parts.path == "/loops/new/bundle"
    assert parse_qs(review_parts.query).get("alignment_session_id") == [session_id]
    assert parse_qs(review_parts.query).get("workdir") == [expected["workdir"]]
    assert payload["next_actions"][1]["endpoint"] == f"/api/alignments/sessions/{session_id}/bundle/sync"
    assert payload["next_actions"][1]["after_action"] == "review_alignment_bundle"
    expected_retry_endpoint = (
        f"/api/alignments/sessions/{session_id}/bundle" if retry_kind == "retry_alignment_bundle_preview" else f"/api/alignments/sessions/{session_id}/import"
    )
    assert payload["next_actions"][2]["endpoint"] == expected_retry_endpoint
    assert payload["next_actions"][2]["after_action"] == expected["retry_after"]
    support_parts = urlsplit(payload["next_actions"][3]["redirect_url"])
    assert support_parts.path == "/support"
    assert parse_qs(support_parts.query).get("alignment_session_id") == [session_id]
    assert parse_qs(support_parts.query).get("workdir") == [expected["workdir"]]
    assert payload["next_action_kinds"] == expected_actions
    assert payload["next_action_ready_now_kinds"] == ["review_alignment_bundle", "open_support"]
    assert payload["next_action_ready_after_actions"] == expected_ready_after
    summary = payload[expected["summary_key"]]
    assert summary["session_id"] == session_id
    assert summary["next_action_kinds"] == expected_actions
    assert summary["next_action_ready_after_actions"] == expected_ready_after
