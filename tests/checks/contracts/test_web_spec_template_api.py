from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_api_spec_init_validate_and_delete_loop(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "created-spec.md"
    init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_preset": "build_first"},
    )
    assert init_response.status_code == HTTPStatus.CREATED
    assert spec_path.exists()
    created_text = spec_path.read_text(encoding="utf-8")
    assert "delete `# Done When`" in created_text
    assert "preserve existing user files" in created_text
    assert "# Task" in created_text
    assert "# Done When" in created_text
    assert "# Guardrails" in created_text
    assert "# Role Notes" in created_text
    assert "## Builder Notes" in created_text
    assert "## Inspector Notes" in created_text
    assert "## GateKeeper Notes" in created_text
    assert "## Guide Notes" in created_text

    duplicate_init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_preset": "build_first"},
    )
    assert duplicate_init_response.status_code == HTTPStatus.CONFLICT
    assert "already exists" in duplicate_init_response.json()["error"]

    strategy_alias_path = tmp_path / "created-spec-strategy-alias.md"
    strategy_alias_response = client.post(
        "/api/specs/init",
        json={"path": str(strategy_alias_path), "locale": "en", "strategy_preset": "inspect_first"},
    )
    assert strategy_alias_response.status_code == HTTPStatus.CREATED
    assert "## Inspector Notes" in strategy_alias_path.read_text(encoding="utf-8")

    validate_response = client.get("/api/specs/validate", params={"path": str(spec_path)})
    assert validate_response.status_code == HTTPStatus.OK
    assert validate_response.json()["ok"] is True
    assert validate_response.json()["check_mode"] == "specified"

    loop = service.create_loop(
        name="Delete Me",
        spec_path=spec_path,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="xhigh",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )

    delete_response = client.delete(f"/api/loops/{loop['id']}")
    assert delete_response.status_code == HTTPStatus.OK
    assert delete_response.json()["id"] == loop["id"]
    assert service.list_loops() == []


def test_api_spec_template_accepts_strategy_json_mapping(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/specs/template",
        json={
            "locale": "en",
            "strategy_json": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                ],
                "steps": [
                    {"id": "build", "role_id": "builder"},
                    {"id": "gate", "role_id": "gatekeeper", "on_pass": "finish_run"},
                ],
            },
        },
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["ok"] is True
    assert "# Task" in payload["content"]
    assert "## Builder Notes" in payload["content"]
    assert "## GateKeeper Notes" in payload["content"]
    assert [item["role_name"] for item in payload["role_note_sections"]] == ["Builder", "GateKeeper"]
    assert "<h1>Task</h1>" in payload["rendered_html"]


def test_api_spec_template_and_init_reject_invalid_workflow_json(
    tmp_path: Path,
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    invalid_workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
        "controls": [
            {
                "id": "bad_repair",
                "when": {"signal": "step_failed", "after": "0s"},
                "call": {"role_id": "builder"},
            }
        ],
    }

    template_response = client.post("/api/specs/template", json={"workflow_json": invalid_workflow})
    assert template_response.status_code == HTTPStatus.BAD_REQUEST
    assert "controls may only call Inspector" in template_response.json()["error"]

    spec_path = tmp_path / "invalid-workflow-template.md"
    init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_json": invalid_workflow},
    )
    assert init_response.status_code == HTTPStatus.BAD_REQUEST
    assert "controls may only call Inspector" in init_response.json()["error"]
    assert not spec_path.exists()
