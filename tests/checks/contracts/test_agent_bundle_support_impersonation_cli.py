from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_support_impersonation_rounds_use_policy_first_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-breakglass-policy-contract",
    }
    task_message = (
        "Plan a governed Loop for B2B SaaS support impersonation / break-glass admin access. Success must prove an "
        "approved ticket, customer consent, reason code, supervisor approval, time-bound session, actor/acting_as/"
        "on_behalf_of attribution, MFA or step-up, PII masking, tenant isolation, tamper-evident audit log, immediate "
        "revoke, expiry, anomaly monitoring for no-ticket, after-hours, bulk, sensitive, export, and long-running "
        "sessions. Fake done is a login-as button, feature flag, shared admin token, happy path impersonation, or banner."
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
            "Additional judgment: start with read-only policy inspection that freezes approval, consent, reason, time "
            "limit, attribution, MFA, privacy, tenant, audit, revoke, expiry, monitoring, and export proof targets. "
            "Builder only starts after that policy handoff. Then Access Evidence Inspector verifies no-ticket, expired, "
            "revoked, MFA, PII, cross-tenant, destructive, export, bulk, long-session, audit-integrity, and monitoring "
            "evidence. GateKeeper must fail closed on weak evidence."
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
    assert "Break-glass Policy Inspector" in agreement_text
    assert "Access Evidence Inspector" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this break-glass policy-first direction.",
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
        "support impersonation / break-glass admin access",
        "time-bound session",
        "tenant isolation",
        "tamper-evident audit log",
        "shared admin token",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this break-glass" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]

    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "support-impersonation-policy-first"
    assert [step["id"] for step in workflow["steps"]] == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
        "access_evidence_inspection_step",
        "breakglass_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["breakglass_policy_inspection_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
    ]
    gatekeeper_handoffs = workflow["steps"][-1]["inputs"]["handoffs_from"]
    assert gatekeeper_handoffs == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
        "access_evidence_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "support-impersonation",
        "permission-auth",
        "tenant-isolation",
        "privacy-redaction",
        "audit-integrity",
        "session-lifecycle",
        "monitoring",
        "data-export",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Support Break-glass Access Loop" in bundle_text
    assert "# Execution Strategy" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Repair Builder" not in bundle_text
    assert "Task Evidence Repair Loop" not in bundle_text
    assert "deletion-retention" not in gatekeeper_verifies
    assert "experiment-assignment" not in gatekeeper_verifies
    assert "Confirm; use this break-glass" not in bundle_text
