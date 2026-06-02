from __future__ import annotations

from pathlib import Path

from bundle_control_summary_test_support import bundle_yaml_with_rejection_control


TRACEABILITY_WORKFLOW_STEP_COUNT = 3


def test_bundle_preview_projects_error_control_summary(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    preview = service.preview_bundle_text(bundle_yaml_with_rejection_control(sample_workdir))

    summary = preview["control_summary"]
    traceability = summary["traceability"]
    assert summary["success_surface"]
    assert summary["fake_done_risks"]
    assert summary["evidence_preferences"]
    assert summary["risks"]
    assert summary["evidence"]
    assert summary["gatekeeper"]["enabled"] is True
    assert summary["gatekeeper"]["requires_evidence_refs"] is True
    assert summary["workflow"]["step_count"] == TRACEABILITY_WORKFLOW_STEP_COUNT
    assert summary["controls"][0]["signal"] == "gatekeeper_rejected"
    assert summary["controls"][0]["role_name"] == "Evidence Inspector"
    assert preview["diagnostics"] == summary["diagnostics"]
    assert {item["code"] for item in summary["diagnostics"]} >= {
        "gatekeeper_missing_handoff_fan_in",
        "gatekeeper_missing_evidence_fan_in",
    }
    assert preview["traceability"] == traceability
    assert "loop_fit" in traceability["missing"]
    assert traceability["mapped_count"] == traceability["required_count"] - 1
    assert "spec.markdown#Fake Done" in traceability["surfaces"]
    assert "workflow.controls[]" in traceability["surfaces"]
    workflow_trace = next(item for item in traceability["items"] if item["key"] == "workflow_judgment")
    assert workflow_trace["label"] == "Run flow"
    assert workflow_trace["label"] != "Workflow judgment"
