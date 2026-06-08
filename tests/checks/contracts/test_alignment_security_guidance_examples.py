from __future__ import annotations

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


def test_alignment_examples_require_support_impersonation_breakglass_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Support impersonation break-glass example",
            "support impersonation / break-glass admin access",
            "approved ticket、customer consent、reason code 和 supervisor approval",
            "不能共享 admin token 或绕过 MFA policy",
            "只有 support 能登录客户账号、打开 feature flag、共享管理员 token 或 UI 显示 impersonating banner 必须阻断",
            "access/support-impersonation-breakglass",
            "Impersonation Contract Inspector",
            "Access Evidence Inspector",
            "审批/同意 + 会话归因 + 撤销/审计证据优先",
        ),
    )


def test_alignment_examples_require_consent_preference_governance_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Consent preference governance example",
            "GDPR/CCPA consent and preference center",
            "consent version、policy version、purpose id、legal basis",
            "withdraw consent 后 analytics event、marketing campaign、data export 和 vendor sync",
            "只有 cookie banner 显示、checkbox 保存成功或 localStorage 有 consent=true 必须阻断",
            "privacy/consent-preference-governance",
            "Consent Contract Inspector",
            "Consent Evidence Inspector",
            "purpose/version + withdrawal + vendor sync 证据优先",
        ),
    )


def test_alignment_examples_require_authorization_policy_consistency_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Authorization policy consistency example",
            "RBAC/ABAC authorization policy engine",
            "同一 policy decision",
            "不能把“隐藏按钮”“加 middleware”或“一条 admin happy path 通过”当成 authorization policy engine 完成",
            "access/authorization-policy-consistency",
            "Authorization Policy Contract Inspector",
            "Authorization Evidence Inspector",
            "permission matrix + policy decision trace + 负向授权证据优先",
        ),
    )
