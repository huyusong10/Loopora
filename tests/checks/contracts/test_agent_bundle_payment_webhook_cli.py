from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_payment_webhook_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-webhook-ledger-contract",
    }
    task_message = (
        "Plan a governed Loop for payment provider webhook ingestion for checkout, refunds, disputes, and payouts. "
        "Success must prove provider contract fixtures, signature verification, timestamp tolerance, replay protection, "
        "idempotency key handling, duplicate prevention, out-of-order delivery, event version compatibility, ledger "
        "reconciliation, payout settlement reconciliation, dispute lifecycle state transitions, retry/backoff, "
        "dead-letter queue, audit log, privacy redaction, monitoring alerts, and manual replay tooling. Fake done is "
        "one happy-path checkout.session.completed webhook, accepting unsigned events in dev mode, storing provider "
        "status, deduping only by database unique constraint, or docs-only provider contract. Evidence should include "
        "signed fixture corpus, invalid signature negatives, stale timestamp negatives, replay and duplicate event "
        "negatives, out-of-order sequences, idempotency ledger checks, provider retry/failure proof, DLQ proof, manual "
        "replay proof, audit refs, monitoring alerts, and reconciliation reports."
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
            "Additional judgment: start with a read-only Webhook Contract Inspector that freezes provider event "
            "schemas, signature and timestamp rules, idempotency keys, ordering assumptions, retry/DLQ policy, "
            "ledger/dispute/payout state machines, audit/privacy requirements, monitoring alerts, and manual replay "
            "proof targets. Builder should only implement after that handoff. Then run Webhook Evidence Inspector and "
            "Ledger Reconciliation Inspector in parallel: Webhook Evidence Inspector verifies signed fixtures, invalid "
            "signature, stale timestamp, replay, duplicate, out-of-order, version compatibility, retry/backoff, DLQ, "
            "and manual replay evidence; Ledger Reconciliation Inspector verifies checkout/refund/dispute/payout "
            "ledger entries, settlement reports, idempotency effects, audit refs, privacy redaction, and monitoring. "
            "GateKeeper must fail closed on happy-path webhook only, unsigned dev-mode acceptance, provider-status-only, "
            "database-constraint-only dedupe, docs-only contract, missing replay negatives, missing ordering proof, "
            "missing ledger reconciliation, or missing monitoring/DLQ proof."
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
    assert "Webhook Contract Inspector" in agreement_text
    assert "Webhook Evidence Inspector" in agreement_text
    assert "Ledger Reconciliation Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this webhook contract-first parallel evidence direction.",
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
        "signature verification",
        "out-of-order delivery",
        "ledger reconciliation",
        "dead-letter queue",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this webhook" not in ready_projection_text
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
    assert workflow["preset"] == "payment-webhook-contract-parallel-controls"
    assert [step["id"] for step in workflow["steps"]] == [
        "webhook_contract_inspection_step",
        "payment_webhook_builder_step",
        "webhook_evidence_inspection_step",
        "ledger_reconciliation_inspection_step",
        "payment_webhook_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["webhook_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "payment_webhook_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "payment_webhook_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "webhook_contract_inspection_step",
        "payment_webhook_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "webhook_contract_inspection_step",
        "payment_webhook_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "webhook_contract_inspection_step",
        "payment_webhook_builder_step",
        "webhook_evidence_inspection_step",
        "ledger_reconciliation_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "webhook-ordering",
        "ledger-reconciliation",
        "payout-settlement",
        "dispute-chargeback",
        "payment-refund-billing",
        "provider-contract",
        "idempotency",
        "retry-timeout",
        "queue-recovery",
        "audit-log",
        "privacy-redaction",
        "monitoring",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Payment Webhook Workflow Notes" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this webhook" not in bundle_text
