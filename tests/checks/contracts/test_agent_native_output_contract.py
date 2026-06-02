from __future__ import annotations

from agent_adapter_test_support import (
    LooporaConflictError,
    pytest,
)


def test_agent_native_output_contract_requires_step_view_output_schema(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaConflictError, match="output_schema is required"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": {"action_policy": {"workspace": "read_only"}}},
        )


@pytest.mark.parametrize(
    ("missing_field", "message"),
    [
        ("judgment_contract", "judgment_contract is required"),
        ("required_coverage", "required_coverage is required"),
        ("action_policy", "action_policy is required"),
    ],
)
def test_agent_native_output_contract_requires_frozen_step_view_objects(
    service_factory,
    missing_field: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep the role tied to the reviewed Loop."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
        "known_evidence_ids": [],
    }
    step_view.pop(missing_field)

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )


def test_agent_native_output_contract_requires_known_evidence_id_closed_set(service_factory) -> None:
    service = service_factory(scenario="success")
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep evidence refs inside the step view."},
        "required_coverage": {"status": "pending"},
        "action_policy": {"workspace": "read_only", "can_block": True, "can_finish_run": False},
    }

    with pytest.raises(LooporaConflictError, match="known_evidence_ids must be a list"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )

    step_view["known_evidence_ids"] = [123]
    with pytest.raises(LooporaConflictError, match="known_evidence_ids must contain strings"):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )


@pytest.mark.parametrize(
    ("action_policy", "message"),
    [
        ({"workspace": "workspace-write", "can_block": True, "can_finish_run": False}, "action_policy.workspace"),
        ({"workspace": "read_only", "can_block": "true", "can_finish_run": False}, "action_policy.can_block"),
        ({"workspace": "read_only", "can_block": True, "can_finish_run": "false"}, "action_policy.can_finish_run"),
    ],
)
def test_agent_native_output_contract_rejects_malformed_action_policy(
    service_factory,
    action_policy: dict,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    step_view = {
        "output_schema": {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}},
        "judgment_contract": {"goal": "Keep permissions literal and inspectable."},
        "required_coverage": {"status": "pending"},
        "action_policy": action_policy,
        "known_evidence_ids": [],
    }

    with pytest.raises(LooporaConflictError, match=message):
        service._validate_agent_native_step_output_contract(
            {"summary": "This malformed step view should fail closed."},
            active={"agent_step_view": step_view},
        )
