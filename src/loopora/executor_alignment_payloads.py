from __future__ import annotations

from dataclasses import dataclass

from loopora.executor_alignment_bundle_fixtures import (
    alignment_bundle_yaml,
    alignment_bundle_yaml_with_governance_markers_listed_as_facts,
    alignment_bundle_yaml_with_lineage_metadata,
    alignment_bundle_yaml_with_unsupported_observed_workdir_claim,
    alignment_bundle_yaml_without_semantics,
    alignment_chinese_bundle_yaml,
    alignment_chinese_bundle_yaml_with_english_visible_names,
)
from loopora.executor_alignment_responses import (
    alignment_chinese_readiness_evidence,
    alignment_default_bundle_response,
    alignment_response,
)
from loopora.executor_alignment_preconfirmation_payloads import (
    AlignmentPreconfirmationPayloadRequest,
    alignment_preconfirmation_payload_for_scenario,
)
from loopora.executor_alignment_readiness_payloads import (
    alignment_missing_readiness_evidence,
    alignment_readiness_issue_for_scenario,
)
from loopora.executor_fake_errors import FakePayloadError


@dataclass(frozen=True)
class AlignmentPayloadState:
    mode: str
    alignment_stage: str
    workdir: str
    prefers_chinese: bool
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
        is_improvement=str(working_agreement.get("mode") or "") == "improvement",
    )
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
    payload: dict | None = None
    payload = _alignment_workdir_fact_bundle_payload(scenario, workdir=workdir)
    if payload is not None:
        return payload
    if scenario == "alignment_invalid":
        payload = alignment_response(
            status="bundle",
            assistant_message="我先给出一个故意不完整的 bundle。",
            needs_user_input=False,
            bundle_yaml="version: 1\nmetadata:\n  name: Broken Alignment Bundle\n",
            phase="bundle",
        )
    elif scenario == "alignment_invalid_then_valid" and mode != "repair":
        payload = alignment_response(
            status="bundle",
            assistant_message="我先给出一个需要修复的 bundle。",
            needs_user_input=False,
            bundle_yaml="version: 1\nmetadata:\n  name: Broken Alignment Bundle\n",
            phase="bundle",
        )
    elif scenario == "alignment_semantic_invalid_then_valid" and mode != "repair":
        payload = alignment_response(
            status="bundle",
            assistant_message="我先给出一个语义不完整的 bundle。",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml_without_semantics(workdir),
            phase="bundle",
        )
    elif scenario == "alignment_chinese_readiness_evidence":
        payload = alignment_response(
            status="bundle",
            assistant_message="我已用中文整理成一个可导入的 Loopora bundle。",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    elif scenario == "alignment_english_bundle_prose_for_chinese_user":
        payload = alignment_response(
            status="bundle",
            assistant_message="我准备了一个 bundle，但正文仍然是英文。",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    elif scenario == "alignment_english_visible_bundle_names_for_chinese_user":
        payload = alignment_response(
            status="bundle",
            assistant_message="我准备了一个中文 bundle，但可见名称仍然是英文。",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml_with_english_visible_names(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    elif scenario == "alignment_english_assistant_message_for_chinese_bundle":
        payload = alignment_response(
            status="bundle",
            assistant_message="I prepared an importable Loopora bundle.",
            needs_user_input=False,
            bundle_yaml=alignment_chinese_bundle_yaml(workdir),
            phase="bundle",
        )
        payload["agreement_summary"] = "使用聚焦 Builder、证据 Inspector 和严格 GateKeeper 来推进这个 Loop。"
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    elif scenario == "alignment_english_bundle_for_chinese_user":
        payload = alignment_response(
            status="bundle",
            assistant_message="I prepared an importable Loopora bundle.",
            needs_user_input=False,
            bundle_yaml=alignment_bundle_yaml(workdir),
            phase="bundle",
        )
    else:
        payload = _alignment_readiness_issue_payload_for_scenario(scenario, workdir=workdir)
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
