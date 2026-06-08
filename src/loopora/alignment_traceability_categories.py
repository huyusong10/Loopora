from __future__ import annotations

"""Traceability category classifiers for alignment agreement and Agent candidates."""

import re

from loopora.alignment_traceability_domain_patterns import (
    ACCESSIBILITY_A11Y_PATTERN,
    ANALYTICS_EVENT_INTEGRITY_PATTERN,
    AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
    ASYNC_JOB_LIFECYCLE_PATTERN,
    AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
    BACKUP_RESTORE_RECOVERY_PATTERN,
    BACKWARD_COMPATIBILITY_PATTERN,
    BILLING_LEDGER_RECONCILIATION_PATTERN,
    CACHE_INVALIDATION_CONSISTENCY_PATTERN,
    CDC_REPLICATION_CONSISTENCY_PATTERN,
    CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
    CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
    DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
    DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
    DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
    DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
    EVALUATION_SET_PATTERN,
    EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
    EXTERNAL_PROVIDER_CONTRACT_PATTERN,
    FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
    FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
    HUMAN_REVIEW_QUALITY_PATTERN,
    IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    IDENTITY_SSO_ASSERTION_PATTERN,
    INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
    INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
    KYC_AML_SANCTIONS_SCREENING_PATTERN,
    KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    LOCALE_I18N_PATTERN,
    METRIC_REPORTING_RECONCILIATION_PATTERN,
    MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
    NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
    PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
    QUEUE_FAILURE_RECOVERY_PATTERN,
    RAG_GROUNDING_TOOL_SAFETY_PATTERN,
    REGRESSION_MONITORING_GUARD_PATTERN,
    RESILIENCE_RETRY_TIMEOUT_PATTERN,
    SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
    SEARCH_INDEX_CONSISTENCY_PATTERN,
    SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
    SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
    TAX_CALCULATION_COMPLIANCE_PATTERN,
    TENANT_ISOLATION_PATTERN,
    USAGE_QUOTA_METERING_PATTERN,
    WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
)
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories as agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories as agent_candidate_fake_done_categories,
)


def agent_candidate_tradeoff_categories(task_text: str) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_tradeoff_markers = (
        r"\b(?:proof|evidence|verify|verification)\b.{0,80}\b(?:over|before|rather than|instead of)\b.{0,80}\b(?:speed|fast|quick|polish|ui|narrative|story)\b",
        r"\b(?:speed|fast|quick|polish|ui|narrative|story)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:proof|evidence|verify|verification)\b",
        r"\b(?:strict|blocking|block|reject|fail closed)\b.{0,80}\b(?:over|before|rather than|instead of|beats?)\b.{0,80}\b(?:pragmatic|pragmatism|progress)\b",
        r"\b(?:pragmatic|pragmatism|progress)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:strict|blocking|block|reject|fail closed)\b",
        r"\b(?:prioriti[sz]e|prefer)\b.{0,80}\b(?:proof|evidence|verify|verification|blocking|fail closed)\b",
        r"\b(?:block|reject|fail closed)\b.{0,80}\b(?:fake[- ]?done|fake completion|polished-looking|narrative)\b",
        r"(?:优先|先).{0,24}(?:证明|证据|验证|阻断)",
        r"(?:证明|证据|验证|阻断).{0,24}(?:优先|先于|高于)",
        r"(?:严格|阻断|拒绝).{0,20}(?:优先|先于|高于).{0,20}(?:务实|推进|进度)",
        r"(?:务实|推进|进度).{0,20}(?:等|让位|后于).{0,20}(?:严格|阻断|拒绝)",
        r"(?:先别|不要|别).{0,16}(?:美化|润色|打磨|漂亮|界面)",
        r"(?:阻断|拒绝).{0,20}(?:假完成|漂亮叙事|证据不足)",
    )
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_tradeoff_markers):
        return []
    category_patterns = (
        (
            "proof/evidence",
            r"\b(?:proof|prove|proven|evidence|verify|verification)\b|证明|证据|验证|已证明",
        ),
        (
            "speed/polish",
            r"\b(?:speed|fast|quick|polish|ui|narrative|story|pretty|polished-looking)\b|速度|快速|美化|润色|打磨|界面|漂亮|叙事",
        ),
        (
            "blocking/fake-completion",
            r"\b(?:block|blocking|reject|fail closed|fake[- ]?done|fake completion|unproven|weak)\b|阻断|拒绝|假完成|未证明|弱证据|证据不足",
        ),
        (
            "pragmatic/progress",
            r"\b(?:pragmatic|pragmatism|progress)\b|务实|推进|进度",
        ),
    )
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_has_labeled_execution_strategy(task_text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:execution strategy|priority|priorities|priority order|next round|next pass)\b|执行策略|优先级|下一轮|下一步",
            str(task_text or ""),
            re.IGNORECASE,
        )
    )


def agent_candidate_execution_strategy_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_strategy_markers = (
        r"\b(?:execution strategy|next round|next pass|priority|priorities)\b",
        r"\b(?:first|before|then|after|defer|prioriti[sz]e|start with|do not start|don't start|avoid)\b",
        r"(?:执行策略|下一轮|下一步|优先级|优先|先|再|然后|之后|暂缓|推迟|先别|不要先|别先)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_strategy_markers):
        return []
    category_patterns = (
        (
            "repair/root-cause",
            r"\b(?:root[- ]?cause|regression|failure|failing|bug)\b|根因|故障|失败|回归|缺陷",
        ),
        (
            "evidence/proof",
            r"\b(?:proof|prove|proven|evidence|verify|verification|audit|test|tests)\b|证明|证据|验证|审计|测试|已证明",
        ),
        (
            "scope/narrow",
            r"\b(?:scope|narrow|focused|focus|small|minimal|limit|bounded)\b|范围|收窄|聚焦|小而|最小|有限",
        ),
        (
            "expand/breadth",
            r"\b(?:expand|expansion|broaden|broad|breadth|new feature|dashboard|report)\b|扩展|扩大|铺开|宽泛|新功能|看板|报表",
        ),
        (
            "polish/ui",
            r"\b(?:polish|ui|visual|pretty|styling|copy|narrative|story)\b|美化|打磨|润色|界面|视觉|文案|叙事|漂亮",
        ),
    )
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_residual_risk_policy_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_policy_markers = (
        r"\bresidual risks?\b",
        r"\bremaining risks?\b",
        r"残余风险",
        r"剩余风险",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_policy_markers):
        return []
    no_acceptance_pattern = (
        r"\b(?:no|none|zero)\b.{0,60}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
        r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,60}\baccept\b.{0,60}\bresidual risks?\b"
        r"|(?:不接受|不能接受|不可接受|不允许).{0,24}残余风险"
        r"|残余风险.{0,24}(?:不接受|不能接受|不可接受|不允许)"
    )
    categories: list[tuple[str, str]] = [
        ("residual-risk", r"\bresidual risks?\b|\bremaining risks?\b|残余风险|剩余风险"),
    ]
    if re.search(no_acceptance_pattern, text, re.IGNORECASE):
        categories.append(
            (
                "no-accepted-residual-risk",
                (
                    r"\b(?:no|none|zero)\b.{0,80}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
                    r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,80}\baccept\b.{0,80}\bresidual risks?\b"
                    r"|(?:不接受|不能接受|不可接受|不允许).{0,30}残余风险"
                    r"|残余风险.{0,30}(?:不接受|不能接受|不可接受|不允许)"
                ),
            )
        )
        return categories
    category_patterns = (
        (
            "acceptance",
            r"\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,160}"
                r"(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r"|(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r".{0,160}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "owner/follow-up",
            (
                r"\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解"
            ),
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解)"
                r"|(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "fail-closed",
            r"\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r"|(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
    )
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in category_patterns
        if re.search(task_pattern, text, re.IGNORECASE)
    )
    return categories


def agent_candidate_success_surface_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_success_markers = (
        r"\bsuccess\s+(?:means|requires|is)\b",
        r"\bdone when\b",
        r"\bcomplete when\b",
        r"\bacceptance criteria\b",
        r"\bto pass\b.{0,80}\b(?:must|needs?|should|requires?)\b",
        r"\b(?:must|needs?|should|requires?)\b.{0,80}\b(?:pass|succeed|be complete|be done)\b",
        r"成功.{0,16}(?:必须|需要|应当|要).{0,16}(?:证明|验证|包含|包括)",
        r"成功(?:标准|意味着|要求|面)",
        r"完成(?:标准|条件|时)",
        r"验收(?:标准|条件)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_success_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "success/done-when",
            r"\b(?:success|done when|acceptance criteria|complete when|completion criteria)\b|成功|完成标准|验收",
        ),
    ]
    category_patterns = (
        (
            "actor/user-facing-outcome",
            r"\b(?:user|customer|admin|operator|buyer|merchant|support)\b|用户|客户|管理员|运营|买家|商家|客服",
        ),
        (
            "notification/message",
            r"\b(?:notification|notify|email|message|receipt|alert)\b|通知|邮件|消息|回执|提醒",
        ),
        (
            "idempotency/duplicate-prevention",
            r"\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once|one\s+time)\b|重复|去重|幂等|只发一次|仅发一次|只.*一次|仅.*一次",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace|recorded|records?)\b|审计|日志|账本|记录|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access|role|acl|access[- ]?control|"
            r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?)\b|权限|授权|访问|角色|ACL|权限过滤|访问控制",
        ),
        (
            "access/authorization-policy-consistency",
            AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "migration/rollback-integrity",
            MIGRATION_ROLLBACK_INTEGRITY_PATTERN,
        ),
        (
            "compatibility/backward-compat",
            BACKWARD_COMPATIBILITY_PATTERN,
        ),
        (
            "evaluation/eval-set",
            EVALUATION_SET_PATTERN,
        ),
        (
            "quality/human-review",
            HUMAN_REVIEW_QUALITY_PATTERN,
        ),
        (
            "ai/rag-grounding-tool-safety",
            RAG_GROUNDING_TOOL_SAFETY_PATTERN,
        ),
        (
            "incident/root-cause-repro",
            INCIDENT_ROOT_CAUSE_REPRO_PATTERN,
        ),
        (
            "regression/monitoring-guard",
            REGRESSION_MONITORING_GUARD_PATTERN,
        ),
        (
            "release/feature-flag-rollout",
            FEATURE_FLAG_ROLLOUT_SAFETY_PATTERN,
        ),
        (
            "external/provider-contract",
            EXTERNAL_PROVIDER_CONTRACT_PATTERN,
        ),
        (
            "compliance/kyc-aml-sanctions-screening",
            KYC_AML_SANCTIONS_SCREENING_PATTERN,
        ),
        (
            "resilience/retry-timeout",
            RESILIENCE_RETRY_TIMEOUT_PATTERN,
        ),
        (
            "access/tenant-isolation",
            TENANT_ISOLATION_PATTERN,
        ),
        (
            "data/residency-regional-isolation",
            DATA_RESIDENCY_REGIONAL_ISOLATION_PATTERN,
        ),
        (
            "access/support-impersonation-breakglass",
            SUPPORT_IMPERSONATION_BREAKGLASS_PATTERN,
        ),
        (
            "file-upload/storage-safety",
            FILE_UPLOAD_STORAGE_SAFETY_PATTERN,
        ),
        (
            "data-import/validation-idempotency",
            DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN,
        ),
        (
            "concurrency/conflict-resolution",
            CONCURRENCY_CONFLICT_RESOLUTION_PATTERN,
        ),
        (
            "inventory/reservation-consistency",
            INVENTORY_RESERVATION_CONSISTENCY_PATTERN,
        ),
        (
            "usage/quota-metering",
            USAGE_QUOTA_METERING_PATTERN,
        ),
        (
            "billing/subscription-entitlement-proration",
            SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN,
        ),
        (
            "tax/calculation-compliance",
            TAX_CALCULATION_COMPLIANCE_PATTERN,
        ),
        (
            "backup/restore-recovery",
            BACKUP_RESTORE_RECOVERY_PATTERN,
        ),
        (
            "data/cdc-replication-consistency",
            CDC_REPLICATION_CONSISTENCY_PATTERN,
        ),
        (
            "audit/log-integrity-retention",
            AUDIT_LOG_INTEGRITY_RETENTION_PATTERN,
        ),
        (
            "cache/invalidation-consistency",
            CACHE_INVALIDATION_CONSISTENCY_PATTERN,
        ),
        (
            "search/index-consistency",
            SEARCH_INDEX_CONSISTENCY_PATTERN,
        ),
        (
            "data-lifecycle/deletion-retention",
            DATA_LIFECYCLE_DELETION_RETENTION_PATTERN,
        ),
        (
            "privacy/consent-preference-governance",
            CONSENT_PREFERENCE_GOVERNANCE_PATTERN,
        ),
        (
            "analytics/event-integrity",
            ANALYTICS_EVENT_INTEGRITY_PATTERN,
        ),
        (
            "experiment/assignment-consistency",
            EXPERIMENT_ASSIGNMENT_CONSISTENCY_PATTERN,
        ),
        (
            "async/job-lifecycle",
            ASYNC_JOB_LIFECYCLE_PATTERN,
        ),
        (
            "queue/failure-recovery",
            QUEUE_FAILURE_RECOVERY_PATTERN,
        ),
        (
            "schedule/timezone-recurrence",
            SCHEDULE_TIMEZONE_RECURRENCE_PATTERN,
        ),
        (
            "webhook/signature-replay-ordering",
            WEBHOOK_SIGNATURE_REPLAY_ORDERING_PATTERN,
        ),
        (
            "billing/ledger-reconciliation",
            BILLING_LEDGER_RECONCILIATION_PATTERN,
        ),
        (
            "payment/dispute-chargeback-lifecycle",
            DISPUTE_CHARGEBACK_LIFECYCLE_PATTERN,
        ),
        (
            "payout/settlement-reconciliation",
            PAYOUT_SETTLEMENT_RECONCILIATION_PATTERN,
        ),
        (
            "reporting/metric-reconciliation",
            METRIC_REPORTING_RECONCILIATION_PATTERN,
        ),
        (
            "identity/sso-assertion",
            IDENTITY_SSO_ASSERTION_PATTERN,
        ),
        (
            "identity/provisioning-role-mapping",
            IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
        ),
        (
            "auth/session-token-lifecycle",
            AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
        ),
        (
            "security/key-rotation-lifecycle",
            KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
        ),
        (
            "notification/subscription-deliverability",
            NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
        ),
        (
            "privacy/secrets-redaction",
            (
                r"\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|"
                r"password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b"
                r"|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证"
            ),
        ),
        (
            "accessibility/a11y",
            ACCESSIBILITY_A11Y_PATTERN,
        ),
        (
            "locale/i18n",
            LOCALE_I18N_PATTERN,
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE))
    return categories
