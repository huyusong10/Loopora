from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_authorization_policy_rounds_use_parallel_inspection(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-authz-parallel-contract",
    }
    task_message = (
        "Plan a governed Loop for a B2B admin authorization policy consistency refactor. Success must prove one policy "
        "decision is enforced consistently across API endpoints, UI affordances, background jobs, CSV exports, cache "
        "invalidation, and audit logs for owner/admin/viewer roles, field-level permissions, temporary access, SCIM/SSO "
        "group mapping, and tenant boundaries. Fake done is hiding buttons, adding one middleware check, checking only "
        "the admin happy path, or leaving cache revocation/export/jobs/audit to follow-up; evidence beats speed."
    )

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: the target is clear enough to build a narrow slice, but the review must split independent "
            "concerns. Use a Contract Inspector to verify the permission matrix, policy-decision trace, version rollout and "
            "backwards compatibility. In parallel, use a Security Evidence Inspector to attack negative authorization, "
            "cross-tenant escalation, stale cache/revocation, export/report access, job execution, field-level leakage, and "
            "audit evidence. GateKeeper should block if either inspection is Weak or Unproven."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Contract Inspector" in agreement_text
    assert "Security Evidence Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in (
        "policy decision",
        "API",
        "UI",
        "background jobs",
        "exports",
        "cache",
        "audit",
        "tenant",
        "cross-tenant",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text

    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "authorization-policy-parallel-inspection"
    assert [step["id"] for step in workflow["steps"]] == [
        "policy_builder_step",
        "contract_inspection_step",
        "security_evidence_inspection_step",
        "authorization_gatekeeper_step",
    ]
    assert workflow["steps"][1]["parallel_group"] == "authorization_review_pack"
    assert workflow["steps"][2]["parallel_group"] == "authorization_review_pack"
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["policy_builder_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == ["policy_builder_step"]
    gatekeeper_handoffs = workflow["steps"][-1]["inputs"]["handoffs_from"]
    assert "contract_inspection_step" in gatekeeper_handoffs
    assert "security_evidence_inspection_step" in gatekeeper_handoffs
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "authorization-policy",
        "tenant-isolation",
        "permission-auth",
        "cache-invalidation",
        "data-export",
        "audit-log",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Authorization Policy Workflow Notes" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "task-specific evidence workflow" not in bundle_text
    assert "task-specific proof focuses" not in bundle_text
    assert "Confirm; use this direction" not in bundle_text
