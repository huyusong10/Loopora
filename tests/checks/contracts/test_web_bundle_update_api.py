from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.bundles import bundle_to_yaml
from loopora.web import build_app


def test_api_bundle_update_updates_plan_without_bumping_revision(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Update Source",
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
                name="API Update Bundle",
                description="Before API update.",
                collaboration_summary="Original collaboration summary.",
            )
        )
    )

    client = TestClient(build_app(service=service))
    response = client.put(
        f"/api/bundles/{imported['id']}",
        json={
            "description": "After API update.",
            "collaboration_summary": "Updated collaboration summary.",
            "spec_markdown": "# Task\n\nUpdated.\n\n# Done When\n- Ready.\n",
        },
    )

    assert response.status_code == HTTPStatus.OK
    bundle = response.json()["bundle"]
    assert bundle["description"] == "After API update."
    assert bundle["collaboration_summary"] == "Updated collaboration summary."
    assert bundle["revision"] == imported["revision"]
    assert bundle["source_bundle_id"] == ""


def test_api_bundle_update_redacts_low_level_storage_errors(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Update Storage Error Source",
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
                name="API Update Storage Error Bundle",
                description="Before API update.",
                collaboration_summary="Original collaboration summary.",
            )
        )
    )
    local_path = tmp_path / "bundle.yml"
    spec_path = service._bundle_spec_path(imported["id"])
    original_spec = spec_path.read_text(encoding="utf-8")
    original_replace = Path.replace

    def fail_bundle_spec_replace(path: Path, target: Path) -> Path:
        if Path(target) == spec_path.resolve() and Path(path).name.startswith(f".{spec_path.name}.tmp."):
            raise OSError(f"permission denied: {local_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_bundle_spec_replace)

    response = TestClient(build_app(service=service), raise_server_exceptions=False).put(
        f"/api/bundles/{imported['id']}",
        json={
            "description": "After API update.",
            "collaboration_summary": "Updated collaboration summary.",
            "spec_markdown": "# Task\n\nUpdated.\n\n# Done When\n- Ready.\n",
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "plan file could not be saved"
    assert str(local_path) not in response.text
    assert "permission denied" not in response.text
    assert spec_path.read_text(encoding="utf-8") == original_spec
    assert not list(spec_path.parent.glob(f".{spec_path.name}.tmp.*"))


def test_api_bundle_metadata_update_does_not_require_managed_spec_sidecar(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Bundle Metadata Update Source",
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
                name="Metadata Update Bundle",
                description="Before metadata update.",
                collaboration_summary="Original metadata summary.",
            )
        )
    )
    spec_path = Path(service._bundle_spec_path(imported["id"]))
    spec_path.unlink()

    response = TestClient(build_app(service=service)).put(
        f"/api/bundles/{imported['id']}",
        json={
            "description": "After metadata update.",
            "collaboration_summary": "Updated metadata summary.",
        },
    )

    assert response.status_code == HTTPStatus.OK
    bundle = response.json()["bundle"]
    assert bundle["description"] == "After metadata update."
    assert bundle["collaboration_summary"] == "Updated metadata summary."
    assert "bundle spec does not exist:" not in response.text
    assert not spec_path.exists()
