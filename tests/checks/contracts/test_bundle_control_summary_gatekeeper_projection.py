from __future__ import annotations

from pathlib import Path

from bundle_control_summary_test_support import round_builder_bundle
from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import _traceability_projection


def test_bundle_control_summary_uses_loop_verdict_language_for_completion_diagnostics(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', '  completion_mode: "rounds"')
    )

    summary = service._bundle_control_summary(bundle)
    diagnostic = next(item for item in summary["diagnostics"] if item["code"] == "completion_not_gatekeeper")

    assert "Loop 裁决" in diagnostic["message_zh"]
    assert "任务裁决" not in diagnostic["message_zh"]


def test_bundle_control_summary_marks_gatekeeper_refs_not_applicable_when_disabled(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    summary = service._bundle_control_summary(round_builder_bundle(sample_workdir))
    gatekeeper = summary["gatekeeper"]
    closure_trace = next(item for item in summary["traceability"]["items"] if item["key"] == "gatekeeper_closure")

    assert gatekeeper["enabled"] is False
    assert gatekeeper["requires_evidence_refs"] is False
    assert gatekeeper["roles"] == []
    assert gatekeeper["finish_steps"] == []
    assert closure_trace["mapped"] is False
    assert "gatekeeper_closure" in summary["traceability"]["missing"]


def test_bundle_governance_summary_requires_literal_gatekeeper_enabled(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    service._bundle_control_summary = lambda _bundle: {
        "risks": [],
        "evidence": ["GateKeeper evidence refs"],
        "workflow": {"summary": "Builder -> GateKeeper", "step_count": 2, "parallel_groups": []},
        "gatekeeper": {"enabled": "false", "roles": ["GateKeeper"], "finish_steps": ["gatekeeper_step"]},
    }

    governance = service._bundle_governance_summary(bundle)

    assert governance["gatekeeper"]["enabled"] is False
    assert governance["gatekeeper"]["strictness"] == "not_configured"


def test_bundle_traceability_requires_literal_gatekeeper_enabled() -> None:
    traceability = _traceability_projection(
        {
            "bundle": {},
            "raw_sections": {},
            "roles": [],
            "strategy_source": {},
            "strategy_flow_projection": {},
            "gatekeeper": {"enabled": "true", "roles": ["GateKeeper"], "finish_steps": ["gatekeeper_step"]},
            "controls": [],
        }
    )

    gatekeeper_item = next(item for item in traceability["items"] if item["key"] == "gatekeeper_closure")
    assert gatekeeper_item["mapped"] is False
    assert "gatekeeper_closure" in traceability["missing"]
