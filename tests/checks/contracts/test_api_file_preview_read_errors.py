from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.file_previews import preview_existing_path
from loopora.web import build_app

from web_file_access_test_support import create_file_preview_run


def test_api_file_preview_reports_unreadable_file_without_500(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="Unreadable File Preview Loop")
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

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["kind"] == "file"
    assert payload["content"] == ""
    assert payload["preview_error"] == "file could not be read"


def test_api_file_download_reports_unreadable_file_without_500(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="Unreadable File Download Loop")
    unreadable_path = sample_workdir / "unreadable-download.txt"
    unreadable_path.write_text("hidden", encoding="utf-8")
    unreadable_resolved = unreadable_path.resolve()
    local_path = sample_workdir / "private" / "unreadable-download.txt"
    original_open = Path.open

    def fail_target_open(path: Path, *args: object, **kwargs: object):
        if path == unreadable_resolved:
            raise OSError(f"permission denied: {local_path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_target_open)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)
    response = client.get(f"/api/files/download?run_id={run['id']}&root=workdir&path=unreadable-download.txt")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "file could not be downloaded"
    assert str(unreadable_resolved) not in response.text
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text


def test_api_file_preview_and_download_redact_missing_absolute_path(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="Missing File Preview Loop")
    client = TestClient(build_app(service=service))

    preview_response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=missing.txt")
    download_response = client.get(f"/api/files/download?run_id={run['id']}&root=workdir&path=missing.txt")

    for response in (preview_response, download_response):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"] == "requested path does not exist"
        assert str(sample_workdir.resolve()) not in response.text


def test_api_file_preview_and_download_reject_absolute_request_paths(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="Absolute File Path Loop")
    local_file = sample_workdir / "visible.txt"
    local_file.write_text("server absolute path content", encoding="utf-8")
    client = TestClient(build_app(service=service))

    for request_path in (str(local_file.resolve()), r"C:\Users\runner\project\visible.txt"):
        preview_response = client.get(
            "/api/files",
            params={"run_id": run["id"], "root": "workdir", "path": request_path},
        )
        download_response = client.get(
            "/api/files/download",
            params={"run_id": run["id"], "root": "workdir", "path": request_path},
        )

        for response in (preview_response, download_response):
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json()["error"] == "requested path must be relative"
            assert "server absolute path content" not in response.text
            assert request_path not in response.text
            assert str(local_file.resolve()) not in response.text
            assert str(sample_workdir.resolve()) not in response.text


def test_api_file_access_does_not_use_current_directory_for_blank_run_workdir(
    monkeypatch,
    tmp_path: Path,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = create_file_preview_run(service, sample_spec_file, sample_workdir, name="Blank Workdir File Access Loop")
    wrong_cwd = tmp_path / "wrong-cwd"
    wrong_cwd.mkdir()
    (wrong_cwd / "visible.txt").write_text("must not be exposed\n", encoding="utf-8")
    (wrong_cwd / ".loopora").mkdir()
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_runs SET workdir = ? WHERE id = ?", ("", run["id"]))
    monkeypatch.chdir(wrong_cwd)
    client = TestClient(build_app(service=service))

    workdir_response = client.get(f"/api/files?run_id={run['id']}&root=workdir&path=visible.txt")
    loopora_response = client.get(f"/api/files?run_id={run['id']}&root=loopora")

    for response in (workdir_response, loopora_response):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"] == "run workdir is not available"
        assert str(wrong_cwd) not in response.text
        assert "visible.txt" not in response.text


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
