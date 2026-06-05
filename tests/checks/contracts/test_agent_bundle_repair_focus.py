from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    alignment_bundle_yaml,
    assert_agent_v3_envelope,
    cli,
    cli_agent_adapter_commands,
    json,
    yaml,
)


def test_agent_plan_repair_focus_explains_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project explicit host Agent success criteria "
        "into runnable surfaces: missing data/export/report"
    )

    assert hints[0] == "add these missing success criteria categories from --message to runnable plan surfaces: data/export/report"
    assert hints[1] == (
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, "
        "evidence preferences, and GateKeeper closure"
    )


def test_agent_plan_repair_focus_explains_multiple_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project the host Agent task summary "
        "into runnable surfaces: missing soc2, vendor, rollout; "
        "agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: "
        "missing permission/audit, download/export-only; "
        "agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: "
        "missing audit/log, permission/auth"
    )

    assert "add these missing task objects from --message to runnable plan surfaces: soc2, vendor, rollout" in hints
    assert (
        "add these missing fake-done risks categories from --message to runnable plan surfaces: "
        "permission/audit, download/export-only"
    ) in hints
    assert (
        "add these missing evidence preferences categories from --message to runnable plan surfaces: "
        "audit/log, permission/auth"
    ) in hints
    assert "include those evidence modes in spec Evidence Preferences, Inspector responsibilities, workflow handoffs, and GateKeeper closure" in hints


def test_agent_plan_repair_focus_explains_common_semantic_lint_issues() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: "
        "collaboration_summary must explain why this task needs multi-round Loopora governance; "
        "spec must include at least one Success Surface bullet; "
        "spec Residual Risk guidance must name accepted risk handling or fail closed"
    )

    assert (
        "explain in collaboration_summary what later evidence, reviews, handoffs, or GateKeeper rounds add beyond one Agent pass"
        in hints
    )
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in hints
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in hints


def test_agent_plan_repair_focus_explains_project_local_governance_marker_lint() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: alignment bundle must convert project-local governance markers into "
        "Builder reading, Inspector or Custom verification, and GateKeeper gating responsibilities"
    )

    assert (
        "add local governance responsibility sentences near the marker text: Builder reads and follows applicable "
        "project-local governance before edits; Inspector verifies related design/tests/governance evidence; "
        "GateKeeper treats skipped governance or missing expected validation as Weak, Unproven, or Blocking"
    ) in hints


def test_agent_plan_repair_focus_explains_yaml_control_characters() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        'invalid bundle YAML: unacceptable character #x0000: special characters are not allowed in "<unicode string>", '
        "position 13857"
    )

    assert (
        "remove hidden YAML control characters such as NUL bytes from the plan file, especially inside quoted ids"
        in hints
    )


def test_cli_agent_gen_json_repair_focus_explains_structural_plan_errors(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bad-bundle.yml"
    bundle_file.write_text("version: 1\nspec:\n  name: Refund admin\n", encoding="utf-8")
    result = invoke_agent_plan_json(
        sample_workdir, bundle_file, "Build a refund admin workflow with audit and provider-failure evidence."
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert summary["validation_error"] == "bundle metadata.name is required"
    assert "add metadata.name so the plan has a stable reviewable identity" in summary["repair_focus"]


def test_cli_agent_gen_json_repair_focus_explains_control_character_yaml_errors(
    tmp_path: Path, sample_workdir: Path
) -> None:
    bundle_file = tmp_path / "nul-bundle.yml"
    bundle_file.write_text('version: 1\nmetadata:\n  name: "bad\x00id"\n', encoding="utf-8")
    result = invoke_agent_plan_json(
        sample_workdir,
        bundle_file,
        "Build a refund admin workflow with audit and provider-failure evidence.",
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert "invalid bundle YAML:" in summary["validation_error"]
    assert (
        "remove hidden YAML control characters such as NUL bytes from the plan file, especially inside quoted ids"
        in summary["repair_focus"]
    )


def test_cli_agent_gen_json_repair_focus_explains_semantic_lint_issues(tmp_path: Path, sample_workdir: Path) -> None:
    payload = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    payload["collaboration_summary"] = "Coordinate a starter slice."
    markdown = payload["spec"]["markdown"]
    markdown = markdown.replace(
        "# Success Surface\n\n- The primary user flow is understandable, maintainable, and easy to extend after the first pass.\n\n",
        "",
    )
    markdown = markdown.replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; "
        "fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk remains.",
    )
    payload["spec"]["markdown"] = markdown
    bundle_file = tmp_path / "semantic-lint-bundle.yml"
    bundle_file.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    result = invoke_agent_plan_json(
        sample_workdir,
        bundle_file,
        "Ship the focused starter experience in the target workdir with evidence and GateKeeper review.",
    )

    assert result.exit_code == 0, result.stdout
    output = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        output, kind="agent_plan", summary_key="agent_plan_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "repair_candidate_plan_file"
    assert "collaboration_summary must explain the governance story" in summary["validation_error"]
    assert "spec must include at least one Success Surface bullet" in summary["validation_error"]
    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" in summary["validation_error"]
    assert "rewrite collaboration_summary with the concrete task, evidence flow, blockers, and GateKeeper closure" in summary["repair_focus"]
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in summary["repair_focus"]
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in summary["repair_focus"]


def invoke_agent_plan_json(sample_workdir: Path, bundle_file: Path, message: str):
    return CliRunner().invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            message,
            "--bundle-file",
            str(bundle_file),
            "--no-web",
            "--json",
        ],
    )
