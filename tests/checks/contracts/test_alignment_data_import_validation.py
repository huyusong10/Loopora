from __future__ import annotations

from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, json, yaml
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)


DATA_IMPORT_TASK_TEXT = (
    "我要做客户 CSV 批量导入。成功必须证明字段映射正确、必填列和类型 schema validation 生效，"
    "坏行不会污染好行，partial failure 会生成 row-level error report，重复上传或重试是幂等的，"
    "重复客户按 external_id 去重，PII 不进错误日志，audit log 能追踪导入人和批次；"
    "只有 happy path 样例 CSV 全部导入成功必须阻断。"
)


def test_alignment_agreement_requires_data_import_validation(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship customer CSV import so an admin can upload a sample file and see imported rows.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means customer CSV import proves field mapping, required columns and type schema "
                    "validation, bad-row isolation, partial failure row-level error report, idempotent retry, "
                    "external_id dedupe, PII-safe error logs, and audit batch evidence."
                ),
                "fake_done_risks": (
                    "Only importing one happy-path customer CSV import without schema validation, row-level errors, "
                    "partial-failure isolation, idempotent retry, dedupe, privacy, and audit evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include customer CSV import with mixed good/bad rows, schema validation failures, "
                    "row-level error report, duplicate retry proof, PII-safe logs, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "data-import/validation-idempotency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data-import/validation-idempotency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data-import/validation-idempotency" in issue for issue in issues)


def test_agent_first_traceability_blocks_happy_path_only_csv_import(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship customer CSV import so an admin can upload a sample file and see imported rows.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: field mapping, schema validation, partial failure, row-level error report, "
        "idempotent retry, external_id dedupe, PII-safe error logs, and audit proof can be handled later.\n"
        "  Owner: data operations owner\n"
        "  Follow-up: create an import validation ticket.\n"
        "  Acceptance path: GateKeeper can pass after one happy-path sample CSV imports all rows.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat import field mapping, schema validation, partial failure, row-level errors, idempotent retry, "
        "privacy, and audit as later residual risk.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(DATA_IMPORT_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "data-import/validation-idempotency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data-import/validation-idempotency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data-import/validation-idempotency" in issue for issue in issues)
    assert any("success criteria" in issue and "privacy/secrets-redaction" in issue for issue in issues)


def test_cli_agent_plan_data_import_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-data-import-contract",
    }
    task_message = (
        "Plan a governed Loop for customer CSV bulk import. Success must prove field mapping, required and type "
        "schema validation, dry-run preview, mixed good and bad row fixtures, row-level error report shape, partial "
        "failure isolation, idempotent retry using an idempotency key, external_id dedupe, PII-safe logs, permission "
        "negatives, audit batch id with actor/source/counts/reason/status, failed import cleanup, monitoring, and local "
        "governance. Fake done is happy-path-only CSV, preview-only, all-or-nothing import, success-count-only report, "
        "or saying import works without bad row and retry proof."
    )

    first_summary = _invoke_data_import_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_data_import_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Import Contract Inspector freezing mapping contract, schema, required/type "
            "validation, dry-run preview, mixed good/bad row fixtures, row-level error report shape, bad-row isolation, "
            "idempotency key/retry semantics, external_id dedupe, PII redaction, audit batch fields, permission negatives, "
            "failed import cleanup, monitoring, and local governance targets. CSV Import Builder implements only after "
            "that handoff. Then run Import Evidence Inspector and Privacy Audit Inspector in parallel: Import Evidence "
            "checks mixed rows, bad-row isolation, row-level report, partial failure, idempotent retry, external_id dedupe, "
            "and reconciliation; Privacy Audit checks PII-safe logs and error reports, permission negatives, audit actor/"
            "source/counts/reason/status, cleanup, monitoring, and local governance. GateKeeper must fail closed on "
            "happy-path-only CSV, preview-only, all-or-nothing import, success-count-only report, missing schema validation, "
            "missing row-level errors, missing idempotency/dedupe, missing privacy/audit, or skipped local governance."
        ),
        env=env,
    )
    _assert_data_import_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_data_import_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this import contract-first parallel evidence direction.",
        env=env,
    )
    _assert_data_import_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _data_import_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_data_import_bundle(bundle_text)


def _invoke_data_import_plan_round(
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


def _assert_data_import_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Import Contract Inspector" in agreement_text
    assert "CSV Import Builder" in agreement_text
    assert "Import Evidence Inspector" in agreement_text
    assert "Privacy Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_data_import_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in (
        "field mapping",
        "row-level error report",
        "idempotency key",
        "external_id dedupe",
        "PII-safe logs",
        "audit batch",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this import" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _data_import_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_data_import_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "import-contract-inspector",
        "csv-import-builder",
        "import-evidence-inspector",
        "privacy-audit-inspector",
        "import-validation-gatekeeper",
    ]
    assert workflow["preset"] == "data-import-contract-parallel-validation"
    assert [step["id"] for step in workflow["steps"]] == [
        "import_contract_inspection_step",
        "csv_import_builder_step",
        "import_evidence_inspection_step",
        "privacy_audit_inspection_step",
        "import_validation_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["import_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "data_import_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "data_import_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "import_contract_inspection_step",
        "csv_import_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "import_contract_inspection_step",
        "csv_import_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "import_contract_inspection_step",
        "csv_import_builder_step",
        "import_evidence_inspection_step",
        "privacy_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "data-import-validation",
        "idempotency",
        "privacy-redaction",
        "permission-auth",
        "audit-log",
        "monitoring",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Data Import Validation Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this import" not in bundle_text
