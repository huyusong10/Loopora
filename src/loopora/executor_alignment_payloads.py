from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.alignment_traceability_terms import agent_candidate_task_anchor_terms
from loopora.executor_alignment_task_anchors import alignment_task_anchor_from_user_message, alignment_task_text_from_prompt
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
from loopora.executor_alignment_readiness_payloads import (
    alignment_missing_readiness_evidence,
    alignment_readiness_issue_for_scenario,
)
from loopora.executor_fake_errors import FakePayloadError
from loopora.service_types import LooporaError

BUNDLE_SCENARIO_FIXTURES_ASSET_NAME = "bundle-scenario-fixtures.json"

_alignment_task_anchor_from_user_message = alignment_task_anchor_from_user_message
_alignment_task_text_from_prompt = alignment_task_text_from_prompt


@dataclass(frozen=True)
class AlignmentPayloadState:
    mode: str
    alignment_stage: str
    workdir: str
    prefers_chinese: bool
    display_language: str
    is_improvement: bool


@dataclass(frozen=True)
class AlignmentBundleScenarioFixture:
    assistant_message: str
    bundle_yaml: str
    agreement_summary: str
    agreement_response: str
    readiness_evidence: str
    complete_readiness_checklist: bool
    skip_modes: frozenset[str]


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


def _alignment_bundle_payload_for_scenario(
    scenario: str,
    *,
    mode: str,
    workdir: str,
) -> dict | None:
    payload = _alignment_bundle_fixture_payload_for_scenario(scenario, mode=mode, workdir=workdir)
    if payload is not None:
        return payload
    return _alignment_readiness_issue_payload_for_scenario(scenario, workdir=workdir)


def _alignment_bundle_fixture_payload_for_scenario(scenario: str, *, mode: str, workdir: str) -> dict | None:
    fixture = _alignment_bundle_scenario_fixtures().get(str(scenario or ""))
    if fixture is None or mode in fixture.skip_modes:
        return None
    payload = alignment_response(
        status="bundle",
        assistant_message=fixture.assistant_message,
        needs_user_input=False,
        bundle_yaml=_alignment_bundle_yaml_from_fixture(fixture.bundle_yaml, workdir=workdir),
        phase="bundle",
    )
    agreement_payload = _alignment_bundle_agreement_payload_from_fixture(fixture.agreement_response)
    if agreement_payload is not None:
        payload["agreement_summary"] = agreement_payload["agreement_summary"]
        payload["readiness_evidence"] = agreement_payload["readiness_evidence"]
    elif fixture.agreement_summary:
        payload["agreement_summary"] = fixture.agreement_summary
    if fixture.readiness_evidence == "chinese":
        payload["readiness_evidence"] = alignment_chinese_readiness_evidence()
    elif fixture.readiness_evidence == "missing":
        payload["readiness_evidence"] = alignment_missing_readiness_evidence()
    if fixture.complete_readiness_checklist:
        payload["readiness_checklist"] = dict.fromkeys(payload["readiness_checklist"], True)
    return payload


def _alignment_bundle_agreement_payload_from_fixture(agreement_response: str) -> dict | None:
    if not agreement_response:
        return None
    factories = {
        "refund": alignment_refund_agreement_response,
        "chinese_refund": alignment_chinese_refund_agreement_response,
    }
    factory = factories.get(agreement_response)
    if factory is None:
        raise LooporaError(f"unknown bundle scenario fixture agreement response ref: {agreement_response}")
    return factory()


def _alignment_bundle_yaml_from_fixture(bundle_yaml: str, *, workdir: str) -> str:
    generators = {
        "default": alignment_bundle_yaml,
        "governance_markers_listed_as_facts": alignment_bundle_yaml_with_governance_markers_listed_as_facts,
        "unsupported_observed_workdir_claim": alignment_bundle_yaml_with_unsupported_observed_workdir_claim,
        "without_semantics": alignment_bundle_yaml_without_semantics,
        "chinese": alignment_chinese_bundle_yaml,
        "chinese_with_english_visible_names": alignment_chinese_bundle_yaml_with_english_visible_names,
        "refund_repair": alignment_refund_repair_bundle_yaml,
        "chinese_refund_repair": alignment_chinese_refund_repair_bundle_yaml,
        "lineage_metadata": alignment_bundle_yaml_with_lineage_metadata,
    }
    if bundle_yaml == "invalid_minimal":
        return "version: 1\nmetadata:\n  name: Broken Alignment Bundle\n"
    if bundle_yaml == "markdown_fenced_default":
        return f"```yaml\n{alignment_bundle_yaml(workdir)}```"
    generator = generators.get(bundle_yaml)
    if generator is None:
        raise LooporaError(f"unknown bundle scenario fixture YAML ref: {bundle_yaml}")
    return generator(workdir)


@lru_cache(maxsize=1)
def _alignment_bundle_scenario_fixtures() -> dict[str, AlignmentBundleScenarioFixture]:
    asset = load_alignment_guidance_assets().bundle_scenario_fixtures
    scenario_payloads = asset.get("scenario_payloads")
    if not isinstance(scenario_payloads, dict):
        raise LooporaError(f"{BUNDLE_SCENARIO_FIXTURES_ASSET_NAME} must define scenario_payloads")
    return {str(scenario): _alignment_bundle_scenario_fixture(str(scenario), fixture) for scenario, fixture in scenario_payloads.items()}


def _alignment_bundle_scenario_fixture(scenario: str, fixture: object) -> AlignmentBundleScenarioFixture:
    if not isinstance(fixture, dict):
        raise LooporaError(f"invalid bundle scenario fixture: {scenario}")
    assistant_message = fixture.get("assistant_message")
    bundle_yaml = fixture.get("bundle_yaml")
    agreement_summary = fixture.get("agreement_summary", "")
    agreement_response = fixture.get("agreement_response", "")
    readiness_evidence = fixture.get("readiness_evidence", "")
    complete_readiness_checklist = fixture.get("complete_readiness_checklist", False)
    skip_modes = fixture.get("skip_modes", [])
    if not isinstance(assistant_message, str) or not assistant_message.strip() or not isinstance(bundle_yaml, str):
        raise LooporaError(f"invalid bundle scenario fixture fields: {scenario}")
    if (
        not isinstance(agreement_summary, str)
        or not isinstance(agreement_response, str)
        or readiness_evidence not in {"", "chinese", "missing"}
        or not isinstance(complete_readiness_checklist, bool)
    ):
        raise LooporaError(f"invalid bundle scenario fixture extras: {scenario}")
    if not isinstance(skip_modes, list) or not all(isinstance(mode, str) and mode.strip() for mode in skip_modes):
        raise LooporaError(f"invalid bundle scenario fixture skip modes: {scenario}")
    return AlignmentBundleScenarioFixture(
        assistant_message=assistant_message,
        bundle_yaml=bundle_yaml,
        agreement_summary=agreement_summary,
        agreement_response=agreement_response,
        readiness_evidence=str(readiness_evidence),
        complete_readiness_checklist=complete_readiness_checklist,
        skip_modes=frozenset(skip_modes),
    )


def _alignment_readiness_issue_payload_for_scenario(scenario: str, *, workdir: str) -> dict | None:
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
