from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.alignment_readiness_shared import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.executor_alignment_bundle_fixtures import alignment_bundle_yaml
from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response,
    alignment_chinese_agreement_response,
    alignment_chinese_improvement_agreement_response,
    alignment_chinese_refund_agreement_response,
    alignment_improvement_agreement_response,
    alignment_refund_agreement_response,
)
from loopora.executor_alignment_responses import (
    alignment_response,
)
from loopora.service_types import LooporaError

PRECONFIRMATION_FIXTURES_ASSET_NAME = "preconfirmation-scenario-fixtures.json"


@dataclass(frozen=True)
class AlignmentPreconfirmationPayloadRequest:
    mode: str
    alignment_stage: str
    workdir: str
    prefers_chinese: bool
    is_improvement: bool


def alignment_preconfirmation_payload_for_scenario(
    scenario: str,
    *,
    request: AlignmentPreconfirmationPayloadRequest,
) -> dict | None:
    payload = _alignment_preconfirmation_scenario_payload(scenario, workdir=request.workdir)
    if payload is not None:
        return payload
    if request.mode != "repair" and request.alignment_stage not in {
        "confirmed",
        "compiling",
        "ready_review",
    }:
        return _alignment_preconfirmation_agreement_payload_for_scenario(
            scenario,
            prefers_chinese=request.prefers_chinese,
            is_improvement=request.is_improvement,
        )
    return None


def _alignment_preconfirmation_scenario_payload(scenario: str, *, workdir: str) -> dict | None:
    fixture = _alignment_preconfirmation_scenario_fixtures().get(str(scenario or ""))
    if fixture is None:
        return None
    payload = alignment_response(
        status=fixture["status"],
        assistant_message=fixture["assistant_message"],
        needs_user_input=fixture["needs_user_input"],
        bundle_yaml=_alignment_preconfirmation_bundle_yaml(fixture["bundle_yaml"], workdir=workdir),
        phase=fixture["phase"],
    )
    decision_options = fixture.get("decision_options")
    if decision_options:
        payload["decision_options"] = [dict(option) for option in decision_options]
    return payload


def _alignment_preconfirmation_agreement_payload_for_scenario(
    scenario: str,
    *,
    prefers_chinese: bool,
    is_improvement: bool,
) -> dict:
    scenario_key = str(scenario or "")
    override = _alignment_preconfirmation_agreement_overrides().get(scenario_key, {})
    base_response = override.get("base_response", "")
    routes = _alignment_preconfirmation_agreement_base_routes()
    if base_response == "default_en":
        payload = alignment_agreement_response()
    elif is_improvement and scenario_key not in routes["improvement_excluded_scenarios"]:
        payload = alignment_chinese_improvement_agreement_response() if prefers_chinese else alignment_improvement_agreement_response()
    elif scenario_key in routes["chinese_refund_scenarios"]:
        payload = alignment_chinese_refund_agreement_response()
    elif scenario_key in routes["refund_scenarios"]:
        payload = alignment_refund_agreement_response()
    else:
        payload = alignment_chinese_agreement_response() if prefers_chinese else alignment_agreement_response()
    _apply_alignment_preconfirmation_agreement_override(payload, override)
    return payload


def _apply_alignment_preconfirmation_agreement_override(payload: dict, override: dict[str, object]) -> None:
    assistant_message = override.get("assistant_message")
    if isinstance(assistant_message, str):
        payload["assistant_message"] = assistant_message
    readiness_checklist = override.get("readiness_checklist")
    if isinstance(readiness_checklist, dict):
        payload["readiness_checklist"].update(readiness_checklist)
    readiness_evidence = override.get("readiness_evidence")
    if isinstance(readiness_evidence, dict):
        payload["readiness_evidence"].update(readiness_evidence)


def _alignment_preconfirmation_bundle_yaml(bundle_yaml: str, *, workdir: str) -> str:
    if bundle_yaml == "default_alignment_bundle":
        return alignment_bundle_yaml(workdir)
    return bundle_yaml


@lru_cache(maxsize=1)
def _alignment_preconfirmation_fixtures() -> dict:
    asset = load_alignment_guidance_assets().preconfirmation_fixtures
    if (
        not isinstance(asset.get("scenario_payloads"), dict)
        or not isinstance(asset.get("agreement_base_routes"), dict)
        or not isinstance(asset.get("agreement_overrides"), dict)
    ):
        raise LooporaError(f"{PRECONFIRMATION_FIXTURES_ASSET_NAME} must define preconfirmation fixture maps")
    return asset


@lru_cache(maxsize=1)
def _alignment_preconfirmation_scenario_fixtures() -> dict[str, dict[str, object]]:
    return {
        str(scenario): _alignment_preconfirmation_scenario_fixture(str(scenario), fixture)
        for scenario, fixture in _alignment_preconfirmation_fixtures()["scenario_payloads"].items()
    }


def _alignment_preconfirmation_scenario_fixture(scenario: str, fixture: object) -> dict[str, object]:
    if not isinstance(fixture, dict):
        raise LooporaError(f"invalid preconfirmation scenario fixture: {scenario}")
    status = fixture.get("status")
    assistant_message = fixture.get("assistant_message")
    needs_user_input = fixture.get("needs_user_input")
    bundle_yaml = fixture.get("bundle_yaml", "")
    phase = fixture.get("phase")
    decision_options = fixture.get("decision_options")
    if status not in {"question", "blocked", "bundle"} or phase not in {"clarifying", "blocked", "bundle"}:
        raise LooporaError(f"invalid preconfirmation scenario status: {scenario}")
    if not isinstance(assistant_message, str) or not assistant_message.strip() or not isinstance(needs_user_input, bool) or not isinstance(bundle_yaml, str):
        raise LooporaError(f"invalid preconfirmation scenario fields: {scenario}")
    normalized: dict[str, object] = {
        "status": status,
        "assistant_message": assistant_message,
        "needs_user_input": needs_user_input,
        "bundle_yaml": bundle_yaml,
        "phase": phase,
    }
    if decision_options is not None:
        normalized["decision_options"] = _alignment_preconfirmation_decision_options(scenario, decision_options)
    return normalized


def _alignment_preconfirmation_decision_options(scenario: str, decision_options: object) -> list[dict[str, object]]:
    if not isinstance(decision_options, list) or not decision_options:
        raise LooporaError(f"invalid preconfirmation decision options: {scenario}")
    normalized = []
    for option in decision_options:
        if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not isinstance(option.get("recommended"), bool):
            raise LooporaError(f"invalid preconfirmation decision option: {scenario}")
        normalized.append(dict(option))
    return normalized


@lru_cache(maxsize=1)
def _alignment_preconfirmation_agreement_base_routes() -> dict[str, set[str]]:
    routes = _alignment_preconfirmation_fixtures()["agreement_base_routes"]
    route_names = ("improvement_excluded_scenarios", "chinese_refund_scenarios", "refund_scenarios")
    return {route_name: _alignment_preconfirmation_scenario_set(routes, route_name) for route_name in route_names}


def _alignment_preconfirmation_scenario_set(routes: dict, route_name: str) -> set[str]:
    values = routes.get(route_name)
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise LooporaError(f"invalid preconfirmation agreement route: {route_name}")
    return set(values)


@lru_cache(maxsize=1)
def _alignment_preconfirmation_agreement_overrides() -> dict[str, dict[str, object]]:
    return {
        str(scenario): _alignment_preconfirmation_agreement_override(str(scenario), override)
        for scenario, override in _alignment_preconfirmation_fixtures()["agreement_overrides"].items()
    }


def _alignment_preconfirmation_agreement_override(scenario: str, override: object) -> dict[str, object]:
    if not isinstance(override, dict):
        raise LooporaError(f"invalid preconfirmation agreement override: {scenario}")
    normalized = dict(override)
    base_response = normalized.get("base_response")
    if base_response is not None and base_response != "default_en":
        raise LooporaError(f"invalid preconfirmation agreement base response: {scenario}")
    readiness_checklist = normalized.get("readiness_checklist")
    if readiness_checklist is not None and not _alignment_preconfirmation_checklist_override(readiness_checklist):
        raise LooporaError(f"invalid preconfirmation agreement checklist override: {scenario}")
    readiness_evidence = normalized.get("readiness_evidence")
    if readiness_evidence is not None and not _alignment_preconfirmation_evidence_override(readiness_evidence):
        raise LooporaError(f"invalid preconfirmation agreement evidence override: {scenario}")
    assistant_message = normalized.get("assistant_message")
    if assistant_message is not None and (not isinstance(assistant_message, str) or not assistant_message.strip()):
        raise LooporaError(f"invalid preconfirmation agreement assistant message: {scenario}")
    return normalized


def _alignment_preconfirmation_checklist_override(value: object) -> bool:
    checklist_keys = {*ALIGNMENT_READINESS_EVIDENCE_KEYS, "explicit_confirmation"}
    return isinstance(value, dict) and all(isinstance(key, str) and key in checklist_keys and isinstance(item, bool) for key, item in value.items())


def _alignment_preconfirmation_evidence_override(value: object) -> bool:
    evidence_keys = {*ALIGNMENT_READINESS_EVIDENCE_KEYS, "open_questions"}
    return isinstance(value, dict) and all(isinstance(key, str) and key in evidence_keys and isinstance(item, str) for key, item in value.items())
