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
