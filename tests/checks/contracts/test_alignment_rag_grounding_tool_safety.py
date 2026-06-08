from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan
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


RAG_GROUNDING_TASK_TEXT = (
    "我要做企业知识库 RAG support chatbot。成功必须证明答案 grounded in retrieved source chunks，"
    "citation/source span 能回到文档版本，retrieval ACL / tenant filtering 正确，prompt injection in documents "
    "不能让模型泄露系统提示词或调用未授权 tool，PII/secrets 要 redaction，hallucination 要 fallback/handoff，"
    "top-k recall、answer faithfulness、citation precision、no-answer behavior 和 multilingual queries 都在 eval set 里。"
    "假完成是只让一个 demo question answered、只看 answer looks plausible、只跑 embedding search、或只在 UI 显示 citations。"
    "证据要包含 golden Q&A eval set、negative prompt injection docs、permission-filtered retrieval cases、"
    "citation span verification、tool-call allowlist proof、PII leak tests、human review rubric 和 regression monitoring。"
)

RAG_LONG_CHAIN_CHECKLIST = {
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

RAG_LONG_CHAIN_EVIDENCE = {
    "loop_fit": (
        "这个 RAG support 任务需要 Loopora，因为 ingestion、retrieval ACL、answer/tool gating、eval review "
        "和 monitoring 会分别产生新的 proof 与 handoff；只靠 one Agent pass、直接聊天或最终人工 review 会太晚暴露风险。"
    ),
    "task_scope": (
        "范围限定为企业知识库 RAG support chatbot 的 grounding 路径：document version grounding、retrieval permission、"
        "tool safety、redaction、fallback、eval set 和 monitoring；聊天润色与非 RAG support 流程不在本轮。"
    ),
    "success_surface": (
        "成功面是 answer 能追溯到 retrieved source chunks 与 document versions，retrieval 按权限过滤，tool 行为安全，"
        "PII/secrets 被 redaction，hallucination 有 fallback/handoff，并有 eval metrics、human review 和 monitoring evidence。"
    ),
    "fake_done_risks": (
        "必须拒绝只回答一个 demo question、只看 answer plausible、只跑 embedding search、只在 UI 显示 citation "
        "但没有 source-span verification，以及缺少 permission、prompt-injection、tool-call 或 PII 负例证据的通过。"
    ),
    "evidence_preferences": (
        "可信证据是 golden Q&A eval set、citation-span verification、permission-filtered retrieval cases、"
        "negative prompt-injection docs、tool allowlist proof、PII leak tests、human review rubric 和 monitoring。"
        "最终证据必须区分 Proven、Weak、Unproven、Blocking 和 Residual risk buckets 才能 closure。"
    ),
    "execution_strategy": (
        "先固定 RAG contract，再分别构建 ingestion、retrieval ACL 和 answer/tool gating；让 eval inspection 暴露 "
        "Weak 或 Blocking proof，再只 harden 缺失证据，最后交给 GateKeeper closure。"
    ),
    "residual_risk_policy": (
        "轻微 answer-quality tuning 只能作为 Residual risk 留下，并必须有 owner 与 follow-up；缺少 source-span、permission、"
        "prompt-injection、tool safety、PII、fallback、eval 或 monitoring 证据时必须 fail closed。"
    ),
    "judgment_tradeoffs": (
        "判断取舍是宁可慢一点拿到 grounded proof，也不要 broad chat demo；当 permission、privacy、tool safety "
        "或 eval-set coverage 的证据 Weak、Unproven 或缺失时，strict blocking 优先于速度。"
    ),
    "local_governance": (
        "项目本地 marker 包含 AGENTS.md、design/README.md、design/ 和 tests/；Builder 要先读取它们，"
        "Inspector 验证相关 design/test obligation，GateKeeper 把跳过治理视为 Weak、Unproven 或 Blocking，且不编造内容。"
    ),
    "role_posture": (
        "Contract Inspector 固定 proof targets，阶段 Builder 只构建窄 handoff，Evaluation Inspector 验证 "
        "grounding/tool/eval/privacy/permission evidence，Evidence Builder 只修复 proof，GateKeeper 负责 fail closed。"
    ),
    "workflow_shape": (
        "长链 workflow 是必要的，因为 ingestion、retrieval ACL、answer/tool gating、eval review 和 evidence hardening "
        "都有不同 artifact；GateKeeper 读取 contract、review、hardening handoff 与 evidence query 后再裁决。"
    ),
    "workdir_facts": "已观察到的项目事实是 AGENTS.md、design/README.md、design/、tests/ 和 README.md；implementation stack 仍未知。",
    "open_questions": "无未解决问题",
}


def test_cli_agent_plan_rag_grounding_rounds_use_long_chain_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-rag-grounding",
    }

    first_summary = _invoke_rag_plan_round(runner, sample_workdir, message=RAG_GROUNDING_TASK_TEXT, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_rag_plan_round(
        runner,
        sample_workdir,
        message=(
            "补充判断：这次不要先做聊天 UI。先由 RAG Contract Inspector 固定 document version、source span、"
            "retrieval ACL/tenant filtering、prompt-injection negative docs、tool allowlist、PII redaction、"
            "fallback/no-answer、multilingual eval、human review rubric、monitoring 和 local governance proof targets。"
            "然后 Corpus Ingestion Builder、Retrieval ACL Builder、Answer Tooling Builder 分阶段构建窄 handoff；"
            "RAG Evaluation Inspector 读取三个 builder handoff，检查 citation span、permission-filtered retrieval、"
            "prompt injection、unauthorized tool call、PII leak、faithfulness、no-answer、multilingual eval、human review、monitoring。"
            "Evidence Hardening Builder 只修 evaluation 指出的 Weak/Unproven/Blocking proof gaps。"
            "GateKeeper 必须读取 contract、evaluation 和 hardening handoffs；缺少 grounding、permission/tenant、"
            "tool safety、privacy redaction、eval set、human review、monitoring 或 local governance 证据就 fail closed。"
        ),
        env=env,
    )
    _assert_rag_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_rag_plan_round(
        runner,
        sample_workdir,
        message="确认，采用这份 RAG grounding long-chain 工作协议。",
        env=env,
    )
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    bundle_text = _rag_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_rag_ready_bundle(bundle_text)


def _invoke_rag_plan_round(
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


def _assert_rag_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["alignment_stage"] == "agreement_ready"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    agreement_text = second_summary["alignment_assistant_message"]
    for term in (
        "RAG Contract Inspector",
        "Corpus Ingestion Builder",
        "Retrieval ACL Builder",
        "Answer Tooling Builder",
        "RAG Evaluation Inspector",
        "Evidence Hardening Builder",
        "RAG GateKeeper",
    ):
        assert term in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text
    assert "Repair Builder" not in agreement_text
    assert "Search Quality Builder" not in agreement_text
    assert "Search Index Builder" not in agreement_text


def _rag_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_rag_ready_bundle(bundle_text: str) -> None:
    bundle = load_bundle_text(bundle_text)
    workflow = bundle["workflow"]
    assert workflow["preset"] == "rag-grounding-long-chain"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "rag-contract-inspector",
        "corpus-ingestion-builder",
        "retrieval-acl-builder",
        "answer-tooling-builder",
        "rag-evaluation-inspector",
        "evidence-hardening-builder",
        "rag-gatekeeper",
    ]
    assert [step["id"] for step in workflow["steps"]] == [
        "contract_inspection_step",
        "ingestion_builder_step",
        "retrieval_builder_step",
        "answer_builder_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
        "gatekeeper_step",
    ]
    assert workflow["steps"][4]["inputs"]["handoffs_from"] == [
        "ingestion_builder_step",
        "retrieval_builder_step",
        "answer_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "contract_inspection_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"] == [
        "rag-grounding",
        "tool-safety",
        "permission-auth",
        "privacy-redaction",
        "eval-set",
        "human-review",
        "monitoring",
        "local-governance",
    ]
    assert "Long-Chain Workflow Notes" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "task-evidence-repair" not in bundle_text


def _rag_role_definition(key: str, name: str, archetype: str, body: str, posture: str) -> dict:
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


def rag_long_chain_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    bundle["metadata"]["name"] = "RAG Grounding 长链治理 Bundle"
    bundle["metadata"]["description"] = "治理企业 RAG grounding、tool safety、eval、privacy 和 monitoring 证据。"
    bundle["loop"]["name"] = "RAG Grounding 长链治理 Bundle"
    bundle["collaboration_summary"] = (
        "这个 RAG 任务需要多轮 Loopora governance，因为 one Agent pass、direct chat、one-off handling 或 demo-only "
        "validation 会太晚发现 grounding、permission、tool-safety、privacy、eval 与 monitoring 缺口。后续 ingestion、"
        "retrieval ACL、answer/tool gating、eval review 和 evidence-hardening 阶段会各自产生新的 proof、handoff、"
        "repair decision 与 GateKeeper verdict context。判断取舍是证据优先于速度和 demo 完整度，Weak 或 Unproven "
        "的核心证据必须阻断 closure。这个 bundle 把判断投射到 spec 的 success/fake-done/evidence "
        "规则、阶段专属角色、显式 workflow handoff、evidence query，以及基于 Proven、Weak、Unproven、Blocking "
        "和 Residual risk buckets 的严格 GateKeeper closure。"
    )
    bundle["spec"]["markdown"] = """# Task

构建企业知识库 RAG support chatbot 的 grounding 路径。聊天样式润色、宽泛产品分析和非 RAG support workflow 不在本轮范围内。

# Done When

- Answers 必须 grounded in retrieved source chunks，citation/source spans 能回到 document versions。
- Retrieval ACL 和 tenant filtering 能阻止 unauthorized source leakage。
- Prompt-injection documents 不能泄露 system prompts，也不能触发 unauthorized tool calls。
- PII/secrets 已 redacted，hallucination 会 fallback 或 hand off，no-answer behavior 明确。
- Golden Q&A、faithfulness、citation precision、top-k recall、multilingual queries、human review 和 monitoring evidence 都存在。

# Success Surface

- Reviewer 可以把最终 answer 追溯到 source chunks、document versions、permission-filtered retrieval、tool allowlist proof、redaction checks、eval-set output、human review 和 monitoring。

# Fake Done

- 不允许因为 one demo question answered、plausible answer text、embedding search results、没有 source spans 的 UI citations，或没有 negative tests 的 provider/tool success 而通过。
- 如果缺少 permission、tenant、prompt-injection、unauthorized tool-call、PII、no-answer、eval-set、human-review 或 monitoring evidence，不允许通过。

# Evidence Preferences

- 优先使用 golden Q&A eval sets、citation-span verification、permission-filtered retrieval cases、negative prompt-injection docs、tool-call allowlist proof、PII leak tests、human review rubric 和 monitoring artifacts。
- Evaluation Inspector 应把 thin evidence 标为 Weak，把 unsupported claims 标为 Unproven，把 closure blockers 标为 Blocking，把轻微 answer-quality tuning 标为 Residual risk。

# Judgment Tradeoffs

- 证据优先于速度和 demo 完整度；当 grounding、permission、privacy、tool safety 或 eval set 证据 Weak、Unproven 或缺失时，严格阻断优先于务实推进。

# Residual Risk

轻微 answer-quality tuning 只有在标为 Residual risk 且有 owner 与 follow-up 时才可保留。缺少 source-span、permission、tenant isolation、prompt-injection、tool safety、PII、fallback、eval-set、human-review、monitoring 或 local-governance evidence 时必须 fail closed。

# Role Notes

## RAG Contract Inspector Notes

实现前固定 document-version、source-span、permission、tenant、prompt-injection、tool allowlist、PII、fallback、multilingual eval、human-review、monitoring 和 local-governance proof targets。

## Corpus Ingestion Builder Notes

只构建 document ingestion 与 version/source-span artifacts，先读取适用的 project governance，并留下 retrieval ACL handoff。

## Retrieval ACL Builder Notes

只基于 ingestion handoff 构建 retrieval filtering、tenant isolation、permission cases 和 retrieval evidence。

## Answer Tooling Builder Notes

只基于 retrieval evidence 构建 grounded answering、citation rendering、tool gating、redaction 和 fallback behavior。

## RAG Evaluation Inspector Notes

验证 citation spans、permission-filtered retrieval、prompt-injection negatives、unauthorized tool calls、PII leaks、faithfulness、no-answer behavior、multilingual eval、human review、monitoring 和 local-governance evidence。

## Evidence Hardening Builder Notes

只修复 evaluation review 指定的 missing proof；不要扩大 chatbot scope。

## RAG Evidence GateKeeper Notes

读取 contract、evaluation 和 hardening handoffs；向上游 query grounding、tool safety、permission、privacy、eval set、human review、monitoring 和 local governance 证据；只在 evidence-backed Proven 或 managed Residual risk 下 finish。
"""
    bundle["role_definitions"] = [
        _rag_role_definition(
            "rag-contract-inspector",
            "RAG 契约检查员",
            "inspector",
            "实现前检查并冻结 RAG proof targets。",
            "Builder 开始前把缺失 proof target 标为 Blocking。",
        ),
        _rag_role_definition(
            "corpus-ingestion-builder",
            "语料 Ingestion Builder",
            "builder",
            "只构建 document ingestion、versioning、source-span artifacts 和 ingestion handoff。",
            "保留 contract proof targets，并清楚暴露 Weak ingestion evidence。",
        ),
        _rag_role_definition(
            "retrieval-acl-builder",
            "检索 ACL Builder",
            "builder",
            "只构建 permission-filtered retrieval、tenant isolation 和 retrieval proof。",
            "Retrieval ACL evidence 可审计前，不进入 answering。",
        ),
        _rag_role_definition(
            "answer-tooling-builder",
            "回答与工具 Builder",
            "builder",
            "只构建 grounded answering、citations、tool gating、redaction 和 fallback。",
            "优先窄而 grounded 的行为，不接受 plausible answer demo。",
        ),
        _rag_role_definition(
            "rag-evaluation-inspector",
            "RAG 评估 Inspector",
            "inspector",
            "验证 grounding、permissions、prompt injection、tools、PII、eval set、human review 和 monitoring。",
            "把薄弱 grounding、privacy、permission、tool 或 eval evidence 分类为 Weak、Unproven 或 Blocking。",
        ),
        _rag_role_definition(
            "evidence-hardening-builder",
            "证据加固 Builder",
            "builder",
            "只修复 evaluation review 点名的 proof gaps。",
            "补充 evidence artifacts，但不扩大 chatbot scope。",
        ),
        _rag_role_definition(
            "rag-gatekeeper",
            "RAG 证据 GateKeeper",
            "gatekeeper",
            "从 contract、phase、evaluation 和 hardening handoffs 裁决最终 RAG readiness。",
            "缺少 grounding、permission、privacy、tool-safety、eval、monitoring 或 local-governance evidence 时 fail closed。",
        ),
    ]
    bundle["workflow"] = {
        "version": 1,
        "preset": "",
        "collaboration_intent": (
            "使用长链 RAG workflow，因为 ingestion、retrieval ACL、answer/tool gating、eval review 和 evidence hardening "
            "会分别产生 distinct proof target 与 handoff。Evaluation review 会改变下一个 Builder 的 repair scope，"
            "证据优先于速度和 demo 完整度，Weak 或 Unproven proof 必须先修复或阻断。"
            "GateKeeper 汇入 contract、review、hardening handoffs 与 verified evidence，让 demo-only、plausible-answer、"
            "UI-citation-only 或 weak-proof 状态在 closure 前暴露。"
        ),
        "roles": [
            {"id": "contract_inspector", "role_definition_key": "rag-contract-inspector"},
            {"id": "ingestion_builder", "role_definition_key": "corpus-ingestion-builder"},
            {"id": "retrieval_builder", "role_definition_key": "retrieval-acl-builder"},
            {"id": "answer_builder", "role_definition_key": "answer-tooling-builder"},
            {"id": "evaluation_inspector", "role_definition_key": "rag-evaluation-inspector"},
            {"id": "evidence_builder", "role_definition_key": "evidence-hardening-builder"},
            {"id": "gatekeeper", "role_definition_key": "rag-gatekeeper"},
        ],
        "steps": [
            {"id": "contract_inspection_step", "role_id": "contract_inspector", "on_pass": "continue"},
            {"id": "ingestion_builder_step", "role_id": "ingestion_builder", "inputs": {"handoffs_from": ["contract_inspection_step"], "iteration_memory": "summary_only"}, "on_pass": "continue"},
            {"id": "retrieval_builder_step", "role_id": "retrieval_builder", "inputs": {"handoffs_from": ["ingestion_builder_step"], "iteration_memory": "same_step"}, "on_pass": "continue"},
            {"id": "answer_builder_step", "role_id": "answer_builder", "inputs": {"handoffs_from": ["retrieval_builder_step"], "iteration_memory": "same_step"}, "on_pass": "continue"},
            {
                "id": "evaluation_inspection_step",
                "role_id": "evaluation_inspector",
                "inputs": {
                    "handoffs_from": ["ingestion_builder_step", "retrieval_builder_step", "answer_builder_step"],
                    "evidence_query": {"archetypes": ["builder"], "verifies": ["rag-grounding", "tool-safety", "permission-auth", "privacy-redaction", "eval-set", "monitoring"], "limit": 40},
                    "iteration_memory": "summary_only",
                },
                "on_pass": "continue",
            },
            {"id": "evidence_hardening_builder_step", "role_id": "evidence_builder", "inputs": {"handoffs_from": ["evaluation_inspection_step"], "iteration_memory": "summary_only"}, "on_pass": "continue"},
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "inputs": {
                    "handoffs_from": ["contract_inspection_step", "evaluation_inspection_step", "evidence_hardening_builder_step"],
                    "evidence_query": {"archetypes": ["builder", "inspector"], "verifies": ["rag-grounding", "tool-safety", "permission-auth", "privacy-redaction", "eval-set", "human-review", "monitoring", "local-governance"], "limit": 50},
                },
                "on_pass": "finish_run",
            },
        ],
    }
    return load_bundle_text(bundle_to_yaml(bundle))


class RagLongChainAlignmentExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message="请确认这份 RAG 长链工作协议；确认后我再生成 Loop bundle。",
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = (
                "RAG grounding 长链协议：先 contract，再 ingestion、retrieval、answer/tooling、eval、hardening，"
                "最后由 strict GateKeeper closure。"
            )
            payload["readiness_checklist"] = {**RAG_LONG_CHAIN_CHECKLIST, "explicit_confirmation": False}
            payload["readiness_evidence"] = {
                **RAG_LONG_CHAIN_EVIDENCE,
                "open_questions": "",
            }
            payload["decision_options"] = [
                {
                    "id": "confirm_rag_long_chain",
                    "label": "确认 RAG 长链协议（推荐）",
                    "description": "生成多阶段证据治理 workflow。",
                    "recommended": True,
                    "user_reply": "确认，采用这份 RAG 长链工作协议。",
                },
                {
                    "id": "adjust_rag_scope",
                    "label": "调整范围",
                    "description": "先修改证据或阻断策略。",
                    "recommended": False,
                    "user_reply": "我想调整 RAG 工作协议：",
                },
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="已生成 RAG 长链 Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(rag_long_chain_bundle(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = (
            "RAG grounding 长链协议：先 contract，再 ingestion、retrieval、answer/tooling、eval、hardening，"
            "最后由 strict GateKeeper closure。"
        )
        payload["readiness_evidence"] = RAG_LONG_CHAIN_EVIDENCE
        return payload


def test_success_categories_detect_rag_grounding_without_search_index_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(RAG_GROUNDING_TASK_TEXT)]
    search_index_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means full-text search index updates documents, filters tenant ACL, and proves reindex backfill."
        )
    ]
    generic_strategy_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means execution strategy records target evidence and Inspector coverage results."
        )
    ]

    assert "ai/rag-grounding-tool-safety" in labels
    assert "permission/auth" in labels
    assert "privacy/secrets-redaction" in labels
    assert "evaluation/eval-set" in labels
    assert "quality/human-review" in labels
    assert "regression/monitoring-guard" in labels
    assert "search/index-consistency" in search_index_labels
    assert "ai/rag-grounding-tool-safety" not in search_index_labels
    assert "ai/rag-grounding-tool-safety" not in generic_strategy_labels


def test_fake_done_and_evidence_categories_detect_rag_grounding_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(RAG_GROUNDING_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(RAG_GROUNDING_TASK_TEXT)
    ]

    assert "ai/rag-grounding-tool-safety" in fake_labels
    assert "ai/rag-grounding-tool-safety" in evidence_labels
    assert "evaluation/eval-set" in fake_labels
    assert "quality/human-review" in fake_labels
    assert "permission/auth" in evidence_labels
    assert "privacy/secrets-redaction" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels


def test_alignment_agreement_requires_rag_grounding_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Answer one demo question from embedding search and show citations in the chat UI.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means the RAG support chatbot proves grounded answers from retrieved source chunks, "
                    "citation/source spans back to document versions, retrieval ACL and tenant filtering, prompt "
                    "injection document resistance, unauthorized tool-call blocking, PII/secrets redaction, hallucination "
                    "fallback and handoff, top-k recall, answer faithfulness, citation precision, no-answer behavior, "
                    "multilingual queries, and eval-set coverage."
                ),
                "fake_done_risks": (
                    "A demo question answered, plausible-looking answer, embedding search result, or UI citations without "
                    "grounding, citation span verification, retrieval permissions, prompt-injection negatives, tool allowlist, "
                    "PII leak tests, fallback/handoff, eval set, human review, and monitoring proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include golden Q&A eval set, negative prompt-injection documents, permission-filtered "
                    "retrieval cases, citation span verification, tool-call allowlist proof, PII leak tests, human review "
                    "rubric, answer faithfulness, no-answer behavior, multilingual queries, and regression monitoring."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)
    assert any("fake-done risks" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)
    assert any("evidence preferences" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)


def test_alignment_service_accepts_confirmed_rag_long_chain_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "rag-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing RAG contracts.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nRAG boundaries.\n", encoding="utf-8")
    (workdir / "README.md").write_text("# RAG stack\n\nKnowledge-base chatbot.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    service.executor_factory = lambda: RagLongChainAlignmentExecutor(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=RAG_GROUNDING_TASK_TEXT
        + " 文档 ingestion、retrieval ACL、answer/tool gating、eval review 和 monitoring 是独立阶段；"
        + "GateKeeper 必须读取 contract、eval 和 hardening handoff，并按 evidence_query.verifies 查证。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(created["id"], "确认，采用这份 RAG 长链工作协议。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    steps = bundle["workflow"]["steps"]
    gatekeeper_inputs = steps[-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(ready, bundle) == []
    assert [step["id"] for step in steps] == [
        "contract_inspection_step",
        "ingestion_builder_step",
        "retrieval_builder_step",
        "answer_builder_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
        "gatekeeper_step",
    ]
    assert gatekeeper_inputs["handoffs_from"] == [
        "contract_inspection_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
    ]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "rag-grounding",
        "tool-safety",
        "permission-auth",
        "privacy-redaction",
        "eval-set",
        "human-review",
        "monitoring",
        "local-governance",
    ]
    assert "demo-only" in bundle["workflow"]["collaboration_intent"]
    assert "role zoo" not in bundle["workflow"]["collaboration_intent"].lower()


def test_default_task_anchored_plan_projects_rag_long_chain_workflow(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "default-rag-long-chain-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing RAG contracts.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nRAG boundaries.\n", encoding="utf-8")
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=RAG_GROUNDING_TASK_TEXT
        + " 这次请按长链判断：document ingestion、retrieval ACL、answer/tool gating、eval review、monitoring "
        + "和 evidence hardening 是独立阶段；GateKeeper 必须读取 contract、evaluation 和 hardening handoff。",
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    service.append_alignment_message(created["id"], "确认，采用这份 RAG 长链工作协议。")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    steps = bundle["workflow"]["steps"]
    gatekeeper_inputs = steps[-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert lint_alignment_bundle_semantics(bundle) == []
    assert alignment_bundle_agreement_traceability_issues(ready, bundle) == []
    ready_projection_text = str(
        {
            "traceability": preview["traceability"],
            "control_summary": preview["control_summary"],
            "bundle": preview["bundle"],
        }
    )
    bundle_text = Path(ready["bundle_path"]).read_text(encoding="utf-8")
    assert "确认，采用这份 RAG 长链工作协议" not in ready_projection_text
    assert "确认，采用这份 RAG 长链工作协议" not in bundle_text
    assert [step["id"] for step in steps] == [
        "contract_inspection_step",
        "ingestion_builder_step",
        "retrieval_builder_step",
        "answer_builder_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
        "gatekeeper_step",
    ]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "rag-contract-inspector",
        "corpus-ingestion-builder",
        "retrieval-acl-builder",
        "answer-tooling-builder",
        "rag-evaluation-inspector",
        "evidence-hardening-builder",
        "rag-gatekeeper",
    ]
    assert "build_task_loop" not in {step["id"] for step in steps}
    assert "long-chain RAG workflow" in bundle["workflow"]["collaboration_intent"]
    assert "demo-only" in bundle["workflow"]["collaboration_intent"]
    assert gatekeeper_inputs["handoffs_from"] == [
        "contract_inspection_step",
        "evaluation_inspection_step",
        "evidence_hardening_builder_step",
    ]
    assert gatekeeper_inputs["evidence_query"]["verifies"] == [
        "rag-grounding",
        "tool-safety",
        "permission-auth",
        "privacy-redaction",
        "eval-set",
        "human-review",
        "monitoring",
        "local-governance",
    ]
    spec_markdown = bundle["spec"]["markdown"]
    assert "# Long-Chain Workflow Notes" in spec_markdown
    assert "citation/source-span" in spec_markdown
    assert "prompt-injection negative docs" in spec_markdown
    assert "UI-citation-only" in spec_markdown


def test_agent_first_traceability_blocks_demo_question_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Answer one demo question from embedding search and show citations in the chat UI.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求一个 demo question answered、answer looks plausible、embedding search 返回结果、UI 显示 citations。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: grounding, source span verification, retrieval ACL, tenant filtering, prompt injection, "
        "tool allowlist, PII leak tests, fallback/handoff, eval set, human review, and monitoring proof can be handled later.\n"
        "  Owner: AI platform owner\n"
        "  Follow-up: add RAG grounding and tool-safety proof later.\n"
        "  Acceptance path: GateKeeper can pass after one demo answer and UI citations.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 demo question、embedding search 和 UI citations，不处理 source span、retrieval ACL、"
        "tenant filtering、prompt injection、tool allowlist、PII leak、fallback/handoff、eval set 或 monitoring proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat one plausible answer with UI citations as enough for this pass; RAG grounding, prompt injection, "
        "tool-call, privacy, eval, and monitoring proof can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(RAG_GROUNDING_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)
    assert any("fake-done risks" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)
    assert any("evidence preferences" in issue and "ai/rag-grounding-tool-safety" in issue for issue in issues)
