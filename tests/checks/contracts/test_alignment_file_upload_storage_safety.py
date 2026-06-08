from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)


UPLOAD_TASK_TEXT = (
    "我要做用户文件上传到对象存储。成功必须证明 MIME/content-type sniffing、文件大小限制、"
    "virus/malware scan、quarantine、signed URL 权限、租户隔离、失败上传清理和 audit log 都可靠；"
    "只有 upload 返回 URL 或一个 happy path 文件上传成功必须阻断。"
)


def test_cli_agent_plan_file_upload_rounds_use_parallel_storage_safety_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-file-upload-storage-safety",
    }
    task_message = (
        "Plan a governed Loop for user file upload to object storage. Success must prove MIME/content-type sniffing, "
        "file size limits, virus/malware scan, quarantine before serving, private object ACL, signed URL permission and expiry, "
        "tenant isolation so another tenant cannot read objects, failed upload cleanup, orphan object cleanup, audit log fields "
        "for actor/object id/content hash/scan verdict/reason, and monitoring alerts for scan failures and public-object exposure. "
        "Fake done is upload returns a URL, one happy-path PDF upload, trusting browser content-type, public bucket access, "
        "scan as follow-up, or no tenant negative and cleanup proof."
    )

    first_summary = _invoke_file_upload_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_file_upload_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Upload Storage Contract Inspector freezing MIME/content sniffing, extension/content "
            "mismatch cases, size limits, malware fixtures, quarantine state machine, private bucket/object ACL, signed URL "
            "permission and expiry, tenant object-key isolation, failed upload cleanup, orphan cleanup, audit fields, monitoring, "
            "and local governance. File Upload Builder implements only after that handoff. Then run Storage Access Inspector and "
            "Malware Cleanup Inspector in parallel: Storage Access verifies private ACL, signed URL auth/expiry, tenant negative "
            "access, object-key isolation, and public exposure monitoring; Malware Cleanup verifies MIME spoofing, oversize "
            "rejection, malware scan, quarantine before serving, failed upload cleanup, orphan cleanup, audit actor/object/hash/"
            "verdict/reason, scan failure alerts, and governance. GateKeeper must fail closed on returned-URL-only, happy PDF "
            "only, browser-content-type-only, public bucket, scan follow-up, missing quarantine, missing tenant negatives, "
            "missing cleanup, missing audit/monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_file_upload_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_file_upload_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this file upload storage-safety contract-first parallel evidence direction.",
        env=env,
    )
    _assert_file_upload_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _file_upload_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_file_upload_bundle(bundle_text)


def _invoke_file_upload_plan_round(
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


def _assert_file_upload_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Upload Storage Contract Inspector" in agreement_text
    assert "File Upload Builder" in agreement_text
    assert "Storage Access Inspector" in agreement_text
    assert "Malware Cleanup Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_file_upload_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("file upload", "MIME", "malware", "quarantine", "signed URL", "tenant", "cleanup", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this file upload" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _file_upload_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_file_upload_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "upload-storage-contract-inspector",
        "file-upload-builder",
        "storage-access-inspector",
        "malware-cleanup-inspector",
        "upload-storage-gatekeeper",
    ]
    assert workflow["preset"] == "file-upload-contract-parallel-storage-safety"
    assert [step["id"] for step in workflow["steps"]] == [
        "upload_storage_contract_inspection_step",
        "file_upload_builder_step",
        "storage_access_inspection_step",
        "malware_cleanup_inspection_step",
        "upload_storage_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["upload_storage_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "file_upload_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "file_upload_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "upload_storage_contract_inspection_step",
        "file_upload_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "upload_storage_contract_inspection_step",
        "file_upload_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "upload_storage_contract_inspection_step",
        "file_upload_builder_step",
        "storage_access_inspection_step",
        "malware_cleanup_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "file-upload-safety",
        "tenant-isolation",
        "permission-auth",
        "privacy-redaction",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "File Upload Storage Safety Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this file upload" not in bundle_text


def test_alignment_agreement_requires_file_upload_storage_safety(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship file upload so users can upload a PDF and receive a stored object URL.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means user file upload to object storage proves MIME/content-type sniffing, "
                    "file size limits, virus/malware scan, quarantine, signed URL permission, tenant isolation, "
                    "failed upload cleanup, and audit log evidence."
                ),
                "fake_done_risks": (
                    "Only returning an upload URL or proving one happy-path upload without MIME, malware scan, "
                    "signed URL access, quarantine, and failed-upload cleanup evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include MIME spoofing, oversize file, malware quarantine, signed URL auth, "
                    "tenant negative access, cleanup, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "file-upload/storage-safety" in issue for issue in issues)
    assert any("fake-done risks" in issue and "file-upload/storage-safety" in issue for issue in issues)
    assert any("evidence preferences" in issue and "file-upload/storage-safety" in issue for issue in issues)


def test_agent_first_traceability_blocks_returned_url_only_file_upload(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship file upload so a user can upload a PDF and receive a stored object URL.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: MIME sniffing, malware scan, quarantine, signed URL access, tenant isolation, "
        "failed-upload cleanup, and audit proof can be handled later.\n"
        "  Owner: storage owner\n"
        "  Follow-up: create an upload security ticket.\n"
        "  Acceptance path: GateKeeper can pass after upload returns URL for one sample PDF.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat upload MIME, malware scan, quarantine, signed URL auth, tenant isolation, cleanup, "
        "and audit as later residual risk.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(UPLOAD_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "file-upload/storage-safety" in issue for issue in issues)
    assert any("fake-done risks" in issue and "file-upload/storage-safety" in issue for issue in issues)
    assert any("evidence preferences" in issue and "file-upload/storage-safety" in issue for issue in issues)
    assert any("success criteria" in issue and "access/tenant-isolation" in issue for issue in issues)
