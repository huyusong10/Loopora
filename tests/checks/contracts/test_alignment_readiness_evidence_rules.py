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


def test_alignment_readiness_evidence_does_not_treat_existing_user_goal_as_useful_placeholder() -> None:
    readiness_evidence = _complete_readiness_evidence(
        success_surface="成功意味着修订后的独立 bundle 保持既有用户目标，同时让证据缺口可观察、可验证。"
    )

    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "success_surface" not in issues

    readiness_evidence["success_surface"] = "成功意味着最终结果对用户有用。"
    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "success_surface" in issues


def test_alignment_readiness_evidence_accepts_specific_completion_judgment_with_vague_context() -> None:
    readiness_evidence = _complete_readiness_evidence(
        success_surface=(
            "成功面采用用户给出的完成判断：帮我规划一个更好的用户体验，先别太复杂，"
            "但完成时必须证明新用户能从注册进入第一个关键操作，失败时有清晰错误和恢复路径。"
            "GateKeeper 还要看到可运行行为、handoff 和证据桶能证明这条判断。"
        )
    )

    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "success_surface" not in issues


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


def test_alignment_readiness_evidence_accepts_confirmation_only_open_questions_variants() -> None:
    for value in (
        "no-open-questions",
        "explicit-confirmation-only",
        "No unresolved bundle-shaping questions remain. The only remaining step is explicit confirmation of this visible working agreement.",
    ):
        readiness_evidence = _complete_readiness_evidence(open_questions=value)

        issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

        assert "open_questions" not in issues


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


def test_alignment_readiness_evidence_accepts_plural_inspector_governance_responsibility() -> None:
    readiness_evidence = _complete_readiness_evidence(
        local_governance=(
            "Observed project-local markers affect this Loop. The workdir snapshot shows design/ exists, "
            "design/README.md exists, and tests/ exists. Builder should read relevant design and tests before changing work. "
            "Inspectors should verify relevant design or test contracts or explain why validation is unavailable. "
            "GateKeeper should treat skipped local governance, missing expected validation, unsupported workdir claims, "
            "or unreviewed proof-harness changes as Weak, Unproven, or Blocking."
        )
    )

    issues = readiness_evidence_issues({"readiness_evidence": readiness_evidence})

    assert "local_governance" not in issues


def test_alignment_readiness_evidence_accepts_natural_chinese_governance_responsibility() -> None:
    readiness_evidence = _complete_readiness_evidence(
        local_governance=(
            "Workdir Snapshot 显示 /Users/hys/dev/Loopora 存在 design/、design/README.md 和 tests/，"
            "不存在 AGENTS.md 或适用 AGENTS.md；还显示 pyproject.toml、README.md、README.zh-CN.md、uv.lock，"
            "但未读取内容。后续 Loop 应要求执行方先读相关 design 入口和测试约定，"
            "检视方核对设计/测试契约，最终判断把跳过本地 design/tests 或缺少预期验证视为 "
            "Weak、Unproven 或 Blocking；不能发明具体设计内容、测试命令或技术栈。"
        )
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
