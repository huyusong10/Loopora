from __future__ import annotations

from dataclasses import dataclass
import json
import re

from loopora.alignment_readiness_rules import (
    alignment_governance_marker_responsibilities_present,
    has_any_marker,
    workdir_facts_claims_unsupported_observed_stack,
)
from loopora.service_alignment_decision_options import (
    alignment_has_recommended_decision_options,
    alignment_needs_user_input,
    agreement_confirmation_decision_options,
    default_alignment_decision_options,
)
from loopora.specs import SpecError, compile_markdown_spec


@dataclass(frozen=True)
class AlignmentBundleStageGate:
    stage: str
    confirmed_stages: set[str]
    phase: str
    agreement_summary: str
    checklist: object
    readiness_keys: list[str]
    evidence_issues: list[str]
    improvement_issues: list[str]
    language_issues: list[str]
    prefers_chinese: bool


@dataclass(frozen=True)
class AlignmentOutputMessagePlan:
    assistant_message: str
    bundle_yaml: str
    missing_items: list[str] | None
    has_bundle_for_options: bool
    event_type: str = ""
    event_payload: dict | None = None
    force_needs_user_input: bool = False
    use_default_decision_options: bool = False


@dataclass(frozen=True)
class AlignmentUserMessageStagePlan:
    update_fields: dict
    event_type: str = ""
    event_payload: dict | None = None


@dataclass(frozen=True)
class AlignmentAgreementBlockCandidate:
    issues: list[str]
    event_type: str
    fallback_message: str


@dataclass(frozen=True)
class AlignmentAgreementBlockPlan:
    event_type: str
    event_payload: dict
    output_updates: dict


@dataclass(frozen=True)
class AlignmentAgreementReadyStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str
    event_payload: dict


@dataclass(frozen=True)
class AlignmentClarifyingStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str = ""
    event_payload: dict | None = None


def alignment_agreement_working_agreement(output: dict, *, captured_at: str) -> dict:
    checklist = output.get("readiness_checklist")
    normalized_checklist = dict(checklist) if isinstance(checklist, dict) else {}
    normalized_checklist["explicit_confirmation"] = False
    readiness_evidence = output.get("readiness_evidence")
    return {
        "summary": str(output.get("agreement_summary", "") or "").strip(),
        "readiness_checklist": normalized_checklist,
        "readiness_evidence": readiness_evidence if isinstance(readiness_evidence, dict) else {},
        "captured_at": captured_at,
        "confirmed_at": "",
        "confirmation_message": "",
    }


def alignment_merge_improvement_context(previous: object, working_agreement: dict) -> dict:
    if not isinstance(previous, dict) or previous.get("mode") != "improvement":
        return working_agreement
    merged = dict(working_agreement)
    for key in ("mode", "source", "seed_bundle_metadata"):
        if key in previous and key not in merged:
            merged[key] = previous[key]
    return merged


def alignment_visible_agreement_message(working_agreement: dict, *, prefers_chinese: bool) -> str:
    evidence = working_agreement.get("readiness_evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    summary = alignment_agreement_text_snippet(working_agreement.get("summary"), limit=360)
    values = {
        key: alignment_agreement_text_snippet(evidence.get(key), limit=280)
        for key in (
            "loop_fit",
            "task_scope",
            "success_surface",
            "fake_done_risks",
            "evidence_preferences",
            "execution_strategy",
            "residual_risk_policy",
            "judgment_tradeoffs",
            "local_governance",
            "role_posture",
            "workflow_shape",
            "workdir_facts",
        )
    }
    if prefers_chinese:
        return "\n".join(
            [
                "请先确认这份工作协议。确认后我再生成 Loop 方案；如果任一判断不对，请直接指出要改哪一项。",
                "",
                f"摘要：{summary}",
                f"为什么用 Loopora：{values['loop_fit']}",
                f"任务范围：{values['task_scope']}",
                f"成功面：{values['success_surface']}",
                f"假完成风险：{values['fake_done_risks']}",
                f"证据偏好：{values['evidence_preferences']}",
                f"执行策略：{values['execution_strategy']}",
                f"残余风险：{values['residual_risk_policy']}",
                f"判断取舍：{values['judgment_tradeoffs']}",
                f"本地治理：{values['local_governance']}",
                f"角色姿态：{values['role_posture']}",
                f"运行流程形状：{values['workflow_shape']}",
                f"项目事实：{values['workdir_facts']}",
            ]
        )
    return "\n".join(
        [
            "Please confirm this working agreement. After confirmation I will generate the Loop plan; if any judgment is wrong, name the item to adjust.",
            "",
            f"Summary: {summary}",
            f"Loopora fit: {values['loop_fit']}",
            f"Task scope: {values['task_scope']}",
            f"Success surface: {values['success_surface']}",
            f"Fake-done risks: {values['fake_done_risks']}",
            f"Evidence preferences: {values['evidence_preferences']}",
            f"Execution strategy: {values['execution_strategy']}",
            f"Residual risk: {values['residual_risk_policy']}",
            f"Judgment tradeoffs: {values['judgment_tradeoffs']}",
            f"Local governance: {values['local_governance']}",
            f"Role posture: {values['role_posture']}",
            f"Run-flow shape: {values['workflow_shape']}",
            f"Project facts: {values['workdir_facts']}",
        ]
    )


def alignment_agreement_text_snippet(value: object, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def alignment_agreement_ready_stage_plan(
    working_agreement: dict,
    *,
    assistant_message: str,
    prefers_chinese: bool,
) -> AlignmentAgreementReadyStagePlan:
    return AlignmentAgreementReadyStagePlan(
        update_fields={
            "alignment_stage": "agreement_ready",
            "working_agreement": working_agreement,
        },
        output_updates={
            "assistant_message": assistant_message,
            "needs_user_input": True,
            "bundle_yaml": "",
            "decision_options": agreement_confirmation_decision_options(prefers_chinese=prefers_chinese),
        },
        event_type="alignment_agreement_ready",
        event_payload={
            "alignment_stage": "agreement_ready",
            "working_agreement": working_agreement,
        },
    )


def alignment_user_message_stage_plan(
    session: dict,
    message: str,
    *,
    captured_at: str,
    confirmed_stages: set[str],
) -> AlignmentUserMessageStagePlan:
    stage = str(session.get("alignment_stage", "") or "clarifying")
    status = str(session.get("status", "") or "")
    if stage == "agreement_ready":
        agreement = dict(session.get("working_agreement") or {})
        checklist = dict(agreement.get("readiness_checklist") or {})
        if alignment_message_confirms_agreement(message):
            checklist["explicit_confirmation"] = True
            agreement["readiness_checklist"] = checklist
            agreement["confirmed_at"] = captured_at
            agreement["confirmation_message"] = message
            return AlignmentUserMessageStagePlan(
                update_fields={"alignment_stage": "confirmed", "working_agreement": agreement},
                event_type="alignment_agreement_confirmed",
                event_payload={"alignment_stage": "confirmed"},
            )
        checklist["explicit_confirmation"] = False
        agreement["readiness_checklist"] = checklist
        agreement["confirmed_at"] = ""
        agreement["confirmation_message"] = ""
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "clarifying", "working_agreement": agreement},
            event_type="alignment_agreement_reopened",
            event_payload={"alignment_stage": "clarifying"},
        )
    if status == "ready":
        agreement = dict(session.get("working_agreement") or {})
        ready_review = dict(agreement.get("ready_review") or {})
        ready_review["feedback"] = message
        ready_review["requested_at"] = captured_at
        ready_review["source_status"] = status
        agreement["ready_review"] = ready_review
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "ready_review", "working_agreement": agreement},
            event_type="alignment_ready_review_started",
            event_payload={
                "alignment_stage": "ready_review",
                "feedback": message,
                "bundle_path": session.get("bundle_path", ""),
            },
        )
    if status in {"imported", "running_loop"}:
        return AlignmentUserMessageStagePlan(
            update_fields={
                "alignment_stage": "clarifying",
                "working_agreement": session.get("working_agreement") or {},
            },
        )
    if status == "failed" and stage not in confirmed_stages:
        return AlignmentUserMessageStagePlan(update_fields={"alignment_stage": "clarifying"})
    return AlignmentUserMessageStagePlan(update_fields={})


def alignment_message_confirms_agreement(message: str) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"no", "nope"}:
        return False
    negative_scan = normalized
    for no_change_marker in (
        "但是不需要修改",
        "但不需要修改",
        "不过不需要修改",
        "不需要修改",
        "但是不用修改",
        "但不用修改",
        "不过不用修改",
        "不用修改",
        "但是无需修改",
        "但无需修改",
        "不过无需修改",
        "无需修改",
        "但是不需要调整",
        "但不需要调整",
        "不过不需要调整",
        "不需要调整",
        "但是不用调整",
        "但不用调整",
        "不过不用调整",
        "不用调整",
        "但是无需调整",
        "但无需调整",
        "不过无需调整",
        "无需调整",
        "但是不需要改",
        "但不需要改",
        "不过不需要改",
        "不需要改",
        "但是不用改",
        "但不用改",
        "不过不用改",
        "不用改",
        "但是无需改",
        "但无需改",
        "不过无需改",
        "无需改",
        "but no changes",
        "but no change",
        "but without changes",
        "no changes",
        "no change",
        "without changes",
    ):
        negative_scan = negative_scan.replace(no_change_marker, "")
    negative_tokens = [
        "不确认",
        "不同意",
        "不要",
        "先别",
        "不是",
        "不对",
        "但是",
        "不过",
        "但",
        "改成",
        "改为",
        "改一下",
        "增加",
        "补充",
        "添加",
        "删除",
        "去掉",
        "修改",
        "调整",
        "换成",
        "再改",
        " no",
        "not",
        " but",
        "add",
        "change",
        "delete",
        "remove",
        "revise",
        "adjust",
        "instead",
    ]
    if any(token in negative_scan for token in negative_tokens):
        return False
    confirm_tokens = [
        "确认",
        "同意",
        "可以",
        "就这样",
        "按这个",
        "没问题",
        "继续",
        "ok",
        "yes",
        "confirm",
        "approved",
        "go ahead",
        "proceed",
    ]
    return any(token in normalized for token in confirm_tokens)


def alignment_agreement_readiness_checklist_issues(checklist: object, *, readiness_keys: list[str]) -> list[str]:
    if not isinstance(checklist, dict):
        return ["readiness_checklist"]
    return [key for key in readiness_keys if key != "explicit_confirmation" and checklist.get(key) is not True]


def alignment_agreement_language_issues(output: dict, *, evidence_keys: list[str], prefers_chinese: bool) -> list[str]:
    if not prefers_chinese:
        return []
    issues = []
    if not _text_has_cjk(output.get("agreement_summary")):
        issues.append("agreement_summary")
    evidence = output.get("readiness_evidence")
    if not isinstance(evidence, dict):
        return [*issues, "readiness_evidence"]
    issues.extend(key for key in evidence_keys if not _text_has_cjk(evidence.get(key)))
    return issues


def alignment_bundle_language_issues(bundle: dict, *, prefers_chinese: bool) -> list[str]:
    if not prefers_chinese:
        return []
    issues = []
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    field_values = {
        "metadata.name": metadata.get("name"),
        "metadata.description": metadata.get("description"),
        "loop.name": loop.get("name"),
        "collaboration_summary": bundle.get("collaboration_summary"),
        "spec.markdown": (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        "workflow.collaboration_intent": ((bundle.get("workflow") or {}).get("collaboration_intent") if isinstance(bundle.get("workflow"), dict) else ""),
    }
    issues.extend(
        f"bundle field {field_name} must follow Chinese user language" for field_name, value in field_values.items() if not _text_has_cjk(value)
    )
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        issues.extend(
            f"bundle role_definition {key}.{field_name} must follow Chinese user language"
            for field_name in ("name", "description", "prompt_markdown", "posture_notes")
            if not _text_has_cjk(role.get(field_name))
        )
    return issues


def alignment_bundle_workdir_fact_issues(bundle: dict, *, workdir_snapshot: str) -> list[str]:
    fields: dict[str, object] = {
        "collaboration_summary": bundle.get("collaboration_summary"),
        "spec.markdown": (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        "workflow.collaboration_intent": ((bundle.get("workflow") or {}).get("collaboration_intent") if isinstance(bundle.get("workflow"), dict) else ""),
    }
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        for field_name in ("description", "prompt_markdown", "posture_notes"):
            fields[f"role_definition {key}.{field_name}"] = role.get(field_name)
    return [
        f"bundle field {field_name} must not claim an observed workdir stack unsupported by Workdir Snapshot"
        for field_name, value in fields.items()
        if workdir_facts_claims_unsupported_observed_stack(
            str(value or "").lower(),
            workdir_snapshot=workdir_snapshot,
        )
    ]


def alignment_improvement_bundle_issues(working_agreement: object, bundle: dict) -> list[str]:
    agreement = working_agreement if isinstance(working_agreement, dict) else {}
    if str(agreement.get("mode") or "") != "improvement":
        return []
    text = alignment_bundle_visible_text(bundle).lower()
    issues: list[str] = []
    if not has_any_marker(
        text,
        (
            "source intent",
            "source loop",
            "source bundle",
            "source workdir",
            "source defaults",
            "source posture",
            "stable intent",
            "stable task intent",
            "existing loop",
            "existing bundle",
            "base candidate",
            "既有意图",
            "来源 loop",
            "来源 bundle",
            "来源意图",
            "稳定意图",
            "原 bundle",
        ),
    ):
        issues.append("improvement bundle must state what source intent, workdir, defaults, or posture is preserved")
    if not has_any_marker(
        text,
        (
            "feedback-driven",
            "feedback",
            "run evidence",
            "evidence summary",
            "evidence gap",
            "gatekeeper verdict",
            "coverage",
            "delta",
            "反馈驱动",
            "反馈",
            "运行证据",
            "证据摘要",
            "证据缺口",
            "变化",
        ),
    ):
        issues.append("improvement bundle must state the feedback-driven governance delta")
    if not has_any_marker(
        text,
        (
            "spec",
            "role",
            "roles",
            "workflow",
            "evidence",
            "gatekeeper",
            "证据",
            "角色",
            "裁决",
            "治理面",
            "任务契约",
        ),
    ):
        issues.append("improvement bundle must map the delta to spec, roles, workflow, evidence, or GateKeeper")
    source = agreement.get("source") if isinstance(agreement.get("source"), dict) else {}
    source_bundle_id = str(source.get("source_bundle_id") or "").strip()
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    generated_bundle_id = str(metadata.get("bundle_id") or "").strip()
    if source_bundle_id and generated_bundle_id == source_bundle_id:
        issues.append("improvement bundle must not reuse the source bundle id as metadata.bundle_id; leave bundle_id empty or choose a new standalone candidate id")
    has_run_context = str(source.get("source_type") or "") == "run" and (
        source.get("coverage_summary") or source.get("evidence_summary") or source.get("task_verdict") or source.get("gatekeeper_verdict")
    )
    if has_run_context and not has_any_marker(
        text,
        (
            "run evidence",
            "coverage",
            "verdict",
            "gatekeeper verdict",
            "evidence summary",
            "运行证据",
            "覆盖",
            "裁决",
            "证据摘要",
        ),
    ):
        issues.append("improvement bundle must translate run evidence, coverage, or GateKeeper verdict into bundle changes")
    source_completion_mode = str(source.get("source_completion_mode") or "").strip().lower()
    if source_completion_mode and source_completion_mode != "gatekeeper":
        has_source_completion_mode_delta = has_any_marker(
            text,
            (
                "completion mode",
                "completion_mode",
                "`rounds`",
                "rounds completion",
                "source uses rounds",
                "run lifecycle",
                "lifecycle completion",
                "source completion",
                "完成模式",
                "运行生命周期",
                "生命周期收束",
            ),
        ) and has_any_marker(
            text,
            (
                "gatekeeper",
                "task verdict",
                "evidence-based verdict",
                "证据裁决",
                "loop 裁决",
                "任务裁决",
                "守门",
            ),
        )
        if not has_source_completion_mode_delta:
            issues.append("improvement bundle must state the source completion-mode governance delta")
    return issues


def alignment_bundle_visible_text(bundle: dict) -> str:
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts = [
        str(metadata.get("name", "") or ""),
        str(metadata.get("description", "") or ""),
        str(bundle.get("collaboration_summary", "") or ""),
        str(loop.get("name", "") or ""),
        str(spec.get("markdown", "") or ""),
        str(workflow.get("collaboration_intent", "") or ""),
    ]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("name", "") or ""),
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    return "\n".join(parts)


def alignment_session_user_task_text(session: dict) -> str:
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    user_messages = [
        str(entry.get("content") or "").strip()
        for entry in transcript
        if isinstance(entry, dict) and entry.get("role") == "user" and str(entry.get("content") or "").strip()
    ]
    return "\n".join(user_messages[:4])


def normalize_alignment_traceability_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def alignment_traceability_term_is_present(term: str, *, normalized_bundle_text: str) -> bool:
    value = str(term or "").strip().lower()
    if not value:
        return False
    if "/" in value or "." in value:
        return value in normalized_bundle_text
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(value)}(?![a-z0-9])", normalized_bundle_text))


def alignment_governance_marker_responsibility_issues(evidence: dict, *, normalized_runtime_text: str) -> list[str]:
    agreement_evidence_text = normalize_alignment_traceability_text(" ".join(str(value or "") for value in evidence.values()))
    governance_markers = ("agents.md", "design/readme.md", "design/", "tests/")
    if not any(marker in agreement_evidence_text for marker in governance_markers):
        return []
    if alignment_governance_marker_responsibilities_present(normalized_runtime_text):
        return []
    return [
        "alignment bundle must convert project-local governance markers into Builder reading, "
        "Inspector or Custom verification, and GateKeeper gating responsibilities"
    ]


def alignment_bundle_agreement_projection_text(bundle: dict) -> str:
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts = [
        str(bundle.get("collaboration_summary", "") or ""),
        str(spec.get("markdown", "") or ""),
        str(workflow.get("collaboration_intent", "") or ""),
    ]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("description", "") or ""),
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
            ]
        )
    if isinstance(workflow, dict):
        parts.append(json.dumps(_alignment_workflow_traceability_projection(workflow), ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def alignment_bundle_runtime_responsibility_projection_text(bundle: dict) -> str:
    spec_role_notes = alignment_bundle_spec_role_notes_projection_text(bundle)
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    parts: list[str] = [spec_role_notes]
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        parts.extend(
            [
                str(role.get("prompt_markdown", "") or ""),
                str(role.get("posture_notes", "") or ""),
                str(role.get("description", "") or ""),
            ]
        )
    if isinstance(workflow, dict):
        parts.append(str(workflow.get("collaboration_intent", "") or ""))
        parts.append(json.dumps(_alignment_workflow_traceability_projection(workflow), ensure_ascii=False, sort_keys=True))
    return "\n".join(parts)


def alignment_bundle_spec_role_notes_projection_text(bundle: dict) -> str:
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    markdown = str(spec.get("markdown", "") or "")
    if not markdown.strip():
        return ""
    try:
        compiled_spec = compile_markdown_spec(markdown)
    except SpecError:
        return ""
    raw_sections = compiled_spec.get("raw_sections") if isinstance(compiled_spec, dict) else {}
    return str(raw_sections.get("Role Notes") or "") if isinstance(raw_sections, dict) else ""


def _alignment_workflow_traceability_projection(workflow: dict) -> dict:
    return {
        "steps": [
            {
                "inputs": step.get("inputs") if isinstance(step.get("inputs"), dict) else {},
                "action_policy": step.get("action_policy") if isinstance(step.get("action_policy"), dict) else {},
                "control": step.get("control") if isinstance(step.get("control"), dict) else {},
            }
            for step in list(workflow.get("steps") or [])
            if isinstance(step, dict)
        ],
        "controls": list(workflow.get("controls") or []) if isinstance(workflow.get("controls"), list) else [],
    }


def alignment_agreement_block_plan(
    candidates: list[AlignmentAgreementBlockCandidate],
    *,
    prefers_chinese: bool,
) -> AlignmentAgreementBlockPlan | None:
    for candidate in candidates:
        missing = list(candidate.issues)
        if not missing:
            continue
        return AlignmentAgreementBlockPlan(
            event_type=candidate.event_type,
            event_payload={"alignment_stage": "clarifying", "missing": missing},
            output_updates={
                "alignment_phase": "clarifying",
                "agreement_summary": "",
                "bundle_yaml": "",
                "needs_user_input": True,
                "alignment_missing_items": missing,
                "assistant_message": alignment_block_message(
                    prefers_chinese=prefers_chinese,
                    event_type=candidate.event_type,
                    missing=missing,
                    fallback_zh=candidate.fallback_message,
                ),
            },
        )
    return None


def alignment_assistant_message_language_issue(assistant_message: str, *, prefers_chinese: bool) -> bool:
    return prefers_chinese and not _text_has_cjk(assistant_message)


def alignment_output_message_plan(
    output: dict,
    *,
    stage_error: str,
    missing_items: list[str] | None,
    prefers_chinese: bool,
) -> AlignmentOutputMessagePlan:
    assistant_message = str(output.get("assistant_message", "") or "").strip()
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    if stage_error:
        return AlignmentOutputMessagePlan(
            assistant_message=stage_error,
            bundle_yaml="",
            missing_items=None,
            has_bundle_for_options=False,
            event_type="alignment_stage_blocked",
            event_payload={"status": "waiting_user", "error": stage_error},
            force_needs_user_input=True,
            use_default_decision_options=True,
        )
    if assistant_message and alignment_assistant_message_language_issue(assistant_message, prefers_chinese=prefers_chinese):
        return AlignmentOutputMessagePlan(
            assistant_message=alignment_fallback_assistant_message(
                has_bundle=bool(bundle_yaml),
                needs_user_input=alignment_needs_user_input(output),
            ),
            bundle_yaml=bundle_yaml,
            missing_items=missing_items,
            has_bundle_for_options=bool(bundle_yaml),
            event_type="alignment_language_mismatch",
            event_payload={"missing": ["assistant_message"], "surface": "assistant_message"},
            use_default_decision_options=True,
        )
    return AlignmentOutputMessagePlan(
        assistant_message=assistant_message,
        bundle_yaml=bundle_yaml,
        missing_items=missing_items,
        has_bundle_for_options=bool(bundle_yaml),
    )


def _text_has_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def alignment_block_message(
    *,
    prefers_chinese: bool,
    event_type: str,
    missing: list[str],
    fallback_zh: str,
) -> str:
    labels = ", ".join(missing)
    if prefers_chinese:
        return fallback_zh.format(missing=labels)
    if event_type == "alignment_checklist_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; these readiness checks are incomplete: "
            f"{labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_evidence_incomplete":
        return (
            "I can't prepare the confirmation agreement yet; this readiness evidence is not specific enough: "
            f"{labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_improvement_incomplete":
        return (
            "I can't prepare the improvement agreement yet; these source-based improvement judgments "
            f"are not specific enough: {labels}. Please answer the next Loop-shaping question first."
        )
    if event_type == "alignment_language_mismatch":
        return (
            "I can't prepare the confirmation agreement yet; these user-facing agreement fields need "
            f"the user's language: {labels}. Please rewrite those judgments."
        )
    return fallback_zh.format(missing=labels)


def alignment_fallback_assistant_message(*, has_bundle: bool, needs_user_input: bool) -> str:
    if has_bundle:
        return "已整理成一个可导入的 Loopora bundle。"
    if needs_user_input:
        return "我需要继续用中文对齐；请先确认一个会改变 Loop 形状的点：这次更怕结果看起来完成但证据不足，还是推进太慢？"
    return "我需要继续用中文对齐后再继续。"


def alignment_clarifying_reframe_message(*, prefers_chinese: bool) -> str:
    if prefers_chinese:
        return (
            "我先给一个推荐判断：默认应该优先阻断“看起来完成但证据不足”的结果，"
            "这样后续运行不会靠漂亮叙事过关。你可以直接选推荐，也可以改成更偏速度的方向。"
        )
    return (
        "My recommended default is to block results that look done but lack evidence, so the run cannot "
        "pass on a polished story alone. You can choose that recommendation or switch toward speed."
    )


def alignment_clarifying_stage_plan(output: dict, *, prefers_chinese: bool) -> AlignmentClarifyingStagePlan:
    question_issues = alignment_clarifying_question_issues(output)
    if not question_issues:
        return AlignmentClarifyingStagePlan(update_fields={"alignment_stage": "clarifying"}, output_updates={})
    return AlignmentClarifyingStagePlan(
        update_fields={"alignment_stage": "clarifying"},
        output_updates={
            "assistant_message": alignment_clarifying_reframe_message(prefers_chinese=prefers_chinese),
            "decision_options": default_alignment_decision_options(prefers_chinese=prefers_chinese),
            "needs_user_input": True,
            "bundle_yaml": "",
        },
        event_type="alignment_question_reframed",
        event_payload={"alignment_stage": "clarifying", "issues": question_issues},
    )


def alignment_bundle_stage_error(gate: AlignmentBundleStageGate) -> str:
    missing = [key for key in gate.readiness_keys if isinstance(gate.checklist, dict) and gate.checklist.get(key) is not True]
    error = ""
    if gate.stage not in gate.confirmed_stages:
        error = (
            "我还需要先完成需求对齐并得到你的明确确认，再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need to finish alignment and get your explicit confirmation before generating the Loop plan."
        )
    elif gate.phase != "bundle":
        error = (
            "我还需要先完成需求对齐，再生成 Loop 方案。请先确认边界、成功标准和协作方式。"
            if gate.prefers_chinese
            else "I need to finish alignment before generating the Loop plan. Please confirm the boundary, success criteria, and collaboration shape first."
        )
    elif not gate.agreement_summary:
        error = (
            "我还需要先整理一份工作协议摘要并得到确认，然后再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need a confirmed working agreement summary before generating the Loop plan."
        )
    elif not isinstance(gate.checklist, dict):
        error = (
            "我还需要先补齐对齐检查清单，再生成 Loop 方案。"
            if gate.prefers_chinese
            else "I need the alignment readiness checklist before generating the Loop plan."
        )
    elif missing:
        labels = ", ".join(missing)
        error = (
            f"我还不能直接生成 Loop 方案；对齐检查还缺：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these readiness checks are incomplete: {labels}. Please fill in this information first."
        )
    elif gate.evidence_issues:
        labels = ", ".join(gate.evidence_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些对齐证据还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; this readiness evidence is not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.improvement_issues:
        labels = ", ".join(gate.improvement_issues)
        error = (
            f"我还不能直接生成 Loop 方案；这些改进判断还不够具体：{labels}。请先补齐这些信息。"
            if gate.prefers_chinese
            else f"I can't generate the Loop plan yet; these improvement judgments are not specific enough: {labels}. Please fill in this information first."
        )
    elif gate.language_issues:
        labels = ", ".join(gate.language_issues)
        error = f"我还不能直接生成 Loop 方案；这些用户可见对齐证据需要使用中文：{labels}。请先补齐这些信息。"
    return error


def alignment_clarifying_question_issues(output: dict) -> list[str]:
    if output.get("needs_user_input") is not True:
        return []
    message = str(output.get("assistant_message", "") or "").strip()
    if not message:
        return []
    normalized = message.lower()
    issues: list[str] = []
    mechanical_terms = (
        "yaml",
        "bundle",
        "spec",
        "role_definition",
        "role definition",
        "role_definition_key",
        "workflow",
        "parallel_group",
        "parallel group",
        "controls",
        "builder",
        "inspector",
        "gatekeeper",
        "guide",
        "配置",
        "方案文件",
        "角色",
        "工作流",
        "并行组",
    )
    config_verbs = (
        "configure",
        "set up",
        "select",
        "choose",
        "use",
        "enable",
        "add",
        "want",
        "配置",
        "选择",
        "要不要",
        "是否需要",
        "启用",
        "添加",
        "扮演",
    )
    task_risk_terms = (
        "risk",
        "afraid",
        "worry",
        "fake",
        "evidence",
        "proof",
        "trust",
        "block",
        "strict",
        "done",
        "residual",
        "progress",
        "drift",
        "风险",
        "怕",
        "担心",
        "假完成",
        "证据",
        "证明",
        "信任",
        "阻断",
        "严格",
        "完成",
        "残余",
        "进展",
        "偏差",
    )
    has_mechanics = has_any_marker(normalized, mechanical_terms)
    has_config = has_any_marker(normalized, config_verbs)
    has_task_risk = has_any_marker(normalized, task_risk_terms)
    if has_mechanics and has_config and not has_task_risk:
        issues.append("mechanical_configuration_question")
    if alignment_questionnaire_overload(message):
        issues.append("questionnaire_overload")
    generic_patterns = (
        "do you want high quality",
        "what are your preferences",
        "what preferences do you have",
        "tell me your preferences",
        "what do you prefer",
        "what quality level do you want",
        "what is your preferred collaboration style",
        "what roles do you want",
        "what role should i play",
        "你要高质量吗",
        "你有什么偏好",
        "你的偏好是什么",
        "你想要什么质量",
        "你希望质量怎么样",
        "你喜欢什么风格",
        "你希望我扮演什么角色",
        "你想要哪些角色",
    )
    if has_any_marker(normalized, generic_patterns):
        issues.append("generic_alignment_question")
    if not alignment_has_recommended_decision_options(output):
        issues.append("missing_recommended_decision_options")
    return issues


def alignment_questionnaire_overload(message: str) -> bool:
    question_marks = message.count("?") + message.count("？")
    if question_marks >= 4:
        return True
    question_lines = 0
    question_line_re = re.compile(r"^\s*(?:[-*]|\d+[.)、]|[一二三四五六七八九十]+[、.])\s*")
    question_cues = (
        "?",
        "？",
        "请说明",
        "请描述",
        "请列出",
        "what ",
        "which ",
        "whether ",
        "how ",
        "do you ",
        "would you ",
    )
    for line in message.splitlines():
        normalized_line = line.strip().lower()
        if question_line_re.match(normalized_line) and has_any_marker(normalized_line, question_cues):
            question_lines += 1
    return question_lines >= 3
