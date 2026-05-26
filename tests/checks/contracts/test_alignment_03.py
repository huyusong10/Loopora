from __future__ import annotations

from pathlib import Path

import pytest

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import build_bundle_control_summary
import loopora.service_alignment as alignment_module

from alignment_test_support import (
    _wait_for_status,
    _confirm_alignment_agreement,
)

def test_alignment_service_blocks_bundle_without_residual_risk_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_missing_residual_risk_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without clarifying what risks can remain.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "residual_risk_policy" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "residual_risk_policy" in event["payload"].get("error", "") for event in events)

def test_alignment_service_blocks_bundle_without_execution_strategy_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_missing_execution_strategy_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without deciding what the next rounds should prioritize.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "execution_strategy" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "execution_strategy" in event["payload"].get("error", "") for event in events)

def test_alignment_service_blocks_bundle_without_local_governance_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_missing_local_governance_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without clarifying local governance responsibilities.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "local_governance" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "local_governance" in event["payload"].get("error", "") for event in events)

@pytest.mark.parametrize(
    ("scenario", "missing_key"),
    [
        ("alignment_vague_success_surface_readiness_evidence", "success_surface"),
        ("alignment_vague_fake_done_readiness_evidence", "fake_done_risks"),
        ("alignment_vague_evidence_preferences_readiness_evidence", "evidence_preferences"),
        ("alignment_vague_role_posture_readiness_evidence", "role_posture"),
        ("alignment_role_posture_without_gatekeeper_readiness_evidence", "role_posture"),
    ],
)
def test_alignment_service_blocks_placeholder_judgment_readiness_evidence(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    missing_key: str,
) -> None:
    service = service_factory(scenario=scenario)

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=f"Build a starter experience with placeholder {missing_key} evidence.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert missing_key in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_stage_blocked" and missing_key in event["payload"].get("error", "")
        for event in events
    )

def test_alignment_readiness_evidence_rejects_placeholder_judgment_surfaces() -> None:
    service = alignment_module.ServiceAlignmentMixin
    readiness_evidence = {
        "loop_fit": "Loopora is needed because roles must gather proof, compare findings, and keep judgment alive across iterations.",
        "task_scope": "The task scope is the requested starter workflow and its evidence-bearing bundle surfaces.",
        "success_surface": "The success surface is the user-visible primary path plus the runnable checks that prove it works.",
        "fake_done_risks": "Blocking fake-done findings include screenshots without checks and claims without direct artifacts.",
        "evidence_preferences": "Evidence must project Proven, Weak, Unproven, Blocking, and Residual risk before closure.",
        "execution_strategy": "Build the focused flow first, then repair evidence gaps before expanding or polishing.",
        "residual_risk_policy": "Minor polish risk may remain visible as a tracked follow-up owned by product; ownerless primary-flow risk fails closed.",
        "judgment_tradeoffs": "Prefer proof over speed when the primary flow or evidence boundary is uncertain.",
        "local_governance": "No extra repository-rule content is claimed; roles follow the task contract and evidence rules.",
        "role_posture": "Builder implements, Inspector verifies direct evidence, and GateKeeper decides from the evidence buckets.",
        "workflow_shape": "Builder, Inspector, and GateKeeper exchange explicit handoffs before any finish decision.",
        "workdir_facts": "Snapshot assumptions remain unknown until observed in the workdir.",
    }
    valid_issues = service._readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert not {
        "success_surface",
        "fake_done_risks",
        "evidence_preferences",
        "role_posture",
    }.intersection(valid_issues)

    placeholders = {
        "success_surface": "The final result should be good and useful for the user.",
        "fake_done_risks": "The result should avoid bugs and should be high quality.",
        "evidence_preferences": "The user needs enough proof to feel confident before the result is accepted.",
        "role_posture": "Use three roles to complete the task well.",
    }
    for key, value in placeholders.items():
        candidate = dict(readiness_evidence)
        candidate[key] = value
        issues = service._readiness_evidence_issues({"readiness_evidence": candidate})
        assert key in issues

    no_gatekeeper = dict(readiness_evidence)
    no_gatekeeper["role_posture"] = "Builder leaves evidence and Inspector reviews the handoff carefully."
    assert "role_posture" in service._readiness_evidence_issues({"readiness_evidence": no_gatekeeper})
    chinese_no_gatekeeper = dict(readiness_evidence)
    chinese_no_gatekeeper["role_posture"] = "Builder 负责构建，Inspector 验证证据。"
    assert "role_posture" in service._readiness_evidence_issues({"readiness_evidence": chinese_no_gatekeeper})

def test_alignment_readiness_evidence_rejects_unmanaged_residual_risk_policy() -> None:
    readiness_evidence = {
        "loop_fit": "Loopora is needed because roles must gather proof, compare findings, and keep judgment alive across iterations.",
        "task_scope": "The task scope is the requested starter workflow and its evidence-bearing bundle surfaces.",
        "success_surface": "The success surface is the user-visible primary path plus the runnable checks that prove it works.",
        "fake_done_risks": "Blocking fake-done findings include screenshots without checks and claims without direct artifacts.",
        "evidence_preferences": (
            "Evidence must project Proven direct checks, Weak indirect signals, Unproven claims, "
            "Blocking findings, and Residual risk."
        ),
        "execution_strategy": "Build the focused flow first, then repair evidence gaps before expanding or polishing.",
        "residual_risk_policy": "Minor polish risk may remain visible as a tracked follow-up owned by product; ownerless primary-flow risk fails closed.",
        "judgment_tradeoffs": "Prefer proof over speed when the primary flow or evidence boundary is uncertain.",
        "local_governance": "No extra repository-rule content is claimed; roles follow the task contract and evidence rules.",
        "role_posture": "Builder implements, Inspector verifies direct evidence, and GateKeeper decides from the evidence buckets.",
        "workflow_shape": "Builder, Inspector, and GateKeeper exchange explicit handoffs before any finish decision.",
        "workdir_facts": "Snapshot assumptions remain unknown until observed in the workdir.",
    }
    valid_issues = alignment_module.ServiceAlignmentMixin._readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "residual_risk_policy" not in valid_issues

    readiness_evidence["residual_risk_policy"] = "Some risk is fine."
    issues = alignment_module.ServiceAlignmentMixin._readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" in issues

    readiness_evidence["residual_risk_policy"] = "有些风险可以接受。"
    issues = alignment_module.ServiceAlignmentMixin._readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" in issues

    readiness_evidence["residual_risk_policy"] = "有些风险可以接受，但必须由客服负责人跟进工单。"
    issues = alignment_module.ServiceAlignmentMixin._readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" not in issues

def test_alignment_readiness_evidence_rejects_local_governance_marker_lists_without_responsibility() -> None:
    service = alignment_module.ServiceAlignmentMixin
    readiness_evidence = {
        "loop_fit": "Loopora is needed because roles must gather proof, compare findings, and keep judgment alive across iterations.",
        "task_scope": "The task scope is the requested starter workflow and its evidence-bearing bundle surfaces.",
        "success_surface": "The success surface is the user-visible primary path plus the runnable checks that prove it works.",
        "fake_done_risks": "Blocking fake-done findings include screenshots without checks and claims without direct artifacts.",
        "evidence_preferences": "Evidence must project Proven, Weak, Unproven, Blocking, and Residual risk before closure.",
        "execution_strategy": "Build the focused flow first, then repair evidence gaps before expanding or polishing.",
        "residual_risk_policy": "Minor polish risk may remain visible as a tracked follow-up owned by product; ownerless primary-flow risk fails closed.",
        "judgment_tradeoffs": "Prefer proof over speed when the primary flow or evidence boundary is uncertain.",
        "local_governance": "AGENTS.md, design/README.md, design/, and tests/ are visible governance markers.",
        "role_posture": "Builder implements, Inspector verifies direct evidence, and GateKeeper decides from the evidence buckets.",
        "workflow_shape": "Builder, Inspector, and GateKeeper exchange explicit handoffs before any finish decision.",
        "workdir_facts": "Snapshot assumptions remain unknown until observed in the workdir.",
    }

    issues = service._readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "local_governance" in issues

    readiness_evidence["local_governance"] = (
        "Builder reads AGENTS.md and design/README.md before editing; Inspector verifies design/ and tests/ "
        "obligations against the result; GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, "
        "Unproven, or Blocking."
    )
    issues = service._readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "local_governance" not in issues

def test_alignment_readiness_evidence_uses_workdir_snapshot_for_local_governance() -> None:
    service = alignment_module.ServiceAlignmentMixin
    readiness_evidence = {
        "loop_fit": "Loopora is needed because roles must gather proof, compare findings, and keep judgment alive across iterations.",
        "task_scope": "The task scope is the requested starter workflow and its evidence-bearing bundle surfaces.",
        "success_surface": "The success surface is the user-visible primary path plus the runnable checks that prove it works.",
        "fake_done_risks": "Blocking fake-done findings include screenshots without checks and claims without direct artifacts.",
        "evidence_preferences": "Evidence must project Proven, Weak, Unproven, Blocking, and Residual risk before closure.",
        "execution_strategy": "Build the focused flow first, then repair evidence gaps before expanding or polishing.",
        "residual_risk_policy": "Minor polish risk may remain visible as a tracked follow-up owned by product; ownerless primary-flow risk fails closed.",
        "judgment_tradeoffs": "Prefer proof over speed when the primary flow or evidence boundary is uncertain.",
        "local_governance": "No extra repository-rule content is claimed.",
        "role_posture": "Builder implements, Inspector verifies direct evidence, and GateKeeper decides from the evidence buckets.",
        "workflow_shape": "Builder, Inspector, and GateKeeper exchange explicit handoffs before any finish decision.",
        "workdir_facts": "Snapshot observed project markers.",
    }
    snapshot = "\n".join(
        [
            "AGENTS.md exists: yes",
            "design/ exists: yes",
            "design/README.md exists: yes",
            "tests/ exists: yes",
        ]
    )

    issues = service._readiness_evidence_issues({"readiness_evidence": readiness_evidence}, workdir_snapshot=snapshot)
    assert "local_governance" in issues

    readiness_evidence["local_governance"] = (
        "Builder reads AGENTS.md and design/README.md before editing; Inspector verifies design/ and tests/ "
        "obligations against the result; GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, "
        "Unproven, or Blocking."
    )
    issues = service._readiness_evidence_issues({"readiness_evidence": readiness_evidence}, workdir_snapshot=snapshot)
    assert "local_governance" not in issues

def test_alignment_traceability_uses_workdir_snapshot_for_local_governance(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()
    session = {
        "workdir": str(sample_workdir),
        "working_agreement": {
            "readiness_evidence": {
                "local_governance": (
                    "If project-local governance markers are present, Builder reads applicable rules, "
                    "Inspector verifies related obligations, and GateKeeper blocks skipped governance."
                ),
            }
        },
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("project-local governance markers" in issue for issue in issues)

def test_alignment_workdir_snapshot_detects_applicable_parent_agents_file(tmp_path: Path) -> None:
    service = alignment_module.ServiceAlignmentMixin
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")

    snapshot = service._alignment_workdir_snapshot(workdir)

    assert "AGENTS.md exists: no" in snapshot
    assert "Applicable AGENTS.md exists: yes" in snapshot
    assert "Applicable AGENTS.md paths: ../../AGENTS.md" in snapshot
    assert service._workdir_snapshot_has_governance_markers(snapshot)

def test_alignment_traceability_uses_parent_agents_snapshot_for_local_governance(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir)))
    session = {
        "workdir": str(workdir),
        "working_agreement": {
            "readiness_evidence": {
                "local_governance": "No direct AGENTS.md file is visible in the selected workdir.",
            }
        },
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("project-local governance markers" in issue for issue in issues)

def test_alignment_service_blocks_invented_workdir_facts_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_invented_workdir_facts_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without grounding workdir facts.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "workdir_facts" in session["transcript"][-1]["content"]

def test_alignment_service_blocks_observed_stack_claims_not_in_workdir_snapshot(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_invented_observed_workdir_facts_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without inventing stack facts.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "workdir_facts" in session["transcript"][-1]["content"]
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")
    assert "package.json" not in prompt_text
    assert "tests/ exists: no" in prompt_text

def test_alignment_service_blocks_bundle_observed_stack_claims_not_in_workdir_snapshot(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_bundle_unsupported_observed_workdir_claim")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without inventing stack facts in the final bundle.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field spec.markdown must not claim an observed workdir stack" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_validation_failed" and "bundle field spec.markdown" in event["payload"].get("error", "") for event in events)

def test_alignment_service_blocks_governance_markers_without_bundle_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_governance_markers_listed_without_responsibilities")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience that must respect local project governance markers.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "project-local governance markers" in session["error_message"]
    assert "Builder reading" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "project-local governance markers" in event["payload"].get("error", "") for event in events
    )

def test_alignment_traceability_checks_governance_markers_across_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(
        alignment_bundle_yaml(str(sample_workdir)).replace(
            "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
            "Workdir Snapshot detected AGENTS.md and tests/. Ship the focused starter experience.",
        )
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "AGENTS.md and tests/ are project-local governance markers that must shape runtime evidence.",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("project-local governance markers" in issue for issue in issues)

def test_alignment_traceability_checks_loop_fit_task_terms(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "loop_fit": (
                    "Browsertrace needs Loopora because later rounds must create new browsertrace proof "
                    "before GateKeeper can close."
                ),
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("loop_fit missing browsertrace" in issue for issue in issues)

def test_alignment_traceability_checks_agreement_success_categories(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund approval path so Support admin can approve a refund and audit log records the actor.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means Support admin can approve a refund, audit log records the actor, "
                    "and customer receives an email notification."
                ),
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "notification/message" in issue for issue in issues)

def test_alignment_traceability_checks_agreement_evidence_preference_categories(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Prefer project-owned checks, direct run output, and concrete artifacts before screenshots or claims.",
        "Prefer browser journey proof before screenshots or claims.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": (
                    "Evidence must include a browser journey and audit log command output before GateKeeper can pass."
                ),
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence preferences" in issue and "audit/log" in issue for issue in issues)

def test_alignment_traceability_checks_agreement_accessibility_and_locale_categories(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means keyboard users can complete checkout, screen reader labels are available, "
                    "and Chinese and English variants preserve the same action."
                ),
                "evidence_preferences": (
                    "Evidence must include keyboard navigation proof and Chinese and English locale verification."
                ),
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("success surface" in issue and "locale/i18n" in issue for issue in issues)
    assert any("evidence preferences" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("evidence preferences" in issue and "locale/i18n" in issue for issue in issues)

def test_alignment_traceability_rejects_disconnected_governance_marker_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] += (
        "\nWorkdir Snapshot detected AGENTS.md, design/README.md, design/, and tests/.\n"
        + ("Neutral context keeps the marker list separate from generic role responsibilities. " * 10)
    )
    bundle["collaboration_summary"] += (
        "\nBuilder reads task notes. Inspector checks the result. GateKeeper blocks weak proof."
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "workdir_facts": "AGENTS.md, design/README.md, design/, and tests/ must shape runtime governance.",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("project-local governance markers" in issue for issue in issues)

def test_alignment_traceability_accepts_marker_specific_role_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\n\nInspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result."
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        "\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking."
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "workdir_facts": "AGENTS.md, design/README.md, design/, and tests/ must shape runtime governance.",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not any("project-local governance markers" in issue for issue in issues)

def test_alignment_traceability_accepts_role_notes_governance_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    spec_without_role_notes = bundle["spec"]["markdown"].split("\n# Role Notes\n", 1)[0]
    bundle["spec"]["markdown"] = (
        spec_without_role_notes
        + "\n\n# Role Notes\n\n"
        + "## Builder Notes\n\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing.\n\n"
        + "## Inspector Notes\n\nInspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result.\n\n"
        + "## GateKeeper Notes\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking.\n"
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "workdir_facts": "AGENTS.md, design/README.md, design/, and tests/ must shape runtime governance.",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not any("project-local governance markers" in issue for issue in issues)

def test_alignment_traceability_rejects_summary_only_governance_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["collaboration_summary"] += (
        "\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing. "
        "Inspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result. "
        "GateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking."
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "workdir_facts": "AGENTS.md, design/README.md, design/, and tests/ must shape runtime governance.",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("project-local governance markers" in issue for issue in issues)

def test_alignment_traceability_ignores_metadata_and_loop_names(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["metadata"]["name"] = "browsertrace"
    bundle["metadata"]["description"] = "browsertrace"
    bundle["loop"]["name"] = "browsertrace"
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence_preferences missing browsertrace" in issue for issue in issues)

def test_alignment_traceability_counts_workflow_step_inputs_as_runtime_surface(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["workflow"]["steps"][0]["inputs"] = {"evidence_query": {"target_ids": ["browsertrace"]}}
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = service._alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not any("evidence_preferences" in issue for issue in issues)

def test_bundle_control_summary_projects_execution_strategy(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))

    summary = build_bundle_control_summary(bundle)

    assert any("Build one focused starter slice" in item for item in summary["execution_strategy"])
    assert any(item["key"] == "execution_strategy" and item["mapped"] for item in summary["traceability"]["items"])

def test_alignment_service_blocks_generated_bundle_lineage_metadata(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_generated_lineage_metadata")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a standalone candidate bundle, not a lineage revision.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must omit metadata.source_bundle_id and metadata.revision" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_validation_failed" and "source context is temporary" in event["payload"].get("error", "") for event in events)

def test_alignment_service_blocks_markdown_fenced_bundle_yaml(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_markdown_fenced_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a raw YAML bundle without wrappers.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must be one raw YAML document" in session["error_message"]
    assert "must start with version: 1" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_validation_failed" and "markdown-fenced output" in event["payload"].get("error", "") for event in events)
