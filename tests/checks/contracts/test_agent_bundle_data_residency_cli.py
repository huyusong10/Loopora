from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_data_residency_rounds_use_contract_first_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-residency-contract",
    }
    task_message = (
        "Plan a governed Loop for enterprise SaaS data residency and regional isolation for EU and US tenants. "
        "Success must prove tenant residency policy, EU/US region routing, primary DB, object storage, search index, "
        "cache, queue, backups, logs, analytics export, third-party processor and subprocessor allowlist, DPA, "
        "encryption key region, failover, migration/backfill, support/admin access, data export, audit log, "
        "observability trace, cross-region egress monitoring, and wrong-region write negatives. Fake done is UI "
        "showing region=EU, an env var, tenant table region field, one routed request, or docs-only DPA. Evidence "
        "should include regional data-flow inventory, processor contract fixtures, wrong-region write/read/export "
        "negatives, cross-region egress alert proof, key-region proof, failover proof, migration/backfill proof, "
        "backup/search/analytics/log region proof, support/admin access proof, audit refs, and monitoring alerts."
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
            "Additional judgment: start with a read-only Residency Contract Inspector that freezes EU/US data-plane "
            "inventory, tenant residency policy, region routing, primary DB, object storage, search index, cache, "
            "queue, backup, logs, analytics export, processor/subprocessor allowlist, DPA, key region, failover, "
            "migration/backfill, support/admin access, export, audit, observability, cross-region egress monitoring, "
            "and wrong-region write/read/export negative targets. Builder should only implement after that contract "
            "handoff. Then Residency Evidence Inspector verifies DB/storage/search/cache/queue/backup/logs/analytics/"
            "processor region proof, wrong-region writes and reads, cross-region egress, stale policy, processor "
            "mismatch, key-region, failover, migration/backfill, access/export/audit/trace, and monitoring alerts. "
            "GateKeeper must fail closed on UI region-only, env-var-only, tenant-field-only, one routed request, "
            "docs-only DPA, missing processor proof, missing wrong-region negatives, missing key-region proof, or "
            "missing observability/egress alerts."
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
    assert "Residency Contract Inspector" in agreement_text
    assert "Regional Isolation Builder" in agreement_text
    assert "Residency Evidence Inspector" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this residency contract-first direction.",
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
        "tenant residency policy",
        "wrong-region write",
        "processor",
        "cross-region egress",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this residency" not in ready_projection_text
    assert "support-impersonation" not in ready_projection_text
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
    assert workflow["preset"] == "data-residency-contract-first"
    assert [step["id"] for step in workflow["steps"]] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
        "residency_evidence_inspection_step",
        "residency_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["residency_contract_inspection_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
        "residency_evidence_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "regional-isolation",
        "tenant-isolation",
        "provider-contract",
        "backup-restore",
        "search-index",
        "event-integrity",
        "privacy-redaction",
        "data-export",
        "monitoring",
        "audit-log",
        "migration-rollback",
        "permission-auth",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "support-impersonation" not in gatekeeper_verifies
    assert "# Execution Strategy" in bundle_text
    assert "Data Residency Isolation Loop" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Repair Builder" not in bundle_text
    assert "Task Evidence Repair Loop" not in bundle_text
    assert "Confirm; use this residency" not in bundle_text
