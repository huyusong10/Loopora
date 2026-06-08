from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_kyc_aml_rounds_use_compliance_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-kyc-aml-contract",
    }
    task_message = (
        "Plan a governed Loop for marketplace seller onboarding KYC/KYB and AML sanctions screening. Success must prove "
        "identity verification, business registry, beneficial owner checks, document OCR/liveness, address verification, "
        "sanctions/PEP/adverse-media/watchlist screening, risk score, manual review queue, appeal/resubmission, "
        "periodic rescreening, provider webhook signature/replay/out-of-order/idempotency, region retention, audit reason "
        "codes, and payout hold/release consistency. Fake done is one provider sandbox approved response, UI verified, "
        "stored provider status, or one happy-path webhook. Evidence should include provider contract fixtures, golden "
        "approved/rejected/manual-review cases, false positive and false negative sanctions samples, expired/fraudulent "
        "document negatives, manual review rubric, decision reason audit trail, webhook ordering proof, rescreening job "
        "proof, payout hold ledger reconciliation, privacy redaction, and monitoring alerts."
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
            "Additional judgment: start with a read-only Compliance Contract Inspector that freezes provider contracts, "
            "jurisdiction/retention rules, required KYC/KYB fields, sanctions/PEP/watchlist sample sets, manual review "
            "rubric, appeal/resubmission policy, rescreening cadence, webhook signature/replay/order/idempotency, audit "
            "reason code schema, privacy redaction, monitoring, and payout hold/release ledger proof targets. Builder "
            "should only implement after that contract handoff. Then run independent Screening Evidence Inspector and "
            "Financial Controls Inspector in parallel: Screening verifies golden approved/rejected/manual-review cases, "
            "false positive/false negative sanctions samples, expired/fraudulent document negatives, provider failure and "
            "webhook replay/order; Financial Controls verifies payout holds/releases, ledger reconciliation, region "
            "retention, audit reason trail, privacy redaction, and monitoring alerts. GateKeeper must fail closed on "
            "sandbox-approved-only, UI verified-only, stored provider status-only, happy-path webhook, weak manual review "
            "evidence, or missing payout ledger proof."
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
    assert "Compliance Contract Inspector" in agreement_text
    assert "Screening Evidence Inspector" in agreement_text
    assert "Financial Controls Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this compliance contract-first direction.",
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
        "KYC/KYB",
        "AML sanctions",
        "manual review queue",
        "payout hold/release",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this compliance" not in ready_projection_text
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
    assert workflow["preset"] == "kyc-aml-compliance-parallel-controls"
    assert [step["id"] for step in workflow["steps"]] == [
        "compliance_contract_inspection_step",
        "kyc_builder_step",
        "screening_evidence_inspection_step",
        "financial_controls_inspection_step",
        "kyc_aml_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["compliance_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "kyc_aml_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "kyc_aml_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "compliance_contract_inspection_step",
        "kyc_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "compliance_contract_inspection_step",
        "kyc_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "compliance_contract_inspection_step",
        "kyc_builder_step",
        "screening_evidence_inspection_step",
        "financial_controls_inspection_step",
    ]
    assert yaml.safe_load(bundle_text)["metadata"]["name"] == "KYC/AML Seller Onboarding Loop"
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "kyc-aml-screening",
        "provider-contract",
        "webhook-ordering",
        "payout-settlement",
        "ledger-reconciliation",
        "privacy-redaction",
        "human-review",
        "monitoring",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "KYC/AML GateKeeper Notes" in bundle_text
    assert "Confirm; use this compliance" not in bundle_text
    for generic_repair_token in (
        "Task Evidence Repair Loop",
        "Repair Builder",
        "Guide 只把弱证据",
        "task-evidence-repair",
        "Builder -> Inspector -> Guide",
    ):
        assert generic_repair_token not in bundle_text
