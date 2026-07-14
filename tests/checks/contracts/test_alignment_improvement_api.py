from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import shutil
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.web import build_app


def test_alignment_api_creates_improvement_sessions_from_bundle_and_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="API Improvement Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="API Improvement Source Bundle",
                description="API improvement source.",
                collaboration_summary="Keep the source posture visible.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    client = TestClient(build_app(service=service))

    bundle_response = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})
    assert bundle_response.status_code == HTTPStatus.CREATED
    bundle_payload = bundle_response.json()
    bundle_redirect = urlsplit(bundle_payload["redirect_url"])
    assert bundle_redirect.path == "/loops/new/bundle"
    assert parse_qs(bundle_redirect.query)["alignment_session_id"] == [bundle_payload["session"]["id"]]
    assert parse_qs(bundle_redirect.query)["workdir"] == [str(sample_workdir.resolve())]
    assert bundle_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_type"] == "bundle"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_bundle_id"] == source["id"]

    run_response = client.post(f"/api/runs/{run['id']}/revise", json={"start_immediately": False})
    assert run_response.status_code == HTTPStatus.CREATED
    run_payload = run_response.json()
    run_redirect = urlsplit(run_payload["redirect_url"])
    assert run_redirect.path == "/loops/new/bundle"
    assert parse_qs(run_redirect.query)["alignment_session_id"] == [run_payload["session"]["id"]]
    assert parse_qs(run_redirect.query)["workdir"] == [str(sample_workdir.resolve())]
    assert run_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert run_payload["session"]["working_agreement"]["source"]["source_type"] == "run"
    assert run_payload["session"]["working_agreement"]["source"]["source_run_id"] == run["id"]


def test_alignment_improvement_surfaces_explain_missing_source_workdir(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Missing Workdir Improvement Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Missing Workdir Improvement Bundle",
                description="Source workdir recovery.",
                collaboration_summary="Do not create revision sessions when the source project is gone.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    shutil.rmtree(sample_workdir)
    client = TestClient(build_app(service=service))

    bundle_api = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})
    run_api = client.post(f"/api/runs/{run['id']}/revise", json={"start_immediately": False})

    assert bundle_api.status_code == HTTPStatus.BAD_REQUEST
    assert run_api.status_code == HTTPStatus.BAD_REQUEST
    bundle_payload = bundle_api.json()
    run_payload = run_api.json()
    assert bundle_payload["loop_recovery"] == "target_workdir_unavailable"
    assert bundle_payload["status"] == "blocked_by_workdir"
    assert bundle_payload["action"] == "revise_bundle"
    assert bundle_payload["source_bundle_id"] == source["id"]
    assert "workdir does not exist:" not in bundle_payload["error"]
    assert run_payload["loop_recovery"] == "target_workdir_unavailable"
    assert run_payload["status"] == "blocked_by_workdir"
    assert run_payload["action"] == "revise_run"
    assert run_payload["source_run_id"] == run["id"]
    assert "workdir does not exist:" not in run_payload["error"]
    assert service.list_alignment_sessions() == []

    bundle_page = client.post(f"/bundles/{source['id']}/revise", follow_redirects=True)
    run_page = client.post(f"/runs/{run['id']}/revise", follow_redirects=True)

    assert bundle_page.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-action-error"' in bundle_page.text
    assert 'data-testid="bundle-action-recovery"' in bundle_page.text
    assert 'data-recovery-action-kind="create_workdir"' in bundle_page.text
    assert 'data-recovery-action-kind="confirm_readiness"' in bundle_page.text
    assert 'data-recovery-action-kind="retry_web_compose"' in bundle_page.text
    assert "mkdir -p" in bundle_page.text
    assert "workdir does not exist:" not in bundle_page.text
    assert run_page.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in run_page.text
    assert 'data-testid="run-action-recovery"' in run_page.text
    assert 'data-recovery-action-kind="create_workdir"' in run_page.text
    assert 'data-recovery-action-kind="confirm_readiness"' in run_page.text
    assert 'data-recovery-action-kind="retry_web_compose"' in run_page.text
    assert "loopora doctor --workdir" in run_page.text
    assert "workdir does not exist:" not in run_page.text
    assert service.list_alignment_sessions() == []


def test_alignment_improvement_surfaces_redact_low_level_revision_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Revision Storage Error Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Revision Storage Error Bundle",
                description="Source revision storage error.",
                collaboration_summary="Do not expose local storage failures.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    local_path = tmp_path / "alignment.json"

    def fail_revision(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_bundle_revision_session", fail_revision)
    monkeypatch.setattr(service, "create_run_revision_session", fail_revision)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    bundle_api = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})
    run_api = client.post(f"/api/runs/{run['id']}/revise", json={"start_immediately": False})

    assert bundle_api.status_code == HTTPStatus.BAD_REQUEST
    assert run_api.status_code == HTTPStatus.BAD_REQUEST
    bundle_payload = bundle_api.json()
    run_payload = run_api.json()
    assert_revision_creation_recovery(
        bundle_payload,
        {
            "action": "revise_bundle",
            "source_key": "source_bundle_id",
            "source_id": source["id"],
            "review_kind": "review_source_bundle",
            "review_url": f"/bundles/{source['id']}",
            "workdir": str(sample_workdir.resolve()),
            "endpoint": f"/api/bundles/{source['id']}/revise",
        },
    )
    assert_revision_creation_recovery(
        run_payload,
        {
            "action": "revise_run",
            "source_key": "source_run_id",
            "source_id": run["id"],
            "review_kind": "review_source_run",
            "review_url": f"/runs/{run['id']}",
            "workdir": str(sample_workdir.resolve()),
            "endpoint": f"/api/runs/{run['id']}/revise",
        },
    )
    assert str(local_path) not in bundle_api.text
    assert str(local_path) not in run_api.text
    assert "permission denied" not in bundle_api.text
    assert "permission denied" not in run_api.text

    bundle_page = client.post(f"/bundles/{source['id']}/revise", follow_redirects=True)
    run_page = client.post(f"/runs/{run['id']}/revise", follow_redirects=True)

    assert bundle_page.status_code == HTTPStatus.OK
    assert 'data-testid="bundle-action-error"' in bundle_page.text
    assert 'data-testid="bundle-action-recovery"' in bundle_page.text
    assert 'data-recovery-action-kind="review_source_bundle"' in bundle_page.text
    assert 'data-recovery-action-kind="retry_revision_session"' in bundle_page.text
    assert "data-recovery-action-form" in bundle_page.text
    assert f'action="/bundles/{source["id"]}/revise' in bundle_page.text
    assert f'action="/api/bundles/{source["id"]}/revise"' not in bundle_page.text
    assert 'data-recovery-action-kind="open_support"' in bundle_page.text
    assert "revision session could not be created" in bundle_page.text
    assert str(local_path) not in bundle_page.text
    assert "permission denied" not in bundle_page.text
    assert run_page.status_code == HTTPStatus.OK
    assert 'data-testid="run-action-error"' in run_page.text
    assert 'data-testid="run-action-recovery"' in run_page.text
    assert 'data-recovery-action-kind="review_source_run"' in run_page.text
    assert 'data-recovery-action-kind="retry_revision_session"' in run_page.text
    assert "data-recovery-action-form" in run_page.text
    assert f'action="/runs/{run["id"]}/revise' in run_page.text
    assert f'action="/api/runs/{run["id"]}/revise"' not in run_page.text
    assert 'data-recovery-action-kind="open_support"' in run_page.text
    assert "revision session could not be created" in run_page.text
    assert str(local_path) not in run_page.text
    assert "permission denied" not in run_page.text


def test_alignment_improvement_recovers_wrapped_revision_seed_failure(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Wrapped Revision Failure Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Wrapped Revision Failure Bundle",
                description="Recover from wrapped revision seed failures.",
                collaboration_summary="Do not strand API clients after seed write failures.",
            )
        )
    )

    def fail_revision(*_args, **_kwargs):
        raise LooporaError("revision session could not be created")

    monkeypatch.setattr(service, "create_bundle_revision_session", fail_revision)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert_revision_creation_recovery(
        response.json(),
        {
            "action": "revise_bundle",
            "source_key": "source_bundle_id",
            "source_id": source["id"],
            "review_kind": "review_source_bundle",
            "review_url": f"/bundles/{source['id']}",
            "workdir": str(sample_workdir.resolve()),
            "endpoint": f"/api/bundles/{source['id']}/revise",
        },
    )


def assert_revision_creation_recovery(payload: dict, expected: dict[str, str]) -> None:
    action = expected["action"]
    source_key = expected["source_key"]
    source_id = expected["source_id"]
    review_kind = expected["review_kind"]
    review_url = expected["review_url"]
    workdir = expected["workdir"]
    endpoint = expected["endpoint"]
    expected_actions = [review_kind, "retry_revision_session", "open_support"]
    assert payload["ok"] is False
    assert payload["error"] == "revision session could not be created"
    assert payload["resource_recovery"] == "revision_session_creation_failed"
    assert payload["status"] == "blocked_by_revision_session_creation"
    assert payload["surface"] == "web_revision"
    assert payload["resource"] == "revision session"
    assert payload["action"] == action
    assert payload[source_key] == source_id
    assert [item["kind"] for item in payload["next_actions"]] == expected_actions
    review_parts = urlsplit(payload["next_actions"][0]["redirect_url"])
    assert review_parts.path == review_url
    assert parse_qs(review_parts.query).get("workdir") == [workdir]
    assert payload["next_actions"][1]["endpoint"] == endpoint
    assert payload["next_actions"][1]["after_action"] == review_kind
    support_parts = urlsplit(payload["next_actions"][2]["redirect_url"])
    assert support_parts.path == "/support"
    assert parse_qs(support_parts.query).get("workdir") == [workdir]
    assert payload["next_action_kinds"] == expected_actions
    assert payload["next_action_ready_now_kinds"] == [review_kind, "open_support"]
    assert payload["next_action_ready_after_actions"] == {"retry_revision_session": review_kind}
    summary = payload["web_revision_recovery_summary"]
    assert summary["next_action_kinds"] == expected_actions
    assert summary["next_action_ready_after_actions"] == {"retry_revision_session": review_kind}
