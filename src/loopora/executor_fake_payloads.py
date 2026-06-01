from __future__ import annotations

from loopora.branding import APP_STATE_DIRNAME
from loopora.executor_alignment_bundle_fixtures import (
    alignment_bundle_yaml,
    alignment_bundle_yaml_with_governance_markers_listed_as_facts,
    alignment_bundle_yaml_with_lineage_metadata,
    alignment_bundle_yaml_with_unsupported_observed_workdir_claim,
    alignment_bundle_yaml_without_semantics,
    alignment_chinese_bundle_yaml,
    alignment_chinese_bundle_yaml_with_english_visible_names,
    alignment_chinese_improvement_bundle_yaml,
    alignment_improvement_bundle_yaml,
)
from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response,
    alignment_chinese_agreement_response,
    alignment_chinese_improvement_agreement_response,
    alignment_chinese_refund_agreement_response,
    alignment_improvement_agreement_response,
    alignment_refund_agreement_response,
)
from loopora.executor_alignment_payloads import build_alignment_payload
from loopora.executor_alignment_readiness_responses import (
    alignment_chinese_improvement_readiness_evidence,
    alignment_chinese_readiness_evidence,
    alignment_improvement_readiness_evidence,
    alignment_readiness_evidence,
)
from loopora.executor_alignment_responses import (
    alignment_default_bundle_response,
    alignment_response,
)
from loopora.executor_fake_errors import FakePayloadError
from loopora.executor_fake_role_payloads import (
    FakePayloadContext,
    fake_payload_context,
    fake_provider_failure_message,
    fake_role_payload,
)


__all__ = (
    "FakePayloadError",
    "alignment_agreement_response",
    "alignment_bundle_yaml",
    "alignment_bundle_yaml_with_governance_markers_listed_as_facts",
    "alignment_bundle_yaml_with_lineage_metadata",
    "alignment_bundle_yaml_with_unsupported_observed_workdir_claim",
    "alignment_bundle_yaml_without_semantics",
    "alignment_chinese_agreement_response",
    "alignment_chinese_bundle_yaml",
    "alignment_chinese_bundle_yaml_with_english_visible_names",
    "alignment_chinese_improvement_agreement_response",
    "alignment_chinese_improvement_bundle_yaml",
    "alignment_chinese_improvement_readiness_evidence",
    "alignment_chinese_readiness_evidence",
    "alignment_chinese_refund_agreement_response",
    "alignment_default_bundle_response",
    "alignment_improvement_agreement_response",
    "alignment_improvement_bundle_yaml",
    "alignment_improvement_readiness_evidence",
    "alignment_readiness_evidence",
    "alignment_refund_agreement_response",
    "alignment_response",
    "build_alignment_payload",
    "build_fake_payload",
)


def build_fake_payload(scenario: str, request) -> dict:
    context = fake_payload_context(request)
    _raise_for_fake_provider_failure(scenario, request, context)
    if request.role == "alignment" or context.archetype == "alignment":
        return build_alignment_payload(scenario, request)
    if _should_destructively_clear_workdir(scenario, context.archetype):
        _clear_workdir_for_destructive_fake(request)
    payload = fake_role_payload(scenario, request, context)
    if payload is None:
        raise FakePayloadError(f"unsupported fake role: {request.role}")
    return payload


def _raise_for_fake_provider_failure(scenario: str, request, context: FakePayloadContext) -> None:
    message = fake_provider_failure_message(scenario, request, context)
    if message:
        raise FakePayloadError(message)


def _should_destructively_clear_workdir(scenario: str, archetype: str) -> bool:
    return (scenario == "destructive_generator" and archetype in {"generator", "builder"}) or (
        scenario == "destructive_tester" and archetype in {"tester", "inspector"}
    )


def _clear_workdir_for_destructive_fake(request) -> None:
    for child in request.workdir.iterdir():
        if child.name == APP_STATE_DIRNAME:
            continue
        if child.is_dir():
            for nested in sorted(child.rglob("*"), key=lambda path: len(path.parts), reverse=True):
                if nested.is_file():
                    nested.unlink()
                elif nested.is_dir():
                    nested.rmdir()
            child.rmdir()
        else:
            child.unlink()
