from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


CDC_REPLICATION_TASK_TEXT = (
    "我要把 Postgres 订单数据通过 CDC 同步到 warehouse 和 read model。成功必须证明 snapshot backfill "
    "和 streaming replication 不丢不重，LSN / watermark / checkpoint 正确推进，out-of-order 和 "
    "duplicate events 幂等，schema evolution / column rename / delete tombstone 处理正确，"
    "replay from checkpoint 能恢复，source row count、checksum、event count 和 warehouse aggregate "
    "reconciliation 一致，replication lag、stale checkpoint、DLQ / poison event 和 sync failure "
    "有监控告警，权限过滤和 tenant id 不会串租户，audit log 记录 connector version、source table、"
    "LSN、watermark、replay run、failure reason；只有 sync job 绿色、抽样 row count 一致或 dashboard "
    "显示 latest 必须阻断。"
)


def test_cli_agent_plan_cdc_replication_rounds_use_parallel_consistency_workflow(
    sample_workdir: Path,
) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-cdc-replication-consistency",
    }
    task_message = (
        "Plan a governed Loop to add CDC replication from Postgres order tables into a warehouse and "
        "customer-facing read model. Success must prove event ordering, replay idempotency, replication lag bounds, "
        "schema evolution compatibility, initial snapshot plus backfill correctness, delete/tombstone handling, "
        "tenant isolation, and warehouse/read-model reconciliation. Fake done is a green sync job, one row-count "
        "sample, dashboard shows latest, no out-of-order events, no replay duplicate proof, no schema change fixture, "
        "or no lag alert. Required evidence should include out-of-order CDC events, replay from checkpoint, backfill "
        "with concurrent writes, schema-version change, tenant negative cases, lag monitoring, and target "
        "reconciliation queries."
    )

    first_summary = _invoke_cdc_replication_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_cdc_replication_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a CDC contract-first workflow. Start with a read-only CDC Contract Inspector "
            "freezing source event schema, ordering keys, snapshot/backfill boundary, replay checkpoint semantics, "
            "delete/tombstone rules, schema evolution compatibility, tenant filters, target reconciliation queries, "
            "lag SLO/alerts, connector failure recovery, audit, and local governance proof targets. CDC Pipeline "
            "Builder implements only after that handoff. Then run Replication Evidence Inspector and Reconciliation "
            "Lag Inspector in parallel: Replication Evidence verifies out-of-order events, duplicate replay from "
            "checkpoint, delete/tombstone propagation, schema-version changes, and tenant isolation negatives; "
            "Reconciliation Lag verifies warehouse/read-model row and aggregate reconciliation, backfill with "
            "concurrent writes, lag metrics/alerts, target drift detection, DLQ/poison events, and recovery after "
            "connector failure. GateKeeper must fail closed on green-sync-job-only, row-count-sample-only, "
            "dashboard-latest-only, no out-of-order proof, no replay duplicate negative, missing schema evolution "
            "fixture, missing tombstone proof, missing lag alert, missing connector recovery, or skipped local "
            "governance."
        ),
        env=env,
    )
    _assert_cdc_replication_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_cdc_replication_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this CDC direction.",
        env=env,
    )
    _assert_cdc_replication_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _cdc_replication_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_cdc_replication_bundle(bundle_text)


def _invoke_cdc_replication_plan_round(
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


def _assert_cdc_replication_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "CDC Contract Inspector" in agreement_text
    assert "CDC Pipeline Builder" in agreement_text
    assert "Replication Evidence Inspector" in agreement_text
    assert "Reconciliation Lag Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Webhook Contract Inspector" not in agreement_text
    assert "Payment Webhook Builder" not in agreement_text
    assert "Ledger Reconciliation Inspector" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_cdc_replication_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("CDC", "checkpoint", "tombstone", "warehouse", "lag", "tenant"):
        assert term in ready_projection_text
    assert "Confirm; use this CDC direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _cdc_replication_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_cdc_replication_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "cdc-contract-inspector",
        "cdc-pipeline-builder",
        "replication-evidence-inspector",
        "reconciliation-lag-inspector",
        "cdc-replication-gatekeeper",
    ]
    assert workflow["preset"] == "cdc-replication-contract-parallel-consistency"
    assert [step["id"] for step in workflow["steps"]] == [
        "cdc_contract_inspection_step",
        "cdc_pipeline_builder_step",
        "replication_evidence_inspection_step",
        "reconciliation_lag_inspection_step",
        "cdc_replication_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["cdc_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "cdc_replication_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "cdc_replication_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "cdc_contract_inspection_step",
        "cdc_pipeline_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "cdc_contract_inspection_step",
        "cdc_pipeline_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "cdc_contract_inspection_step",
        "cdc_pipeline_builder_step",
        "replication_evidence_inspection_step",
        "reconciliation_lag_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "cdc-replication",
        "provider-contract",
        "event-ordering",
        "idempotency",
        "schema-evolution",
        "backfill-consistency",
        "delete-tombstone",
        "tenant-isolation",
        "warehouse-reconciliation",
        "monitoring",
        "connector-recovery",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "CDC Replication Consistency Workflow Notes" in bundle_text
    assert "payment-webhook-contract-parallel-ledger" not in bundle_text
    assert "Webhook Contract Inspector" not in bundle_text
    assert "Payment Webhook Builder" not in bundle_text
    assert "Ledger Reconciliation Inspector" not in bundle_text
    assert "message-delivery" not in bundle_text
    assert "data-export" not in bundle_text
    assert "message delivery, recipient targeting" not in bundle_text
    assert "export/download attempts" not in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this CDC direction" not in bundle_text


def test_success_categories_detect_cdc_replication_without_backup_or_webhook_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(CDC_REPLICATION_TASK_TEXT)]
    backup_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means backup restore recovery proves a cross-region snapshot restore, PITR, checksum, "
            "row count, RPO/RTO, restore drill, monitoring, and audit backup id."
        )
    ]
    weak_sync_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须让 sync job 绿色，抽样 row count 一致，dashboard 显示 latest。"
        )
    ]

    assert "data/cdc-replication-consistency" in labels
    assert "idempotency/duplicate-prevention" in labels
    assert "audit/log" in labels
    assert "permission/auth" in labels
    assert "regression/monitoring-guard" in labels
    assert "queue/failure-recovery" in labels
    assert "backup/restore-recovery" not in labels
    assert "webhook/signature-replay-ordering" not in labels
    assert "data-lifecycle/deletion-retention" not in labels
    assert "backup/restore-recovery" in backup_labels
    assert "data/cdc-replication-consistency" not in backup_labels
    assert "data/cdc-replication-consistency" not in weak_sync_labels


def test_fake_done_and_evidence_categories_detect_cdc_replication_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(CDC_REPLICATION_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(CDC_REPLICATION_TASK_TEXT)
    ]

    assert "data/cdc-replication-consistency" in fake_labels
    assert "data/cdc-replication-consistency" in evidence_labels
    assert "idempotency/duplicate-prevention" in evidence_labels
    assert "permission/auth" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels
    assert "queue/failure-recovery" in evidence_labels
    assert "backup/restore-recovery" not in fake_labels
    assert "webhook/signature-replay-ordering" not in fake_labels
    assert "data-lifecycle/deletion-retention" not in fake_labels


def test_alignment_agreement_requires_cdc_replication_consistency_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a CDC sync job status view and show latest warehouse data.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means CDC replication consistency proves snapshot backfill and streaming replication "
                    "do not lose or duplicate records, LSN/watermark/checkpoint advance correctly, out-of-order "
                    "and duplicate events are idempotent, schema evolution/column rename/delete tombstone are "
                    "handled, checkpoint replay recovers, source row count/checksum/event count/warehouse "
                    "aggregate reconciliation match, replication lag/stale checkpoint/DLQ/poison event/sync "
                    "failure alerts fire, tenant filtering holds, and audit records connector version and LSN."
                ),
                "fake_done_risks": (
                    "A green sync job, sampled row count, or dashboard latest without backfill, streaming, "
                    "LSN/watermark/checkpoint, replay, schema/tombstone, reconciliation, lag/DLQ alerts, tenant "
                    "filtering, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include CDC backfill and streaming proof, LSN/watermark/checkpoint progression, "
                    "out-of-order/duplicate-event idempotency, schema evolution and tombstone fixtures, replay "
                    "from checkpoint, source row count/checksum/event count/warehouse aggregate reconciliation, "
                    "lag/stale checkpoint/DLQ/poison/failure alerts, tenant isolation samples, and audit logs."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "data/cdc-replication-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data/cdc-replication-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data/cdc-replication-consistency" in issue for issue in issues)


def test_agent_first_traceability_blocks_sync_job_dashboard_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a CDC sync job status view with sampled row count and latest dashboard data.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把端到端一致性、失败恢复、租户边界或审计证据作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: end-to-end consistency, failure recovery, tenant isolation, and audit proof "
        "can be handled later.\n"
        "  Owner: data platform owner\n"
        "  Follow-up: add data sync hardening later.\n"
        "  Acceptance path: GateKeeper can pass after sync job is green, sampled row count matches, and dashboard is latest.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 sync job 绿色、抽样 row count 一致和 dashboard latest，不处理端到端正确性、失败恢复、"
        "租户边界或 audit proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat end-to-end correctness, failure recovery, tenant boundaries, and audit proof as later residual risk; "
        "only check sync job status, sampled row count, and dashboard freshness."
    )

    issues = alignment_agent_candidate_traceability_issues(CDC_REPLICATION_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "data/cdc-replication-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data/cdc-replication-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data/cdc-replication-consistency" in issue for issue in issues)
