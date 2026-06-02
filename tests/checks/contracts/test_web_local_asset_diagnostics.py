from __future__ import annotations

import shutil
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.branding import state_dir_for_workdir
from loopora.settings import app_home
from loopora.web import build_app


REPO_ROOT = Path(__file__).resolve().parents[3]


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

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert set(payload) == {"orphan_alignment_dirs", "orphan_bundle_dirs", "orphan_run_dirs", "record_without_dir"}
    assert any(item["session_id"] == "align_orphan" for item in payload["orphan_alignment_dirs"])
    assert any(item["bundle_id"] == "bundle_orphan" for item in payload["orphan_bundle_dirs"])
    assert any(item["run_id"] == "run_orphan" and item["source"] == "recent_workdir" for item in payload["orphan_run_dirs"])
    assert any(
        item["resource_type"] == "bundle" and item["resource_id"] == "bundle_missing_dir"
        for item in payload["record_without_dir"]
    )
    assert any(item["resource_type"] == "run" and item["resource_id"] == run["id"] for item in payload["record_without_dir"])
    assert any(
        item["resource_type"] == "run" and item["resource_id"] == "run_registry_missing"
        for item in payload["record_without_dir"]
    )


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
