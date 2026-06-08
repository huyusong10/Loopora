from __future__ import annotations

# Merged from test_bundle_control_summary_control_projection.py
from pathlib import Path

from bundle_control_summary_test_support import bundle_yaml_with_rejection_control


def test_bundle_control_summary_does_not_hide_invalid_fire_limit_projection(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = service.preview_bundle_text(bundle_yaml_with_rejection_control(sample_workdir))["bundle"]

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = 0
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == 0

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "not-a-number"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "not-a-number"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "2"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "2"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "+2"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "+2"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = True
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "true"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = 1.5
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "1.5"

# Merged from test_bundle_control_summary_coverage_projection.py

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import build_bundle_control_summary


def test_bundle_control_summary_coverage_respects_completion_mode(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["loop"]["completion_mode"] = "rounds"

    summary = build_bundle_control_summary(bundle)
    target_ids = [target["id"] for target in summary["coverage"]["targets"]]

    assert "gatekeeper.finish" not in target_ids
    assert any(target_id.startswith("done_when.") for target_id in target_ids)

# Merged from test_bundle_control_summary_diagnostics.py

from bundle_control_summary_test_support import bundle_yaml_with_legacy_guide
from loopora.bundles import bundle_to_yaml


def test_bundle_preview_warns_about_legacy_guide_and_weak_builder_handoff(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    preview = service.preview_bundle_text(bundle_yaml_with_legacy_guide(sample_workdir))

    codes = {item["code"] for item in preview["diagnostics"]}
    assert "guide_missing_upstream_handoff" in codes
    assert "guide_missing_upstream_evidence" in codes
    assert "builder_missing_guide_handoff" in codes


def test_bundle_preview_warns_when_gatekeeper_drops_parallel_review_fan_in(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["contract_inspection_step"]["parallel_group"] = "inspection_pack"
    steps_by_id["evidence_inspection_step"]["parallel_group"] = "inspection_pack"
    gatekeeper_inputs = steps_by_id["gatekeeper_step"]["inputs"]
    gatekeeper_inputs["handoffs_from"] = ["evidence_inspection_step"]
    gatekeeper_inputs["evidence_query"]["archetypes"] = ["builder"]

    preview = service.preview_bundle_text(bundle_to_yaml(bundle))

    diagnostics_by_code = {item["code"]: item for item in preview["diagnostics"]}
    assert diagnostics_by_code["gatekeeper_missing_parallel_review_handoff"]["details"]["missing_handoffs"] == [
        "contract_inspection_step"
    ]
    assert diagnostics_by_code["gatekeeper_missing_parallel_review_evidence"]["details"]["missing_archetypes"] == [
        "inspector"
    ]

# Merged from test_bundle_control_summary_judgment_surfaces.py

from bundle_control_summary_test_support import traceability_item


def test_bundle_control_summary_projects_explicit_judgment_tradeoffs(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    summary = build_bundle_control_summary(bundle)
    loop_fit_item = traceability_item(summary, "loop_fit")
    success_item = traceability_item(summary, "success_surface")
    fake_done_item = traceability_item(summary, "fake_done_risks")
    evidence_item = traceability_item(summary, "evidence_preferences")
    tradeoff_item = traceability_item(summary, "judgment_tradeoffs")
    role_item = traceability_item(summary, "role_posture")

    assert any("final feedback is too slow to be the only control signal" in item for item in summary["loop_fit_reasons"])
    assert loop_fit_item["mapped"] is True
    assert any("weak-proof control points" in item for item in loop_fit_item["evidence"])
    assert "loop_fit" not in summary["traceability"]["missing"]
    assert any("target user can complete the primary flow" in item for item in summary["success_surface"])
    assert any("happy-path claim" in item for item in summary["fake_done_risks"])
    assert any("project-owned checks" in item for item in summary["evidence_preferences"])
    assert success_item["mapped"] is True
    assert fake_done_item["mapped"] is True
    assert evidence_item["mapped"] is True
    assert "success_surface" not in summary["traceability"]["missing"]
    assert "fake_done_risks" not in summary["traceability"]["missing"]
    assert "evidence_preferences" not in summary["traceability"]["missing"]
    assert any("smaller proven flow" in item for item in summary["judgment_tradeoffs"])
    assert tradeoff_item["mapped"] is True
    assert "judgment_tradeoffs" not in summary["traceability"]["missing"]
    assert any("Focused Builder (builder): Keep implementation narrow" in item for item in summary["role_postures"])
    assert role_item["mapped"] is True
    assert "role_posture" not in summary["traceability"]["missing"]


def test_bundle_control_summary_does_not_treat_done_when_as_success_surface(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "\n# Success Surface\n\n"
        "- The target user can complete the primary flow, and the result is understandable, maintainable, and easy to extend after the first pass.\n",
        "\n",
    )

    summary = build_bundle_control_summary(bundle)
    success_item = traceability_item(summary, "success_surface")

    assert summary["success_surface"] == []
    assert success_item["mapped"] is False
    assert success_item["surfaces"] == ["spec.markdown#Success Surface"]
    assert "success_surface" in summary["traceability"]["missing"]


def test_bundle_control_summary_does_not_treat_role_names_as_posture(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    for role in bundle["role_definitions"]:
        role["description"] = ""
        role["posture_notes"] = ""
        role["prompt_markdown"] = "---\nversion: 1\narchetype: " + role["archetype"] + "\n---\n"

    summary = build_bundle_control_summary(bundle)
    role_item = traceability_item(summary, "role_posture")

    assert role_item["mapped"] is False
    assert role_item["evidence"] == []
    assert summary["role_postures"] == []
    assert "role_posture" in summary["traceability"]["missing"]

# Merged from test_bundle_control_summary_residual_risk_projection.py



def test_bundle_control_summary_projects_residual_risk_policy(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    summary = build_bundle_control_summary(bundle)
    residual_item = traceability_item(summary, "residual_risk_policy")

    assert any("fail closed" in item for item in summary["residual_risk_policy"])
    assert residual_item["mapped"] is True
    assert "residual_risk_policy" not in summary["traceability"]["missing"]


def test_bundle_control_summary_does_not_map_unmanaged_residual_risk_policy(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps or residual risks only when they are explicitly named, visible, tracked, and owned as a follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )

    summary = build_bundle_control_summary(bundle)
    residual_item = traceability_item(summary, "residual_risk_policy")

    assert summary["residual_risk_policy"] == []
    assert residual_item["mapped"] is False
    assert "residual_risk_policy" in summary["traceability"]["missing"]
    assert any(item["code"] == "residual_risk_unmanaged" for item in summary["diagnostics"])

    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Some risk is fine.",
        "有些风险可以接受。",
    )

    summary = build_bundle_control_summary(bundle)
    residual_item = traceability_item(summary, "residual_risk_policy")

    assert summary["residual_risk_policy"] == []
    assert residual_item["mapped"] is False
    assert "residual_risk_policy" in summary["traceability"]["missing"]
