from __future__ import annotations

from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, json, yaml
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


BACKUP_RESTORE_TASK_TEXT = (
    "我要给生产数据库做 backup / restore 和 disaster recovery。成功必须证明 nightly backup、"
    "point-in-time recovery、cross-region snapshot、encryption key access、retention policy、legal hold、"
    "schema migration 后的 restore 都可靠，RPO/RTO 目标有恢复演练证据，restore drill 能在隔离环境恢复指定租户和全量库，"
    "checksum / row count / application smoke test 证明数据完整，备份失败、过期、复制延迟和恢复失败有监控告警，"
    "restore 权限受控且 audit log 记录 backup id、snapshot id、restore run、operator、key id 和 failure reason；"
    "只有 backup job 显示成功、生成一个 snapshot 文件或 dashboard 绿色必须阻断。"
)


def test_cli_agent_plan_backup_restore_rounds_use_recovery_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-backup-restore-contract",
    }
    task_message = (
        "Plan a governed Loop for production database backup / restore and disaster recovery. Success must prove nightly "
        "backups, point-in-time recovery, cross-region snapshots, encryption key access, retention policy, legal hold, "
        "and restore after schema migration all work. RPO/RTO targets need restore drill evidence. Restore drills must "
        "recover one tenant and the full database in an isolated environment. Checksum, row count, and application smoke "
        "tests must prove data integrity. Backup failure, expired backups, replication lag, and restore failure need "
        "monitoring alerts. Restore permission must be controlled, and audit logs must capture backup id, snapshot id, "
        "restore run, operator, key id, and failure reason. Fake done is backup job green, one snapshot file exists, or "
        "dashboard green without restore drill and integrity proof."
    )

    first_summary = _invoke_backup_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_backup_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a backup-recovery contract-first workflow. Start with Backup Recovery Contract "
            "Inspector freezing backup inventory, PITR target, cross-region snapshot, encryption key access, retention/"
            "legal hold, schema-migration restore target, tenant/full-database restore targets, RPO/RTO, integrity checks, "
            "monitoring alerts, restore permission, audit fields, and rollback/fallback proof targets. Backup Restore "
            "Builder may implement only from that handoff. Then run Restore Drill Evidence Inspector and Retention "
            "Security Audit Inspector in parallel: Restore Drill verifies isolated tenant restore, full database restore, "
            "PITR, cross-region snapshot restore, schema-migration restore, checksum, row count, application smoke test, "
            "RPO/RTO timing, and restore-failure behavior; Retention Security verifies retention policy, legal hold, "
            "encryption key access, restore permission, backup/restore audit fields, backup failure/expired backup/"
            "replication lag alerts, and local governance. GateKeeper must fail closed on backup-job-green-only, "
            "snapshot-file-only, dashboard-green-only, no restore drill, no PITR, no checksum/row count/smoke proof, "
            "missing RPO/RTO evidence, missing retention/legal-hold proof, missing permission, missing audit fields, or "
            "missing monitoring alerts."
        ),
        env=env,
    )
    _assert_backup_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_backup_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this backup recovery contract-first parallel evidence direction.",
        env=env,
    )
    _assert_backup_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _backup_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_backup_bundle(bundle_text)


def test_success_categories_detect_backup_restore_without_inventory_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means backup restore recovery proves nightly backup, point-in-time recovery, cross-region "
            "snapshot, encryption key access, retention policy, legal hold, restore drill in an isolated environment, "
            "tenant restore, full database restore, checksum, row count, application smoke test, RPO/RTO, monitoring, "
            "and audit backup id."
        )
    ]
    inventory_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means inventory reservation consistency proves SKU checkout cannot oversell and reservation "
            "hold TTL expiry releases stock."
        )
    ]

    assert "backup/restore-recovery" in labels
    assert "regression/monitoring-guard" in labels
    assert "audit/log" in labels
    assert "permission/auth" in labels
    assert "inventory/reservation-consistency" not in labels
    assert "backup/restore-recovery" not in inventory_labels


def test_fake_done_and_evidence_categories_detect_backup_job_or_snapshot_only_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(BACKUP_RESTORE_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(BACKUP_RESTORE_TASK_TEXT)
    ]

    assert "backup/restore-recovery" in fake_labels
    assert "backup/restore-recovery" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels
    assert "inventory/reservation-consistency" not in fake_labels
    assert "inventory/reservation-consistency" not in evidence_labels


def test_alignment_agreement_requires_backup_restore_recovery_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a backup job status view and create one snapshot file.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means backup restore recovery proves nightly backup, point-in-time recovery, "
                    "cross-region snapshot, encryption key access, retention policy, legal hold, schema migration "
                    "restore, RPO/RTO restore drill, isolated tenant/full database restore, checksum, row count, "
                    "application smoke test, monitoring alerts, restore permission, and audit backup id."
                ),
                "fake_done_risks": (
                    "A green backup job, one snapshot file, or green dashboard without restore drill, PITR, RPO/RTO, "
                    "checksum, row count, application smoke, encryption key access, retention/legal hold, permission, "
                    "monitoring, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include restore drill output, point-in-time recovery, isolated tenant restore, "
                    "full database restore, checksum/row count/application smoke tests, encryption key access, "
                    "retention/legal hold behavior, failed/expired/lagging backup alerts, restore permission, and audit logs."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "backup/restore-recovery" in issue for issue in issues)
    assert any("fake-done risks" in issue and "backup/restore-recovery" in issue for issue in issues)
    assert any("evidence preferences" in issue and "backup/restore-recovery" in issue for issue in issues)


def test_agent_first_traceability_blocks_backup_job_green_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a backup job status view and create one snapshot file.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 restore drill、PITR、RPO/RTO、checksum、row count、application smoke test 或 restore permission "
        "作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: point-in-time recovery, cross-region snapshot restore, encryption key access, "
        "retention policy, legal hold, schema migration restore, RPO/RTO restore drill, isolated tenant/full database "
        "restore, checksum, row count, application smoke test, monitoring, permission, and audit proof can be handled later.\n"
        "  Owner: platform owner\n"
        "  Follow-up: add backup restore hardening later.\n"
        "  Acceptance path: GateKeeper can pass after backup job shows success and one snapshot file exists.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 backup job 显示成功和生成一个 snapshot 文件，不处理 restore drill、PITR、RPO/RTO、"
        "checksum、row count、application smoke test、encryption key access、retention policy、legal hold、"
        "restore permission、monitoring 或 audit proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat restore drill, PITR, RPO/RTO, checksum, row count, application smoke test, encryption key access, "
        "retention policy, legal hold, restore permission, monitoring, and audit proof as later residual risk; "
        "only check backup job success and one snapshot file."
    )

    issues = alignment_agent_candidate_traceability_issues(BACKUP_RESTORE_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "backup/restore-recovery" in issue for issue in issues)
    assert any("fake-done risks" in issue and "backup/restore-recovery" in issue for issue in issues)
    assert any("evidence preferences" in issue and "backup/restore-recovery" in issue for issue in issues)


def _invoke_backup_plan_round(
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


def _assert_backup_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Backup Recovery Contract Inspector" in agreement_text
    assert "Restore Drill Evidence Inspector" in agreement_text
    assert "Retention Security Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_backup_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("point-in-time recovery", "restore drill", "RPO/RTO", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this backup recovery" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _backup_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_backup_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "backup-restore-contract-parallel-recovery"
    assert [step["id"] for step in workflow["steps"]] == [
        "backup_recovery_contract_inspection_step",
        "backup_restore_builder_step",
        "restore_drill_evidence_inspection_step",
        "retention_security_audit_inspection_step",
        "backup_recovery_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["backup_recovery_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "backup_restore_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "backup_restore_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "backup_recovery_contract_inspection_step",
        "backup_restore_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "backup_recovery_contract_inspection_step",
        "backup_restore_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "backup_recovery_contract_inspection_step",
        "backup_restore_builder_step",
        "restore_drill_evidence_inspection_step",
        "retention_security_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "backup-restore",
        "migration-rollback",
        "monitoring",
        "audit-log",
        "permission-auth",
        "data-integrity",
        "retention-policy",
        "security-key-access",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Backup Restore Recovery Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this backup recovery" not in bundle_text
