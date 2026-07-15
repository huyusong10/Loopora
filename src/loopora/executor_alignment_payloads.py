from __future__ import annotations

import json
import re
from dataclasses import dataclass

from loopora.alignment_traceability_terms import agent_candidate_task_anchor_terms
from loopora.executor_alignment_bundle_fixtures import (
    alignment_bundle_yaml,
    alignment_bundle_yaml_with_governance_markers_listed_as_facts,
    alignment_bundle_yaml_with_lineage_metadata,
    alignment_bundle_yaml_with_unsupported_observed_workdir_claim,
    alignment_bundle_yaml_without_semantics,
    alignment_chinese_bundle_yaml,
    alignment_chinese_bundle_yaml_with_english_visible_names,
    alignment_chinese_refund_repair_bundle_yaml,
    alignment_chinese_refactor_improvement_bundle_yaml,
    alignment_refund_repair_bundle_yaml,
    alignment_task_anchored_repair_bundle_yaml,
)
from loopora.executor_alignment_responses import (
    alignment_chinese_refund_agreement_response,
    alignment_chinese_readiness_evidence,
    alignment_default_bundle_response,
    alignment_refund_agreement_response,
    alignment_response,
)
from loopora.executor_alignment_agreement_responses import alignment_task_anchored_agreement_response
from loopora.executor_alignment_agreement_responses import alignment_chinese_refactor_improvement_agreement_response
from loopora.executor_alignment_preconfirmation_payloads import (
    AlignmentPreconfirmationPayloadRequest,
    alignment_preconfirmation_payload_for_scenario,
)
from loopora.service_alignment_language import alignment_message_is_language_neutral_confirmation

class FakePayloadError(RuntimeError):
    """Raised when the fake executor scenario should fail like a provider failure."""

def alignment_missing_readiness_evidence() -> dict[str, str]:
    return {
        "loop_fit": "ok",
        "task_scope": "ok",
        "success_surface": "ok",
        "fake_done_risks": "ok",
        "evidence_preferences": "ok",
        "execution_strategy": "ok",
        "residual_risk_policy": "ok",
        "judgment_tradeoffs": "ok",
        "local_governance": "ok",
        "role_posture": "ok",
        "workflow_shape": "ok",
        "workdir_facts": "ok",
        "open_questions": "",
    }

def alignment_readiness_issue_for_scenario(scenario: str) -> tuple[str, str, str] | None:
    issues = {
        "alignment_missing_residual_risk_readiness_evidence": (
            "residual_risk_policy",
            "",
            "我生成了 bundle，但没有说明残余风险策略。",
        ),
        "alignment_missing_loop_fit_readiness_evidence": (
            "loop_fit",
            "",
            "我生成了 bundle，但没有说明为什么需要 Loopora。",
        ),
        "alignment_contradictory_loop_fit_readiness_evidence": (
            "loop_fit",
            "One Agent pass plus one human review is enough, no later round would produce new evidence, and the judgment does not need to survive this chat.",
            "我生成了 bundle，但 Loopora fit 证据承认这其实不需要 Loopora。",
        ),
        "alignment_single_pass_sufficient_loop_fit_readiness_evidence": (
            "loop_fit",
            "A single implementation pass plus human review is sufficient for this task; no governed Loop should be needed.",
            "我生成了 bundle，但 Loopora fit 证据承认单轮实现已经足够。",
        ),
        "alignment_benchmark_only_loop_fit_readiness_evidence": (
            "loop_fit",
            "The stable benchmark is sufficient and benchmark-only validation is the whole judgment for this task.",
            "我生成了 bundle，但 Loopora fit 证据承认 benchmark-only 验证已经足够。",
        ),
        "alignment_chinese_direct_chat_loop_fit_readiness_evidence": (
            "loop_fit",
            "直接对话就够了，判断只需要本次聊天，不需要 Loopora。",
            "我生成了 bundle，但 Loopora fit 证据承认直接对话已经足够。",
        ),
        "alignment_vague_loop_fit_readiness_evidence": (
            "loop_fit",
            "This is a complex and important task with many parts to handle well.",
            "我生成了 bundle，但只说任务复杂。",
        ),
        "alignment_vague_task_scope_readiness_evidence": (
            "task_scope",
            "The task scope is clear enough to handle well.",
            "我生成了 bundle，但任务范围没有交付物或边界。",
        ),
        "alignment_vague_success_surface_readiness_evidence": (
            "success_surface",
            "The final result should be good and useful for the user.",
            "我生成了 bundle，但成功面没有可观察结果或证据面。",
        ),
        "alignment_single_marker_loop_fit_readiness_evidence": (
            "loop_fit",
            "This task needs human review before the user accepts the final result.",
            "我生成了 bundle，但只提到人工 review，没有说明 Loop 价值。",
        ),
        "alignment_loop_fit_without_new_evidence_readiness_evidence": (
            "loop_fit",
            "One Agent pass plus review is not enough because fake-done risk and GateKeeper judgment matter.",
            "我生成了 bundle，但没有说明后续轮次会产生什么新证据。",
        ),
        "alignment_vague_residual_risk_readiness_evidence": (
            "residual_risk_policy",
            "Some remaining risk is probably fine for this task.",
            "我生成了 bundle，但残余风险策略很泛。",
        ),
        "alignment_invented_workdir_facts_readiness_evidence": (
            "workdir_facts",
            "This is a React frontend app with existing browser tests and a standard build script.",
            "我生成了 bundle，但把未观察到的技术栈当作事实。",
        ),
        "alignment_invented_observed_workdir_facts_readiness_evidence": (
            "workdir_facts",
            "Observed workdir snapshot shows a React frontend app with browser tests and npm build scripts.",
            "我生成了 bundle，但用 observed 包装了未观察到的技术栈。",
        ),
        "alignment_vague_evidence_preferences_readiness_evidence": (
            "evidence_preferences",
            "The user needs enough proof to feel confident before the result is accepted.",
            "我生成了 bundle，但证据偏好没有具体证明类型。",
        ),
        "alignment_missing_execution_strategy_readiness_evidence": (
            "execution_strategy",
            "",
            "我生成了 bundle，但没有说明执行策略。",
        ),
        "alignment_vague_execution_strategy_readiness_evidence": (
            "execution_strategy",
            "The work should proceed iteratively and carefully until it is good enough.",
            "我生成了 bundle，但执行策略只是泛泛说迭代推进。",
        ),
        "alignment_vague_fake_done_readiness_evidence": (
            "fake_done_risks",
            "The result should avoid bugs and should be high quality.",
            "我生成了 bundle，但假完成风险只是泛泛说避免 bug。",
        ),
        "alignment_vague_role_posture_readiness_evidence": (
            "role_posture",
            "Use three roles to complete the task well.",
            "我生成了 bundle，但角色姿态没有区分责任。",
        ),
        "alignment_vague_judgment_tradeoffs_readiness_evidence": (
            "judgment_tradeoffs",
            "The task should be handled with a good balance of quality and progress.",
            "我生成了 bundle，但判断取舍只是泛泛说平衡质量和进展。",
        ),
        "alignment_missing_local_governance_readiness_evidence": (
            "local_governance",
            "",
            "我生成了 bundle，但没有说明本地治理责任。",
        ),
        "alignment_marker_list_local_governance_readiness_evidence": (
            "local_governance",
            "AGENTS.md, design/README.md, design/, and tests/ are visible governance markers.",
            "我生成了 bundle，但本地治理只列 marker，没有说明角色责任。",
        ),
        "alignment_global_persona_readiness_evidence": (
            "judgment_tradeoffs",
            "Always remember the user's global preference memory: prefer fast-looking progress over proof across all tasks.",
            "我生成了 bundle，但把任务取舍写成全局偏好记忆。",
        ),
        "alignment_role_posture_without_gatekeeper_readiness_evidence": (
            "role_posture",
            "Builder leaves evidence and Inspector reviews the handoff carefully before the work continues.",
            "我生成了 bundle，但角色姿态没有最终裁决责任。",
        ),
        "alignment_vague_workflow_shape_readiness_evidence": (
            "workflow_shape",
            "Builder then checker.",
            "我生成了 bundle，但 workflow 只有顺序没有理由。",
        ),
        "alignment_workflow_shape_without_error_exposure_readiness_evidence": (
            "workflow_shape",
            "Builder -> Inspector -> GateKeeper fits because a focused slice is built, then inspected, then gated.",
            "我生成了 bundle，但 workflow 没说明误差在哪里尽早暴露。",
        ),
        "alignment_workflow_shape_without_gatekeeper_readiness_evidence": (
            "workflow_shape",
            "Builder -> Inspector fits because a focused slice is built, then inspected, so weak evidence and fake-done drift are exposed early.",
            "我生成了 bundle，但 workflow 没说明最终裁决或收束节点。",
        ),
    }
    return issues.get(scenario)


ALIGNMENT_SESSION_TRANSCRIPT_BLOCK_RE = re.compile(
    r"## Session Transcript\s*```json\s*(.*?)\s*```",
    re.DOTALL,
)
ALIGNMENT_PROMPT_USER_CONTENT_RE = re.compile(
    r'"role"\s*:\s*"user"\s*,\s*"content"\s*:\s*("(?:\\.|[^"\\])*")',
    re.DOTALL,
)


@dataclass(frozen=True)
class AlignmentPayloadState:
    mode: str
    alignment_stage: str
    workdir: str
    prefers_chinese: bool
    display_language: str
    is_improvement: bool


def build_alignment_payload(scenario: str, request) -> dict:
    if scenario == "alignment_failure":
        raise FakePayloadError("simulated alignment failure")
    working_agreement = request.extra_context.get("working_agreement") if isinstance(request.extra_context.get("working_agreement"), dict) else {}
    state = AlignmentPayloadState(
        mode=str(request.extra_context.get("alignment_mode", "normal")),
        alignment_stage=str(request.extra_context.get("alignment_stage", "clarifying") or "clarifying"),
        workdir=str(request.extra_context.get("target_workdir") or request.workdir),
        prefers_chinese=bool(request.extra_context.get("prefers_chinese")),
        display_language=str(request.extra_context.get("display_language") or ""),
        is_improvement=str(working_agreement.get("mode") or "") == "improvement",
    )
    payload = _alignment_task_anchored_payload(
        scenario,
        state=state,
        task_text=_alignment_task_text_from_prompt(request.prompt),
    )
    if payload is not None:
        return payload
    payload = _alignment_refactor_improvement_payload(
        scenario,
        state=state,
        feedback_text=_alignment_task_text_from_prompt(request.prompt),
    )
    if payload is not None:
        return payload
    payload = _alignment_preconfirmation_payload(
        scenario,
        state=state,
    )
    if payload is not None:
        return payload
    payload = _alignment_bundle_payload_for_scenario(
        scenario,
        mode=state.mode,
        workdir=state.workdir,
    )
    if payload is not None:
        return payload
    return alignment_default_bundle_response(
        state.workdir,
        prefers_chinese=state.prefers_chinese,
        is_improvement=state.is_improvement,
        use_generic_bundle=scenario == "alignment_improvement_generic_bundle",
    )


def _alignment_task_anchored_payload(
    scenario: str,
    *,
    state: AlignmentPayloadState,
    task_text: str,
) -> dict | None:
    if scenario != "success" or state.is_improvement or not _alignment_task_has_specific_anchor(task_text):
        return None
    if state.mode != "repair" and state.alignment_stage not in {
        "confirmed",
        "compiling",
        "ready_review",
    }:
        return alignment_task_anchored_agreement_response(
            task_text,
            prefers_chinese=state.prefers_chinese,
            display_language=state.display_language,
        )
    payload = alignment_response(
        status="bundle",
        assistant_message=_alignment_task_anchored_bundle_message(task_text, state=state),
        needs_user_input=False,
        bundle_yaml=alignment_task_anchored_repair_bundle_yaml(
            state.workdir,
            task_text,
            prefers_chinese=state.prefers_chinese,
            display_language=state.display_language,
        ),
        phase="bundle",
    )
    agreement_payload = alignment_task_anchored_agreement_response(
        task_text,
        prefers_chinese=state.prefers_chinese,
        display_language=state.display_language,
    )
    payload["agreement_summary"] = agreement_payload["agreement_summary"]
    payload["readiness_evidence"] = agreement_payload["readiness_evidence"]
    payload["readiness_checklist"] = dict.fromkeys(payload["readiness_checklist"], True)
    return payload


def _alignment_task_anchored_bundle_message(task_text: str, *, state: AlignmentPayloadState) -> str:
    if _alignment_search_quality_task(task_text):
        if state.prefers_chinese:
            return "已整理成一个保留任务锚点、采用 eval-first search quality workflow 的 Loopora bundle。"
        if state.display_language.strip().lower() == "es":
            return "Preparé un bundle de Loopora que preserva el ancla de tarea y usa un workflow eval-first de search quality."
        return "I prepared a Loopora bundle that preserves the task anchor and uses an eval-first search quality workflow."
    if state.prefers_chinese:
        return "已整理成一个保留任务锚点、采用专属 workflow 的 Loopora bundle。"
    if state.display_language.strip().lower() == "es":
        return "Preparé un bundle de Loopora que preserva el ancla de tarea y usa un workflow especializado."
    return "I prepared a Loopora bundle that preserves the task anchor and uses a specialized workflow."


def _alignment_task_has_specific_anchor(task_text: str) -> bool:
    return bool(agent_candidate_task_anchor_terms(task_text))


def _alignment_search_quality_task(task_text: str) -> bool:
    text = str(task_text or "")
    if re.search(r"\bRAG\b|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(r"semantic\s+search|search|retrieval|ranking|top[- ]?5|搜索|检索|排序|相关性", text, re.IGNORECASE):
        return False
    markers = (
        r"\beval(?:uation)?\b|eval\s*set|benchmark|评测|评估集|评测集|基准",
        r"human\s+review|manual\s+review|人工评审|人工审核",
        r"relevance|groundedness|hallucination|quality|相关性|幻觉|质量",
        r"negative\s+quer|negative\s+example|regression\s+sample|负例|负向|回归样本",
        r"demo\s+query|single\s+score|单点|单个\s*demo|单个\s*benchmark",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def _alignment_refactor_improvement_payload(
    scenario: str,
    *,
    state: AlignmentPayloadState,
    feedback_text: str,
) -> dict | None:
    if scenario != "success" or not state.is_improvement or not _alignment_refactor_improvement_requested(feedback_text):
        return None
    if state.alignment_stage not in {"confirmed", "compiling", "ready_review"}:
        if state.prefers_chinese:
            return alignment_chinese_refactor_improvement_agreement_response(feedback_text)
        # The current realistic refactor fixture is Chinese because the directional critique test path is Chinese.
        # Other display languages still fall back to the generic improvement flow instead of inventing localized detail.
        return None
    if not state.prefers_chinese:
        return None
    agreement_payload = alignment_chinese_refactor_improvement_agreement_response(feedback_text)
    payload = alignment_response(
        status="bundle",
        assistant_message="已整理成一个保留来源意图、包含 search refactor 阶段证据链的 Loopora bundle。",
        needs_user_input=False,
        bundle_yaml=alignment_chinese_refactor_improvement_bundle_yaml(state.workdir),
        phase="bundle",
    )
    payload["agreement_summary"] = agreement_payload["agreement_summary"]
    payload["readiness_evidence"] = agreement_payload["readiness_evidence"]
    payload["readiness_checklist"] = dict.fromkeys(payload["readiness_checklist"], True)
    return payload


def _alignment_refactor_improvement_requested(feedback_text: str) -> bool:
    text = str(feedback_text or "")
    has_refactor = bool(re.search(r"太保守|不够重构|更激进|激进一点|大刀阔斧|too conservative|not enough refactor|more aggressive", text, re.IGNORECASE))
    has_search_phases = sum(
        1
        for pattern in (
            r"\bbaseline\b|基线",
            r"query\s*rewrite|查询改写",
            r"\bretrieval\b|检索",
            r"\branking\b|排序",
            r"evidence\s*hardening|证据.*加固|补.*证据",
        )
        if re.search(pattern, text, re.IGNORECASE)
    )
    return has_refactor and has_search_phases >= 3


def _alignment_task_text_from_prompt(prompt: str) -> str:
    messages = _alignment_user_messages_from_prompt(prompt)
    task_messages: list[str] = []
    for message in messages:
        task_message = _alignment_task_anchor_from_user_message(message)
        if not task_message or _alignment_message_is_confirmation(task_message):
            continue
        if task_message not in task_messages:
            task_messages.append(task_message)
        if len(task_messages) >= 3:
            break
    return _alignment_join_task_messages(task_messages)


def _alignment_user_messages_from_prompt(prompt: str) -> list[str]:
    transcript = _alignment_prompt_transcript(prompt)
    if transcript:
        return [
            str(entry.get("content") or "").strip()
            for entry in transcript
            if isinstance(entry, dict) and entry.get("role") == "user" and str(entry.get("content") or "").strip()
        ]
    messages: list[str] = []
    for match in ALIGNMENT_PROMPT_USER_CONTENT_RE.finditer(str(prompt or "")):
        try:
            content = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if str(content or "").strip():
            messages.append(str(content).strip())
    return messages


def _alignment_prompt_transcript(prompt: str) -> list[dict]:
    match = ALIGNMENT_SESSION_TRANSCRIPT_BLOCK_RE.search(str(prompt or ""))
    if not match:
        return []
    try:
        transcript = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(transcript, list):
        return []
    return [entry for entry in transcript if isinstance(entry, dict)]


def _alignment_task_anchor_from_user_message(message: str) -> str:
    text = " ".join(str(message or "").split())
    if not text:
        return ""
    text = _alignment_strip_mixed_confirmation_adjustment_prefix(text)
    for marker in (
        "Continue Web review from this /loopora-plan task anchor:",
        "First re-check whether this /loopora-plan task anchor fits Loopora:",
        "Task anchor:",
        "请基于这次 /loopora-plan 的任务锚点继续 Web review：",
        "请先按这次 /loopora-plan 的任务锚点重新判断是否适合 Loopora：",
        "任务锚点：",
        "Continuar Web review desde este ancla de tarea de /loopora-plan:",
        "Primero vuelve a comprobar si este ancla de tarea de /loopora-plan encaja con Loopora:",
        "Ancla de tarea:",
    ):
        if marker in text:
            text = text.split(marker, 1)[1].strip()
            break
    for trailer in (
        "Use the evidence-first path:",
        "If we should continue,",
        "推荐采用证据优先路径：",
        "如果仍要继续，",
        "Usa el camino de evidencia primero:",
        "Si debemos continuar,",
    ):
        if trailer in text:
            text = text.split(trailer, 1)[0].strip()
    return text.strip(" \t\r\n:：,，.。")


def _alignment_strip_mixed_confirmation_adjustment_prefix(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(
        r"^(?:确认|同意|可以|好的?|行|没问题)[\s,，;；.。]*(?:但|但是|不过|只是|同时|并且)?[\s,，;；.。]*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:要)?(?:调整|修改|更改|补充|改一下|再改)(?:这份|这个|当前)?(?:工作协议|协议|方案|方向)?[\s:：,，;；]*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:confirm(?:ed)?|approve(?:d)?|ok(?:ay)?|looks good|go ahead|proceed)[\s,;:.]*(?:but|however|and)[\s,;:.]*(?:please\s+)?",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:confirmo|confirmado|de acuerdo|ok)[\s,;:.]*(?:pero|y|aunque)[\s,;:.]*(?:por favor\s+)?",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    return value or str(text or "").strip()


def _alignment_message_is_confirmation(message: str) -> bool:
    if alignment_message_is_language_neutral_confirmation(message):
        return True
    normalized = " ".join(str(message or "").strip().lower().split())
    if not normalized:
        return False
    if re.fullmatch(
        r"(?:confirm|confirmed|approve|approved|go ahead|proceed)(?:\s+(?:this|the)\s+(?:working\s+)?agreement)?[\s.!?]*",
        normalized,
    ):
        return True
    compact = re.sub(r"[\s.!?。！？,，;；:：\"'“”‘’]+", "", normalized)
    return bool(
        re.fullmatch(r"(?:确认|同意|采用|可以|好的?)(?:采用)?(?:这份|这个|当前)?(?:工作协议|协议|方案|方向)?", compact)
        and len(compact) <= 24
    )


def _alignment_join_task_messages(messages: list[str]) -> str:
    text = "\n".join(message for message in messages if message.strip()).strip()
    if len(text) <= 1200:
        return text
    return text[:1199].rstrip() + "…"


def _alignment_preconfirmation_payload(
    scenario: str,
    *,
    state: AlignmentPayloadState,
) -> dict | None:
    return alignment_preconfirmation_payload_for_scenario(
        scenario,
        request=AlignmentPreconfirmationPayloadRequest(
            mode=state.mode,
            alignment_stage=state.alignment_stage,
            workdir=state.workdir,
            prefers_chinese=state.prefers_chinese,
            is_improvement=state.is_improvement,
        ),
    )


def _alignment_workdir_fact_bundle_payload(scenario: str, *, workdir: str) -> dict | None:
    if scenario == "alignment_bundle_unsupported_observed_workdir_claim":
        return alignment_response(
            status="bundle",
            assistant_message="I prepared a bundle with an unsupported observed workdir claim.",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml_with_unsupported_observed_workdir_claim(workdir),
            phase="bundle",
        )
    if scenario == "alignment_governance_markers_listed_without_responsibilities":
        return alignment_response(
            status="bundle",
            assistant_message="I prepared a bundle that lists governance markers but does not route responsibilities.",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml_with_governance_markers_listed_as_facts(workdir),
            phase="bundle",
        )
    return None


def _alignment_bundle_payload_for_scenario(
    scenario: str,
    *,
    mode: str,
    workdir: str,
) -> dict | None:
    payload = _alignment_workdir_fact_bundle_payload(scenario, workdir=workdir)
    if payload is not None:
        return payload
    payload = _alignment_invalid_bundle_payload(scenario, mode=mode, workdir=workdir)
    if payload is not None:
        return payload
    payload = _alignment_language_bundle_payload(scenario, workdir=workdir)
    if payload is not None:
        return payload
    payload = _alignment_refund_bundle_payload(scenario, workdir=workdir)
    if payload is not None:
        return payload
    return _alignment_readiness_issue_payload_for_scenario(scenario, workdir=workdir)


def _alignment_invalid_bundle_payload(
    scenario: str,
    *,
    mode: str,
    workdir: str,
) -> dict | None:
    if scenario == "alignment_invalid":
        return alignment_response(
            status="bundle",
            assistant_message="我先给出一个故意不完整的 bundle。",
            needs_user_input=False,
            bundle_yaml="version: 1\nmetadata:\n  name: Broken Alignment Bundle\n",
            phase="bundle",
        )
    if scenario == "alignment_invalid_then_valid" and mode != "repair":
        return alignment_response(
            status="bundle",
            assistant_message="我先给出一个需要修复的 bundle。",
            needs_user_input=False,
            bundle_yaml="version: 1\nmetadata:\n  name: Broken Alignment Bundle\n",
            phase="bundle",
        )
    if scenario == "alignment_semantic_invalid_then_valid" and mode != "repair":
        return alignment_response(
            status="bundle",
            assistant_message="我先给出一个语义不完整的 bundle。",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml_without_semantics(workdir),
            phase="bundle",
        )
    return None


def _alignment_language_bundle_payload(scenario: str, *, workdir: str) -> dict | None:
    if scenario == "alignment_chinese_readiness_evidence":
        payload = alignment_response(
            status="bundle",
            assistant_message="我已用中文整理成一个可导入的 Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
        return payload
    if scenario == "alignment_english_bundle_prose_for_chinese_user":
        payload = alignment_response(
            status="bundle",
            assistant_message="我准备了一个 bundle，但正文仍然是英文。",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
        return payload
    if scenario == "alignment_english_visible_bundle_names_for_chinese_user":
        payload = alignment_response(
            status="bundle",
            assistant_message="我准备了一个中文 bundle，但可见名称仍然是英文。",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml_with_english_visible_names(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
        return payload
    if scenario == "alignment_english_assistant_message_for_chinese_bundle":
        payload = alignment_response(
            status="bundle",
            assistant_message="I prepared an importable Loopora bundle.",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
        return payload
    if scenario == "alignment_english_bundle_for_chinese_user":
        return alignment_response(
            status="bundle",
            assistant_message="I prepared an importable Loopora bundle.",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml(workdir),
            phase="bundle",
        )
    return None


def _alignment_refund_bundle_payload(scenario: str, *, workdir: str) -> dict | None:
    if scenario == "alignment_refund_agreement_repair_bundle":
        return _alignment_refund_repair_bundle_payload(workdir, prefers_chinese=False)
    if scenario == "alignment_chinese_refund_agreement_repair_bundle":
        return _alignment_refund_repair_bundle_payload(workdir, prefers_chinese=True)
    return None


def _alignment_refund_repair_bundle_payload(workdir: str, *, prefers_chinese: bool) -> dict:
    payload = alignment_response(
        status="bundle",
        assistant_message=(
            "已整理成一个包含 Guide 修复轮次的退款治理 Loopora bundle。"
            if prefers_chinese
            else "I prepared a refund governance Loopora bundle with a Guide repair pass."
        ),
        needs_user_input=False,
        bundle_yaml=(
            alignment_chinese_refund_repair_bundle_yaml(workdir)
            if prefers_chinese
            else alignment_refund_repair_bundle_yaml(workdir)
        ),
        phase="bundle",
    )
    agreement_payload = alignment_chinese_refund_agreement_response() if prefers_chinese else alignment_refund_agreement_response()
    payload["agreement_summary"] = agreement_payload["agreement_summary"]
    payload["readiness_evidence"] = agreement_payload["readiness_evidence"]
    payload["readiness_checklist"] = dict.fromkeys(payload["readiness_checklist"], True)
    return payload


def _alignment_readiness_issue_payload_for_scenario(scenario: str, *, workdir: str) -> dict | None:
    if scenario == "alignment_generated_lineage_metadata":
        return alignment_response(
            status="bundle",
            assistant_message="I prepared a bundle but encoded source lineage metadata.",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml_with_lineage_metadata(workdir),
            phase="bundle",
        )
    if scenario == "alignment_markdown_fenced_bundle":
        return alignment_response(
            status="bundle",
            assistant_message="I prepared a fenced bundle.",
            needs_user_input=False,
            bundle_yaml=f"```yaml\n{alignment_bundle_yaml(workdir)}```",
            phase="bundle",
        )
    if scenario == "alignment_missing_readiness_evidence":
        payload = alignment_response(
            status="bundle",
            assistant_message="我勾选了 checklist 但没有给出具体证据。",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["readiness_evidence"] = alignment_missing_readiness_evidence()
        return payload
    issue = alignment_readiness_issue_for_scenario(scenario)
    if issue is None:
        return None
    field, evidence_text, assistant_message = issue
    payload = alignment_response(
        status="bundle",
        assistant_message=assistant_message,
        needs_user_input=False,
        bundle_yaml=alignment_bundle_yaml(workdir),
        phase="bundle",
    )
    payload["readiness_evidence"][field] = evidence_text
    return payload
