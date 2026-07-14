from __future__ import annotations

from dataclasses import dataclass

from loopora.executor_fake_builder_payloads import (
    fake_builder_payload,
    fake_check_planner_payload,
    fake_tester_payload,
)
from loopora.executor_fake_verifier_payloads import (
    fake_challenger_payload,
    fake_custom_payload,
    fake_verifier_payload,
)


@dataclass(frozen=True)
class FakePayloadContext:
    iter_id: int
    compiled_spec: dict
    checks: list[dict]
    check_count: int
    archetype: str


def fake_payload_context(request) -> FakePayloadContext:
    compiled_spec = request.extra_context.get("compiled_spec", {})
    checks = compiled_spec.get("checks", [])
    return FakePayloadContext(
        iter_id=int(request.extra_context.get("iter_id", 0)),
        compiled_spec=compiled_spec,
        checks=checks,
        check_count=max(len(checks), 1),
        archetype=str(request.role_archetype or request.extra_context.get("archetype") or request.role).strip().lower(),
    )


def fake_provider_failure_message(scenario: str, request, context: FakePayloadContext) -> str:
    if scenario == "alignment_resume_failure" and request.role == "alignment" and request.resume_session_id:
        return "simulated native resume failure"
    if scenario == "role_failure" and context.archetype in {"tester", "inspector"}:
        return "simulated inspector failure"
    return ""


def fake_role_payload(
    scenario: str,
    request,
    context: FakePayloadContext,
    *,
    display_language: str = "en",
) -> dict | None:
    if context.archetype in {"generator", "builder"}:
        payload = fake_builder_payload(context.iter_id, display_language=display_language)
    elif request.role == "check_planner":
        payload = fake_check_planner_payload(context.compiled_spec, display_language=display_language)
    elif context.archetype in {"tester", "inspector"}:
        payload = fake_tester_payload(
            context.iter_id,
            context.checks,
            context.check_count,
            display_language=display_language,
        )
    elif context.archetype in {"verifier", "gatekeeper"}:
        payload = fake_verifier_payload(
            scenario,
            context.iter_id,
            request,
            context.check_count,
            display_language=display_language,
        )
    elif context.archetype in {"challenger", "guide"}:
        payload = fake_challenger_payload(context.iter_id, request, display_language=display_language)
    elif context.archetype == "custom":
        payload = fake_custom_payload(display_language=display_language)
    else:
        payload = None
    return payload
