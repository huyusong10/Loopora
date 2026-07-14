from __future__ import annotations

from http import HTTPStatus
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.service_types import LooporaError
from loopora.settings import configure_logging
from loopora.web import build_app

from web_api_test_support import _read_service_log_records


def test_api_unhandled_error_returns_stable_json_and_logs_exception() -> None:
    configure_logging()
    raw_error = "database unavailable for api-internal-error-test"

    class FlakyService:
        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get("/api/runs/run_test/events")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"error": "internal server error"}
    assert raw_error not in response.text
    assert any(
        record.get("event") == "web.request.failed"
        and (record.get("error") or {}).get("message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/api/runs/run_test/events"
        and (record.get("context") or {}).get("status_code") == HTTPStatus.INTERNAL_SERVER_ERROR
        for record in _read_service_log_records()
    )


def test_page_unhandled_error_returns_stable_html_and_logs_exception() -> None:
    configure_logging()
    raw_error = "database unavailable for page-internal-error-test"

    class FlakyService:
        def list_loops(self) -> list:
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get("/bundles")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert "Loopora could not render this page" in response.text
    assert "Return to Loopora home" in response.text
    assert "Open Support" in response.text
    assert 'href="/support?return_to=%2Fbundles" data-testid="web-error-support-link"' in response.text
    assert 'data-testid="web-error-page"' in response.text
    assert 'data-testid="web-error-status"' in response.text
    assert raw_error not in response.text
    assert any(
        record.get("event") == "web.request.failed"
        and (record.get("error") or {}).get("message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/bundles"
        and (record.get("context") or {}).get("status_code") == HTTPStatus.INTERNAL_SERVER_ERROR
        for record in _read_service_log_records()
    )


def test_page_unhandled_error_preserves_explicit_workdir_recovery_context(tmp_path) -> None:
    configure_logging()
    raw_error = "database unavailable for page-context-error-test"
    workdir = tmp_path / "target project"
    query = urlencode({"workdir": str(workdir)})

    class FlakyService:
        def list_loops(self) -> list:
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get(f"/bundles?{query}")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert f'href="/?{query}" data-testid="web-error-home-link"' in response.text
    expected_return_to = urlencode({"return_to": f"/bundles?{query}"})
    assert f'href="/support?{query}&amp;{expected_return_to}" data-testid="web-error-support-link"' in response.text
    assert raw_error not in response.text


def test_page_unhandled_error_preserves_entity_workdir_recovery_context(
    monkeypatch,
    service_factory,
    sample_spec_file,
    sample_workdir,
) -> None:
    configure_logging()
    raw_error = "database unavailable for entity-context-error-test"
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Fallback Context Source",
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
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Fallback Context Plan",
                description="Unhandled fallback errors should keep the resource target.",
                collaboration_summary="Support recovery should not drift to global state.",
            )
        )
    )

    def fail_bundle_spec_path(bundle_id: str):
        assert bundle_id == imported["id"]
        raise RuntimeError(raw_error)

    monkeypatch.setattr(service, "_bundle_spec_path", fail_bundle_spec_path)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)
    query = urlencode({"workdir": str(sample_workdir.resolve())})

    response = client.get(f"/bundles/{imported['id']}")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert f'href="/?{query}" data-testid="web-error-home-link"' in response.text
    expected_return_to = urlencode({"return_to": f"/bundles/{imported['id']}?{query}"})
    assert f'href="/support?{query}&amp;{expected_return_to}" data-testid="web-error-support-link"' in response.text
    assert raw_error not in response.text


def test_json_client_unhandled_error_returns_stable_json_and_logs_exception() -> None:
    configure_logging()
    raw_error = "database unavailable for json-client-internal-error-test"

    class FlakyService:
        def list_loops(self) -> list:
            raise RuntimeError(raw_error)

    client = TestClient(build_app(service=FlakyService()), raise_server_exceptions=False)

    response = client.get("/bundles", headers={"accept": "Application/JSON"})

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "internal server error"}
    assert raw_error not in response.text
    assert any(
        record.get("event") == "web.request.failed"
        and (record.get("error") or {}).get("message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/bundles"
        and (record.get("context") or {}).get("status_code") == HTTPStatus.INTERNAL_SERVER_ERROR
        for record in _read_service_log_records()
    )


def test_page_domain_error_returns_stable_html_without_raw_json() -> None:
    configure_logging()
    raw_error = "permission denied: /private/domain-error-test"

    class DomainFailingService:
        def list_loops(self) -> list:
            raise LooporaError(raw_error)

    client = TestClient(build_app(service=DomainFailingService()), raise_server_exceptions=False)

    response = client.get("/bundles")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "text/html" in response.headers["content-type"]
    assert "Loopora could not complete this request" in response.text
    assert "Return to Loopora home" in response.text
    assert "Open Support" in response.text
    assert 'href="/support?return_to=%2Fbundles" data-testid="web-error-support-link"' in response.text
    assert 'data-testid="web-error-page"' in response.text
    assert 'data-testid="top-nav"' in response.text
    assert 'data-testid="web-error-home-link"' in response.text
    assert 'data-testid="web-error-support-link"' in response.text
    assert "/static/app.js?v=" in response.text
    assert 'data-testid="app-feedback"' in response.text
    assert "permission denied" not in response.text
    assert "/private/domain-error-test" not in response.text
    assert any(
        record.get("event") == "web.request.domain_error"
        and (record.get("context") or {}).get("error_message") == raw_error
        and (record.get("context") or {}).get("request_path") == "/bundles"
        for record in _read_service_log_records()
    )


def test_api_domain_error_keeps_json_error_contract() -> None:
    raw_error = "run event stream is not available"

    class DomainFailingService:
        def latest_run_event_id(self, run_id: str) -> int:
            assert run_id == "run_test"
            raise LooporaError(raw_error)

    client = TestClient(build_app(service=DomainFailingService()), raise_server_exceptions=False)

    response = client.get("/api/runs/run_test/events")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"error": raw_error}


def test_page_http_error_returns_stable_html_not_raw_json(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get("/missing-loopora-page")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "text/html" in response.headers["content-type"]
    assert "Loopora could not complete this request" in response.text
    assert "Return to Loopora home" in response.text
    assert "Open Support" in response.text
    assert 'href="/support?return_to=%2Fmissing-loopora-page" data-testid="web-error-support-link"' in response.text
    assert 'data-testid="web-error-page"' in response.text
    assert 'data-testid="top-nav"' in response.text
    assert 'data-testid="web-error-status"' in response.text
    assert '"detail"' not in response.text
    assert "Not Found" not in response.text


def test_api_http_error_keeps_json_error_contract(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get("/api/unknown-loopora-resource")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {"error": "Not Found"}


def test_json_client_http_error_keeps_json_error_contract(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get("/missing-loopora-page", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "Not Found"}


def test_page_request_validation_error_returns_stable_html_not_raw_json(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get("/bundles/derive/export")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "text/html" in response.headers["content-type"]
    assert "Loopora could not complete this request" in response.text
    assert "Return to Loopora home" in response.text
    assert "Open Support" in response.text
    assert 'href="/support?return_to=%2Fbundles%2Fderive%2Fexport" data-testid="web-error-support-link"' in response.text
    assert 'data-testid="web-error-page"' in response.text
    assert 'data-testid="top-nav"' in response.text
    assert 'data-testid="web-error-status"' in response.text
    assert '"detail"' not in response.text
    assert "Field required" not in response.text
    assert "loop_id" not in response.text


def test_json_client_request_validation_error_keeps_json_error_contract(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.get("/bundles/derive/export", headers={"accept": "application/json"})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "request validation failed"}


def test_web_logs_completed_requests(service_factory) -> None:
    configure_logging()
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/tutorial")

    assert response.status_code == HTTPStatus.OK
    records = _read_service_log_records()
    record = next(
        item for item in records if item["event"] == "web.request.completed" and item["context"]["request_path"] == "/tutorial"
    )
    assert record["context"]["status_code"] == HTTPStatus.OK
    assert record["context"]["duration_ms"] >= 0
