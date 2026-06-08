from __future__ import annotations

from pathlib import Path

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import alignment_guidance_dir, alignment_system_prompt_asset_ref, load_alignment_guidance_assets
from loopora.system_prompt_assets import system_prompt_asset_path


def test_alignment_guidance_assets_are_internal_compiler_material() -> None:
    source_dir = alignment_guidance_dir()
    assert source_dir.exists()
    assert not (source_dir / "system-prompt.md").exists()
    assert system_prompt_asset_path(alignment_system_prompt_asset_ref()).is_file()
    assert not (Path(__file__).resolve().parents[3] / "skills" / "loopora-task-alignment").exists()

    assets = load_alignment_guidance_assets()
    assert assets.source_dir == source_dir
    assert_contains_all(
        assets.system_prompt_template,
        (
            "You are Loopora's built-in Web Loop alignment agent",
            "Important output discipline",
            "{{bundle_path}}",
            "{{stage_policy}}",
            "{{session_transcript_json}}",
        ),
    )
    assert_contains_all(
        assets.compiler_gates,
        (
            "Current compiler gate: clarifying",
            "Current compiler gate: confirmed agreement",
            "Before asking the user, answer anything you can from the transcript",
        ),
    )
    assert_contains_all(
        assets.compiler_policy,
        (
            "internal compiler flow",
            "not an external Skill workflow",
            "The background Agent drives semantic conversation",
            "Loopora backend owns phase acceptance",
            "Repairable issues may be fixed by the Agent",
            "Human-required issues must go back to conversation",
            "branch-aware pressure testing",
            "answer everything you can from the transcript",
            "Follow the user's chosen or corrected branch",
            "status-only checkpoints",
            "Agent as conversation driver",
            "Backend as compiler guard",
        ),
    )


def test_alignment_guidance_preserves_product_and_bundle_contracts() -> None:
    assets = load_alignment_guidance_assets()
    assert_contains_all(
        assets.product_primer,
        (
            "local-first platform for composing human-shaped governance loops",
            "human-in-the-loop -> human-shaped loop",
            "feedforward governance for slow-feedback work",
            "Control points are not control capability by themselves",
            "compile the user's task judgment into a runnable Loop candidate",
        ),
    )
    assert_contains_all(
        assets.alignment_playbook,
        (
            "Loopora fit gate",
            "Branch-aware pressure test",
            "Make control points decision-capable",
            "A status-only checkpoint is process theater",
            "confirm the working agreement, review the READY Loop",
            "agreement-to-bundle traceability checklist",
            "long-chain phase workflow",
            "Do not use arbitrary DAG language",
        ),
    )
    assert "confirm Loop" not in assets.alignment_playbook
    assert_contains_all(
        assets.bundle_contract,
        (
            "raw YAML document",
            "version: 1",
            "GateKeeper",
            "Proven, Weak, Unproven, Blocking, or Residual risk",
            "what they measure, what decision they trigger, and how they change later execution",
            "Default Web compiler bundles",
            "Do not emit nested Loops, arbitrary branch syntax",
            "`inputs.evidence_query` accepts structured selector keys",
            "Do not put explanatory prose, task instructions, or custom text keys inside `evidence_query`",
        ),
    )
    assert_contains_all(
        assets.system_prompt_template,
        (
            "`collaboration_summary` must open with why this task needs Loopora governance",
            "why final feedback is too late or costly to be the only control signal",
            "what new evidence, handoffs, repair/blocking decisions, or verdict context later rounds create",
        ),
    )
    assert "A control point that cannot change later execution is also role theater" in assets.system_prompt_template
    assert "workflow.steps[].inputs.evidence_query` accepts structured selector keys" in assets.system_prompt_template
    assert_contains_all(
        assets.quality_rubric,
        (
            "final feedback is too slow",
            "intermediate control points must measure a task-specific risk",
            "status-only milestones, reviews, or checkpoints",
        ),
    )


def test_alignment_system_prompt_uses_language_neutral_locale_guidance() -> None:
    assets = load_alignment_guidance_assets()
    prompt_surfaces = "\n".join([assets.system_prompt_template, assets.bundle_contract, assets.quality_rubric])
    expected_snippets = ("Apply the same language rule to every user language",
        "same user-facing language as the current task / agreement",
        "the task-specific part of each visible role name in the user's language",
        "Generated visible names should carry task-language semantics",
        "task phrase, risk label, or responsibility qualifier is not in the user's display language",
        "not one language's prose behind another language's labels",
        "merely appending `Builder`, `Inspector`, `GateKeeper`, `Guide`, or `Custom`",
    )
    assert_contains_all(prompt_surfaces, expected_snippets)
    for forbidden in (
        "For Chinese tasks",
        "Chinese-language tasks",
        "Chinese user's working agreement",
        "Chinese labels wrapped",
        "substantive task or alignment content is Chinese",
    ):
        assert forbidden not in prompt_surfaces


def test_alignment_improvement_guidance_resolves_refactor_critique_to_task_delta() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.feedback_improvement,
        (
            "Directional critique",
            "too conservative",
            "not enough refactor",
            "task-scoped refactor delta",
            "global style preference",
        ),
    )
    assert_contains_all(
        assets.examples,
        (
            "Improvement from vague refactor critique example",
            "这份 Loop 太保守，不够重构",
            "还不能直接生成改进 bundle",
            "复杂度只是换地方",
            "Inspector 无法复验",
            "而不是把“激进”保存成全局偏好",
        ),
    )


def test_alignment_examples_treat_overbroad_scope_as_auditable_deferral() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Overbroad scope with auditable deferral example",
            "一次重做移动端 onboarding",
            "首屏到完成注册作为第一轮 Proven success surface",
            "显式 deferred scope",
            "owner / follow-up / acceptance path",
            "不能在聊天里消失",
            "核心注册路径先证明，其他延期可审计",
        ),
    )


def test_alignment_examples_treat_benchmark_only_acceptance_as_not_fit() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Not-fit gate example: benchmark-only acceptance",
            "只要现有 benchmark 和单元测试全部通过就算完成",
            "硬检查驱动的直接 Agent 工作",
            "先不生成 Loop",
            "同一 benchmark / test harness 验收",
            "benchmark breakdown 决定下一轮优化方向",
            "禁止 benchmark-only shortcut",
        ),
    )


def test_alignment_examples_require_idempotent_notification_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Idempotent notification example",
            "重试或刷新后重复发送两封",
            "exactly one notification",
            "idempotency / duplicate-prevention",
            "audit evidence",
            "通知幂等 + 审计证据优先",
        ),
    )


def test_alignment_examples_require_privacy_redaction_evidence_for_sensitive_exports() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Sensitive export example",
            "客户数据 CSV 导出",
            "手机号、token 和个人信息必须脱敏",
            "不能把“文件能下载”当成成功",
            "privacy/secrets-redaction",
            "权限 + 脱敏 + 日志证据优先",
        ),
    )


def test_alignment_examples_require_data_import_validation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Data import validation example",
            "客户 CSV 批量导入",
            "字段映射正确",
            "partial failure 会生成 row-level error report",
            "不能把“happy path 样例 CSV 全部导入成功”当成客户批量导入完成",
            "data-import/validation-idempotency",
            "Import Contract Inspector",
            "Import Evidence Inspector",
            "字段映射 + 坏行报告 + 幂等重试证据优先",
        ),
    )


def test_alignment_examples_require_collaborative_edit_conflict_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Collaborative edit conflict example",
            "协作文档编辑",
            "不会 silent overwrite",
            "version conflict / optimistic locking",
            "不能把“单人保存成功”或“最后写入 wins”当成协作文档编辑完成",
            "concurrency/conflict-resolution",
            "Conflict Contract Inspector",
            "Conflict Evidence Inspector",
            "双用户冲突 + 离线重放 + 审计证据优先",
        ),
    )


def test_alignment_examples_require_price_cache_invalidation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Price cache invalidation example",
            "商品价格更新后的缓存失效",
            "CDN/Redis/read-model 缓存都在约定 TTL 内刷新",
            "不能把“数据库价格更新成功”或“手动刷新页面看到新价”当成商品价格缓存失效完成",
            "cache/invalidation-consistency",
            "Cache Contract Inspector",
            "Cache Freshness Inspector",
            "多入口 freshness + 旧价下单反证 + rollback 证据优先",
        ),
    )


def test_alignment_examples_require_inventory_reservation_consistency_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Inventory reservation consistency example",
            "checkout 加库存预留和下单防超卖",
            "reservation hold 有 TTL 到期释放",
            "不能把“单个用户 happy path 能下单”或“UI 显示库存减少”当成库存预留完成",
            "inventory/reservation-consistency",
            "Reservation Contract Inspector",
            "Reservation Evidence Inspector",
            "并发防超卖 + hold 释放 + webhook 幂等证据优先",
        ),
    )


def test_alignment_examples_require_usage_quota_metering_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Usage quota metering example",
            "SaaS API 加 usage metering 和 plan quota enforcement",
            "quota window / reset timezone 正确",
            "不能把“dashboard 显示用量”或“单次 API 调用被 429 阻断”当成 usage metering",
            "usage/quota-metering",
            "Quota Contract Inspector",
            "Quota Evidence Inspector",
            "并发计量 + 重复事件幂等 + reset/window 对账证据优先",
        ),
    )


def test_alignment_examples_require_tax_calculation_compliance_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Tax calculation compliance example",
            "checkout 加 sales tax / VAT / GST 计算",
            "US state nexus、EU VAT、GST",
            "不能把“checkout 显示一个 tax 数字”或“provider 返回一个 rate”当成 sales tax",
            "tax/calculation-compliance",
            "Tax Contract Inspector",
            "Tax Evidence Inspector",
            "jurisdiction matrix + exemption/reverse charge + ledger 对账证据优先",
        ),
    )


def test_alignment_examples_require_backup_restore_recovery_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Backup restore recovery example",
            "生产数据库做 backup / restore 和 disaster recovery",
            "RPO/RTO 目标有恢复演练证据",
            "不能把“backup job 显示成功”“生成一个 snapshot 文件”或“dashboard 绿色”当成 backup / restore",
            "backup/restore-recovery",
            "Recovery Contract Inspector",
            "Restore Evidence Inspector",
            "restore drill + PITR + checksum/row count 证据优先",
        ),
    )


def test_alignment_examples_require_search_index_consistency_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Search index consistency example",
            "知识库做全文搜索索引和重建",
            "reindex/backfill 可重跑且幂等",
            "不能把“本地搜索能返回一个公开文档”当成全文搜索索引完成",
            "search/index-consistency",
            "Search Index Contract Inspector",
            "Index Consistency Inspector",
            "增量索引 + ACL 负向 + reindex 幂等证据优先",
        ),
    )


def test_alignment_examples_require_cdc_replication_consistency_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "CDC replication consistency example",
            "Postgres 订单数据通过 CDC 同步到 warehouse 和 read model",
            "LSN / watermark / checkpoint 正确推进",
            "delete tombstone 处理正确",
            "不能把“sync job 绿色”“抽样 row count 一致”或“dashboard 显示 latest”当成 CDC 同步完成",
            "data/cdc-replication-consistency",
            "CDC Contract Inspector",
            "Replication Evidence Inspector",
            "backfill + checkpoint + replay + reconciliation 证据优先",
        ),
    )


def test_alignment_examples_require_file_upload_storage_safety_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "File upload storage safety example",
            "用户文件上传到对象存储",
            "MIME / content-type sniffing",
            "virus / malware scan",
            "不能把“upload 返回 URL”或“一个 happy path 文件上传成功”当成对象存储上传完成",
            "file-upload/storage-safety",
            "Upload Contract Inspector",
            "Storage Safety Inspector",
            "MIME + malware scan + signed URL + cleanup 证据优先",
        ),
    )


def test_alignment_examples_require_notification_deliverability_and_preferences_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Notification deliverability example",
            "lifecycle campaign email",
            "unsubscribe / preference center 生效",
            "suppression list、bounce、complaint 不会继续发送",
            "provider delivery event 能和本地 audit log 对账",
            "不能把“provider accepted”或“一个测试邮箱收到邮件”当成 lifecycle campaign email 完成",
            "notification/subscription-deliverability",
            "Notification Contract Inspector",
            "Deliverability Evidence Inspector",
            "订阅偏好 + suppression/bounce + delivery event 对账证据优先",
        ),
    )


def test_alignment_examples_require_scheduled_digest_timezone_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Scheduled digest timezone example",
            "weekly digest 定时发送",
            "timezone 本地周一 09:00",
            "DST / 夏令时切换前后",
            "不能把“cron expression 配好”或“本地触发一次”当成 weekly digest 完成",
            "schedule/timezone-recurrence",
            "Schedule Contract Inspector",
            "Schedule Evidence Inspector",
            "时区 + DST + catch-up + 幂等证据优先",
        ),
    )


def test_alignment_examples_require_migration_rollback_and_compatibility_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Migration rollback example",
            "旧 enum 迁到新的 state machine",
            "dry-run、row-count/checksum 和 rollback proof",
            "不能把“迁移代码写完”或“单元测试通过”当成成功",
            "migration/rollback-integrity",
            "compatibility/backward-compat",
            "Migration Integrity Inspector",
            "dry-run + checksum + rollback + 兼容证据优先",
        ),
    )


def test_alignment_examples_require_ai_quality_eval_and_human_review_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "AI quality evaluation example",
            "help-center semantic search",
            "Top-5 结果质量提升",
            "负例和回归样本",
            "relevance 和 hallucination risk",
            "不能把“一个 demo query 变好”或“单个 benchmark score 上涨”当成成功",
            "evaluation/eval-set",
            "quality/human-review",
            "Evaluation Baseline Inspector",
            "eval set + 人工评审 + 回归样本优先",
        ),
    )


def test_alignment_examples_require_incident_root_cause_and_monitoring_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Incident remediation example",
            "checkout 偶发重复扣款",
            "repro、root-cause proof 或 monitoring evidence",
            "不能把“打了一个 patch”或“现有测试通过”当成事故修复完成",
            "incident/root-cause-repro",
            "regression/monitoring-guard",
            "Repro Inspector",
            "复现 + 根因 + 回归 + 监控证据优先",
        ),
    )


def test_alignment_examples_require_feature_flag_rollout_safety_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Feature flag rollout safety example",
            "新版 checkout 放到 feature flag 后灰度发布",
            "默认关闭，只有 beta cohort 命中",
            "kill switch 能立即回退",
            "不能把“本地 flag 能打开新版 checkout”当成灰度发布完成",
            "release/feature-flag-rollout",
            "Rollout Contract Inspector",
            "Rollout Safety Inspector",
            "cohort + kill switch + monitoring 证据优先",
        ),
    )


def test_alignment_examples_require_external_provider_contract_and_resilience_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "External provider resilience example",
            "shipping quote provider API",
            "sandbox provider contract 能返回真实 rate",
            "timeout、rate limit、retry/backoff 和 fallback",
            "不能把“mock response 通过”或“一次 happy path API call 成功”当成 provider 集成完成",
            "external/provider-contract",
            "resilience/retry-timeout",
            "Provider Contract Inspector",
            "sandbox contract + auth + resilience 证据优先",
        ),
    )


def test_alignment_examples_require_payment_webhook_ordering_and_ledger_reconciliation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Payment webhook reconciliation example",
            "Stripe subscription webhook",
            "webhook signature 验证",
            "provider event replay 可以恢复本地 ledger",
            "不能把“一个 webhook happy path 更新 invoice 状态”或 mock event 通过当成订阅账单接入完成",
            "webhook/signature-replay-ordering",
            "billing/ledger-reconciliation",
            "Webhook Contract Inspector",
            "Ledger Reconciliation Inspector",
            "签名 + 乱序/replay + ledger 对账证据优先",
        ),
    )


def test_alignment_examples_require_payout_settlement_reconciliation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Marketplace payout settlement example",
            "marketplace seller payout",
            "seller balance ledger",
            "不会 double payout",
            "不能把“Stripe dashboard 显示 paid”“一笔 test payout 成功”或“UI 显示余额减少”当成 marketplace payout 完成",
            "payout/settlement-reconciliation",
            "Payout Contract Inspector",
            "Settlement Evidence Inspector",
            "seller ledger + payout batch + provider/bank 对账证据优先",
        ),
    )


def test_alignment_examples_require_mrr_metric_reconciliation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "MRR metric reconciliation example",
            "MRR dashboard",
            "MRR/ARR 指标口径固定",
            "historical backfill 不改旧月锁账",
            "不能把“图表显示数字”或“CSV 能导出”当成 MRR dashboard 完成",
            "reporting/metric-reconciliation",
            "Metric Contract Inspector",
            "Metric Reconciliation Inspector",
            "指标口径 + 对账 + 锁账回填证据优先",
        ),
    )


def test_alignment_examples_require_tenant_isolation_negative_access_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Tenant isolation example",
            "workspace sharing 权限",
            "direct object ID 访问 Org B dashboard",
            "不能把“owner happy path 能打开”当成权限功能完成",
            "access/tenant-isolation",
            "Access Matrix Inspector",
            "Tenant Isolation Inspector",
            "跨租户负向证据 + 角色矩阵 + 审计优先",
        ),
    )


def test_alignment_examples_require_data_residency_regional_isolation_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Data residency regional isolation example",
            "data residency / regional isolation",
            "primary DB、object storage、search index、cache、queue、backup、logs、analytics export",
            "third-party processor",
            "不能把“UI 显示 region=EU”“配置 env var”或“tenant 表有 region 字段”当成 data residency",
            "data/residency-regional-isolation",
            "Residency Contract Inspector",
            "Residency Evidence Inspector",
            "数据驻留边界 + wrong-region 负向 + processor/DPA 证据优先",
        ),
    )


def test_alignment_examples_require_sso_assertion_and_provisioning_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "SSO identity assertion example",
            "SAML/OIDC SSO",
            "IdP metadata 和 assertion signature 验证正确",
            "tenant domain binding 防止 A 公司 assertion 登录 B 公司",
            "不能把“一个 Okta 测试用户能登录”当成企业 SSO 完成",
            "identity/sso-assertion",
            "identity/provisioning-role-mapping",
            "Identity Contract Inspector",
            "Identity Evidence Inspector",
            "assertion + tenant binding + role mapping 证据优先",
        ),
    )


def test_alignment_examples_require_password_reset_token_lifecycle_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Password reset token lifecycle example",
            "password reset",
            "reset token 是一次性且有 expiry",
            "旧 session / refresh token 全部失效",
            "不能把“邮件发出”或“happy path 重置成功”当成 password reset 完成",
            "auth/session-token-lifecycle",
            "Token Contract Inspector",
            "Token Lifecycle Inspector",
            "token lifecycle + replay + session revocation 证据优先",
        ),
    )


def test_alignment_examples_require_key_rotation_secret_lifecycle_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "API key rotation lifecycle example",
            "service account secret 做 rotation",
            "old key 和 new key 有受控 overlap window",
            "revoked key 不能继续调用",
            "只有 UI 显示生成了新 key",
            "security/key-rotation-lifecycle",
            "Key Rotation Contract Inspector",
            "Rotation Evidence Inspector",
            "overlap + revoke + scope/tenant + storage 证据优先",
        ),
    )


def test_alignment_examples_require_audit_log_integrity_retention_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Compliance audit trail example",
            "compliance audit trail",
            "append-only audit log",
            "tamper-evident hash chain 或 WORM storage",
            "不能把“数据库表里有一行记录”“console log 打出来”或“UI history 显示一条操作”当成 compliance audit trail 完成",
            "audit/log-integrity-retention",
            "Audit Contract Inspector",
            "Audit Evidence Inspector",
            "append-only + tamper evidence + retention/export 证据优先",
        ),
    )


def test_alignment_examples_require_accessibility_and_locale_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Accessibility checkout example",
            "checkout modal",
            "focus trap 不会丢焦点",
            "screen reader / ARIA label",
            "WCAG contrast",
            "中英文界面操作语义一致",
            "不能把“视觉截图”或“鼠标 happy path 通过”当成 checkout modal 完成",
            "accessibility/a11y",
            "locale/i18n",
            "Accessibility Contract Inspector",
            "Accessibility Evidence Inspector",
            "键盘 + 读屏 + locale parity 证据优先",
        ),
    )


def test_alignment_examples_require_data_lifecycle_deletion_retention_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Data lifecycle deletion example",
            "GDPR account erasure",
            "主库、搜索索引、缓存和导出报表里都没有 PII",
            "retention exception",
            "不能把“settings 页面显示 deleted”或“用户表软删除”当成 account erasure 完成",
            "data-lifecycle/deletion-retention",
            "Data Map Inspector",
            "Lifecycle Evidence Inspector",
            "PII 扩散面 + retention exception + 异步清理证据优先",
        ),
    )


def test_alignment_examples_require_analytics_event_and_experiment_integrity_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Analytics instrumentation example",
            "analytics instrumentation 和 A/B experiment exposure",
            "每一步事件 schema 正确",
            "dashboard 或 warehouse 查询能和真实事件对账",
            "不能把“按钮可点”、`console.log` 或 mock analytics call 当成 instrumentation 完成",
            "analytics/event-integrity",
            "experiment/assignment-consistency",
            "Instrumentation Contract Inspector",
            "Event Integrity Inspector",
            "事件 schema + 实验曝光 + 数仓对账证据优先",
        ),
    )


def test_alignment_examples_require_async_job_lifecycle_and_queue_recovery_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Async job queue example",
            "async job queue",
            "pending / running / succeeded / failed 状态",
            "dead-letter queue 或可恢复队列",
            "不能把“按钮显示 queued”或“本地 happy path 生成文件”当成 async export 完成",
            "async/job-lifecycle",
            "queue/failure-recovery",
            "Queue Contract Inspector",
            "Job Lifecycle Inspector",
            "job lifecycle + worker + failure recovery 证据优先",
        ),
    )
