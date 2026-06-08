from __future__ import annotations

from pathlib import Path

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


KEY_ROTATION_TASK_TEXT = (
    "我要给客户 API key / service account secret 做 rotation。成功必须证明 old key 和 new key "
    "有受控 overlap window，zero-downtime rotation 不影响现有调用，compromised key 能立即 revoke，"
    "revoked key 不能继续调用，key scope / tenant binding 正确，secret 只以 hash 或 KMS encrypted "
    "形式存储，rotation schedule、expiry、last-used telemetry、audit log 记录 key id、actor、scope、"
    "tenant、created/rotated/revoked/failed reason；rollback 不能重新启用 revoked key，监控要能发现 "
    "rotation failure 和 stale key。只有 UI 显示生成了新 key、env var 改了或 happy path API call 成功必须阻断。"
)


def test_success_categories_detect_key_rotation_without_password_reset_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(KEY_ROTATION_TASK_TEXT)]
    password_reset_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须证明 password reset token 是一次性且有 expiry，replay 不能改密码，"
            "密码修改后旧 session / refresh token 全部失效。"
        )
    ]
    weak_new_key_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须让 UI 显示一个新的 API key，并把 env var 改成新值。"
        )
    ]

    assert "security/key-rotation-lifecycle" in labels
    assert "privacy/secrets-redaction" in labels
    assert "audit/log" in labels
    assert "regression/monitoring-guard" in labels
    assert "auth/session-token-lifecycle" not in labels
    assert "security/key-rotation-lifecycle" not in password_reset_labels
    assert "security/key-rotation-lifecycle" not in weak_new_key_labels


def test_fake_done_and_evidence_categories_detect_key_rotation_lifecycle_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(KEY_ROTATION_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(KEY_ROTATION_TASK_TEXT)
    ]

    assert "security/key-rotation-lifecycle" in fake_labels
    assert "security/key-rotation-lifecycle" in evidence_labels
    assert "privacy/secrets-redaction" in evidence_labels
    assert "happy-path-only" in fake_labels


def test_alignment_agreement_requires_key_rotation_lifecycle_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Generate a new API key and show the updated env var.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means API key rotation proves old/new overlap window, zero-downtime rotation, "
                    "compromised key revoke, revoked key denial, key scope, tenant binding, KMS encrypted or "
                    "hashed secret storage, expiry, last-used telemetry, rollback safety, stale-key monitoring, "
                    "and audit key id."
                ),
                "fake_done_risks": (
                    "A UI showing one new key, an env var change, or one happy path API call without overlap, revoke, "
                    "revoked-key denial, tenant binding, secret storage, expiry, telemetry, rollback, monitoring, "
                    "and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include API key rotation overlap proof, old and new key API calls, revoked-key "
                    "negative calls, scope and tenant-binding checks, KMS/hash storage inspection, expiry/last-used "
                    "telemetry, rotation failure alerts, rollback safety, and audit logs."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)


def test_agent_first_traceability_blocks_new_key_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Generate a new API key and show the updated env var.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 overlap window、zero-downtime rotation、compromised-key revoke、revoked-key negative call、"
        "scope / tenant binding、secret storage、expiry、last-used telemetry、rollback、monitoring 或 audit proof "
        "作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: overlap window, zero-downtime rotation, compromised-key revoke, revoked-key denial, "
        "scope, tenant binding, hash/KMS storage, expiry, last-used telemetry, rollback safety, monitoring, and audit proof "
        "can be handled later.\n"
        "  Owner: platform owner\n"
        "  Follow-up: add key rotation hardening later.\n"
        "  Acceptance path: GateKeeper can pass after the UI shows a new API key and the env var is updated.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 UI 显示生成了新 API key，并更新 env var，不处理 overlap window、zero-downtime rotation、"
        "revoke、revoked-key negative call、scope、tenant binding、hash/KMS storage、expiry、telemetry、"
        "rollback、monitoring 或 audit proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat rotation overlap, revoked-key denial, tenant binding, hash/KMS storage, expiry, telemetry, "
        "rollback, monitoring, and audit proof as later residual risk; only check new-key UI and env var update."
    )

    issues = alignment_agent_candidate_traceability_issues(KEY_ROTATION_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "security/key-rotation-lifecycle" in issue for issue in issues)
