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


DATA_RESIDENCY_TASK_TEXT = (
    "我要给企业客户做 data residency / regional isolation。成功必须证明 EU tenant 的 primary DB、"
    "object storage、search index、cache、queue、backup、logs、analytics export 和 third-party processor "
    "都只落在 EU region，US tenant 只落在 US region，region routing / tenant residency policy / "
    "encryption key region 不能错，cross-region failover 不能把 EU 数据复制到 US，migration/backfill "
    "不跨区，support/admin access、data export、audit log 和 observability trace 都不能泄露跨区数据，"
    "subprocessor allowlist 和 DPA 标记正确，监控要发现 cross-region egress、wrong-region write、"
    "stale residency policy 和 processor mismatch；只有 UI 显示 region=EU、配置 env var 或数据库 "
    "tenant 表有 region 字段必须阻断。"
)

DATA_RESIDENCY_WORKFLOW_MESSAGE = (
    "补充判断：采用 data residency contract-first workflow。Residency Contract Inspector 先只读固定 "
    "EU/US 数据面清单、tenant residency policy、routing、primary DB、object storage、search index、cache、"
    "queue、backup、logs、analytics export、processor/subprocessor allowlist、DPA、key-region、failover、"
    "migration/backfill、support/admin access、data export、audit log、observability trace、egress monitoring "
    "和 wrong-region write/read/export negative targets。Regional Isolation Builder 只能读取该 handoff 后实现。"
    "Residency Evidence Inspector 必须读取 contract 和 builder handoff，验证 region proof、wrong-region negatives、"
    "processor/DPA、key region、failover、migration、access/export/audit/trace、monitoring 和 local governance。"
    "GateKeeper 必须在 UI-region-only、env-var-only、tenant-field-only、one-routed-request-only、docs-only DPA、"
    "missing processor proof、missing wrong-region negatives、missing key-region proof、missing egress alerts "
    "或 skipped governance 时 fail closed。"
)

DATA_RESIDENCY_CHECKLIST = {
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

DATA_RESIDENCY_EVIDENCE = {
    "loop_fit": (
        "这项 data residency / regional isolation 需要 Loopora，因为 DB、object storage、search、cache、queue、"
        "backup、logs、analytics、processor、failover、migration、access/export/audit 和 monitoring 会分别产生"
        "新的 proof 与 handoff；只靠 one Agent pass、直接聊天、one-off 处理或最终人工 review 会太晚发现错区写入、"
        "跨区复制或处理方不匹配。"
    ),
    "task_scope": (
        "范围限定为企业租户 EU/US regional isolation 的数据面治理；不扩展到普通 regional dashboard、"
        "全平台数据仓库重构或非驻留相关报表。"
    ),
    "success_surface": (
        "成功面是 EU tenant 与 US tenant 的 DB、object storage、search index、cache、queue、backup、logs、"
        "analytics export、processor/subprocessor、routing、residency policy、key region、failover、migration/backfill、"
        "support/admin access、data export、audit log、observability trace 和 monitoring 都有区域证明与 wrong-region 反证。"
    ),
    "fake_done_risks": (
        "必须拒绝只显示 region=EU、配置 env var、tenant 表有 region 字段或只有 dashboard filter 的通过；"
        "没有真实数据面、处理方、failover/migration、access/export/audit/trace 和 monitoring 证据时必须阻断。"
    ),
    "evidence_preferences": (
        "可信证据是 EU/US tenant region proof、wrong-region write negatives、cross-region egress monitoring、"
        "processor/DPA/subprocessor allowlist checks、failover and migration/backfill proof、key-region checks、"
        "support/admin access and data export negatives、audit/observability trace verification，以及 Proven、Weak、"
        "Unproven、Blocking 和 Residual risk buckets。"
    ),
    "execution_strategy": (
        "先由只读 residency contract inspection 固定数据面、处理方、failover、migration、访问/export/trace 和监控样本，"
        "再实现区域路由和存储边界；evidence inspection 暴露 Weak 或 Blocking proof 后，GateKeeper 再裁决。"
    ),
    "residual_risk_policy": (
        "轻微 dashboard 文案或非驻留报表 polish 可作为 Residual risk 留下并指定 owner；缺少 DB/storage/search/cache/"
        "queue/backup/logs/analytics/processor、wrong-region、DPA、failover、migration、access/export/audit/trace、"
        "monitoring 或 local-governance proof 时必须 fail closed。"
    ),
    "judgment_tradeoffs": (
        "严格区域证据优先于快速上线 region selector；宁可先交窄而可审计的 EU/US 数据面证明，也不要 UI/env/tenant-field demo "
        "掩盖跨区或合规风险。"
    ),
    "local_governance": (
        "项目本地 marker 包含 AGENTS.md、design/README.md、design/ 和 tests/；Builder 要先读取它们，"
        "Inspector 验证相关 design/test obligation，GateKeeper 把跳过治理视为 Weak、Unproven 或 Blocking。"
    ),
    "role_posture": (
        "Residency Contract Inspector 固定数据面和负向样本；Regional Isolation Builder 只实现这些边界；"
        "Residency Evidence Inspector 验证 region proof、wrong-region、processor/DPA、access/export/audit/trace 和 monitoring；"
        "GateKeeper 对 UI/env/tenant-field-only 或 weak-proof 状态 fail closed。"
    ),
    "workflow_shape": (
        "workflow 先做只读 residency contract inspection，再 Builder，再 evidence inspection，再 GateKeeper；"
        "Evidence Inspector 的 review 会作为 GateKeeper fan-in，防止 region selector、env var 或 tenant-field-only 结果绕过证据裁决。"
    ),
    "workdir_facts": "已观察到 AGENTS.md、design/README.md、design/、tests/ 和 README.md；具体实现栈仍未知。",
    "open_questions": "无未解决问题",
}


def _residency_role_definition(key: str, name: str, archetype: str, body: str, posture: str) -> dict:
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


def data_residency_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    bundle["metadata"]["name"] = "数据驻留区域隔离治理"
    bundle["metadata"]["description"] = "治理 EU/US tenant 数据驻留、区域隔离、处理方、审计、导出和监控证据。"
    bundle["loop"]["name"] = "数据驻留区域隔离治理"
    bundle["collaboration_summary"] = (
        "这个 data residency / regional isolation 任务需要 multi-round Loopora governance，因为 one Agent pass、"
        "direct chat、one-off handling 或 UI/env/tenant-field demo 会太晚发现错区写入、跨区复制、processor mismatch、"
        "DPA 缺口、support/admin access 泄露或 observability trace 跨区。后续轮次里的 residency contract inspection、"
        "Regional Isolation Builder、evidence inspection 和 GateKeeper 会分别产生 proof、handoff、Blocking decision "
        "与 verdict context。这个 bundle 把判断投射到 spec 的 success/fake-done/evidence/residual-risk 规则、"
        "roles 的差异化责任、workflow 的 handoff/evidence query，以及按 Proven、Weak、Unproven、Blocking "
        "和 Residual risk buckets 裁决的 GateKeeper closure。"
    )
    bundle["spec"]["markdown"] = """# Task

构建企业客户 data residency / regional isolation 的 EU/US tenant 数据面治理路径。普通 regional sales dashboard、全平台数据仓库重构和非驻留报表不在本轮范围内。

# Done When

- EU tenant 的 primary DB、object storage、search index、cache、queue、backup、logs、analytics export 和 third-party processor 都只落在 EU region，US tenant 只落在 US region。
- Region routing、tenant residency policy 和 encryption key region 不能错。
- Cross-region failover 不能把 EU 数据复制到 US，migration/backfill 不跨区。
- Support/admin access、data export、audit log 和 observability trace 都不能泄露跨区数据。
- Subprocessor allowlist 和 DPA 标记正确，monitoring 能发现 cross-region egress、wrong-region write、stale residency policy 和 processor mismatch。

# Success Surface

- Reviewer 可以追踪 EU/US tenant 的 DB、storage、search、cache、queue、backup、logs、analytics、processor/DPA、routing、key-region、failover、migration、access/export/audit/trace 和 monitoring evidence，并看到 wrong-region negative proof。

# Fake Done

- 不允许因为 UI 显示 region=EU、配置 env var、tenant 表有 region 字段、dashboard 有区域筛选，或只跑一个 EU happy path 而通过。
- 如果缺少真实数据面区域证明、wrong-region write 负向、cross-region egress monitoring、processor/DPA、failover、migration/backfill、support/admin access、data export、audit log、observability trace 或 local-governance evidence，不允许通过。

# Evidence Preferences

- 优先使用 EU/US tenant region proof、wrong-region write negatives、cross-region egress monitoring、processor/DPA/subprocessor allowlist checks、failover and migration/backfill proof、key-region checks、support/admin access and data export negatives、audit log and observability trace verification。
- Residency Evidence Inspector 应把 thin evidence 标为 Weak，把 unsupported claims 标为 Unproven，把 closure blockers 标为 Blocking，把非驻留 dashboard polish 标为 Residual risk。

# Judgment Tradeoffs

- 严格区域证据优先于快速上线 region selector；宁可先交窄而可审计的 EU/US 数据面证明，也不要 UI/env/tenant-field demo 掩盖跨区或合规风险。

# Residual Risk

轻微 dashboard 文案或非驻留报表 polish 只有在标为 Residual risk 且有 owner 与 follow-up 时才可保留。缺少 DB/storage/search/cache/queue/backup/logs/analytics/processor、wrong-region、DPA、failover、migration、access/export/audit/trace、monitoring 或 local-governance evidence 时必须 fail closed。

# Role Notes

## Residency Contract Inspector Notes

实现前固定 EU/US 数据面、region routing、residency policy、key region、failover、migration/backfill、processor/DPA、access/export/audit/trace 和 monitoring proof targets。

## Regional Isolation Builder Notes

读取 residency contract handoff 和 project-local governance；只实现区域路由、存储/索引/队列/备份/日志/processor 边界、导出/访问限制和监控证据。

## Residency Evidence Inspector Notes

验证 DB/storage/search/cache/queue/backup/logs/analytics/processor 的 region proof、wrong-region write、cross-region egress、processor mismatch、DPA、failover、migration、access/export/audit/trace 和 local-governance evidence。

## Residency GateKeeper Notes

读取 contract 与 evidence handoffs；查询 data residency、tenant isolation、provider/DPA、backup、search、analytics、privacy、data export、monitoring、audit integrity 和 local-governance evidence；只有核心风险 Proven 或可管理 Residual risk 时 finish。
"""
    bundle["role_definitions"] = [
        _residency_role_definition(
            "residency-contract-inspector",
            "数据驻留 Contract Inspector",
            "inspector",
            "实现前只读检查并冻结 EU/US 数据面、处理方、failover、migration、access/export/audit/trace 和 monitoring proof targets。",
            "任何 UI/env/tenant-field-only、wrong-region 或 missing-DPA 样本都应标为 Blocking。",
        ),
        _residency_role_definition(
            "regional-isolation-builder",
            "区域隔离 Builder",
            "builder",
            "基于 residency contract handoff 构建区域路由、数据面边界、处理方限制、导出/访问限制和监控。",
            "优先窄而可审计的 EU/US 数据面 proof，不接受 region selector demo。",
        ),
        _residency_role_definition(
            "residency-evidence-inspector",
            "数据驻留证据 Inspector",
            "inspector",
            "验证 region proof、wrong-region negatives、processor/DPA、failover、migration、access/export/audit/trace 和 monitoring。",
            "把薄弱 residency、processor、access、audit、trace 或 monitoring evidence 分类为 Weak、Unproven 或 Blocking。",
        ),
        _residency_role_definition(
            "residency-gatekeeper",
            "Residency 证据 GateKeeper",
            "gatekeeper",
            "从 contract 和 evidence handoffs 裁决 regional isolation readiness。",
            "缺少数据面、processor/DPA、wrong-region、failover、migration、access/export/audit/trace、monitoring 或 local-governance evidence 时 fail closed。",
        ),
    ]
    bundle["workflow"] = {
        "version": 1,
        "preset": "",
        "collaboration_intent": (
            "先用只读 residency contract inspection 固定 EU/US 数据面、routing/policy/key、processor/DPA、"
            "failover、migration、access/export/audit/trace 和 monitoring proof targets；Regional Isolation Builder "
            "读取该 handoff 后只构建可审计区域边界；Residency Evidence Inspector 再验证 wrong-region、processor、DPA、"
            "access/export/audit/trace 和监控证据；GateKeeper 汇入 contract/evidence handoffs 与 evidence_query，"
            "让 UI region、env var、tenant-field-only 或 weak-proof 状态在 closure 前暴露并阻断。"
        ),
        "roles": [
            {"id": "contract_inspector", "role_definition_key": "residency-contract-inspector"},
            {"id": "regional_builder", "role_definition_key": "regional-isolation-builder"},
            {"id": "evidence_inspector", "role_definition_key": "residency-evidence-inspector"},
            {"id": "gatekeeper", "role_definition_key": "residency-gatekeeper"},
        ],
        "steps": [
            {"id": "residency_contract_step", "role_id": "contract_inspector", "on_pass": "continue"},
            {
                "id": "regional_isolation_builder_step",
                "role_id": "regional_builder",
                "inputs": {"handoffs_from": ["residency_contract_step"], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": "residency_evidence_inspection_step",
                "role_id": "evidence_inspector",
                "inputs": {
                    "handoffs_from": ["regional_isolation_builder_step"],
                    "evidence_query": {
                        "archetypes": ["builder"],
                        "verifies": [
                            "data-residency",
                            "tenant-isolation",
                            "provider-contract",
                            "backup-restore",
                            "search-index",
                            "analytics",
                            "privacy-redaction",
                            "data-export",
                            "monitoring",
                            "audit-integrity",
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
                    "handoffs_from": ["residency_contract_step", "residency_evidence_inspection_step"],
                    "evidence_query": {
                        "archetypes": ["builder", "inspector"],
                        "verifies": [
                            "data-residency",
                            "tenant-isolation",
                            "provider-contract",
                            "backup-restore",
                            "search-index",
                            "analytics",
                            "privacy-redaction",
                            "data-export",
                            "monitoring",
                            "audit-integrity",
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


class DataResidencyAlignmentExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message="请确认这份 data residency 工作协议；确认后我再生成 Loop bundle。",
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = (
                "Data residency 协议：先固定 EU/US 数据面、处理方、failover、migration、access/export/audit/trace 和监控证据，"
                "再实现区域边界，最后由严格 GateKeeper 裁决。"
            )
            payload["readiness_checklist"] = {**DATA_RESIDENCY_CHECKLIST, "explicit_confirmation": False}
            payload["readiness_evidence"] = {**DATA_RESIDENCY_EVIDENCE, "open_questions": ""}
            payload["decision_options"] = [
                {
                    "id": "confirm_residency",
                    "label": "确认 data residency 协议（推荐）",
                    "description": "生成以区域数据面、处理方、错区负向和监控证据为核心的 workflow。",
                    "recommended": True,
                    "user_reply": "确认，采用这份 data residency 工作协议。",
                },
                {
                    "id": "adjust_residency_scope",
                    "label": "调整范围",
                    "description": "先修改数据面、处理方或阻断策略。",
                    "recommended": False,
                    "user_reply": "我想调整 data residency 工作协议：",
                },
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="已生成 data residency Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(data_residency_bundle(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = (
            "Data residency 协议：先固定 EU/US 数据面、处理方、failover、migration、access/export/audit/trace 和监控证据，"
            "再实现区域边界，最后由严格 GateKeeper 裁决。"
        )
        payload["readiness_evidence"] = DATA_RESIDENCY_EVIDENCE
        return payload


def test_success_categories_detect_data_residency_without_backup_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(DATA_RESIDENCY_TASK_TEXT)]
    backup_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means backup restore recovery proves cross-region snapshot restore, RPO/RTO, checksum, "
            "row count, and application smoke tests."
        )
    ]
    weak_region_field_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须让 UI 显示 region=EU，配置 env var，并在数据库 tenant 表加 region 字段。"
        )
    ]

    assert "data/residency-regional-isolation" in labels
    assert "audit/log" in labels
    assert "permission/auth" in labels
    assert "data/export/report" in labels
    assert "migration/rollback-integrity" in labels
    assert "regression/monitoring-guard" in labels
    assert "external/provider-contract" in labels
    assert "backup/restore-recovery" in labels
    assert "search/index-consistency" in labels
    assert "analytics/event-integrity" in labels
    assert "privacy/secrets-redaction" in labels
    assert "access/support-impersonation-breakglass" not in labels
    assert "backup/restore-recovery" in backup_labels
    assert "data/residency-regional-isolation" not in backup_labels
    assert "data/residency-regional-isolation" not in weak_region_field_labels


def test_fake_done_and_evidence_categories_detect_data_residency_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(DATA_RESIDENCY_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(DATA_RESIDENCY_TASK_TEXT)
    ]

    assert "data/residency-regional-isolation" in fake_labels
    assert "data/residency-regional-isolation" in evidence_labels
    assert "backup/restore-recovery" in evidence_labels
    assert "search/index-consistency" in evidence_labels
    assert "analytics/event-integrity" in evidence_labels
    assert "external/provider-contract" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels
    assert "access/support-impersonation-breakglass" not in fake_labels
    assert "access/support-impersonation-breakglass" not in evidence_labels


def test_alignment_agreement_requires_data_residency_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show a region selector, set an env var, and add a region field to the tenant table.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means data residency and regional isolation prove EU tenant primary DB, object storage, "
                    "search index, cache, queue, backup, logs, analytics export, and third-party processor stay in "
                    "EU region while US tenant data stays in US region; region routing, tenant residency policy, "
                    "encryption key region, cross-region failover, migration/backfill, support/admin access, data "
                    "export, audit log, observability trace, subprocessor allowlist, DPA, and monitoring are covered."
                ),
                "fake_done_risks": (
                    "For data residency/regional isolation, UI region=EU, an env var, or a tenant table region field "
                    "without DB/storage/search/cache/queue/backup/logs/analytics/processor region proof, wrong-region "
                    "write negatives, cross-region egress monitoring, processor/DPA checks, access/export/audit/trace "
                    "proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include region proof for primary DB, object storage, search index, cache, queue, "
                    "backup, logs, analytics export, processor/subprocessor, DPA, region routing, tenant residency "
                    "policy, encryption key region, failover, migration/backfill, support/admin access, data export, "
                    "audit log, observability trace, cross-region egress, wrong-region write, stale policy, and "
                    "processor mismatch."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "data/residency-regional-isolation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data/residency-regional-isolation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data/residency-regional-isolation" in issue for issue in issues)


def test_alignment_service_accepts_confirmed_data_residency_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "residency-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing residency boundaries.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nRegional data boundaries.\n", encoding="utf-8")
    (workdir / "README.md").write_text("# Enterprise data platform\n\nEU/US residency surface.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    service.executor_factory = lambda: DataResidencyAlignmentExecutor(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=DATA_RESIDENCY_TASK_TEXT
        + " 我希望先固定数据面和 wrong-region 负向样本，再实现，最后让 GateKeeper 读取 contract/evidence handoff。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(created["id"], "确认，采用这份 data residency 工作协议。")
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
        "residency_contract_step",
        "regional_isolation_builder_step",
        "residency_evidence_inspection_step",
        "gatekeeper_step",
    ]
    assert steps[1]["inputs"]["handoffs_from"] == ["residency_contract_step"]
    assert inspector_inputs["handoffs_from"] == ["regional_isolation_builder_step"]
    assert inspector_inputs["evidence_query"]["verifies"] == [
        "data-residency",
        "tenant-isolation",
        "provider-contract",
        "backup-restore",
        "search-index",
        "analytics",
        "privacy-redaction",
        "data-export",
        "monitoring",
        "audit-integrity",
    ]
    assert gatekeeper_inputs["handoffs_from"] == ["residency_contract_step", "residency_evidence_inspection_step"]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "data-residency",
        "tenant-isolation",
        "provider-contract",
        "backup-restore",
        "search-index",
        "analytics",
        "privacy-redaction",
        "data-export",
        "monitoring",
        "audit-integrity",
        "local-governance",
    ]
    assert "tenant-field-only" in bundle["workflow"]["collaboration_intent"]
    assert "wrong-region" in bundle["workflow"]["collaboration_intent"]
    assert "role zoo" not in bundle["workflow"]["collaboration_intent"].lower()


def test_cli_agent_plan_data_residency_rounds_use_contract_first_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-data-residency",
    }
    first_summary = _invoke_data_residency_plan_round(runner, sample_workdir, message=DATA_RESIDENCY_TASK_TEXT, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_data_residency_plan_round(
        runner,
        sample_workdir,
        message=DATA_RESIDENCY_WORKFLOW_MESSAGE,
        env=env,
    )
    _assert_data_residency_agreement_round(second_summary)

    third_summary = _invoke_data_residency_plan_round(
        runner,
        sample_workdir,
        message="确认，采用这份 data residency 工作协议。",
        env=env,
    )
    _assert_data_residency_ready_round(third_summary, first_summary["alignment_session_id"])

    bundle_text = _data_residency_bundle_text(sample_workdir, first_summary["alignment_session_id"])
    _assert_data_residency_bundle(bundle_text, third_summary)


def _invoke_data_residency_plan_round(runner: CliRunner, workdir: Path, *, message: str, env: dict) -> dict:
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


def _assert_data_residency_agreement_round(summary: dict) -> None:
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "continue_alignment_dialogue"
    assert summary["alignment_stage"] == "agreement_ready"
    assert summary["question_action"]["must_wait_for_user_reply"] is True
    agreement_text = summary["alignment_assistant_message"]
    assert "Residency Contract Inspector" in agreement_text
    assert "Regional Isolation Builder" in agreement_text
    assert "Residency Evidence Inspector" in agreement_text
    assert "GateKeeper" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Repair Builder" not in agreement_text


def _assert_data_residency_ready_round(summary: dict, alignment_session_id: str) -> None:
    assert summary["ready"] is True
    assert summary["continued_alignment_session"] is True
    assert summary["alignment_session_id"] == alignment_session_id
    traceability = summary["ready_review_projection"]["traceability"]
    assert traceability["mapped_count"] == traceability["required_count"]
    assert summary["ready_review_projection"]["diagnostic_count"] == 0


def _data_residency_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_data_residency_bundle(bundle_text: str, third_summary: dict) -> None:
    bundle = load_bundle_text(bundle_text)
    workflow = bundle["workflow"]
    assert bundle["metadata"]["name"] == "数据驻留区域隔离 Loop"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "residency-contract-inspector",
        "regional-isolation-builder",
        "residency-evidence-inspector",
        "residency-gatekeeper",
    ]
    names_by_key = {role["key"]: role["name"] for role in bundle["role_definitions"]}
    assert names_by_key["residency-contract-inspector"] == "数据驻留 Contract Inspector"
    assert names_by_key["regional-isolation-builder"] == "区域隔离 Builder"
    assert names_by_key["residency-evidence-inspector"] == "数据驻留证据 Inspector"
    assert names_by_key["residency-gatekeeper"] == "数据驻留 GateKeeper"
    assert workflow["preset"] == "data-residency-contract-first"
    assert [step["id"] for step in workflow["steps"]] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
        "residency_evidence_inspection_step",
        "residency_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["residency_contract_inspection_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "residency_contract_inspection_step",
        "regional_isolation_builder_step",
        "residency_evidence_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "regional-isolation",
        "tenant-isolation",
        "provider-contract",
        "backup-restore",
        "search-index",
        "event-integrity",
        "privacy-redaction",
        "data-export",
        "monitoring",
        "audit-log",
        "migration-rollback",
        "permission-auth",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    for forbidden_text in (
        "任务证据修复 Loop",
        "Task Evidence Repair Loop",
        "Builder -> Inspector -> Guide",
        "Repair Builder",
        "修复 Builder",
        "Guide 只把弱证据",
        "notification-subscription-contract",
        "schedule-timezone-contract",
        "usage-quota-contract",
    ):
        assert forbidden_text not in bundle_text
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(third_summary, bundle) == []


def test_agent_first_traceability_blocks_region_field_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Add a region selector, set APP_REGION=EU, and add a tenant table region field.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求 UI 显示 region=EU、配置 APP_REGION，并让 tenant 表有 region 字段。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: storage, index, cache, queue, backup, logs, analytics, processor, routing, key, "
        "failover, migration, access, export, audit, observability, DPA, and monitoring proof can be handled later.\n"
        "  Owner: compliance platform owner\n"
        "  Follow-up: add regional proof later.\n"
        "  Acceptance path: GateKeeper can pass after the UI shows the selected region and the tenant table stores it.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 region selector、APP_REGION 配置和 tenant 表 region 字段，不处理真实区域落地、处理方、"
        "跨区访问、监控或审计证明。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat the region selector, env var, and tenant table region field as enough for this pass; storage, index, "
        "cache, queue, backup, logs, analytics, processor, routing, key, failover, migration, access, export, audit, "
        "observability, DPA, and monitoring proof can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(DATA_RESIDENCY_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "data/residency-regional-isolation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "data/residency-regional-isolation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "data/residency-regional-isolation" in issue for issue in issues)
