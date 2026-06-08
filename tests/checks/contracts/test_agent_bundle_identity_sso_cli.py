from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_identity_sso_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-identity-sso-contract",
    }
    task_message = (
        "Plan a governed Loop for enterprise SAML/OIDC SSO rollout with SCIM/JIT provisioning. Success must prove "
        "IdP metadata signature validation, issuer and audience checks, assertion signature validation, tenant domain "
        "binding so Company A assertions cannot log into Company B, JIT provisioning and SCIM role/group mapping for "
        "owner/admin/member, deprovisioning and role downgrade behavior, logout and session expiry, replay/expired "
        "assertion negatives, audit logs for failed and forged assertions, migration/backward compatibility for "
        "password-login tenants, monitoring alerts, and support handoff. Fake done is one Okta user can log in, a "
        "SAML library accepts a happy-path assertion, UI shows SSO enabled, role mapping only works for admin, or "
        "forged/cross-tenant assertions are untested."
    )

    first_summary = _invoke_identity_sso_plan_round(
        runner,
        sample_workdir,
        message=task_message,
        env=env,
    )
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_identity_sso_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with a read-only Identity Contract Inspector that freezes IdP metadata, "
            "issuer/audience, signed assertion, tenant domain binding, replay/expiry, role/group mapping, SCIM/JIT "
            "provisioning and deprovisioning, password-login compatibility, audit and monitoring proof targets. Builder "
            "should only implement after that handoff. Then run SSO Assertion Evidence Inspector and Provisioning Mapping "
            "Inspector in parallel: Assertion Inspector verifies metadata/signature/issuer/audience, forged assertion, "
            "expired/replayed assertion, tenant confusion, logout/session expiry, and audit negatives; Provisioning Mapping "
            "Inspector verifies JIT/SCIM create/update/deactivate, owner/admin/member mapping, downgrade, deprovisioning, "
            "password-login compatibility, monitoring, and support handoff. GateKeeper must fail closed on "
            "Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, missing forged assertion "
            "negatives, missing tenant-binding proof, missing deprovisioning proof, or missing audit/monitoring proof."
        ),
        env=env,
    )
    _assert_identity_sso_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_identity_sso_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this identity contract-first parallel evidence direction.",
        env=env,
    )
    _assert_identity_sso_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _identity_sso_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_identity_sso_bundle(bundle_text)


def _invoke_identity_sso_plan_round(
    runner: CliRunner,
    sample_workdir: Path,
    *,
    message: str,
    env: dict[str, str],
) -> dict:
    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)["summary"]


def _assert_identity_sso_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Identity Contract Inspector" in agreement_text
    assert "SSO Assertion Evidence Inspector" in agreement_text
    assert "Provisioning Mapping Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "payment provider webhook" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_identity_sso_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    assert "Guide repair pass" not in third_summary["alignment_assistant_message"]
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in (
        "assertion signature",
        "tenant domain binding",
        "SCIM/JIT",
        "deprovisioning",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this identity" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _identity_sso_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_identity_sso_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "identity-sso-contract-parallel-controls"
    assert [step["id"] for step in workflow["steps"]] == [
        "identity_contract_inspection_step",
        "sso_builder_step",
        "sso_assertion_evidence_inspection_step",
        "provisioning_mapping_inspection_step",
        "identity_sso_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["identity_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "identity_sso_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "identity_sso_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "identity_contract_inspection_step",
        "sso_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "identity_contract_inspection_step",
        "sso_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "identity_contract_inspection_step",
        "sso_builder_step",
        "sso_assertion_evidence_inspection_step",
        "provisioning_mapping_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "sso-assertion",
        "identity-provisioning",
        "tenant-isolation",
        "permission-auth",
        "session-lifecycle",
        "audit-log",
        "monitoring",
        "backward-compatibility",
        "migration-rollback",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Identity SSO Workflow Notes" in bundle_text
    assert "Payment Webhook Workflow Notes" not in bundle_text
    assert "payment-webhook-contract-parallel-controls" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this identity" not in bundle_text
