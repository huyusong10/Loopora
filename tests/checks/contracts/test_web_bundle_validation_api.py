from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def test_api_bundle_file_inputs_reject_invalid_utf8(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    bundle_path = tmp_path / "broken-bundle.yaml"
    bundle_path.write_bytes(b"\xff")
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": str(bundle_path)})
    assert preview_response.status_code == HTTPStatus.OK
    preview_payload = preview_response.json()
    assert preview_payload["ok"] is False
    assert "UTF-8 encoded YAML" in preview_payload["error"]

    import_response = client.post("/api/bundles/import", json={"bundle_path": str(bundle_path)})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert "UTF-8 encoded YAML" in import_response.json()["error"]


def test_api_bundle_file_inputs_redact_missing_path(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    missing_path = tmp_path / "missing-bundle.yaml"
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": str(missing_path)})
    assert preview_response.status_code == HTTPStatus.OK
    assert preview_response.json() == {"ok": False, "error": "bundle file does not exist"}
    assert str(missing_path) not in preview_response.text

    import_response = client.post("/api/bundles/import", json={"bundle_path": str(missing_path)})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == "bundle file does not exist"
    assert str(missing_path) not in import_response.text


def test_api_bundle_file_inputs_project_path_normalization_failures_as_validation(
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": "bad\0bundle.yaml"})
    assert preview_response.status_code == HTTPStatus.OK
    assert preview_response.json() == {"ok": False, "error": "bundle file could not be read"}
    assert "embedded null" not in preview_response.text
    assert str(Path.cwd()) not in preview_response.text

    import_response = client.post("/api/bundles/import", json={"bundle_path": "bad\0bundle.yaml"})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == "bundle file could not be read"
    assert "embedded null" not in import_response.text
    assert str(Path.cwd()) not in import_response.text
    assert service.list_bundles() == []
    assert service.list_loops() == []


def test_api_bundle_file_inputs_accept_explicit_server_paths(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Server Path Bundle Source",
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
    bundle_path = tmp_path / "server-path-bundle.yaml"
    bundle_path.write_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Server Path Plan",
                description="Preview and import accept explicit server paths.",
                collaboration_summary="Keep Plan File path semantics distinct from run artifact paths.",
            )
        ),
        encoding="utf-8",
    )
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": str(bundle_path.resolve())})
    assert preview_response.status_code == HTTPStatus.OK
    preview_payload = preview_response.json()
    assert preview_payload["ok"] is True
    assert preview_payload["metadata"]["name"] == "Server Path Plan"

    import_response = client.post("/api/bundles/import", json={"bundle_path": str(bundle_path.resolve())})
    assert import_response.status_code == HTTPStatus.CREATED
    assert import_response.json()["bundle"]["name"] == "Server Path Plan"


def test_api_bundle_file_inputs_expand_home_paths_consistently(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Home Path Bundle Source",
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
    bundle_path = tmp_path / "home-path-bundle.yaml"
    bundle_path.write_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Home Path Plan",
                description="Preview and import share home-path normalization.",
                collaboration_summary="A file that previews from ~/path must import from the same path.",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    client = TestClient(build_app(service=service))

    preview_response = client.post("/api/bundles/preview", json={"bundle_path": f"~/{bundle_path.name}"})
    assert preview_response.status_code == HTTPStatus.OK
    preview_payload = preview_response.json()
    assert preview_payload["ok"] is True
    assert preview_payload["metadata"]["name"] == "Home Path Plan"
    assert preview_payload["source_path"] == str(bundle_path.resolve())

    import_response = client.post("/api/bundles/import", json={"bundle_path": f"~/{bundle_path.name}"})
    assert import_response.status_code == HTTPStatus.CREATED
    assert import_response.json()["bundle"]["name"] == "Home Path Plan"


def test_api_bundle_preview_and_import_report_invalid_version_without_500(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    invalid_yaml = "version: not-a-number\nmetadata:\n  name: Broken Bundle\n"

    preview_response = client.post("/api/bundles/preview", json={"bundle_yaml": invalid_yaml})
    assert preview_response.status_code == HTTPStatus.OK
    assert preview_response.json() == {"ok": False, "error": "bundle version must be an integer"}

    import_response = client.post("/api/bundles/import", json={"bundle_yaml": invalid_yaml})
    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == "bundle version must be an integer"


def test_api_bundle_import_redacts_low_level_storage_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Import Storage Error Source",
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
    bundle_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="API Import Storage Error Bundle",
            description="Import should keep storage failures stable.",
            collaboration_summary="No local storage path should be shown.",
        )
    )
    local_path = tmp_path / "loopora.sqlite"

    def fail_import_bundle_text(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "import_bundle_text", fail_import_bundle_text)

    response = TestClient(build_app(service=service), raise_server_exceptions=False).post(
        "/api/bundles/import",
        json={"bundle_yaml": bundle_yaml},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "plan file could not be imported"
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text


@pytest.mark.parametrize(
    ("replace_bundle_id", "expected_error"),
    [
        (False, "bundle replace_bundle_id must be a string"),
        ("../escape", "bundle replace_bundle_id must use letters, numbers, dot, underscore, or dash"),
    ],
)
def test_api_bundle_import_rejects_invalid_replace_bundle_id(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    replace_bundle_id: object,
    expected_error: str,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Replace Source",
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
    bundle_yaml = bundle_to_yaml(
        service.derive_bundle_from_loop(
            loop["id"],
            name="Replacement Bundle",
            description="Bundle import with invalid replace id.",
            collaboration_summary="Keep replace targets explicit.",
        )
    )
    client = TestClient(build_app(service=service))

    import_response = client.post(
        "/api/bundles/import",
        json={"bundle_yaml": bundle_yaml, "replace_bundle_id": replace_bundle_id},
    )

    assert import_response.status_code == HTTPStatus.BAD_REQUEST
    assert import_response.json()["error"] == expected_error
