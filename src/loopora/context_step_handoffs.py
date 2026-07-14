from __future__ import annotations

"""Step handoff projection from role output."""

from typing import Protocol

from loopora.context_step_artifact_refs import output_workspace_artifact_refs
from loopora.context_value_helpers import clean_text, gatekeeper_blockers, inspector_blockers, string_list
from loopora.run_artifacts import RunArtifactLayout, artifact_ref
from loopora.runtime_task_language import runtime_task_text
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import coerced_non_negative_int


class StepHandoffContext(Protocol):
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    output: dict
    task_language: str


def build_step_handoff(result: StepHandoffContext) -> dict:
    archetype = str(result.role["archetype"])
    iter_id = coerced_non_negative_int(result.iter_id)
    step_order = coerced_non_negative_int(result.step_order)
    handoff = _handoff_core(archetype, result.output, language=result.task_language)
    artifact_refs = [
        artifact_ref(
            result.layout,
            result.layout.step_output_raw_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="output-raw",
        ),
        artifact_ref(
            result.layout,
            result.layout.step_output_normalized_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="output-normalized",
        ),
        artifact_ref(
            result.layout,
            result.layout.step_metadata_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="metadata",
        ),
    ]
    artifact_refs.extend(output_workspace_artifact_refs(result.layout, result.output))
    return {
        "source": {
            "iter": iter_id,
            "step_id": str(result.step["id"]),
            "step_order": step_order,
            "role_id": str(result.role["id"]),
            "role_name": str(result.role["name"]),
            "runtime_role": str(result.runtime_role),
            "archetype": archetype,
        },
        **handoff,
        "evidence_refs": [],
        "artifact_refs": artifact_refs,
    }


def _handoff_core(archetype: str, output: dict, *, language: str) -> dict:
    if archetype == "builder":
        return _builder_handoff(output, language=language)
    if archetype == "inspector":
        return _inspector_handoff(output, language=language)
    if archetype == "gatekeeper":
        return _gatekeeper_handoff(output, language=language)
    if archetype == "guide":
        return _guide_handoff(output, language=language)
    return _custom_handoff(output, language=language)


def _builder_handoff(output: dict, *, language: str) -> dict:
    summary = clean_text(output.get("summary") or output.get("attempted")) or runtime_task_text(
        language,
        "Builder completed its change pass.",
        "Builder 已完成本轮改动。",
    )
    abandoned = clean_text(output.get("abandoned"))
    if abandoned:
        abandoned_label = runtime_task_text(language, "Out-of-scope or unfinished note: ", "范围外或未完成说明：")
        summary = f"{summary} {abandoned_label}{abandoned}"
    return {
        "status": "completed",
        "summary": summary,
        "blocking_items": [],
        "recommended_next_action": clean_text(output.get("assumption"))
        or runtime_task_text(language, "Validate the visible change with inspection.", "通过检查验证可见改动。"),
    }


def _inspector_handoff(output: dict, *, language: str) -> dict:
    blocking_items = inspector_blockers(output)
    return {
        "status": "blocked" if blocking_items else "completed",
        "summary": clean_text(output.get("tester_observations"))
        or runtime_task_text(language, "Inspector collected workspace evidence.", "Inspector 已收集工作区证据。"),
        "blocking_items": blocking_items,
        "recommended_next_action": (
            runtime_task_text(language, "Address the failing checks with the strongest direct evidence.", "用最强的直接证据处理未通过的检查。")
            if blocking_items
            else runtime_task_text(language, "Pass the evidence bundle to GateKeeper for a verdict.", "将证据包提交给 GateKeeper 裁决。")
        ),
    }


def _gatekeeper_handoff(output: dict, *, language: str) -> dict:
    blocking_items = gatekeeper_blockers(output)
    status = "passed" if structured_bool_is_true(output.get("passed")) else "blocked"
    recommended_next_action = clean_text(output.get("feedback_to_builder") or output.get("feedback_to_generator"))
    if not recommended_next_action:
        recommended_next_action = (
            runtime_task_text(language, "No further role action is required; the GateKeeper verdict passed.", "GateKeeper 裁决已通过，无需继续执行角色动作。")
            if status == "passed"
            else runtime_task_text(language, "Continue only after the blocking issues are resolved.", "只有解决阻断问题后才能继续。")
        )
    return {
        "status": status,
        "summary": clean_text(output.get("decision_summary"))
        or runtime_task_text(language, "GateKeeper evaluated the current evidence.", "GateKeeper 已评估当前证据。"),
        "blocking_items": blocking_items,
        "recommended_next_action": recommended_next_action,
    }


def _guide_handoff(output: dict, *, language: str) -> dict:
    analysis = output.get("analysis") if isinstance(output.get("analysis"), dict) else {}
    blocking_items = []
    risk_note = clean_text(analysis.get("risk_note"))
    if risk_note:
        blocking_items.append(risk_note)
    return {
        "status": "advisory",
        "summary": clean_text(analysis.get("recommended_shift") or output.get("meta_note"))
        or runtime_task_text(language, "Guide proposed a direction shift.", "Guide 提出了方向调整建议。"),
        "blocking_items": blocking_items,
        "recommended_next_action": (
            clean_text(output.get("seed_question") or analysis.get("recommended_shift"))
            or runtime_task_text(language, "Use the guidance as the next experiment seed.", "将这条建议作为下一次实验的起点。")
        ),
    }


def _custom_handoff(output: dict, *, language: str) -> dict:
    blocking_items = [item for item in string_list(output.get("blocking_items")) if item]
    if not blocking_items:
        blocking_items = [item for item in string_list(output.get("risks")) if item]
    return {
        "status": clean_text(output.get("status")).lower() or "advisory",
        "summary": clean_text(output.get("summary") or output.get("handoff_note"))
        or runtime_task_text(language, "Custom role prepared a scoped handoff.", "自定义角色已准备好范围明确的交接。"),
        "blocking_items": blocking_items,
        "recommended_next_action": (
            clean_text(output.get("recommended_next_action"))
            or clean_text((string_list(output.get("recommendations")) or [""])[0] or output.get("handoff_note"))
            or runtime_task_text(language, "Use this handoff in a Builder or Inspector step.", "在 Builder 或 Inspector 步骤中使用这份交接。")
        ),
    }
