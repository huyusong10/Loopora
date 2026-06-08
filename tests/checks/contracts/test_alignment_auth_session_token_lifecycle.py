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


PASSWORD_RESET_TASK_TEXT = (
    "我要做 password reset。成功必须证明 reset token 是一次性且有 expiry，重复点击或 replay 不能改密码，"
    "token 只以 hash 存储，密码修改后旧 session / refresh token 全部失效，"
    "rate limit 和 enumeration resistance 生效，audit log 记录 request、consume、expired、replay blocked；"
    "只有邮件发出或 happy path 重置成功必须阻断。"
)


def test_cli_agent_plan_auth_session_rounds_use_parallel_lifecycle_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-auth-session-token-lifecycle",
    }
    task_message = (
        "Plan a governed Loop for auth session and token lifecycle hardening. Success must prove access token expiry, "
        "refresh token rotation and reuse detection, logout and all-devices session revocation, password reset and MFA "
        "step-up invalidating sessions where required, stolen/expired/revoked token negative cases, secure/httpOnly/"
        "SameSite cookie flags, CSRF boundary for browser flows, API token boundary for non-browser clients, tenant/"
        "device/session audit trail, monitoring alerts for token replay or reuse, and backward-compatible migration. "
        "Fake done is login/logout happy path, clearing UI session only, relying on framework defaults, short expiry only, "
        "no revoked/stolen token negative proof, no refresh token reuse proof, or treating revocation as follow-up."
    )

    first_summary = _invoke_auth_session_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_auth_session_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Session Token Contract Inspector freezing access/refresh token expiry, "
            "refresh rotation, reuse detection, logout/all-device revocation, password reset invalidation, MFA step-up "
            "invalidation, cookie flags, CSRF/API boundary, tenant/device/session audit fields, monitoring alerts, "
            "migration and local governance. Session Token Builder implements only after that handoff. Then run Token "
            "Misuse Inspector and Session Revocation Audit Inspector in parallel: Token Misuse checks expired/revoked/"
            "stolen tokens, refresh reuse, cookie security, CSRF/API token boundary, tenant negatives, and replay alerts; "
            "Session Revocation Audit checks logout current/all devices, password reset and MFA invalidation, audit trail, "
            "monitoring, compatibility/migration, and governance. GateKeeper must fail closed on login/logout happy path, "
            "frontend-only session clear, library defaults, short expiry only, missing revoked or stolen token negatives, "
            "missing refresh reuse detection, missing session invalidation, missing audit/monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_auth_session_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_auth_session_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this auth session/token contract-first parallel lifecycle direction.",
        env=env,
    )
    _assert_auth_session_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _auth_session_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_auth_session_bundle(bundle_text)


def _invoke_auth_session_plan_round(
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


def _assert_auth_session_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Session Token Contract Inspector" in agreement_text
    assert "Session Token Builder" in agreement_text
    assert "Token Misuse Inspector" in agreement_text
    assert "Session Revocation Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_auth_session_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("session", "refresh", "revocation", "cookie", "CSRF", "audit", "monitoring"):
        assert term in ready_projection_text
    assert "Confirm; use this auth session" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _auth_session_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_auth_session_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "session-token-contract-inspector",
        "session-token-builder",
        "token-misuse-inspector",
        "session-revocation-audit-inspector",
        "auth-session-gatekeeper",
    ]
    assert workflow["preset"] == "auth-session-token-contract-parallel-lifecycle"
    assert [step["id"] for step in workflow["steps"]] == [
        "session_token_contract_inspection_step",
        "session_token_builder_step",
        "token_misuse_inspection_step",
        "session_revocation_audit_inspection_step",
        "auth_session_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["session_token_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "auth_session_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "auth_session_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "session_token_contract_inspection_step",
        "session_token_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "session_token_contract_inspection_step",
        "session_token_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "session_token_contract_inspection_step",
        "session_token_builder_step",
        "token_misuse_inspection_step",
        "session_revocation_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "session-lifecycle",
        "permission-auth",
        "privacy-redaction",
        "tenant-isolation",
        "audit-log",
        "monitoring",
        "backward-compatibility",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Auth Session Token Lifecycle Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this auth session" not in bundle_text


def test_success_categories_separate_session_token_lifecycle_from_plain_secret_terms() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means password reset proves reset token single-use, expiry, replay prevention, "
            "token hashing, old session revocation, refresh token invalidation, rate limiting, and audit."
        )
    ]

    assert "auth/session-token-lifecycle" in labels
    assert "privacy/secrets-redaction" in labels


def test_alignment_agreement_requires_password_reset_token_lifecycle_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship password reset so users receive a reset email and can set a new password.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means password reset proves reset token single-use, expiry, replay prevention, "
                    "token hashing, old session and refresh token invalidation, rate limiting, enumeration resistance, "
                    "and audit records request, consume, expired, and replay blocked."
                ),
                "fake_done_risks": (
                    "Only proving email sent or happy-path password reset without token lifecycle, expiry, replay, "
                    "old session invalidation, rate limit, enumeration resistance, and audit evidence must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include password reset token single-use, expiry, replay blocked, hashed token storage, "
                    "old session and refresh token revocation, rate limit, enumeration resistance, and audit log checks."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "auth/session-token-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "auth/session-token-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "auth/session-token-lifecycle" in issue for issue in issues)


def test_agent_first_traceability_blocks_email_only_password_reset_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship password reset so users receive a reset email and can set a new password.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: reset token one-time use, expiry, replay prevention, token hashing, "
        "old session revocation, refresh token invalidation, rate limiting, enumeration resistance, "
        "and audit proof can be handled later.\n"
        "  Owner: identity owner\n"
        "  Follow-up: create token lifecycle follow-up.\n"
        "  Acceptance path: GateKeeper can pass after a reset email sends and one happy-path password reset succeeds.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat reset token one-time use, expiry, replay prevention, token hashing, old session revocation, "
        "refresh token invalidation, rate limiting, enumeration resistance, and audit as later residual risk; "
        "only check email send and happy-path password reset.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(PASSWORD_RESET_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "auth/session-token-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "auth/session-token-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "auth/session-token-lifecycle" in issue for issue in issues)
    assert any("success criteria" in issue and "audit/log" in issue for issue in issues)
