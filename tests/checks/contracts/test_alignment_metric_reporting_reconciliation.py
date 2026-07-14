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


MRR_DASHBOARD_TASK_TEXT = (
    "我要做 MRR dashboard。成功必须证明 MRR/ARR 指标口径固定，trial、coupon、discount、refund、"
    "proration、downgrade/upgrade、paused subscription 的处理正确，币种转换和汇率日期一致，"
    "月份 cutoff / timezone 正确，和 billing ledger / invoice / subscription provider 对账，"
    "historical backfill 不改旧月锁账，权限不同的用户只能看自己的 revenue segment，"
    "audit log 记录 metric definition version 和 backfill run；只有图表显示数字或 CSV 能导出必须阻断。"
)


def test_cli_agent_plan_metric_reporting_rounds_use_parallel_reconciliation_workflow(
    sample_workdir: Path,
) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-metric-reporting-reconciliation",
    }
    task_message = (
        "Plan a governed Loop for a SaaS revenue reporting dashboard for MRR, ARR, churn, expansion, contraction, "
        "and net revenue retention. Success must prove metric definition version, trial/coupon/discount/refund/"
        "proration/downgrade/upgrade/paused-subscription edge cases, currency and FX-date handling, month cutoff "
        "and timezone consistency, billing ledger/invoice/subscription provider reconciliation, historical backfill "
        "that does not rewrite locked months, segment permissions so users see only their revenue scope, export "
        "consistency, and audit records for metric definition version and backfill runs. Fake done is charts showing "
        "numbers, one CSV export, dashboard matches today provider totals, no edge-case fixture, no ledger "
        "reconciliation, no locked-month backfill proof, no permission negative, or no audit trail."
    )

    first_summary = _invoke_metric_reporting_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_metric_reporting_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a metric contract-first workflow. Start with a read-only Metric Contract "
            "Inspector freezing MRR/ARR/churn/expansion/contraction/NRR definitions, metric definition version, "
            "trial/coupon/discount/refund/proration/downgrade/upgrade/paused-subscription edge cases, currency and "
            "FX-date policy, month cutoff and timezone, locked-month backfill rules, billing ledger/invoice/"
            "subscription-provider reconciliation queries, revenue segment permission boundaries, export consistency, "
            "audit fields, and local governance proof targets. Revenue Dashboard Builder implements only after that "
            "handoff. Then run Metric Reconciliation Inspector and Permission Backfill Inspector in parallel: Metric "
            "Reconciliation verifies edge-case aggregation, FX/cutoff/timezone cases, provider/ledger/invoice "
            "reconciliation, dashboard/export parity, and drift alerts; Permission Backfill verifies segment "
            "permission negatives, historical backfill idempotency, locked-month no-rewrite proof, metric-version "
            "audit, and backfill-run audit. GateKeeper must fail closed on chart-only, CSV-only, provider-total-only, "
            "no edge-case fixtures, no ledger reconciliation, no locked-month proof, no permission negative, no audit "
            "trail, no monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_metric_reporting_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_metric_reporting_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this metric reporting direction.",
        env=env,
    )
    _assert_metric_reporting_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _metric_reporting_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_metric_reporting_bundle(bundle_text)


def _invoke_metric_reporting_plan_round(
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


def _assert_metric_reporting_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Metric Contract Inspector" in agreement_text
    assert "Revenue Dashboard Builder" in agreement_text
    assert "Metric Reconciliation Inspector" in agreement_text
    assert "Permission Backfill Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Webhook Contract Inspector" not in agreement_text
    assert "Payment Webhook Builder" not in agreement_text


def _assert_metric_reporting_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("MRR", "metric definition", "ledger", "locked", "permission", "backfill"):
        assert term in ready_projection_text
    assert "deletion, retention, legal hold" not in ready_projection_text
    assert "deletion-retention" not in ready_projection_text
    assert "Confirm; use this metric reporting direction" not in ready_projection_text
    assert (
        third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary["ready_review_projection"]["traceability"]["required_count"]
    )


def _metric_reporting_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (sample_workdir / ".loopora" / "alignment_sessions" / alignment_session_id / "artifacts" / "bundle.yml").read_text(encoding="utf-8")


def _assert_metric_reporting_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    spec_markdown = bundle["spec"]["markdown"]
    assert bundle["metadata"]["name"] == "Metric Reporting Reconciliation Loop"
    assert bundle["loop"]["name"] == "Metric Reporting Reconciliation Loop"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "metric-contract-inspector",
        "revenue-dashboard-builder",
        "metric-reconciliation-inspector",
        "permission-backfill-inspector",
        "metric-reporting-gatekeeper",
    ]
    assert workflow["preset"] == "metric-reporting-contract-parallel-reconciliation"
    assert [step["id"] for step in workflow["steps"]] == [
        "metric_contract_inspection_step",
        "revenue_dashboard_builder_step",
        "metric_reconciliation_inspection_step",
        "permission_backfill_inspection_step",
        "metric_reporting_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["metric_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "metric_reporting_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "metric_reporting_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "metric_contract_inspection_step",
        "revenue_dashboard_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "metric_contract_inspection_step",
        "revenue_dashboard_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "metric_contract_inspection_step",
        "revenue_dashboard_builder_step",
        "metric_reconciliation_inspection_step",
        "permission_backfill_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "metric-reconciliation",
        "ledger-reconciliation",
        "provider-contract",
        "metric-definition",
        "edge-case-aggregation",
        "fx-cutoff-timezone",
        "locked-backfill",
        "permission-auth",
        "data-export",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "deletion-retention" not in gatekeeper_verifies
    assert "Metric Reporting Reconciliation Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Guide converts Weak" not in bundle_text
    assert "Repair Guide Notes" not in bundle_text
    assert "Repair Builder Notes" not in bundle_text
    assert "Judge from Builder, Inspector, Guide" not in bundle_text
    assert (
        "Metric Contract Inspector -> Revenue Dashboard Builder -> "
        "[Metric Reconciliation Inspector + Permission Backfill Inspector] -> Metric Reporting GateKeeper"
    ) in spec_markdown
    assert "payment-webhook-contract-parallel-ledger" not in bundle_text
    assert "Webhook Contract Inspector" not in bundle_text
    assert "Payment Webhook Builder" not in bundle_text
    assert "deletion-retention" not in bundle_text
    assert "Confirm; use this metric reporting direction" not in bundle_text


def test_success_categories_detect_metric_reporting_reconciliation_without_migration_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means the MRR dashboard proves fixed MRR/ARR metric definition, trial/coupon/refund/proration "
            "rules, currency FX date, month cutoff timezone, billing ledger reconciliation, provider reconciliation, "
            "historical backfill locked-month behavior, revenue segment permission filtering, and audit definition version."
        )
    ]

    assert "reporting/metric-reconciliation" in labels
    assert "billing/ledger-reconciliation" in labels
    assert "analytics/event-integrity" not in labels
    assert "migration/rollback-integrity" not in labels


def test_fake_done_and_evidence_categories_detect_chart_export_only_metric_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(MRR_DASHBOARD_TASK_TEXT)]
    evidence_labels = [label for label, _pattern in agent_candidate_evidence_preference_categories(MRR_DASHBOARD_TASK_TEXT)]

    assert "reporting/metric-reconciliation" in fake_labels
    assert "reporting/metric-reconciliation" in evidence_labels
    assert "analytics/event-integrity" not in fake_labels
    assert "analytics/event-integrity" not in evidence_labels
    assert "migration/rollback-integrity" not in fake_labels
    assert "migration/rollback-integrity" not in evidence_labels


def test_alignment_agreement_requires_metric_reporting_reconciliation_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship an MRR dashboard so the chart renders and CSV export works.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means MRR/ARR metric definition is fixed, trial, coupon, discount, refund, proration, "
                    "downgrade, upgrade, and paused subscription rules are correct, currency FX date and month cutoff "
                    "timezone are consistent, billing ledger, invoice, and provider reconciliation passes, historical "
                    "backfill does not rewrite locked months, revenue segment permissions are enforced, and audit records "
                    "metric definition version plus backfill run."
                ),
                "fake_done_risks": (
                    "Only chart numbers or CSV export without metric definition, billing ledger/provider reconciliation, "
                    "currency/timezone/cutoff proof, locked-month backfill, permission segment filtering, and audit proof "
                    "must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include metric definition version, MRR/ARR edge-case fixtures, currency FX date, "
                    "month cutoff timezone, ledger/invoice/provider reconciliation, locked-month backfill proof, "
                    "permission segment checks, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert not any("analytics/event-integrity" in issue for issue in issues)
    assert not any("migration/rollback-integrity" in issue for issue in issues)


def test_agent_first_traceability_blocks_chart_export_only_mrr_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship an MRR dashboard so the chart renders and CSV export works.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: metric definition, MRR/ARR rules, trial, coupon, discount, refund, proration, "
        "downgrade, upgrade, paused subscription, currency FX date, month cutoff, timezone, ledger reconciliation, "
        "provider reconciliation, locked-month backfill, revenue segment permission filtering, audit metric definition "
        "version, and backfill run proof can be handled later.\n"
        "  Owner: analytics owner\n"
        "  Follow-up: add revenue metric hardening later.\n"
        "  Acceptance path: GateKeeper can pass after the dashboard chart displays numbers and CSV export works.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 MRR dashboard 图表和 CSV 导出，不处理 metric definition、ledger reconciliation、FX date、"
        "cutoff、backfill lock、permission segment 或 audit proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat metric definition, MRR/ARR rules, trial, coupon, discount, refund, proration, downgrade, upgrade, "
        "paused subscription, currency FX date, month cutoff, timezone, ledger/provider reconciliation, locked-month "
        "backfill, revenue segment permission filtering, audit metric definition version, and backfill run as later "
        "residual risk; only check chart rendering and CSV export.\n"
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        "\n可以接受 metric definition、对账、汇率日期、cutoff、锁账回填、权限分段和 audit proof 后续补，只要图表和 CSV 可用。\n"
    )

    issues = alignment_agent_candidate_traceability_issues(MRR_DASHBOARD_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "reporting/metric-reconciliation" in issue for issue in issues)
    assert any("success criteria" in issue and "billing/ledger-reconciliation" in issue for issue in issues)
    assert any("success criteria" in issue and "audit/log" in issue for issue in issues)
    assert not any("analytics/event-integrity" in issue for issue in issues)
    assert not any("migration/rollback-integrity" in issue for issue in issues)
