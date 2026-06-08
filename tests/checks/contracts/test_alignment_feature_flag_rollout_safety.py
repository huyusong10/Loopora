from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


FEATURE_FLAG_ROLLOUT_TASK_TEXT = (
    "我要把新版 checkout 放到 feature flag 后灰度发布。成功必须证明默认关闭，只有 beta cohort 命中，"
    "percentage rollout 稳定，用户不会在一次 session 内新旧体验来回跳，kill switch 能立即回退，"
    "rollback 不留脏状态，监控/告警能发现错误率和支付转化异常，"
    "audit log 记录谁改了 flag、cohort、percentage 和 kill switch；只有本地 flag 能打开新版 checkout 必须阻断。"
)


def test_cli_agent_plan_feature_flag_rounds_use_parallel_rollout_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-feature-flag-rollout-contract",
    }
    task_message = (
        "Plan a governed Loop for rolling out a new checkout behind a feature flag. Success must prove default-off "
        "behavior, beta cohort targeting, stable percentage rollout, sticky session exposure so users do not bounce "
        "between old and new checkout, immediate kill switch rollback, rollback cleanup with no dirty state, "
        "monitoring/alerts for error rate and payment conversion, audit log for who changed flag/cohort/percentage/"
        "kill switch, and prevention of local-only flag bypass. Fake done is a UI toggle, a local flag, one beta "
        "happy path, docs-only rollout plan, or monitoring left as follow-up. Evidence should include cohort negatives, "
        "percentage boundary cases, sticky assignment checks, kill switch proof, rollback cleanup proof, conversion/error "
        "monitoring, audit reviewability, and local governance."
    )

    first_summary = _invoke_feature_flag_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_feature_flag_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a release rollout contract-first workflow. Start with Rollout Contract Inspector "
            "freezing default-off, cohort targeting, percentage rollout math, sticky assignment, exposure logging, kill "
            "switch, rollback cleanup, monitoring/alert thresholds, audit, local governance, and local-only bypass proof "
            "targets. Rollout Builder may implement only after that handoff. Then run Exposure Consistency Inspector and "
            "Operational Rollback Inspector in parallel: Exposure verifies cohort negatives, percentage boundary cases, "
            "sticky session behavior, exposure logs, and local-only bypass prevention; Operational Rollback verifies "
            "default-off, kill switch immediacy, rollback cleanup, monitoring/alerts, payment conversion guard, audit "
            "reviewability, and governance. GateKeeper must fail closed on UI-toggle-only, local-flag-only, one beta "
            "happy path, docs-only rollout, missing sticky assignment, missing kill switch/rollback proof, missing "
            "monitoring/conversion evidence, missing audit, or missing cohort negative cases."
        ),
        env=env,
    )
    _assert_feature_flag_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_feature_flag_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this release rollout contract-first parallel evidence direction.",
        env=env,
    )
    _assert_feature_flag_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _feature_flag_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_feature_flag_bundle(bundle_text)


def _invoke_feature_flag_plan_round(
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


def _assert_feature_flag_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Rollout Contract Inspector" in agreement_text
    assert "Exposure Consistency Inspector" in agreement_text
    assert "Operational Rollback Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_feature_flag_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("feature-flag targeting", "sticky", "kill switch", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this release rollout" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _feature_flag_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_feature_flag_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "feature-flag-rollout-contract-parallel-release"
    assert [step["id"] for step in workflow["steps"]] == [
        "rollout_contract_inspection_step",
        "rollout_builder_step",
        "exposure_consistency_inspection_step",
        "operational_rollback_inspection_step",
        "release_rollout_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["rollout_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "feature_rollout_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "feature_rollout_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "rollout_contract_inspection_step",
        "rollout_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "rollout_contract_inspection_step",
        "rollout_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "rollout_contract_inspection_step",
        "rollout_builder_step",
        "exposure_consistency_inspection_step",
        "operational_rollback_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "rollout-safety",
        "experiment-assignment",
        "monitoring",
        "audit-log",
        "payment-refund-billing",
        "migration-rollback",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Feature Flag Rollout Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this release rollout" not in bundle_text


def test_cli_agent_plan_analytics_experiment_rounds_use_parallel_instrumentation_workflow(
    sample_workdir: Path,
) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-analytics-experiment-contract",
    }
    task_message = (
        "Plan a governed Loop for mobile onboarding analytics instrumentation and A/B experiment exposure. Success must "
        "prove signup funnel events for app_open, signup_start, email_submitted, verification_sent, "
        "verification_completed, account_created, onboarding_completed, paywall_viewed, and paywall_dismissed all match "
        "a versioned event schema; anonymous and logged-in identities merge without double counting; retries, refreshes, "
        "offline replay, and duplicate SDK callbacks do not duplicate events; consent denial suppresses PII and tracking; "
        "experiment assignment, exposure, variant, holdout, and re-assignment behavior are consistent across app restarts "
        "and devices; warehouse/dashboard queries reconcile with raw events and assignment logs; monitoring detects event "
        "drift, missing exposure, duplicate spikes, and schema version mismatch. Fake done is button clicks working, "
        "console.log, mock analytics call, one Segment provider accepted event, no warehouse reconciliation, no consent "
        "negative, no duplicate/offline replay negatives, or treating experiment exposure as follow-up."
    )

    first_summary = _invoke_analytics_experiment_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_analytics_experiment_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with an Instrumentation Contract Inspector freezing versioned event schema, "
            "identity merge rules, consent/PII boundaries, SDK retry/offline replay semantics, experiment assignment/"
            "exposure/variant/holdout rules, raw-event to warehouse/dashboard reconciliation queries, monitoring alerts, "
            "schema migration/backward compatibility, and local governance. Tracking Builder implements only from that "
            "handoff. Then run Event Integrity Inspector and Experiment Consistency Inspector in parallel: Event Integrity "
            "checks real event payloads, dedupe, offline replay, identity merge, consent-negative behavior, warehouse/"
            "dashboard reconciliation, drift monitoring, and schema-version mismatch; Experiment Consistency checks "
            "assignment stability, exposure logging, variant/holdout consistency, app restart/device behavior, missing "
            "exposure alerts, and no reassignment pollution. GateKeeper must fail closed on button-click-only, "
            "console-log-only, mock analytics, one provider accepted event, no raw-event reconciliation, no consent "
            "negative, no duplicate/offline replay negative, missing experiment exposure, missing monitoring, or skipped "
            "local governance."
        ),
        env=env,
    )
    _assert_analytics_experiment_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_analytics_experiment_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        env=env,
    )
    _assert_analytics_experiment_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _analytics_experiment_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_analytics_experiment_bundle(bundle_text)


def _invoke_analytics_experiment_plan_round(
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


def _assert_analytics_experiment_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Instrumentation Contract Inspector" in agreement_text
    assert "Tracking Builder" in agreement_text
    assert "Event Integrity Inspector" in agreement_text
    assert "Experiment Consistency Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Notification Contract Inspector" not in agreement_text
    assert "Campaign Email Builder" not in agreement_text
    assert "Deliverability Evidence Inspector" not in agreement_text
    assert "Rollout Contract Inspector" not in agreement_text


def _assert_analytics_experiment_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("event", "experiment", "identity", "warehouse", "consent", "monitoring"):
        assert term in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _analytics_experiment_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_analytics_experiment_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "instrumentation-contract-inspector",
        "tracking-builder",
        "event-integrity-inspector",
        "experiment-consistency-inspector",
        "analytics-experiment-gatekeeper",
    ]
    assert workflow["preset"] == "analytics-experiment-contract-parallel-instrumentation"
    assert [step["id"] for step in workflow["steps"]] == [
        "instrumentation_contract_inspection_step",
        "tracking_builder_step",
        "event_integrity_inspection_step",
        "experiment_consistency_inspection_step",
        "analytics_experiment_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["instrumentation_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "analytics_experiment_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "analytics_experiment_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "instrumentation_contract_inspection_step",
        "tracking_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "instrumentation_contract_inspection_step",
        "tracking_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "instrumentation_contract_inspection_step",
        "tracking_builder_step",
        "event_integrity_inspection_step",
        "experiment_consistency_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "event-integrity",
        "experiment-assignment",
        "idempotency",
        "identity-merge",
        "privacy-redaction",
        "warehouse-reconciliation",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "subscription-deliverability" not in gatekeeper_verifies
    assert "Analytics Experiment Instrumentation Workflow Notes" in bundle_text
    assert "notification-subscription-contract-parallel-deliverability" not in bundle_text
    assert "feature-flag-rollout-contract-parallel-release" not in bundle_text
    assert "Notification Contract Inspector" not in bundle_text
    assert "Campaign Email Builder" not in bundle_text
    assert "Confirm; use this direction" not in bundle_text


def test_cli_agent_plan_database_schema_migration_rounds_use_parallel_backfill_workflow(
    sample_workdir: Path,
) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-database-schema-migration",
    }
    task_message = (
        "Plan a governed Loop to migrate a multi-tenant SaaS billing database from per-customer JSON settings to "
        "normalized plan_entitlements tables. Success must prove dual-write compatibility, background backfill "
        "idempotency, tenant isolation, read-after-write consistency, rollback to old readers, migration progress "
        "monitoring, and no billing invoice drift. Fake done is adding only the new table and one happy-path test, "
        "running a backfill once without retry proof, or claiming rollback from docs. Required evidence should include "
        "old/new reader parity, mixed migrated/unmigrated tenants, failed backfill retry, invoice reconciliation, and "
        "migration rollback proof."
    )

    first_summary = _invoke_schema_migration_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_schema_migration_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: this migration must use a contract-first workflow. Start with a read-only Migration "
            "Contract Inspector freezing old/new schema semantics, dual-write window, reader compatibility, tenant "
            "isolation, backfill cursor/idempotency, invoice reconciliation, monitoring, rollback switch, and local "
            "governance proof targets. Migration Builder may implement only after that handoff. Run Data Consistency "
            "Inspector and Operational Rollback Inspector in parallel: Data Consistency verifies old/new reader parity, "
            "mixed migrated/unmigrated tenants, tenant isolation negatives, invoice drift reconciliation, and backfill "
            "retry idempotency; Operational Rollback verifies rollback to old readers, progress monitoring/alerts, "
            "failed batch recovery, migration pause/resume, and cleanup. GateKeeper must fail closed on table-only "
            "migration, one-time backfill, no retry proof, no invoice reconciliation, no tenant-negative evidence, "
            "no rollback proof, or skipped local governance."
        ),
        env=env,
    )
    _assert_schema_migration_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_schema_migration_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        env=env,
    )
    _assert_schema_migration_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _schema_migration_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_schema_migration_bundle(bundle_text)


def _invoke_schema_migration_plan_round(
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


def _assert_schema_migration_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Migration Contract Inspector" in agreement_text
    assert "Schema Migration Builder" in agreement_text
    assert "Data Consistency Inspector" in agreement_text
    assert "Operational Rollback Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Instrumentation Contract Inspector" not in agreement_text
    assert "Notification Contract Inspector" not in agreement_text


def _assert_schema_migration_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("migration", "backfill", "dual-write", "tenant", "invoice", "rollback"):
        assert term in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _schema_migration_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_schema_migration_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "migration-contract-inspector",
        "schema-migration-builder",
        "data-consistency-inspector",
        "operational-rollback-inspector",
        "migration-gatekeeper",
    ]
    assert workflow["preset"] == "database-schema-migration-contract-parallel-backfill"
    assert [step["id"] for step in workflow["steps"]] == [
        "migration_contract_inspection_step",
        "schema_migration_builder_step",
        "data_consistency_inspection_step",
        "operational_rollback_inspection_step",
        "migration_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["migration_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "database_migration_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "database_migration_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "migration_contract_inspection_step",
        "schema_migration_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "migration_contract_inspection_step",
        "schema_migration_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "migration_contract_inspection_step",
        "schema_migration_builder_step",
        "data_consistency_inspection_step",
        "operational_rollback_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "schema-migration",
        "provider-contract",
        "dual-write",
        "reader-compatibility",
        "tenant-isolation",
        "backfill-idempotency",
        "invoice-reconciliation",
        "monitoring",
        "rollback-recovery",
        "migration-rollback",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Database Schema Migration Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "analytics-experiment-contract-parallel-instrumentation" not in bundle_text
    assert "notification-subscription-contract-parallel-deliverability" not in bundle_text
    assert "Confirm; use this direction" not in bundle_text


def test_success_categories_detect_feature_flag_rollout_safety() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means the feature flag rollout proves default-off behavior, beta cohort targeting, "
            "percentage rollout stability, session exposure consistency, kill switch rollback, monitoring, and audit."
        )
    ]

    assert "release/feature-flag-rollout" in labels
    assert "regression/monitoring-guard" in labels


def test_alignment_agreement_requires_feature_flag_rollout_safety_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a new checkout behind a feature flag so developers can turn it on locally.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means checkout feature flag rollout proves default-off behavior, beta cohort targeting, "
                    "percentage rollout stability, session exposure consistency, kill switch rollback, clean rollback state, "
                    "monitoring and alert thresholds for error rate and payment conversion, and audit records flag changes."
                ),
                "fake_done_risks": (
                    "Only proving a local feature flag toggle without cohort targeting, percentage rollout, kill switch, "
                    "rollback cleanup, monitoring, payment-conversion evidence, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include feature flag default-off, cohort targeting, percentage rollout, sticky session exposure, "
                    "kill switch rollback, monitoring or alert proof, payment conversion guard, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "release/feature-flag-rollout" in issue for issue in issues)
    assert any("fake-done risks" in issue and "release/feature-flag-rollout" in issue for issue in issues)
    assert any("evidence preferences" in issue and "release/feature-flag-rollout" in issue for issue in issues)


def test_agent_first_traceability_blocks_local_flag_only_rollout_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a new checkout behind a feature flag so developers can turn it on locally.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: cohort targeting, percentage rollout, default-off safety, kill switch, rollback, "
        "monitoring, alert thresholds, exposure consistency, payment conversion guard, and audit proof can be handled later.\n"
        "  Owner: release owner\n"
        "  Follow-up: create rollout safety follow-up.\n"
        "  Acceptance path: GateKeeper can pass after a local feature flag toggles the new checkout on.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat cohort targeting, percentage rollout, default-off safety, kill switch, rollback, monitoring, "
        "alert thresholds, exposure consistency, payment conversion guard, and audit as later residual risk; "
        "only check local flag toggle.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(FEATURE_FLAG_ROLLOUT_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "release/feature-flag-rollout" in issue for issue in issues)
    assert any("fake-done risks" in issue and "release/feature-flag-rollout" in issue for issue in issues)
    assert any("evidence preferences" in issue and "release/feature-flag-rollout" in issue for issue in issues)
    assert any("success criteria" in issue and "audit/log" in issue for issue in issues)
