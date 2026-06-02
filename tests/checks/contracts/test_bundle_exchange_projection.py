from __future__ import annotations

from pathlib import Path

import pytest

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service import LooporaError
from loopora.service_agent_adapters import AgentBundleCandidateRequest


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
    assert any("primary user flow is understandable" in item for item in governance["success_surface"])
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
    assert result["session"]["validation"]["error"].startswith("invalid bundle YAML:")
    assert str(exc_info.value).startswith("invalid bundle YAML:")
