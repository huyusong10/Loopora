from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from alignment_test_support import _wait_for_status
from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import bundle_to_yaml, lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor import FakeCodexExecutor
from loopora.executor_alignment_responses import alignment_response
from loopora.executor_fake_payloads import alignment_bundle_yaml


CONSENT_GOVERNANCE_TASK_TEXT = (
    "我要做 GDPR/CCPA consent and preference center。成功必须证明 cookie consent、marketing opt-in、"
    "email/SMS/push preferences、tracking purposes 和 third-party vendor consent 都按 region 生效；"
    "consent version、policy version、purpose id、legal basis、source、timestamp、IP/user agent 和 "
    "withdrawal 都有 immutable audit log；用户 withdraw consent 后 analytics event、marketing campaign、"
    "data export 和 vendor sync 都立即停止或更新，double opt-in、unsubscribe、suppression list、DSAR export "
    "和 deletion request 与 consent ledger 对账，未登录用户 cookie consent 能和登录后 account preference merge；"
    "监控要发现 consent drift、vendor mismatch、tracking without consent、stale preference cache 和 "
    "re-consent required；只有 cookie banner 显示、checkbox 保存成功或 localStorage 有 consent=true 必须阻断。"
)

CONSENT_GOVERNANCE_CHECKLIST = {
    "loop_fit": True,
    "task_scope": True,
    "success_surface": True,
    "fake_done_risks": True,
    "evidence_preferences": True,
    "execution_strategy": True,
    "residual_risk_policy": True,
    "judgment_tradeoffs": True,
    "local_governance": True,
    "role_posture": True,
    "workflow_shape": True,
}

CONSENT_GOVERNANCE_EVIDENCE = {
    "loop_fit": (
        "这项 consent and preference center 需要 Loopora，因为 purpose/version/legal basis、withdrawal enforcement、"
        "vendor sync、analytics/marketing/export suppression、DSAR/deletion 对账、anonymous-to-account merge、cache invalidation "
        "和 monitoring 会分别产生新的 proof 与 handoff；只靠 one Agent pass、直接聊天、one-off 处理或最终人工 review "
        "会太晚发现 tracking without consent、vendor mismatch 或 consent drift。"
    ),
    "task_scope": (
        "范围限定为 GDPR/CCPA consent and preference center 的同意账本和偏好治理；不扩展到普通 email unsubscribe、"
        "完整隐私平台重写或非同意相关营销页面。"
    ),
    "success_surface": (
        "成功面是 cookie consent、marketing opt-in、email/SMS/push preferences、tracking purposes、vendor consent、"
        "region rules、consent/policy version、purpose id、legal basis、withdrawal、immutable audit、vendor sync、"
        "double opt-in、unsubscribe、suppression list、DSAR export、deletion request、account preference merge、cache 和 monitoring evidence 可验证。"
    ),
    "fake_done_risks": (
        "必须拒绝只实现 cookie banner、checkbox save 或 localStorage consent=true；如果没有 consent ledger、purpose/legal basis、"
        "withdrawal enforcement、vendor sync、analytics/marketing/data export/report blocking、audit、cache、DSAR/deletion reconciliation "
        "和 monitoring proof，必须阻断。"
    ),
    "evidence_preferences": (
        "可信证据是 consent ledger fixtures、purpose/legal-basis contract、withdrawal cases、vendor sync proof、"
        "analytics/marketing/export suppression proof、double opt-in/unsubscribe/suppression reconciliation、DSAR/deletion reconciliation、"
        "anonymous-cookie/account-preference merge proof、stale-cache negatives、consent drift/vendor mismatch/tracking-without-consent alerts，"
        "以及 Proven、Weak、Unproven、Blocking 和 Residual risk buckets。"
    ),
    "execution_strategy": (
        "先由只读 consent contract inspection 固定 purpose、region、version、legal basis、withdrawal、vendor、marketing/tracking、"
        "DSAR/deletion 和 audit ledger 样本，再实现偏好中心与同步；evidence inspection 暴露 Weak 或 Blocking proof 后，GateKeeper 再裁决。"
    ),
    "residual_risk_policy": (
        "轻微偏好中心文案或非关键通知 polish 可作为 Residual risk 留下并指定 owner；缺少 purpose/version/legal-basis、withdrawal、"
        "vendor sync、analytics/marketing/export suppression、audit/cache、DSAR/deletion、merge、monitoring 或 local-governance proof 时必须 fail closed。"
    ),
    "judgment_tradeoffs": (
        "严格 privacy proof 优先于快速上线 banner；宁可先交窄而可审计的 consent ledger 和 withdrawal enforcement，"
        "也不要 cookie banner demo 掩盖跟踪、营销或 vendor 合规风险。"
    ),
    "local_governance": (
        "项目本地 marker 包含 AGENTS.md、design/README.md、design/ 和 tests/；Builder 要先读取它们，"
        "Inspector 验证相关 design/test obligation，GateKeeper 把跳过治理视为 Weak、Unproven 或 Blocking。"
    ),
    "role_posture": (
        "同意契约 Inspector 固定同意账本和负向样本；Preference Governance Builder 只实现这些治理边界；"
        "Consent Evidence Inspector 验证 withdrawal、vendor、analytics/marketing/export suppression、DSAR/deletion、merge、cache 和 monitoring；"
        "GateKeeper 对 banner/checkbox/localStorage-only 或 weak-proof 状态 fail closed。"
    ),
    "workflow_shape": (
        "workflow 先做只读 consent contract inspection，再 Builder，再 evidence inspection，再 GateKeeper；"
        "Evidence Inspector 的 review 会作为 GateKeeper fan-in，防止 banner、checkbox 或 localStorage-only 结果绕过证据裁决。"
    ),
    "workdir_facts": "已观察到 AGENTS.md、design/README.md、design/、tests/ 和 README.md；具体实现栈仍未知。",
    "open_questions": "无未解决问题",
}


def _consent_role_definition(key: str, name: str, archetype: str, body: str, posture: str) -> dict:
    return {
        "key": key,
        "name": name,
        "description": body,
        "archetype": archetype,
        "prompt_ref": f"{key}.md",
        "prompt_markdown": (
            f"---\nversion: 1\narchetype: {archetype}\n---\n\n{body} "
            "使用 Proven、Weak、Unproven、Blocking 和 Residual risk buckets。"
            "当 AGENTS.md、design/README.md、design/ 和 tests/ 存在时必须尊重这些本地治理来源，且不能编造其内容。"
        ),
        "posture_notes": posture,
        "executor_kind": "codex",
        "executor_mode": "preset",
        "command_cli": "",
        "command_args_text": "",
        "model": "",
        "reasoning_effort": "",
    }


def consent_governance_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    bundle["metadata"]["name"] = "Consent 偏好治理"
    bundle["metadata"]["description"] = "治理 GDPR/CCPA consent ledger、withdrawal、vendor sync、DSAR/deletion、cache 和 monitoring 证据。"
    bundle["loop"]["name"] = "Consent 偏好治理"
    bundle["collaboration_summary"] = (
        "这个 GDPR/CCPA consent and preference center 任务需要 multi-round Loopora governance，因为 one Agent pass、"
        "direct chat、one-off handling 或 banner/checkbox/localStorage demo 会太晚发现 tracking without consent、"
        "vendor mismatch、withdrawal 未生效、DSAR/deletion 未对账或 stale preference cache。后续轮次里的 consent contract inspection、"
        "Preference Governance Builder、evidence inspection 和 GateKeeper 会分别产生 proof、handoff、Blocking decision 与 verdict context。"
        "这个 bundle 把判断投射到 spec 的 success/fake-done/evidence/residual-risk 规则、roles 的差异化责任、workflow 的 "
        "handoff/evidence query，以及按 Proven、Weak、Unproven、Blocking 和 Residual risk buckets 裁决的 GateKeeper closure。"
    )
    bundle["spec"]["markdown"] = """# Task

构建 GDPR/CCPA consent and preference center 的同意账本和偏好治理路径。普通 email unsubscribe、完整隐私平台重写和非同意相关营销页面不在本轮范围内。

# Done When

- Cookie consent、marketing opt-in、email/SMS/push preferences、tracking purposes 和 third-party vendor consent 都按 region 生效。
- Consent version、policy version、purpose id、legal basis、source、timestamp、IP/user agent 和 withdrawal 都有 immutable audit log。
- 用户 withdraw consent 后 analytics event、marketing campaign、data export 和 vendor sync 都立即停止或更新。
- Double opt-in、unsubscribe、suppression list、DSAR export 和 deletion request 与 consent ledger 对账。
- 未登录用户 cookie consent 能和登录后 account preference merge。
- Monitoring 能发现 consent drift、vendor mismatch、tracking without consent、stale preference cache 和 re-consent required。

# Success Surface

- Reviewer 可以追踪 purpose/version/legal-basis contract、withdrawal enforcement、vendor sync、analytics/marketing/export suppression、double opt-in/unsubscribe/suppression reconciliation、DSAR/deletion reconciliation、account preference merge、cache invalidation 和 monitoring evidence。

# Fake Done

- 不允许因为 cookie banner 显示、checkbox 保存成功或 localStorage 有 consent=true 而通过。
- 如果缺少 consent ledger、purpose/legal basis、withdrawal enforcement、vendor sync、analytics/marketing/data export/report blocking、audit/cache、DSAR/deletion reconciliation、account merge、monitoring 或 local-governance evidence，不允许通过。
- 缺少 data export/report suppression proof 时不能通过。

# Evidence Preferences

- 优先使用 consent ledger fixtures、purpose/legal-basis contract、withdrawal cases、vendor sync proof、analytics/marketing/export suppression proof、double opt-in/unsubscribe/suppression reconciliation、DSAR/deletion reconciliation、anonymous-cookie/account-preference merge proof、stale-cache negatives、consent drift/vendor mismatch/tracking-without-consent alerts。
- Consent Evidence Inspector 应把 thin evidence 标为 Weak，把 unsupported claims 标为 Unproven，把 closure blockers 标为 Blocking，把非关键偏好中心 polish 标为 Residual risk。

# Judgment Tradeoffs

- 严格 privacy proof 优先于快速上线 banner；宁可先交窄而可审计的 consent ledger 和 withdrawal enforcement，也不要 cookie banner demo 掩盖跟踪、营销或 vendor 合规风险。

# Residual Risk

轻微偏好中心文案或非关键通知 polish 只有在标为 Residual risk 且有 owner 与 follow-up 时才可保留。缺少 purpose/version/legal-basis、withdrawal、vendor sync、analytics/marketing/export suppression、audit/cache、DSAR/deletion、merge、monitoring 或 local-governance proof 时必须 fail closed。

# Role Notes

## 同意契约 Inspector Notes

实现前固定 purpose、region、version、legal basis、withdrawal、vendor、marketing/tracking enforcement、DSAR/deletion、account merge、audit ledger、cache 和 monitoring proof targets。

## Preference Governance Builder Notes

读取 consent contract handoff 和 project-local governance；只实现同意账本、偏好中心、withdrawal enforcement、vendor sync、cache invalidation、DSAR/deletion 对账、merge 和审计/监控证据。

## Consent Evidence Inspector Notes

验证 withdrawal 后 analytics/marketing/export/vendor 停止或更新、double opt-in/unsubscribe/suppression 对账、DSAR/deletion 对账、未登录 cookie 与账号偏好 merge、stale cache、vendor mismatch、tracking-without-consent 和 local-governance evidence。

## Consent GateKeeper Notes

读取 contract 与 evidence handoffs；查询 consent governance、privacy、subscription deliverability、analytics enforcement、provider sync、audit integrity、cache invalidation、data export/report、deletion、monitoring 和 local-governance evidence；只有核心风险 Proven 或可管理 Residual risk 时 finish。
"""
    bundle["role_definitions"] = [
        _consent_role_definition(
            "consent-contract-inspector",
            "同意契约 Inspector",
            "inspector",
            "实现前只读检查并冻结 purpose/version/legal-basis、withdrawal、vendor、analytics/marketing/export、DSAR/deletion、merge、cache 和 monitoring proof targets。",
            "任何 banner/checkbox/localStorage-only、tracking-without-consent 或 missing-legal-basis 样本都应标为 Blocking。",
        ),
        _consent_role_definition(
            "preference-governance-builder",
            "偏好治理 Builder",
            "builder",
            "基于 consent contract handoff 构建同意账本、偏好中心、withdrawal enforcement、vendor sync、cache invalidation、DSAR/deletion 对账和监控。",
            "优先窄而可审计的 consent ledger proof，不接受 cookie banner demo。",
        ),
        _consent_role_definition(
            "consent-evidence-inspector",
            "Consent 证据 Inspector",
            "inspector",
            "验证 withdrawal、vendor sync、analytics/marketing/export suppression、DSAR/deletion、merge、cache 和 monitoring。",
            "把薄弱 consent、vendor、audit、cache、deletion 或 monitoring evidence 分类为 Weak、Unproven 或 Blocking。",
        ),
        _consent_role_definition(
            "consent-gatekeeper",
            "Consent 证据 GateKeeper",
            "gatekeeper",
            "从 contract 和 evidence handoffs 裁决 consent governance readiness。",
            "缺少 purpose/legal-basis、withdrawal、vendor、analytics/marketing/data export/report、DSAR/deletion、merge、cache、monitoring 或 local-governance evidence 时 fail closed。",
        ),
    ]
    bundle["workflow"] = {
        "version": 1,
        "preset": "",
        "collaboration_intent": (
            "先用只读 consent contract inspection 固定 purpose/version/legal-basis、withdrawal、vendor、marketing/tracking、"
            "DSAR/deletion、merge、audit/cache 和 monitoring proof targets；Preference Governance Builder 读取该 handoff 后只构建可审计同意账本；"
            "Consent Evidence Inspector 再验证 withdrawal、vendor sync、analytics/marketing/export suppression、DSAR/deletion、merge、cache 和 monitoring；"
            "GateKeeper 汇入 contract/evidence handoffs 与 evidence_query，让 banner、checkbox、localStorage-only 或 weak-proof 状态在 closure 前暴露并阻断。"
            "tracking-without-consent 必须作为显式 Blocking risk 进入 evidence review。"
        ),
        "roles": [
            {"id": "contract_inspector", "role_definition_key": "consent-contract-inspector"},
            {"id": "preference_builder", "role_definition_key": "preference-governance-builder"},
            {"id": "evidence_inspector", "role_definition_key": "consent-evidence-inspector"},
            {"id": "gatekeeper", "role_definition_key": "consent-gatekeeper"},
        ],
        "steps": [
            {"id": "consent_contract_step", "role_id": "contract_inspector", "on_pass": "continue"},
            {
                "id": "preference_governance_builder_step",
                "role_id": "preference_builder",
                "inputs": {"handoffs_from": ["consent_contract_step"], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": "consent_evidence_inspection_step",
                "role_id": "evidence_inspector",
                "inputs": {
                    "handoffs_from": ["preference_governance_builder_step"],
                    "evidence_query": {
                        "archetypes": ["builder"],
                        "verifies": [
                            "consent-governance",
                            "privacy-redaction",
                            "subscription-deliverability",
                            "analytics",
                            "provider-contract",
                            "audit-integrity",
                            "cache-invalidation",
                            "data-export",
                            "deletion-retention",
                            "monitoring",
                        ],
                        "limit": 40,
                    },
                    "iteration_memory": "summary_only",
                },
                "on_pass": "continue",
            },
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "inputs": {
                    "handoffs_from": ["consent_contract_step", "consent_evidence_inspection_step"],
                    "evidence_query": {
                        "archetypes": ["builder", "inspector"],
                        "verifies": [
                            "consent-governance",
                            "privacy-redaction",
                            "subscription-deliverability",
                            "analytics",
                            "provider-contract",
                            "audit-integrity",
                            "cache-invalidation",
                            "data-export",
                            "deletion-retention",
                            "monitoring",
                            "local-governance",
                        ],
                        "limit": 50,
                    },
                },
                "on_pass": "finish_run",
            },
        ],
    }
    return load_bundle_text(bundle_to_yaml(bundle))


class ConsentGovernanceAlignmentExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message="请确认这份 consent governance 工作协议；确认后我再生成 Loop bundle。",
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = (
                "Consent governance 协议：先固定 purpose/version/legal basis、withdrawal、vendor、DSAR/deletion、merge、cache 和监控证据，"
                "再实现同意账本，最后由严格 GateKeeper 裁决。"
            )
            payload["readiness_checklist"] = {**CONSENT_GOVERNANCE_CHECKLIST, "explicit_confirmation": False}
            payload["readiness_evidence"] = {**CONSENT_GOVERNANCE_EVIDENCE, "open_questions": ""}
            payload["decision_options"] = [
                {
                    "id": "confirm_consent",
                    "label": "确认 consent governance 协议（推荐）",
                    "description": "生成以同意账本、withdrawal、vendor sync、DSAR/deletion 和监控证据为核心的 workflow。",
                    "recommended": True,
                    "user_reply": "确认，采用这份 consent governance 工作协议。",
                },
                {
                    "id": "adjust_consent_scope",
                    "label": "调整范围",
                    "description": "先修改同意账本、vendor 或阻断策略。",
                    "recommended": False,
                    "user_reply": "我想调整 consent governance 工作协议：",
                },
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="已生成 consent governance Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(consent_governance_bundle(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = (
            "Consent governance 协议：先固定 purpose/version/legal basis、withdrawal、vendor、DSAR/deletion、merge、cache 和监控证据，"
            "再实现同意账本，最后由严格 GateKeeper 裁决。"
        )
        payload["readiness_evidence"] = CONSENT_GOVERNANCE_EVIDENCE
        return payload


def test_success_categories_detect_consent_governance_without_email_preference_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(CONSENT_GOVERNANCE_TASK_TEXT)]
    email_preference_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means lifecycle email unsubscribe and preference center update the suppression list and delivery event."
        )
    ]

    assert "privacy/consent-preference-governance" in labels
    assert "notification/subscription-deliverability" in labels
    assert "analytics/event-integrity" in labels
    assert "external/provider-contract" in labels
    assert "audit/log" in labels
    assert "audit/log-integrity-retention" in labels
    assert "cache/invalidation-consistency" in labels
    assert "data/export/report" in labels
    assert "data-lifecycle/deletion-retention" not in labels
    assert "notification/subscription-deliverability" in email_preference_labels
    assert "privacy/consent-preference-governance" not in email_preference_labels


def test_fake_done_and_evidence_categories_detect_consent_governance_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(CONSENT_GOVERNANCE_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(CONSENT_GOVERNANCE_TASK_TEXT)
    ]

    assert "privacy/consent-preference-governance" in fake_labels
    assert "privacy/consent-preference-governance" in evidence_labels
    assert "notification/subscription-deliverability" in fake_labels
    assert "analytics/event-integrity" in evidence_labels
    assert "audit/log-integrity-retention" in evidence_labels
    assert "cache/invalidation-consistency" in evidence_labels
    assert "external/provider-contract" in evidence_labels


def test_alignment_agreement_requires_consent_governance_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show a cookie banner, save a checkbox, and store consent=true in localStorage.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means consent preference governance proves cookie consent, marketing opt-in, email/SMS/"
                    "push preferences, tracking purposes, vendor consent, region rules, consent version, policy "
                    "version, purpose id, legal basis, withdrawal, immutable audit, vendor sync, double opt-in, "
                    "unsubscribe, suppression, DSAR export, deletion request, account preference merge, and monitoring."
                ),
                "fake_done_risks": (
                    "A cookie banner, checkbox save, or localStorage consent=true without consent ledger, purpose/legal "
                    "basis, withdrawal enforcement, vendor sync, analytics/marketing/export blocking, audit, cache, "
                    "DSAR/deletion reconciliation, and monitoring proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include consent version, policy version, purpose id, legal basis, source, timestamp, "
                    "IP/user agent, withdrawal, immutable audit log, analytics event and marketing campaign suppression, "
                    "data export and vendor sync updates, double opt-in, unsubscribe, suppression list, DSAR export, "
                    "deletion request, account preference merge, consent drift, vendor mismatch, tracking without "
                    "consent, stale preference cache, and re-consent required alerts."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "privacy/consent-preference-governance" in issue for issue in issues)
    assert any("fake-done risks" in issue and "privacy/consent-preference-governance" in issue for issue in issues)
    assert any("evidence preferences" in issue and "privacy/consent-preference-governance" in issue for issue in issues)


def test_alignment_service_accepts_confirmed_consent_governance_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "consent-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing privacy consent flows.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nConsent ledger boundaries.\n", encoding="utf-8")
    (workdir / "README.md").write_text("# Privacy platform\n\nConsent and preference surface.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    service.executor_factory = lambda: ConsentGovernanceAlignmentExecutor(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=CONSENT_GOVERNANCE_TASK_TEXT
        + " 我希望先固定 purpose/version/legal basis 和 withdrawal/vendor 负向样本，再实现，最后让 GateKeeper 读取 contract/evidence handoff。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(created["id"], "确认，采用这份 consent governance 工作协议。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    steps = bundle["workflow"]["steps"]
    inspector_inputs = steps[2]["inputs"]
    gatekeeper_inputs = steps[-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(ready, bundle) == []
    assert [step["id"] for step in steps] == [
        "consent_contract_step",
        "preference_governance_builder_step",
        "consent_evidence_inspection_step",
        "gatekeeper_step",
    ]
    assert steps[1]["inputs"]["handoffs_from"] == ["consent_contract_step"]
    assert inspector_inputs["handoffs_from"] == ["preference_governance_builder_step"]
    assert inspector_inputs["evidence_query"]["verifies"] == [
        "consent-governance",
        "privacy-redaction",
        "subscription-deliverability",
        "analytics",
        "provider-contract",
        "audit-integrity",
        "cache-invalidation",
        "data-export",
        "deletion-retention",
        "monitoring",
    ]
    assert gatekeeper_inputs["handoffs_from"] == ["consent_contract_step", "consent_evidence_inspection_step"]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "consent-governance",
        "privacy-redaction",
        "subscription-deliverability",
        "analytics",
        "provider-contract",
        "audit-integrity",
        "cache-invalidation",
        "data-export",
        "deletion-retention",
        "monitoring",
        "local-governance",
    ]
    assert "localStorage-only" in bundle["workflow"]["collaboration_intent"]
    assert "tracking-without-consent" in bundle["workflow"]["collaboration_intent"]
    assert "role zoo" not in bundle["workflow"]["collaboration_intent"].lower()


def test_agent_first_traceability_blocks_banner_checkbox_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show a cookie banner, save a checkbox, and write localStorage consent=true.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求 cookie banner 显示、checkbox 保存成功、localStorage 有 consent=true。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: purpose, version, legal basis, withdrawal, vendor sync, analytics, marketing, "
        "export, audit, cache, DSAR, deletion, merge, and monitoring proof can be handled later.\n"
        "  Owner: privacy platform owner\n"
        "  Follow-up: add consent governance proof later.\n"
        "  Acceptance path: GateKeeper can pass after banner, checkbox, and localStorage work.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 cookie banner、checkbox 保存和 localStorage consent=true，不处理 purpose、version、"
        "legal basis、withdrawal、vendor sync、analytics、marketing、export、audit、cache、DSAR、deletion 或 monitoring proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat banner, checkbox, and localStorage consent=true as enough for this pass; deeper consent governance proof "
        "can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(CONSENT_GOVERNANCE_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "privacy/consent-preference-governance" in issue for issue in issues)
    assert any("fake-done risks" in issue and "privacy/consent-preference-governance" in issue for issue in issues)
    assert any("evidence preferences" in issue and "privacy/consent-preference-governance" in issue for issue in issues)


def test_cli_agent_plan_notification_rounds_use_parallel_deliverability_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-notification-deliverability",
    }
    task_message = (
        "Plan a governed Loop for lifecycle campaign email deliverability and subscription preferences. Success must prove "
        "only subscribed eligible users receive the campaign; unsubscribe and preference center choices suppress sends; "
        "global suppression list, bounce, complaint, disabled user, tenant, and locale filters work; duplicate sends are "
        "prevented under retries and provider webhook replays; provider accepted, delivered, bounced, complained, and "
        "dropped events reconcile with local delivery audit; template variables render safely in English and Chinese "
        "without leaking PII or tokens; rate limits, retry/backoff, DLQ/manual replay, monitoring, and audit reason codes "
        "work. Fake done is one test email received, provider accepted status only, a UI toggle, happy-path send, "
        "docs-only unsubscribe, no bounce/complaint proof, no locale variable proof, no PII redaction, no duplicate-send "
        "negative, or treating delivery audit reconciliation as follow-up."
    )

    first_summary = _invoke_notification_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_notification_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Notification Contract Inspector freezing subscription eligibility, preference "
            "center semantics, unsubscribe, suppression list, bounce/complaint/drop event contract, disabled-user and tenant "
            "filters, locale/template variable matrix, PII/token redaction, provider webhook signature/replay/idempotency, "
            "retry/backoff/DLQ/manual replay, delivery audit fields, monitoring, migration/backward compatibility, and "
            "local governance. Campaign Email Builder implements only after that handoff. Then run Deliverability Evidence "
            "Inspector and Template Privacy Inspector in parallel: Deliverability checks subscribed/unsubscribed/preference/"
            "suppression/disabled/tenant cases, provider accepted/delivered/bounced/complained/dropped reconciliation, "
            "duplicate retry and replay negatives, rate limit and DLQ/manual replay; Template Privacy checks English/Chinese "
            "templates, variable fallback, PII/token redaction, audit reason codes, monitoring, compatibility, and governance. "
            "GateKeeper must fail closed on one test email, provider accepted only, UI toggle only, happy-path send, docs-only "
            "unsubscribe, missing bounce/complaint proof, missing duplicate negative, missing locale/template proof, missing "
            "PII redaction, missing audit reconciliation, missing monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_notification_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_notification_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        env=env,
    )
    _assert_notification_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _notification_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_notification_bundle(bundle_text)


def test_cli_agent_plan_chinese_notification_bundle_uses_user_facing_role_language(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-notification-deliverability-zh",
    }
    task_message = (
        "我要做 lifecycle campaign email / notification subscription deliverability。成功必须证明只有 "
        "subscribed eligible users 收到 campaign；unsubscribe、preference center、global suppression list 生效；"
        "bounce/complaint/drop provider events、disabled user、tenant filter、locale filter 都正确；"
        "retry/provider replay 不重复发送；provider accepted/delivered/bounced/complained/dropped events 与本地 "
        "delivery audit 能对账；English/Chinese template variables 安全渲染，PII/tokens 不泄露；rate limit、"
        "retry/backoff、DLQ/manual replay、monitoring、audit reason codes、migration/backward compatibility 和 "
        "local governance 都可审计。假完成是 one test email、provider accepted-only、UI toggle-only、"
        "happy-path send-only、docs-only unsubscribe、缺少 bounce/complaint proof、duplicate negative、"
        "locale/template proof、PII redaction、audit reconciliation、monitoring、migration 或 governance。"
    )

    first_summary = _invoke_notification_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_notification_plan_round(
        runner,
        sample_workdir,
        message=(
            "补充判断：采用 notification subscription-deliverability contract-first workflow。先由只读 "
            "Notification Contract Inspector 固定 subscription eligibility、preference center、unsubscribe、"
            "global suppression list、bounce/complaint/drop event contract、disabled-user 和 tenant filters、"
            "locale/template variable matrix、PII/token redaction、provider webhook signature/replay/idempotency、"
            "retry/backoff、rate limit、DLQ/manual replay、delivery audit fields、monitoring alerts、migration/"
            "backward compatibility 和 local-governance proof targets。Campaign Email Builder 只能读取该 "
            "handoff 后实现。然后 Deliverability Evidence Inspector 与 Template Privacy Inspector 并行检查同一个产物："
            "Deliverability 验证 subscribed/unsubscribed/preference/suppression/disabled/tenant cases、provider "
            "accepted/delivered/bounced/complained/dropped reconciliation、duplicate retry/replay negatives、"
            "rate limit、DLQ/manual replay；Template Privacy 验证 English/Chinese templates、variable fallback、"
            "PII/token redaction、audit reason codes、monitoring、compatibility 和 governance。GateKeeper 必须在 "
            "one-test-email、provider-accepted-only、UI-toggle-only、happy-path-send-only、docs-only unsubscribe、"
            "缺少 bounce/complaint proof、duplicate negative、locale/template proof、PII redaction、audit reconciliation、"
            "monitoring、migration 或 governance 时 fail closed。"
        ),
        env=env,
    )
    _assert_notification_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_notification_plan_round(
        runner,
        sample_workdir,
        message="确认，采用这个方向。",
        env=env,
    )
    _assert_notification_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _notification_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_notification_bundle(bundle_text)
    bundle = yaml.safe_load(bundle_text)
    names_by_key = {role["key"]: role["name"] for role in bundle["role_definitions"]}
    assert names_by_key == {
        "notification-contract-inspector": "通知契约 Inspector",
        "campaign-email-builder": "活动邮件 Builder",
        "deliverability-evidence-inspector": "投递证据 Inspector",
        "template-privacy-inspector": "模板隐私 Inspector",
        "notification-deliverability-gatekeeper": "通知投递 GateKeeper",
    }


def _invoke_notification_plan_round(
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


def _assert_notification_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Notification Contract Inspector" in agreement_text
    assert "Campaign Email Builder" in agreement_text
    assert "Deliverability Evidence Inspector" in agreement_text
    assert "Template Privacy Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "SaaS API usage metering" not in agreement_text
    assert "Quota Contract Inspector" not in agreement_text
    assert "Usage Metering Builder" not in agreement_text


def _assert_notification_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("notification", "subscription", "unsubscribe", "bounce", "template", "redaction", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _notification_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_notification_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "notification-contract-inspector",
        "campaign-email-builder",
        "deliverability-evidence-inspector",
        "template-privacy-inspector",
        "notification-deliverability-gatekeeper",
    ]
    assert workflow["preset"] == "notification-subscription-contract-parallel-deliverability"
    assert [step["id"] for step in workflow["steps"]] == [
        "notification_contract_inspection_step",
        "campaign_email_builder_step",
        "deliverability_evidence_inspection_step",
        "template_privacy_inspection_step",
        "notification_deliverability_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["notification_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "notification_deliverability_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "notification_deliverability_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "notification_contract_inspection_step",
        "campaign_email_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "notification_contract_inspection_step",
        "campaign_email_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "notification_contract_inspection_step",
        "campaign_email_builder_step",
        "deliverability_evidence_inspection_step",
        "template_privacy_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "subscription-deliverability",
        "message-delivery",
        "provider-contract",
        "idempotency",
        "retry-timeout",
        "queue-recovery",
        "privacy-redaction",
        "locale-i18n",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "quota-metering" not in gatekeeper_verifies
    assert "Notification Subscription Deliverability Workflow Notes" in bundle_text
    assert "usage-quota-contract-parallel-metering" not in bundle_text
    assert "Quota Contract Inspector" not in bundle_text
    assert "Confirm; use this direction" not in bundle_text
