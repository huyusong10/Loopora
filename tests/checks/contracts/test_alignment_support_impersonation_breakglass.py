from __future__ import annotations

from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, json
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


SUPPORT_IMPERSONATION_TASK_TEXT = (
    "我要给 B2B SaaS 做 support impersonation / break-glass admin access。成功必须证明 support agent "
    "只能在 approved ticket、customer consent、reason code 和 supervisor approval 下限时 impersonate "
    "指定 tenant/user；session attribution 必须区分 actor、acting_as、on_behalf_of，不能共享 admin token "
    "或绕过 MFA policy，PII 字段默认遮蔽，destructive actions 要阻断或 step-up approval，tenant isolation "
    "不能串租户，audit log 不可篡改并记录 actor、target user、ticket id、reason、start/end、IP、user agent、"
    "viewed records、changes、export attempts；访问自动过期，revoke 立即生效，监控要发现 no-ticket "
    "impersonation、after-hours access、bulk record view、sensitive data view、export/download attempt "
    "和 long-running session；只有 support 能登录客户账号、打开 feature flag、共享管理员 token 或 UI 显示 "
    "impersonating banner 必须阻断。"
)

SUPPORT_IMPERSONATION_WORKFLOW_MESSAGE = (
    "补充判断：采用 support impersonation contract-first workflow。Support Access Contract Inspector 先只读固定 "
    "approved ticket、customer consent、reason code、supervisor approval、timebox、tenant/user scope、"
    "actor/acting_as/on_behalf_of attribution、MFA/step-up、PII masking、destructive action blocking、"
    "tenant isolation、tamper-evident audit、expiry/revoke、export/download attempt、monitoring alert "
    "和 local-governance proof targets。Break-glass Access Builder 只能读取该 handoff 后实现。"
    "Support Evidence Inspector 必须读取 contract 和 builder handoff，验证 no-ticket、missing consent、"
    "wrong tenant、shared token、MFA bypass、unmasked PII、destructive action、audit tamper、revoke/expiry、"
    "export attempt、after-hours/bulk/sensitive/long-running monitoring negatives。GateKeeper 必须在 "
    "login-as-only、feature-flag-only、shared-admin-token、banner-only、missing approval/consent/attribution/"
    "MFA/privacy/tenant/audit/revoke/monitoring 或 skipped governance 时 fail closed。"
)

SUPPORT_IMPERSONATION_CHECKLIST = {
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

SUPPORT_IMPERSONATION_EVIDENCE = {
    "loop_fit": (
        "这项 break-glass access 需要 Loopora，因为审批、同意、会话归因、隐私遮蔽、租户负向、审计不可篡改、"
        "撤销/过期和异常监控会分阶段产生新的 proof 与 handoff；只靠 one Agent pass、直接聊天、one-off "
        "处理或最终人工 review 会太晚发现共享 token、越权或审计缺口。"
    ),
    "task_scope": (
        "范围限定为 B2B SaaS support impersonation / break-glass admin access 的治理路径；不扩展到普通客服工单、"
        "客户资料编辑或全平台 RBAC 重写。"
    ),
    "success_surface": (
        "成功面是 support agent 只能在 approved ticket、customer consent、reason code、supervisor approval "
        "下限时 impersonate 指定 tenant/user，并且 actor/acting_as/on_behalf_of attribution、MFA/step-up、"
        "PII masking、tenant isolation、audit immutability、revoke、expiry、monitoring 和 export-attempt proof 可验证。"
    ),
    "fake_done_risks": (
        "必须拒绝只实现 impersonate button、feature flag、shared admin token、login-as happy path 或 UI banner，"
        "但没有审批、同意、归因、MFA、隐私、租户、撤销、过期、审计和监控负例证据的通过。"
    ),
    "evidence_preferences": (
        "可信证据是 approval/consent fixture、reason code、supervisor approval、time-bound session、"
        "actor/acting_as/on_behalf_of attribution、MFA/step-up cases、PII masking checks、tenant negative samples、"
        "tamper-evident audit refs、revoke/expiry cases、export/download attempt proof 和 anomaly-monitoring artifacts。"
        "最终证据必须区分 Proven、Weak、Unproven、Blocking 和 Residual risk buckets。"
    ),
    "execution_strategy": (
        "先由只读 contract inspection 固定 break-glass policy 和负向样本，再实现授权、会话、遮蔽、审计和撤销；"
        "evidence inspection 暴露 Weak 或 Blocking proof 后，GateKeeper 再决定 closure 或阻断。"
    ),
    "residual_risk_policy": (
        "轻微监控阈值调优可作为 Residual risk 留下，但必须有 owner 与 follow-up；缺少 approval、consent、"
        "attribution、MFA/step-up、PII masking、tenant isolation、audit immutability、revoke、expiry、export attempt "
        "或 anomaly-monitoring proof 时必须 fail closed。"
    ),
    "judgment_tradeoffs": (
        "严格阻断优先于快速放出代理登录；宁可先交窄而可审计的 break-glass flow，也不要宽泛 login-as demo "
        "掩盖隐私、权限或审计风险。"
    ),
    "local_governance": (
        "项目本地 marker 包含 AGENTS.md、design/README.md、design/ 和 tests/；Builder 要先读取它们，"
        "Inspector 验证相关 design/test obligation，GateKeeper 把跳过治理视为 Weak、Unproven 或 Blocking。"
    ),
    "role_posture": (
        "Contract Inspector 固定 approval/consent/session/audit/privacy/tenant proof targets；Break-glass Builder "
        "只实现这些治理边界；Evidence Inspector 验证负向与审计证据；GateKeeper 对 shared-token、banner-only "
        "或 weak-proof 状态 fail closed。"
    ),
    "workflow_shape": (
        "workflow 先做只读 policy inspection，再 Builder，再 evidence inspection，再 GateKeeper；"
        "Evidence Inspector 的 review 会作为 GateKeeper fan-in，防止 login-as 或 banner-only 结果绕过证据裁决。"
    ),
    "workdir_facts": "已观察到 AGENTS.md、design/README.md、design/、tests/ 和 README.md；具体实现栈仍未知。",
    "open_questions": "无未解决问题",
}


def _support_role_definition(key: str, name: str, archetype: str, body: str, posture: str) -> dict:
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


def support_impersonation_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    bundle["metadata"]["name"] = "Support 破窗访问治理"
    bundle["metadata"]["description"] = "治理 support impersonation、审批、会话归因、隐私、租户隔离、审计和监控证据。"
    bundle["loop"]["name"] = "Support 破窗访问治理"
    bundle["collaboration_summary"] = (
        "这个 support impersonation / break-glass access 任务需要 multi-round Loopora governance，因为 one Agent pass、"
        "direct chat、one-off handling 或 banner/login demo 会太晚发现共享 token、审批缺失、隐私泄露、"
        "跨租户访问、撤销失效或审计不可追溯。后续轮次里的 policy inspection、Break-glass Builder、"
        "evidence inspection 和 GateKeeper 会分别产生 proof、handoff、Blocking decision 与 verdict context。这个 bundle 把判断投射到 "
        "spec 的 success/fake-done/evidence/residual-risk 规则、roles 的差异化责任、workflow 的 handoff/evidence query，"
        "以及按 Proven、Weak、Unproven、Blocking 和 Residual risk buckets 裁决的 GateKeeper closure。"
    )
    bundle["spec"]["markdown"] = """# Task

构建 B2B SaaS support impersonation / break-glass admin access 的治理路径。普通客服工单、客户资料编辑和全平台 RBAC 重写不在本轮范围内。

# Done When

- Support agent 只能在 approved ticket、customer consent、reason code 和 supervisor approval 下限时 impersonate 指定 tenant/user。
- Session attribution 区分 actor、acting_as、on_behalf_of，不能共享 admin token，也不能绕过 MFA policy。
- PII 字段默认遮蔽，destructive actions 被阻断或要求 step-up approval，tenant isolation 有负向证明。
- Audit log 不可篡改，并记录 actor、target user、ticket id、reason、start/end、IP、user agent、viewed records、changes 和 export attempts。
- 访问自动过期，revoke 立即生效，monitoring 能发现 no-ticket impersonation、after-hours access、bulk record view、sensitive data view、export/download attempt 和 long-running session。

# Success Surface

- Reviewer 可以追踪 approval、consent、reason、supervisor approval、time-bound session、actor/acting_as/on_behalf_of attribution、MFA/step-up、PII masking、tenant negative cases、tamper-evident audit refs、revoke/expiry 和 anomaly-monitoring evidence。

# Fake Done

- 不允许因为 support 能登录客户账号、打开 feature flag、共享管理员 token、login-as happy path 或 UI 显示 impersonating banner 而通过。
- 如果缺少 approved-ticket、customer-consent、reason-code、supervisor-approval、attribution、MFA/step-up、privacy、tenant-isolation、audit-integrity、revoke、expiry、export-attempt 或 monitoring evidence，不允许通过。

# Evidence Preferences

- 优先使用 approval/consent fixtures、reason-code and supervisor-approval cases、time-bound session checks、actor/acting_as/on_behalf_of traces、MFA/step-up negatives、PII masking tests、tenant isolation negatives、tamper-evident audit refs、revoke/expiry cases、export/download attempts 和 anomaly-monitoring artifacts。
- Evidence Inspector 应把 thin evidence 标为 Weak，把 unsupported claims 标为 Unproven，把 closure blockers 标为 Blocking，把轻微监控阈值调优标为 Residual risk。

# Judgment Tradeoffs

- 严格阻断优先于快速放出代理登录；宁可先交窄而可审计的 break-glass flow，也不要宽泛 login-as demo 掩盖隐私、权限或审计风险。

# Residual Risk

轻微 monitoring threshold tuning 只有在标为 Residual risk 且有 owner 与 follow-up 时才可保留。缺少 approval、consent、reason、supervisor approval、attribution、MFA/step-up、PII masking、tenant isolation、audit immutability、revoke、expiry、export attempt、anomaly monitoring 或 local-governance evidence 时必须 fail closed。

# Role Notes

## Break-glass Policy Inspector Notes

实现前固定 approval、consent、reason、supervisor approval、time limit、attribution、MFA、PII、destructive action、tenant isolation、audit、revoke、expiry、monitoring 和 export-attempt proof targets。

## Break-glass Builder Notes

读取 policy inspection handoff 和 project-local governance；只实现授权校验、会话归因、遮蔽、step-up、租户隔离、审计、撤销、过期和监控证据。

## Access Evidence Inspector Notes

验证 no-ticket、expired、revoked、MFA/step-up、PII masking、cross-tenant、destructive-action、export/download、bulk view、long-running session、audit immutability 和 local-governance evidence。

## Break-glass GateKeeper Notes

读取 policy inspection 与 evidence inspection handoffs；查询 approval、permission、privacy、tenant、session lifecycle、audit integrity、monitoring、export-attempt 和 local-governance evidence；只有核心风险 Proven 或可管理 Residual risk 时 finish。
"""
    bundle["role_definitions"] = [
        _support_role_definition(
            "breakglass-policy-inspector",
            "Break-glass 策略 Inspector",
            "inspector",
            "实现前只读检查并冻结 approval、consent、session、privacy、tenant、audit、revoke 和 monitoring proof targets。",
            "任何 login-as、banner-only、shared-token 或 missing-policy 样本都应标为 Blocking。",
        ),
        _support_role_definition(
            "breakglass-builder",
            "Break-glass 实现 Builder",
            "builder",
            "基于 policy inspection handoff 构建授权校验、会话归因、PII masking、step-up、审计、撤销、过期和监控。",
            "优先窄而可审计的 break-glass flow，不接受 generic login-as demo。",
        ),
        _support_role_definition(
            "access-evidence-inspector",
            "访问证据 Inspector",
            "inspector",
            "验证 approval、consent、MFA/step-up、privacy、tenant negatives、audit immutability、revoke/expiry 和 monitoring。",
            "把薄弱 permission、privacy、tenant、audit 或 session evidence 分类为 Weak、Unproven 或 Blocking。",
        ),
        _support_role_definition(
            "breakglass-gatekeeper",
            "Break-glass 证据 GateKeeper",
            "gatekeeper",
            "从 policy 和 evidence handoffs 裁决 break-glass readiness。",
            "缺少 approval、attribution、privacy、tenant、audit、revoke、expiry、monitoring 或 local-governance evidence 时 fail closed。",
        ),
    ]
    bundle["workflow"] = {
        "version": 1,
        "preset": "",
        "collaboration_intent": (
            "先用只读 policy inspection 固定 approval、consent、time limit、attribution、MFA、privacy、tenant、audit、"
            "revoke、expiry、monitoring 和 export-attempt proof targets；Break-glass Builder 读取该 handoff 后只构建可审计路径；"
            "Access Evidence Inspector 再验证负向和审计证据；GateKeeper 汇入 policy/evidence handoffs 与 evidence_query，"
            "让 shared-token、login-as happy path、banner-only 或 weak-proof 状态在 closure 前暴露并阻断。"
        ),
        "roles": [
            {"id": "policy_inspector", "role_definition_key": "breakglass-policy-inspector"},
            {"id": "breakglass_builder", "role_definition_key": "breakglass-builder"},
            {"id": "access_evidence_inspector", "role_definition_key": "access-evidence-inspector"},
            {"id": "gatekeeper", "role_definition_key": "breakglass-gatekeeper"},
        ],
        "steps": [
            {"id": "policy_inspection_step", "role_id": "policy_inspector", "on_pass": "continue"},
            {
                "id": "breakglass_builder_step",
                "role_id": "breakglass_builder",
                "inputs": {"handoffs_from": ["policy_inspection_step"], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": "access_evidence_inspection_step",
                "role_id": "access_evidence_inspector",
                "inputs": {
                    "handoffs_from": ["breakglass_builder_step"],
                    "evidence_query": {
                        "archetypes": ["builder"],
                        "verifies": [
                            "support-impersonation",
                            "permission-auth",
                            "tenant-isolation",
                            "privacy-redaction",
                            "audit-integrity",
                            "session-lifecycle",
                            "monitoring",
                            "data-export",
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
                    "handoffs_from": ["policy_inspection_step", "access_evidence_inspection_step"],
                    "evidence_query": {
                        "archetypes": ["builder", "inspector"],
                        "verifies": [
                            "support-impersonation",
                            "permission-auth",
                            "tenant-isolation",
                            "privacy-redaction",
                            "audit-integrity",
                            "session-lifecycle",
                            "monitoring",
                            "data-export",
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


class SupportImpersonationAlignmentExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message="请确认这份 break-glass access 工作协议；确认后我再生成 Loop bundle。",
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = (
                "Support impersonation / break-glass 协议：先固定审批、同意、会话、隐私、租户、审计、撤销和监控证据，"
                "再实现可审计路径，最后由严格 GateKeeper 裁决。"
            )
            payload["readiness_checklist"] = {**SUPPORT_IMPERSONATION_CHECKLIST, "explicit_confirmation": False}
            payload["readiness_evidence"] = {
                **SUPPORT_IMPERSONATION_EVIDENCE,
                "open_questions": "",
            }
            payload["decision_options"] = [
                {
                    "id": "confirm_breakglass",
                    "label": "确认 break-glass 协议（推荐）",
                    "description": "生成以审批、隐私、租户、审计和撤销证据为核心的 workflow。",
                    "recommended": True,
                    "user_reply": "确认，采用这份 break-glass access 工作协议。",
                },
                {
                    "id": "adjust_breakglass_scope",
                    "label": "调整范围",
                    "description": "先修改证据优先级或阻断策略。",
                    "recommended": False,
                    "user_reply": "我想调整 break-glass 工作协议：",
                },
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="已生成 break-glass access Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(support_impersonation_bundle(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = (
            "Support impersonation / break-glass 协议：先固定审批、同意、会话、隐私、租户、审计、撤销和监控证据，"
            "再实现可审计路径，最后由严格 GateKeeper 裁决。"
        )
        payload["readiness_evidence"] = SUPPORT_IMPERSONATION_EVIDENCE
        return payload


def test_success_categories_detect_support_impersonation_without_inventory_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(SUPPORT_IMPERSONATION_TASK_TEXT)]
    generic_support_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means support staff can read a customer's public profile and create a support ticket."
        )
    ]

    assert "access/support-impersonation-breakglass" in labels
    assert "permission/auth" in labels
    assert "access/tenant-isolation" in labels
    assert "audit/log" in labels
    assert "audit/log-integrity-retention" in labels
    assert "auth/session-token-lifecycle" in labels
    assert "privacy/secrets-redaction" in labels
    assert "regression/monitoring-guard" in labels
    assert "data/export/report" in labels
    assert "inventory/reservation-consistency" not in labels
    assert "access/support-impersonation-breakglass" not in generic_support_labels
    assert "inventory/reservation-consistency" not in generic_support_labels


def test_fake_done_and_evidence_categories_detect_support_impersonation_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(SUPPORT_IMPERSONATION_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(SUPPORT_IMPERSONATION_TASK_TEXT)
    ]

    assert "access/support-impersonation-breakglass" in fake_labels
    assert "access/support-impersonation-breakglass" in evidence_labels
    assert "permission/audit" in fake_labels
    assert "privacy/secrets-redaction" in fake_labels
    assert "access/tenant-isolation" in evidence_labels
    assert "audit/log-integrity-retention" in evidence_labels
    assert "auth/session-token-lifecycle" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels
    assert "inventory/reservation-consistency" not in fake_labels
    assert "inventory/reservation-consistency" not in evidence_labels


def test_alignment_agreement_requires_support_impersonation_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add an impersonate button, show a banner, and let support log into a customer account.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means support impersonation and break-glass admin access prove approved ticket, customer "
                    "consent, reason code, supervisor approval, time-bound session, actor/acting_as/on_behalf_of "
                    "attribution, MFA policy, PII masking, destructive-action step-up, tenant isolation, immutable "
                    "audit, expiry, revoke, monitoring, export attempt, and long-running session controls."
                ),
                "fake_done_risks": (
                    "Support can log into a customer account, a feature flag is on, a shared admin token works, or a "
                    "UI impersonating banner appears without approval, consent, attribution, MFA, privacy, tenant, "
                    "expiry, revoke, audit integrity, monitoring, and export/download negative proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include approved ticket, customer consent, reason code, supervisor approval, "
                    "time-bound session, actor/acting_as/on_behalf_of attribution, MFA and step-up checks, PII masking, "
                    "destructive-action blocking, tenant negative samples, immutable audit log, revoke, expiry, "
                    "no-ticket impersonation, after-hours access, bulk record view, sensitive data view, export/download "
                    "attempt, and long-running session monitoring."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)
    assert any("fake-done risks" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)
    assert any("evidence preferences" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)


def test_alignment_service_accepts_confirmed_support_impersonation_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "breakglass-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing access controls.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nAccess-control boundaries.\n", encoding="utf-8")
    (workdir / "README.md").write_text("# Support platform\n\nBreak-glass access surface.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    service.executor_factory = lambda: SupportImpersonationAlignmentExecutor(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=SUPPORT_IMPERSONATION_TASK_TEXT
        + " 我希望先固定 break-glass policy 和负向样本，再实现，最后让 GateKeeper 读取 policy/evidence handoff。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(created["id"], "确认，采用这份 break-glass access 工作协议。")
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
        "policy_inspection_step",
        "breakglass_builder_step",
        "access_evidence_inspection_step",
        "gatekeeper_step",
    ]
    assert steps[1]["inputs"]["handoffs_from"] == ["policy_inspection_step"]
    assert inspector_inputs["handoffs_from"] == ["breakglass_builder_step"]
    assert inspector_inputs["evidence_query"]["verifies"] == [
        "support-impersonation",
        "permission-auth",
        "tenant-isolation",
        "privacy-redaction",
        "audit-integrity",
        "session-lifecycle",
        "monitoring",
        "data-export",
    ]
    assert gatekeeper_inputs["handoffs_from"] == ["policy_inspection_step", "access_evidence_inspection_step"]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "support-impersonation",
        "permission-auth",
        "tenant-isolation",
        "privacy-redaction",
        "audit-integrity",
        "session-lifecycle",
        "monitoring",
        "data-export",
        "local-governance",
    ]
    assert "shared-token" in bundle["workflow"]["collaboration_intent"]
    assert "banner-only" in bundle["workflow"]["collaboration_intent"]
    assert "role zoo" not in bundle["workflow"]["collaboration_intent"].lower()


def test_default_task_anchored_plan_projects_support_impersonation_domain_keys(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "generic-breakglass-workdir"
    workdir.mkdir()
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=SUPPORT_IMPERSONATION_TASK_TEXT
        + " 先做最小可审计 break-glass flow，再证明 approval、privacy、tenant、audit、revoke、expiry 和 monitoring。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    service.append_alignment_message(created["id"], "确认，采用这个方向。")
    ready = _wait_for_status(service, created["id"], "ready")
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    spec_markdown = bundle["spec"]["markdown"]
    success_surface = spec_markdown.split("# Success Surface", 1)[1].split("# Fake Done", 1)[0]
    fake_done = spec_markdown.split("# Fake Done", 1)[1].split("# Evidence Preferences", 1)[0]
    evidence_preferences = spec_markdown.split("# Evidence Preferences", 1)[1].split("# Execution Strategy", 1)[0]
    inspect_verifies = bundle["workflow"]["steps"][1]["inputs"]["evidence_query"]["verifies"]
    gatekeeper_verifies = bundle["workflow"]["steps"][-1]["inputs"]["evidence_query"]["verifies"]

    assert "核心路径如何从输入事件" not in success_surface
    assert "approved ticket" in success_surface
    assert "customer consent" in success_surface
    assert "actor/acting_as/on_behalf_of" in success_surface
    assert "tenant isolation" in success_surface
    assert "PII" in evidence_preferences or "遮蔽" in evidence_preferences
    assert "monitoring" in evidence_preferences or "监控" in evidence_preferences
    assert "shared-admin-token" in fake_done or "共享管理员 token" in fake_done
    assert "support-impersonation" in inspect_verifies
    assert "tenant-isolation" in inspect_verifies
    assert "privacy-redaction" in inspect_verifies
    assert "audit-integrity" in gatekeeper_verifies
    assert "session-lifecycle" in gatekeeper_verifies
    assert "monitoring" in gatekeeper_verifies
    assert "data-export" in gatekeeper_verifies


def test_cli_agent_plan_support_impersonation_rounds_use_policy_first_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-support-impersonation",
    }
    first_summary = _invoke_support_impersonation_plan_round(
        runner,
        sample_workdir,
        message=SUPPORT_IMPERSONATION_TASK_TEXT,
        env=env,
    )
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_support_impersonation_plan_round(
        runner,
        sample_workdir,
        message=SUPPORT_IMPERSONATION_WORKFLOW_MESSAGE,
        env=env,
    )
    _assert_support_impersonation_agreement_round(second_summary)

    third_summary = _invoke_support_impersonation_plan_round(
        runner,
        sample_workdir,
        message="确认，采用这份 support impersonation 工作协议。",
        env=env,
    )
    _assert_support_impersonation_ready_round(third_summary, first_summary["alignment_session_id"])

    bundle_text = _support_impersonation_bundle_text(sample_workdir, first_summary["alignment_session_id"])
    _assert_support_impersonation_bundle(bundle_text, third_summary)


def _invoke_support_impersonation_plan_round(runner: CliRunner, workdir: Path, *, message: str, env: dict) -> dict:
    result = _invoke_codex_plan(
        runner,
        workdir,
        message=message,
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)["summary"]


def _assert_support_impersonation_agreement_round(summary: dict) -> None:
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "continue_alignment_dialogue"
    assert summary["alignment_stage"] == "agreement_ready"
    assert summary["question_action"]["must_wait_for_user_reply"] is True
    agreement_text = summary["alignment_assistant_message"]
    assert "Break-glass Policy Inspector" in agreement_text
    assert "Break-glass Builder" in agreement_text
    assert "Access Evidence Inspector" in agreement_text
    assert "GateKeeper" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Repair Builder" not in agreement_text


def _assert_support_impersonation_ready_round(summary: dict, alignment_session_id: str) -> None:
    assert summary["ready"] is True
    assert summary["continued_alignment_session"] is True
    assert summary["alignment_session_id"] == alignment_session_id
    traceability = summary["ready_review_projection"]["traceability"]
    assert traceability["mapped_count"] == traceability["required_count"]
    assert summary["ready_review_projection"]["diagnostic_count"] == 0


def _support_impersonation_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_support_impersonation_bundle(bundle_text: str, third_summary: dict) -> None:
    bundle = load_bundle_text(bundle_text)
    workflow = bundle["workflow"]
    assert bundle["metadata"]["name"] == "Support 破窗访问 Loop"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "breakglass-policy-inspector",
        "breakglass-builder",
        "access-evidence-inspector",
        "breakglass-gatekeeper",
    ]
    assert workflow["preset"] == "support-impersonation-policy-first"
    assert [step["id"] for step in workflow["steps"]] == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
        "access_evidence_inspection_step",
        "breakglass_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["breakglass_policy_inspection_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "breakglass_policy_inspection_step",
        "breakglass_builder_step",
        "access_evidence_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "support-impersonation",
        "permission-auth",
        "tenant-isolation",
        "privacy-redaction",
        "audit-integrity",
        "session-lifecycle",
        "monitoring",
        "data-export",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "deletion-retention" not in gatekeeper_verifies
    assert "experiment-assignment" not in gatekeeper_verifies
    for forbidden_text in (
        "任务证据修复 Loop",
        "Task Evidence Repair Loop",
        "Builder -> Inspector -> Guide",
        "Repair Builder",
        "修复 Builder",
        "Guide 只把弱证据",
        "data-residency-contract",
        "authorization-policy",
        "auth-session",
    ):
        assert forbidden_text not in bundle_text
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(third_summary, bundle) == []


def test_agent_first_traceability_blocks_login_banner_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add an impersonate button, a feature flag, shared admin-token login, and an impersonating banner.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求 support 能登录客户账号、打开 feature flag、共享管理员 token 和 UI 显示 banner。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: approval, consent, reason, time limit, attribution, MFA, privacy, tenant, "
        "destructive-action, audit, expiry, revoke, monitoring, and export/download proof can be handled later.\n"
        "  Owner: support platform owner\n"
        "  Follow-up: add break-glass governance later.\n"
        "  Acceptance path: GateKeeper can pass after login and banner work.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 impersonate button、feature flag、shared admin-token login 和 banner，不处理审批、同意、"
        "归因、MFA、隐私、租户、审计、撤销或监控证明。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat login and banner as enough for this pass; approval, consent, attribution, MFA, privacy, tenant, audit, "
        "expiry, revoke, monitoring, and export/download proof can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(SUPPORT_IMPERSONATION_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)
    assert any("fake-done risks" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)
    assert any("evidence preferences" in issue and "access/support-impersonation-breakglass" in issue for issue in issues)
