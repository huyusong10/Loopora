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


AUTHORIZATION_POLICY_TASK_TEXT = (
    "我要重做企业后台的 RBAC/ABAC authorization policy engine。成功必须证明 role hierarchy、"
    "resource scope、team membership、owner/admin/viewer、deny-overrides-allow、field-level permissions、"
    "审批流、API endpoint enforcement、UI affordance、background job、export/report 和 audit log 都使用"
    "同一 policy decision；角色变更、组织迁移、SCIM/SSO group mapping、临时权限、policy version rollout "
    "和 cache invalidation 都一致。假完成是只隐藏按钮、只加 middleware、只检查一个 admin role、或只让 "
    "happy-path endpoint 过。证据要包含 permission matrix contract、policy decision trace、"
    "negative authorization cases、cross-resource escalation attempts、cache stale/revocation proof、"
    "audit log immutable refs 和 migration rollback/compat proof。"
)


def test_success_categories_detect_authorization_policy_consistency_without_role_matrix_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(AUTHORIZATION_POLICY_TASK_TEXT)]
    generic_permission_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means owner/member/viewer can share a workspace and the role matrix covers direct object ID access."
        )
    ]

    assert "access/authorization-policy-consistency" in labels
    assert "permission/auth" in labels
    assert "data/export/report" in labels
    assert "audit/log" in labels
    assert "audit/log-integrity-retention" in labels
    assert "cache/invalidation-consistency" in labels
    assert "identity/provisioning-role-mapping" in labels
    assert "migration/rollback-integrity" in labels
    assert "access/tenant-isolation" in generic_permission_labels
    assert "access/authorization-policy-consistency" not in generic_permission_labels


def test_fake_done_and_evidence_categories_detect_authorization_policy_consistency_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(AUTHORIZATION_POLICY_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(AUTHORIZATION_POLICY_TASK_TEXT)
    ]

    assert "access/authorization-policy-consistency" in fake_labels
    assert "access/authorization-policy-consistency" in evidence_labels
    assert "permission/audit" in fake_labels
    assert "permission/auth" in evidence_labels
    assert "cache/invalidation-consistency" in fake_labels
    assert "identity/provisioning-role-mapping" in evidence_labels
    assert "audit/log-integrity-retention" in evidence_labels


def test_alignment_agreement_requires_authorization_policy_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show a restricted dashboard page and make one protected route return success.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means the RBAC/ABAC authorization policy engine proves one policy decision across role "
                    "hierarchy, resource scope, team membership, owner/admin/viewer, deny-overrides-allow, field-level "
                    "permissions, approval workflow, API endpoint enforcement, UI affordance, background job, "
                    "export/report, audit log, role change, SCIM/SSO group mapping, temporary permissions, policy "
                    "version rollout, and cache invalidation."
                ),
                "fake_done_risks": (
                    "Hidden buttons, one middleware check, one admin role, or happy-path endpoint coverage without the "
                    "shared policy decision, negative authorization cases, cross-resource escalation attempts, cache "
                    "stale and revocation proof, audit immutability, migration rollback, and compatibility proof must "
                    "be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include a permission matrix contract, policy decision trace, negative authorization "
                    "cases, cross-resource escalation attempts, cache stale and revocation proof, immutable audit log "
                    "refs, SCIM/SSO group mapping, policy version rollout, and migration rollback/compat proof."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "access/authorization-policy-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "access/authorization-policy-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "access/authorization-policy-consistency" in issue for issue in issues)


def test_agent_first_traceability_blocks_button_middleware_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Hide unauthorized buttons, add one admin middleware check, and make the happy-path endpoint pass.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求隐藏按钮、加一个 admin middleware check、让 happy-path endpoint 通过。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: policy decision trace, role hierarchy, resource scope, team membership, field-level "
        "permissions, API/UI/job/export/audit consistency, SCIM/SSO group mapping, cache stale/revocation, negative "
        "authorization, cross-resource escalation, migration rollback, and compatibility proof can be handled later.\n"
        "  Owner: platform security owner\n"
        "  Follow-up: add authorization policy consistency proof later.\n"
        "  Acceptance path: GateKeeper can pass after button hiding, middleware, and one endpoint test.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现隐藏按钮、admin middleware check 和 happy-path endpoint，不处理同一 policy decision、"
        "角色层级、资源范围、字段级权限、SCIM/SSO、缓存撤销、负向授权、跨资源提权、审计或迁移兼容证明。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat hidden buttons, one admin middleware check, and one happy-path endpoint as enough for this pass; "
        "policy decision trace and negative authorization proof can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(AUTHORIZATION_POLICY_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "access/authorization-policy-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "access/authorization-policy-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "access/authorization-policy-consistency" in issue for issue in issues)
