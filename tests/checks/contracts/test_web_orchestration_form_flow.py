from __future__ import annotations

import json
from http import HTTPStatus

from fastapi.testclient import TestClient

from loopora.web import build_app


def test_builtin_orchestration_form_route_is_read_only(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    builtin = service.get_orchestration("builtin:build_first")
    custom_before = [item for item in service.list_orchestrations() if item["source"] == "custom"]

    response = client.post(
        "/orchestrations/builtin:build_first/edit",
        data={
            "name": "Attempted Custom Copy",
            "description": "Should not be created from the built-in edit route.",
            "workflow_preset": "build_first",
            "workflow_json": json.dumps(builtin["workflow_json"], ensure_ascii=False),
            "prompt_files_json": json.dumps(builtin["prompt_files_json"], ensure_ascii=False),
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "built-in orchestrations are read-only" in response.text
    custom_after = [item for item in service.list_orchestrations() if item["source"] == "custom"]
    assert custom_after == custom_before


def test_blank_orchestration_form_does_not_fall_back_to_build_first(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/orchestrations/new",
        data={
            "name": "Blank Starter",
            "description": "Should stay blank until steps are added.",
            "workflow_json": json.dumps({"version": 1, "preset": "", "roles": [], "steps": []}, ensure_ascii=False),
            "prompt_files_json": json.dumps({}, ensure_ascii=False),
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "workflow requires at least one role" in response.text
    custom_records = [item for item in service.list_orchestrations() if item["source"] == "custom"]
    assert custom_records == []
