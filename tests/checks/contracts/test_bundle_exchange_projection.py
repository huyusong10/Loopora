from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest

from loopora.bundles import bundle_to_yaml
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service import LooporaError
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.web import build_app


def test_bundle_exchange_list_omits_default_governance_card_projection(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    item = next(item for item in service.list_bundle_exchange_items() if item["id"] == imported["id"])

    assert item["id"] == imported["id"]
    assert item["loop_id"]
    assert "governance_summary" not in item


def test_bundle_detail_diagnostic_projection_remains_available(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    governance = service.get_bundle_governance_summary(imported["id"])

    assert governance["success_surface"]
    assert governance["loop_fit_reasons"]
    assert any("target user can complete the primary flow" in item for item in governance["success_surface"])
    assert governance["gatekeeper"]["enabled"] is True


def test_web_preview_and_agent_candidate_share_bundle_parse_errors(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = "version: 1\nmetadata: ["

    with pytest.raises(LooporaError) as exc_info:
        service.preview_bundle_text(invalid_yaml)

    result = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Run a multi-round refund safety task with evidence checkpoints.",
            bundle_yaml=invalid_yaml,
        )
    )

    assert result["ready"] is False
    assert result["requires_candidate_repair"] is True
    assert result["session"]["validation"]["error"] == "invalid bundle YAML: check Plan File YAML syntax"
    assert str(exc_info.value) == "invalid bundle YAML: check Plan File YAML syntax"


def test_bundles_page_scopes_plan_files_and_loop_export_picker_to_target_workdir(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    current_workdir.mkdir()
    other_workdir.mkdir()

    def create_loop(*, name: str, workdir: Path) -> dict:
        return service.create_loop(
            name=name,
            spec_path=sample_spec_file,
            workdir=workdir,
            model="gpt-5.4-mini",
            reasoning_effort="medium",
            max_iters=2,
            max_role_retries=1,
            delta_threshold=0.005,
            trigger_window=2,
            regression_window=2,
            role_models={},
        )

    other_loop = create_loop(name="Other Project Loop", workdir=other_workdir)
    service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                other_loop["id"],
                name="Other Project Plan",
                description="Keep scoped Plan File pages from showing cross-project assets.",
                collaboration_summary="This plan belongs to the other project.",
            )
        )
    )
    client = TestClient(build_app(service=service))
    encoded_current_workdir = quote(str(current_workdir.resolve()), safe="")
    foreign_only_response = client.get(f"/bundles?workdir={encoded_current_workdir}")

    assert foreign_only_response.status_code == HTTPStatus.OK
    assert "Other Project Loop" not in foreign_only_response.text
    assert "Other Project Plan" not in foreign_only_response.text

    current_loop = create_loop(name="Current Project Loop", workdir=current_workdir)
    service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                current_loop["id"],
                name="Current Project Plan",
                description="Keep the current project plan visible on scoped Plan File pages.",
                collaboration_summary="This plan belongs to the current project.",
            )
        )
    )
    scoped_response = client.get(f"/bundles?workdir={encoded_current_workdir}")
    global_response = client.get("/bundles")

    assert scoped_response.status_code == HTTPStatus.OK
    assert "Current Project Loop" in scoped_response.text
    assert "Current Project Plan" in scoped_response.text
    assert "Other Project Loop" not in scoped_response.text
    assert "Other Project Plan" not in scoped_response.text
    assert global_response.status_code == HTTPStatus.OK
    assert "Current Project Loop" in global_response.text
    assert "Current Project Plan" in global_response.text
    assert "Other Project Loop" in global_response.text
    assert "Other Project Plan" in global_response.text
