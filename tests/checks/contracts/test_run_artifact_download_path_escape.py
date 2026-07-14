from __future__ import annotations

from http import HTTPStatus
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from loopora.web import build_app

from web_api_test_support import _create_api_loop_run, _wait_for_run_success


def test_run_artifact_download_missing_known_file_returns_structured_payload(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    run = client.get(f"/api/runs/{run_id}").json()

    summary_path = Path(run["runs_dir"]) / "summary.md"
    summary_path.unlink()

    preview = client.get(f"/api/runs/{run_id}/artifacts/summary")
    assert preview.status_code == HTTPStatus.OK
    assert preview.json()["kind"] == "missing"

    download = client.get(f"/api/runs/{run_id}/artifacts/summary/download")
    assert download.status_code == HTTPStatus.NOT_FOUND
    payload = download.json()
    assert payload["kind"] == "missing"
    assert payload["message"] == "missing"
    assert payload["artifact"]["id"] == "summary"
    assert payload["artifact"]["path"] == f"runs/{run_id}/summary.md"
    assert str(summary_path) not in download.text


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
    assert artifacts.status_code == HTTPStatus.OK
    summary_artifact = next(item for item in artifacts.json() if item["id"] == "summary")
    assert summary_artifact["available"] is False

    preview = client.get(f"/api/runs/{run_id}/artifacts/summary")
    assert preview.status_code == HTTPStatus.BAD_REQUEST

    download = client.get(f"/api/runs/{run_id}/artifacts/summary/download")
    assert download.status_code == HTTPStatus.BAD_REQUEST
    assert "outside secret" not in download.text


def test_run_evidence_package_is_curated_private_and_redacts_local_paths(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)

    response = client.get(f"/api/runs/{run_id}/evidence-package")

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"].startswith("application/zip")
    assert f'filename="loopora-evidence-{run_id}.zip"' in response.headers["content-disposition"]
    assert str(sample_workdir.resolve()).encode() not in response.content
    assert str(Path.home()).encode() not in response.content
    with ZipFile(BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {"README.md", "manifest.json", "contract/spec.md", "evidence/task_verdict.json"} <= names
        assert not any(path.startswith(("iterations/", "context/", "workspace/")) for path in names)
        manifest = json.loads(archive.read("manifest.json"))
        verdict = json.loads(archive.read("evidence/task_verdict.json"))
    assert manifest["kind"] == "loopora_run_evidence_package"
    assert (manifest["public_safe"], manifest["content_scope"]) == (False, "private_task_review")
    assert "workspace files" in manifest["omitted_by_default"]
    assert verdict["status"] in {"passed", "insufficient_evidence", "failed"}


def test_run_evidence_package_rejects_symlinked_curated_artifact(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)
    run = client.get(f"/api/runs/{run_id}").json()
    summary_path = Path(run["runs_dir"]) / "summary.md"
    outside_artifact = sample_workdir.parent / "outside-evidence-secret.md"
    outside_artifact.write_text("outside evidence secret", encoding="utf-8")
    summary_path.unlink()
    try:
        summary_path.symlink_to(outside_artifact)
    except OSError as exc:
        pytest.skip(f"symlinks are not available in this environment: {exc}")

    response = client.get(f"/api/runs/{run_id}/evidence-package")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "symbolic link" in response.text
    assert "outside evidence secret" not in response.text
