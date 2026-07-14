# Loopora Domain Workflow Contracts

This document carries task-domain workflow routing contracts that are product/compiler evidence, but too detailed for `contracts.md`. Keep the core product claims in `contracts.md`; update this file when task-domain routing, phase-scoped role projection, or secondary-object precedence changes.

Task-domain recognition is a shared compiler boundary: `executor_alignment_task_predicates.py` owns the predicate logic used by both working-agreement routing and bundle workflow routing. Compatibility alias modules must not reimplement or fork those regular expressions.

## Stable Claim

Loopora routes a task by its primary success surface and fake-done risk. Domain-specific workflows are not a taxonomy for its own sake: they protect users from shallow plans that mention a risky object but fail to project the required evidence path into the working agreement, runnable roles, step inputs, and GateKeeper fan-in.

## Long-Chain Routing

Confirmed long-chain workflows must project phase-scoped judgment into the working agreement and runnable surfaces too: spec, role prompts, step inputs, evidence buckets, marker-specific local governance responsibilities, and GateKeeper fan-in carry the same agreement, not only a longer role list.

| Task domain | Required evidence shape |
| --- | --- |
| RAG grounding / tool safety | RAG contract inspection -> corpus ingestion -> retrieval ACL -> answer/tool gating -> evaluation inspection -> evidence hardening -> GateKeeper fan-in |
| CDC replication consistency | CDC contract inspection -> parallel replication-evidence and reconciliation/lag evidence -> GateKeeper |
| Metric reporting reconciliation | Metric contract inspection -> parallel metric-reconciliation and permission/backfill evidence -> GateKeeper |
| Payout settlement reconciliation | Payout contract inspection -> parallel settlement-reconciliation and access/idempotency evidence -> GateKeeper |
| Dispute / chargeback lifecycle | Dispute contract inspection -> parallel dispute-evidence and ledger/notification evidence -> GateKeeper |
| Schedule/timezone recurrence | Schedule contract inspection -> digest scheduler builder -> parallel temporal-correctness and delivery-audit evidence -> GateKeeper |
| Data residency / regional isolation | Residency contract inspection -> regional-isolation builder -> residency evidence inspection -> GateKeeper |
| Support impersonation / break-glass access | Policy inspection -> break-glass builder -> access evidence inspection -> GateKeeper |
| Support ticket SLA escalation | Support-ticket contract inspection -> ticket SLA builder -> parallel ticket-lifecycle and access/notification/audit evidence -> GateKeeper |
| B2B subscription entitlement / proration | Subscription contract inspection -> entitlement billing builder -> parallel entitlement-state and billing-proration reconciliation evidence -> GateKeeper |
| DSAR / subject access data export | DSAR export contract inspection -> privacy export builder -> parallel export-scope and access/retention/audit evidence -> GateKeeper |

Secondary objects are evidence surfaces, not routing owners. For example, NRR stays metric semantics rather than data-lifecycle deletion/retention; KYC hold and chargeback orders stay payout settlement state/input rather than KYC onboarding or dispute lifecycle; customer notification and payout hold/release stay dispute evidence surfaces rather than notification or payout as the main task.

The same rule applies to common distractors: provider webhooks, ledgers, invoices, CSVs, dashboards, caches, audit logs, SSO assertions, API keys, refunds, receipts, tax reports, rate limits, migration/rollback markers, replay/checkpoint/order/reconciliation terms, or event names like `email_submitted` must not steal routing from the task's primary success surface and fake-done risk.

Specific precedence examples:

- Schedule/timezone recurrence owns notification provider delivery, subscription filters, queue backlog, retry/replay, audit, monitoring, migration, and locale filters as schedule evidence.
- Database schema migration owns expand-contract rollout, backfill, rollback, data-consistency checks, audit, and monitoring as migration evidence rather than feature-flag rollout evidence.
- CDC replication consistency owns schema evolution, snapshot/backfill, checkpoints, replay, idempotency, lag alerts, reconciliation, dashboard/latest state, and sync-job status as replication evidence rather than database-migration, generic task, or metric/dashboard evidence.
- Metric reporting reconciliation owns subscription-provider reconciliation, historical backfill, locked-month proof, export consistency, and audit records as metric evidence rather than audit-log or database-migration evidence.
- Data residency / regional isolation owns backup, search, analytics, audit, export, processor/DPA, key-region, failover, migration, monitoring, permission, and local governance as residency evidence.
- Support impersonation / break-glass access owns auth sessions, permission, tenant isolation, privacy redaction, audit integrity, data export, monitoring, eval-set fixtures, revoke/expiry, and local governance as break-glass evidence.
- Support ticket SLA escalation owns notification delivery, queue backlog, permission checks, tenant isolation, audit notes, PII redaction, and monitoring as ticket/SLA evidence.
- B2B subscription entitlement / proration owns provider checkout, webhooks, quota/history, notification, tax words, invoices, ledgers, provider totals, audit, rollback, and monitoring as subscription evidence.
- DSAR / subject access data export owns CSV/download, dashboard-ready state, notification dedupe, rate limiting, audit, signed URL delivery, retention/legal hold, async jobs, monitoring, and local governance as export evidence.

## Evidence Boundary

| Boundary | Stable claim | Primary code and assets | Verification | Not a contract |
| --- | --- | --- | --- | --- |
| Domain workflow routing | Primary task domains such as RAG grounding, CDC replication, metric reconciliation, payout settlement, disputes, schedule/timezone recurrence, data residency, break-glass access, support-ticket SLA, B2B entitlement/proration, and DSAR export must keep their contract-first evidence shape instead of collapsing into a generic repair chain. | `alignment_traceability_domain_patterns.py`, `alignment_traceability_categories.py`, `alignment_traceability_risk_categories.py`, `service_alignment_traceability_projection.py`, `executor_alignment_task_projection.py`, `executor_alignment_task_projection_scope.py`, `src/loopora/assets/alignment/task-domain-projection.json`, `src/loopora/assets/alignment/task-role-fixtures.json`, `src/loopora/assets/alignment/task-spec-workflow-notes.json`, `src/loopora/assets/alignment/task-spec-scaffold-templates.json`, `src/loopora/assets/alignment/task-visible-scaffolds.json`, `src/loopora/assets/alignment/specialized-workflow-display-names.json`, `src/loopora/assets/alignment/task-workflow-intents.json` | Domain-specific alignment tests, prompt example-selection tests, task-role fixture governance tests, executor alignment fixture architecture tests | Exact role display text, every possible business domain, or current fixture prose as permanent product copy |
| Secondary-object precedence | Secondary words like dashboards, providers, CSVs, queues, notifications, audits, refunds, receipts, or migration terms cannot steal routing from a more specific main task domain. | `alignment_traceability_*`, `service_alignment_traceability_projection.py`, alignment guidance assets | Task-domain projection and domain-specific regression tests | Treating keyword order, exact synonym lists, or prompt examples as the stable routing algorithm |

## Maintenance Rule

When adding a new high-risk task domain, update the routing evidence in code/assets and add focused contract tests for the user-observable bundle shape before extending this document. If a domain is only an example with no stable routing behavior, keep it in guidance assets or tests rather than this design boundary.
