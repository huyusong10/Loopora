from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.alignment_traceability_terms import agent_candidate_traceability_terms


def test_alignment_traceability_checks_loop_fit_task_terms(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "loop_fit": (
                    "Browsertrace needs Loopora because later rounds must create new browsertrace proof "
                    "before GateKeeper can close."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("loop_fit missing browsertrace" in issue for issue in issues)


def test_alignment_traceability_cjk_terms_keep_domain_terms_without_sentence_shards() -> None:
    terms = agent_candidate_traceability_terms(
        "我要给审批通过后的客户发邮件通知。成功必须证明客户 exactly once 收到通知，"
        "重试或刷新不能重复发送；审计日志必须能追溯是谁触发。重复通知、缺审计或只有发送成功叙述都要阻断。"
    )

    assert "邮件" in terms
    assert "通知" in terms
    assert "重复" in terms
    assert "审计" in terms
    assert "日志" in terms
    for noisy in ("我要", "给审", "批通", "户发"):
        assert noisy not in terms


def test_alignment_traceability_checks_agreement_success_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the refund approval path so Support admin can approve a refund and audit log records the actor.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means Support admin can approve a refund, audit log records the actor, "
                    "and customer receives an email notification."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "notification/message" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_idempotency_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the account alert path so a customer receives an email notification after profile approval.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means the customer receives exactly one email notification after approval; "
                    "duplicate notifications must block GateKeeper, unsubscribe/preference center is respected, "
                    "suppression list and delivery event proof are covered."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "idempotency/duplicate-prevention" in issue for issue in issues)
    assert any("success surface" in issue and "notification/subscription-deliverability" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_privacy_redaction_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the admin CSV export path so an operator can download customer records.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means only authorized admins can export a redacted customer CSV; "
                    "phone numbers, access tokens, and PII must not leak into the export or logs."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "privacy/secrets-redaction" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_migration_rollback_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the invoice state-machine migration so billing data continues to appear in reports.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means invoice status migration preserves historical invoice data, "
                    "row-count and checksum proof show no amount or status loss, rollback is proven, "
                    "and old API clients plus legacy reports stay backward compatible."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "migration/rollback-integrity" in issue for issue in issues)
    assert any("success surface" in issue and "compatibility/backward-compat" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_evaluation_quality_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Improve the help-center semantic search ranking quality so users see better answers.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means Top-5 search result quality improves across an eval set covering real queries, "
                    "negative examples, and regression samples, with human review of relevance and hallucination risk."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "evaluation/eval-set" in issue for issue in issues)
    assert any("success surface" in issue and "quality/human-review" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_incident_remediation_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Fix the intermittent duplicate charge incident in checkout with a targeted patch and existing tests.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means the duplicate-charge incident has repro or trigger-condition evidence, "
                    "root-cause proof, regression coverage, monitoring or alerting for recurrence, and a clear rollback path."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "incident/root-cause-repro" in issue for issue in issues)
    assert any("success surface" in issue and "regression/monitoring-guard" in issue for issue in issues)
    assert not any("migration/rollback-integrity" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_provider_resilience_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Integrate the shipping quote provider API so checkout can display rates.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means the sandbox provider contract returns real shipping rates, "
                    "signature/auth handling is verified, and timeout, rate-limit, retry/backoff, "
                    "and fallback behavior all have evidence."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "external/provider-contract" in issue for issue in issues)
    assert any("success surface" in issue and "resilience/retry-timeout" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_tenant_isolation_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add workspace sharing permissions so organization members can open shared dashboards.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means tenant isolation is proven: Org A users cannot reach Org B dashboards "
                    "through UI, API, or direct object ID, the owner/member/viewer role matrix is correct, "
                    "and audit log records unauthorized attempts."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "access/tenant-isolation" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_data_lifecycle_deletion_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add account deletion so users can delete their profile from settings.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means GDPR erasure proof covers the primary database, search index, cache, "
                    "export reports, anonymized audit or billing retention exceptions, backups, and async cleanup."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "data-lifecycle/deletion-retention" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_analytics_experiment_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add onboarding continue behavior so the continue button works.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means onboarding analytics instrumentation proves funnel event schema, "
                    "warehouse reconciliation, and A/B experiment assignment/exposure consistency."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "analytics/event-integrity" in issue for issue in issues)
    assert any("success surface" in issue and "experiment/assignment-consistency" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_async_job_queue_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add report export so the export button shows queued.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means async job queue proof covers persisted job enqueue, worker processing, "
                    "pending/running/succeeded/failed job status, generated files, dead-letter queue or recoverable "
                    "failure path, and refresh recovery."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "async/job-lifecycle" in issue for issue in issues)
    assert any("success surface" in issue and "queue/failure-recovery" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_webhook_billing_reconciliation_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add Stripe subscription webhook handling so invoices update when a webhook is received.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means Stripe subscription webhook proof covers signature verification, duplicate event "
                    "idempotency, out-of-order invoice/subscription events, provider event replay, local billing ledger "
                    "reconciliation, invoice amount reconciliation, and entitlement sync."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "webhook/signature-replay-ordering" in issue for issue in issues)
    assert any("success surface" in issue and "billing/ledger-reconciliation" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_sso_identity_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add enterprise SSO login so one Okta test user can sign in.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means SAML/OIDC proof covers IdP metadata, assertion signature validation, "
                    "tenant domain binding, JIT provisioning or SCIM, owner/admin/member role mapping, logout, "
                    "session expiry, and audit evidence for forged assertions."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "identity/sso-assertion" in issue for issue in issues)
    assert any("success surface" in issue and "identity/provisioning-role-mapping" in issue for issue in issues)
    assert any("success surface" in issue and "access/tenant-isolation" in issue for issue in issues)


def test_agent_first_traceability_checks_idempotent_notification_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the customer email notification path after approval and keep audit-log evidence for the triggering actor.",
    )
    task_text = (
        "我要给审批通过后的客户发邮件通知。成功必须证明客户 exactly once 收到通知，"
        "重试或刷新不能重复发送；审计日志必须能追溯是谁触发。重复通知、缺审计或只有发送成功叙述都要阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("evidence preferences" in issue and "idempotency/duplicate-prevention" in issue for issue in issues)
    assert not any(noisy in " ".join(issues) for noisy in ("我要", "给审", "批通", "户发"))


def test_agent_first_traceability_checks_notification_deliverability_and_preferences(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship lifecycle campaign email so one internal test address receives a provider-accepted message.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: unsubscribe, preference center, suppression list, bounce, complaint, "
        "provider delivery event, audit-log reconciliation, locale template parity, and PII checks can be handled later.\n"
        "  Owner: lifecycle marketing owner\n"
        "  Follow-up: create an email compliance ticket.\n"
        "  Acceptance path: GateKeeper can pass after provider accepted and one test inbox receives the message.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Accept unsubscribe, preference center, suppression list, bounce, complaint, and delivery event proof as later residual risk."
    )
    task_text = (
        "我要做 lifecycle campaign email。成功必须证明只给已订阅且符合偏好的用户发送，"
        "unsubscribe / preference center 生效，suppression list、bounce、complaint 不会继续发送，"
        "provider delivery event 能和本地 audit log 对账，中英文模板变量一致且 PII 不泄露；"
        "只有 provider accepted 或一个测试邮箱收到邮件必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "notification/subscription-deliverability" in issue for issue in issues)
    assert any("fake-done risks" in issue and "notification/subscription-deliverability" in issue for issue in issues)
    assert any("evidence preferences" in issue and "notification/subscription-deliverability" in issue for issue in issues)
    assert any("evidence preferences" in issue and "audit/log" in issue for issue in issues)
    assert any("success criteria" in issue and "privacy/secrets-redaction" in issue for issue in issues)
    assert any("success criteria" in issue and "locale/i18n" in issue for issue in issues)


def test_agent_first_traceability_checks_privacy_redaction_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the admin CSV export path with role-gated download and audit-log evidence.",
    )
    task_text = (
        "我要做客户数据 CSV 导出。成功必须证明只有授权管理员可以导出，手机号、token 和个人信息必须脱敏，"
        "导出文件和日志都不能泄露敏感数据；只有下载成功截图或自然语言声明必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "privacy/secrets-redaction" in issue for issue in issues)
    assert any("evidence preferences" in issue and "privacy/secrets-redaction" in issue for issue in issues)
    assert not any("locale/i18n" in issue for issue in issues)


def test_agent_first_traceability_checks_migration_rollback_and_compatibility(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship the invoice state-machine migration and keep billing reports available.",
    )
    task_text = (
        "我要把 billing 的 invoice 状态从旧 enum 迁到新的 state machine。成功必须证明历史 invoice 数据迁移后金额和状态不丢失，"
        "旧 API 和旧报表兼容，迁移可以回滚；只有单元测试通过但没有 dry-run、row-count/checksum 和 rollback proof 必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "migration/rollback-integrity" in issue for issue in issues)
    assert any("success criteria" in issue and "compatibility/backward-compat" in issue for issue in issues)
    assert any("fake-done risks" in issue and "migration/rollback-integrity" in issue for issue in issues)
    assert any("evidence preferences" in issue and "migration/rollback-integrity" in issue for issue in issues)


def test_agent_first_traceability_checks_evaluation_quality_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Improve the help-center semantic search ranking quality so users see better answers.",
    )
    task_text = (
        "我要优化 help-center semantic search。成功必须证明 Top-5 结果质量提升，eval set 覆盖真实查询、负例和回归样本，"
        "人工评审要看 relevance 和 hallucination risk；只有一个 demo query 看起来更好或 benchmark 分数单点上涨必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "evaluation/eval-set" in issue for issue in issues)
    assert any("success criteria" in issue and "quality/human-review" in issue for issue in issues)
    assert any("fake-done risks" in issue and "evaluation/eval-set" in issue for issue in issues)
    assert any("evidence preferences" in issue and "evaluation/eval-set" in issue for issue in issues)
    assert any("evidence preferences" in issue and "quality/human-review" in issue for issue in issues)


def test_agent_first_traceability_checks_incident_root_cause_and_monitoring(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Fix the intermittent duplicate charge incident in checkout with a targeted patch and existing tests.",
    )
    task_text = (
        "我要修一个生产事故：checkout 偶发重复扣款。成功必须证明能复现或解释触发条件，找到 root cause，"
        "补 regression test，监控/告警能发现复发，发布或回滚路径清楚；只有 patch 了一个分支但没有 repro、"
        "root-cause proof 或 monitoring evidence 必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "incident/root-cause-repro" in issue for issue in issues)
    assert any("success criteria" in issue and "regression/monitoring-guard" in issue for issue in issues)
    assert any("fake-done risks" in issue and "incident/root-cause-repro" in issue for issue in issues)
    assert any("evidence preferences" in issue and "regression/monitoring-guard" in issue for issue in issues)
    assert not any("migration/rollback-integrity" in issue for issue in issues)


def test_agent_first_traceability_checks_provider_contract_and_resilience(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Integrate the shipping quote provider API so checkout can display rates.",
    )
    bundle["spec"]["markdown"] += "\n# Residual Risk\n少量外部服务异常可以由后续线上观察跟进。\n"
    task_text = (
        "我要接入一个第三方 shipping quote provider API。成功必须证明 sandbox provider contract 能返回真实 rate，"
        "signature/auth 处理正确，timeout、rate limit、retry/backoff 和 fallback 都有证据；"
        "只有 mock response 或 happy path API call 成功必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "external/provider-contract" in issue for issue in issues)
    assert any("success criteria" in issue and "resilience/retry-timeout" in issue for issue in issues)
    assert any("fake-done risks" in issue and "external/provider-contract" in issue for issue in issues)
    assert any("fake-done risks" in issue and "resilience/retry-timeout" in issue for issue in issues)
    assert any("evidence preferences" in issue and "external/provider-contract" in issue for issue in issues)
    assert any("evidence preferences" in issue and "resilience/retry-timeout" in issue for issue in issues)


def test_agent_first_traceability_checks_tenant_isolation_access_control(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add workspace sharing permissions so organization members can open shared dashboards.",
    )
    task_text = (
        "我要给 B2B SaaS 加 workspace sharing 权限。成功必须证明 tenant isolation：Org A 用户不能通过 UI、API "
        "或 direct object ID 访问 Org B dashboard，owner/member/viewer 角色矩阵正确，audit log 记录越权尝试；"
        "只有 owner happy path 能打开 dashboard 必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "access/tenant-isolation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "access/tenant-isolation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "access/tenant-isolation" in issue for issue in issues)
    assert not any("visual/polish/screenshot-only" in issue for issue in issues)


def test_agent_first_traceability_checks_data_lifecycle_deletion_retention(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add account deletion so settings shows the profile as deleted.",
    )
    task_text = (
        "我要做 GDPR account erasure。成功必须证明用户删除后主库、搜索索引、缓存和导出报表里都没有 PII，"
        "需要保留的审计/账务记录必须匿名化并说明 retention exception，备份或异步清理路径有证据；"
        "只有 settings 页面显示 deleted 或用户表软删除必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "data-lifecycle/deletion-retention" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data-lifecycle/deletion-retention" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data-lifecycle/deletion-retention" in issue for issue in issues)


def test_agent_first_traceability_checks_analytics_event_and_experiment_integrity(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add onboarding click logging so the continue button works.",
    )
    bundle["collaboration_summary"] = "This run talks about analytics instrumentation and experiment exposure only in summary."
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: analytics, experiment exposure, and reporting can be handled later.\n"
        "  Owner: product owner\n"
        "  Follow-up: create a follow-up ticket if instrumentation is needed.\n"
        "- Fail closed if: the continue button does not advance.\n"
    )
    task_text = (
        "我要给移动端 onboarding 加 analytics instrumentation 和 A/B experiment exposure。成功必须证明 signup funnel "
        "每一步事件 schema 正确，同一次用户路径不会重复上报，consent 拒绝时不发 PII，实验 assignment/exposure 一致，"
        "dashboard 或 warehouse 查询能和真实事件对账；只有按钮可点、console.log 或 mock analytics call 必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "analytics/event-integrity" in issue for issue in issues)
    assert any("success criteria" in issue and "experiment/assignment-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "analytics/event-integrity" in issue for issue in issues)
    assert any("evidence preferences" in issue and "analytics/event-integrity" in issue for issue in issues)
    assert any("evidence preferences" in issue and "experiment/assignment-consistency" in issue for issue in issues)
    assert not any("migration/rollback-integrity" in issue for issue in issues)


def test_agent_first_traceability_checks_async_job_lifecycle_and_queue_recovery(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add report export so users can click export and see queued status.",
    )
    task_text = (
        "我要把大报表导出改成 async job queue。成功必须证明点击 export 后 job 被持久化入队，worker 会处理并生成文件，"
        "用户能看到 pending/running/succeeded/failed 状态，重试不会生成重复文件，失败会进入 dead-letter queue 或可恢复队列，"
        "断线刷新后状态仍能恢复；只有按钮显示 queued 或本地 happy path 生成文件必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "async/job-lifecycle" in issue for issue in issues)
    assert any("success criteria" in issue and "queue/failure-recovery" in issue for issue in issues)
    assert any("fake-done risks" in issue and "async/job-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "queue/failure-recovery" in issue for issue in issues)


def test_agent_first_traceability_checks_webhook_signature_ordering_and_billing_reconciliation(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add Stripe subscription webhook handling so a happy-path webhook updates invoice status.",
    )
    task_text = (
        "我要接 Stripe subscription webhook。成功必须证明 webhook signature 验证、重复事件幂等、"
        "乱序 invoice.paid / customer.subscription.updated 不会把订阅状态写错，provider event replay 可以恢复本地 ledger，"
        "invoice 金额和订阅权限要能和 Stripe dashboard/fixture 对账；只有一个 webhook happy path 更新 invoice 状态或 mock event 通过必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "webhook/signature-replay-ordering" in issue for issue in issues)
    assert any("success criteria" in issue and "billing/ledger-reconciliation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "webhook/signature-replay-ordering" in issue for issue in issues)
    assert any("evidence preferences" in issue and "billing/ledger-reconciliation" in issue for issue in issues)


def test_agent_first_traceability_checks_sso_assertion_and_provisioning(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add enterprise SSO login so one Okta test user can sign in.",
    )
    task_text = (
        "我要给企业客户接 SAML/OIDC SSO。成功必须证明 IdP metadata 和 assertion signature 验证正确，"
        "tenant domain binding 防止 A 公司 assertion 登录 B 公司，JIT provisioning/SCIM 角色映射 owner/admin/member 正确，"
        "logout 和 session expiry 有证据，失败断言和伪造 assertion 会被审计；只有一个 Okta 测试用户能登录必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "identity/sso-assertion" in issue for issue in issues)
    assert any("success criteria" in issue and "identity/provisioning-role-mapping" in issue for issue in issues)
    assert any("success criteria" in issue and "access/tenant-isolation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "identity/sso-assertion" in issue for issue in issues)
    assert any("evidence preferences" in issue and "identity/provisioning-role-mapping" in issue for issue in issues)


def test_agent_first_traceability_checks_accessibility_and_locale_fake_done(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Redesign the checkout modal so it matches the visual design screenshot.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Residual Risk\n"
        "- Accepted residual risk: keyboard navigation, focus trap, screen reader labels, ARIA states, "
        "contrast, error announcements, and locale parity can be handled later.\n"
        "  Owner: frontend owner\n"
        "  Follow-up: create an accessibility ticket if needed.\n"
        "  Acceptance path: GateKeeper can pass after a screenshot and mouse happy path.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat keyboard, screen reader, ARIA, contrast, and locale parity as accepted residual risk for follow-up.\n"
    )
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Accept a11y and locale parity as residual risk when screenshot evidence exists."
    )
    task_text = (
        "我要重做 checkout modal。成功必须证明键盘用户可以完整下单，focus trap 不会丢焦点，"
        "screen reader/ARIA label、错误提示 announcement、WCAG contrast 都有证据；"
        "中英文界面操作语义一致；只有视觉截图或鼠标 happy path 通过必须阻断。"
    )

    issues = alignment_agent_candidate_traceability_issues(task_text, bundle)

    assert any("success criteria" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("success criteria" in issue and "locale/i18n" in issue for issue in issues)
    assert any("fake-done risks" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("fake-done risks" in issue and "locale/i18n" in issue for issue in issues)
    assert any("evidence preferences" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("evidence preferences" in issue and "locale/i18n" in issue for issue in issues)
    assert not any("accessibility/i18n" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_evidence_preference_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Prefer project-owned checks, direct run output, and concrete artifacts before screenshots or claims.",
        "Prefer browser journey proof before screenshots or claims.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": (
                    "Evidence must include a browser journey and audit log command output before GateKeeper can pass."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence preferences" in issue and "audit/log" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_accessibility_and_locale_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means keyboard users can complete checkout, screen reader labels are available, "
                    "and Chinese and English variants preserve the same action."
                ),
                "evidence_preferences": (
                    "Evidence must include keyboard navigation proof and Chinese and English locale verification."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("success surface" in issue and "locale/i18n" in issue for issue in issues)
    assert any("evidence preferences" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("evidence preferences" in issue and "locale/i18n" in issue for issue in issues)


def test_alignment_traceability_ignores_metadata_and_loop_names(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["metadata"]["name"] = "browsertrace"
    bundle["metadata"]["description"] = "browsertrace"
    bundle["loop"]["name"] = "browsertrace"
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence_preferences missing browsertrace" in issue for issue in issues)


def test_alignment_traceability_counts_workflow_step_inputs_as_runtime_surface(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["workflow"]["steps"][0]["inputs"] = {"evidence_query": {"target_ids": ["browsertrace"]}}
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not any("evidence_preferences" in issue for issue in issues)
