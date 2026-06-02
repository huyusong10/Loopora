from __future__ import annotations

from loopora.alignment_readiness_rules import readiness_evidence_issues


def _complete_readiness_evidence(**overrides: str) -> dict[str, str]:
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
    readiness_evidence.update(overrides)
    return readiness_evidence


def test_alignment_readiness_evidence_rejects_placeholder_judgment_surfaces() -> None:
    readiness_evidence = _complete_readiness_evidence()
    valid_issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})
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
        issues = readiness_evidence_issues({"readiness_evidence": candidate})
        assert key in issues

    no_gatekeeper = dict(readiness_evidence)
    no_gatekeeper["role_posture"] = "Builder leaves evidence and Inspector reviews the handoff carefully."
    assert "role_posture" in readiness_evidence_issues({"readiness_evidence": no_gatekeeper})
    chinese_no_gatekeeper = dict(readiness_evidence)
    chinese_no_gatekeeper["role_posture"] = "Builder 负责构建，Inspector 验证证据。"
    assert "role_posture" in readiness_evidence_issues({"readiness_evidence": chinese_no_gatekeeper})


def test_alignment_readiness_evidence_rejects_unmanaged_residual_risk_policy() -> None:
    readiness_evidence = _complete_readiness_evidence()
    valid_issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "residual_risk_policy" not in valid_issues

    readiness_evidence["residual_risk_policy"] = "Some risk is fine."
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" in issues

    readiness_evidence["residual_risk_policy"] = "有些风险可以接受。"
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" in issues

    readiness_evidence["residual_risk_policy"] = "有些风险可以接受，但必须由客服负责人跟进工单。"
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "residual_risk_policy" not in issues


def test_alignment_readiness_evidence_rejects_local_governance_marker_lists_without_responsibility() -> None:
    readiness_evidence = _complete_readiness_evidence(
        local_governance="AGENTS.md, design/README.md, design/, and tests/ are visible governance markers."
    )

    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "local_governance" in issues

    readiness_evidence["local_governance"] = (
        "Builder reads AGENTS.md and design/README.md before editing; Inspector verifies design/ and tests/ "
        "obligations against the result; GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, "
        "Unproven, or Blocking."
    )
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})
    assert "local_governance" not in issues


def test_alignment_readiness_evidence_uses_workdir_snapshot_for_local_governance() -> None:
    readiness_evidence = _complete_readiness_evidence(
        local_governance="No extra repository-rule content is claimed.",
        workdir_facts="Snapshot observed project markers.",
    )
    snapshot = "\n".join(
        [
            "AGENTS.md exists: yes",
            "design/ exists: yes",
            "design/README.md exists: yes",
            "tests/ exists: yes",
        ]
    )

    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence}, workdir_snapshot=snapshot)
    assert "local_governance" in issues

    readiness_evidence["local_governance"] = (
        "Builder reads AGENTS.md and design/README.md before editing; Inspector verifies design/ and tests/ "
        "obligations against the result; GateKeeper treats skipped AGENTS.md or tests/ validation as Weak, "
        "Unproven, or Blocking."
    )
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence}, workdir_snapshot=snapshot)
    assert "local_governance" not in issues
