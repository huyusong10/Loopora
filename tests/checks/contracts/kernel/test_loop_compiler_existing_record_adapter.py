from __future__ import annotations

from loopora.compiler import compile_existing_loop_record


EXISTING_RECORD_MAX_ITERATIONS = 3


def test_existing_loop_record_compiles_to_loop_definition_kernel_objects() -> None:
    definition = compile_existing_loop_record(
        {
            "id": "loop_refund",
            "name": "Refund Loop",
            "workdir": "/tmp/refund",
            "spec_path": "/tmp/refund/spec.md",
            "compiled_spec": {
                "goal": "Ship refund safety.",
                "checks": [{"id": "permission", "title": "Permission proof", "details": "Admin permission is verified."}],
                "fake_done_states": ["Happy path only."],
                "evidence_preferences": ["Prefer contract tests."],
            },
            "workflow": {
                "roles": [{"id": "builder", "name": "Builder", "archetype": "builder"}],
                "steps": [{"id": "build", "role_id": "builder", "objective": "Produce proof."}],
            },
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": EXISTING_RECORD_MAX_ITERATIONS,
            "max_role_retries": 2,
        }
    )

    assert definition.id == "loop_refund"
    assert definition.contract.task == "Ship refund safety."
    assert definition.contract.done_when[0].id == "permission"
    assert definition.contract.evidence_targets[0].id == "done_when.permission"
    assert definition.strategy.roles[0].id == "builder"
    assert definition.strategy.steps[0].id == "build"
    assert definition.runtime_defaults.max_iterations == EXISTING_RECORD_MAX_ITERATIONS
    assert definition.metadata.source_kind == "existing_loop_record"


def test_existing_loop_record_compiler_prefers_strategy_source_over_legacy_aliases() -> None:
    definition = compile_existing_loop_record(
        {
            "id": "loop_strategy_source",
            "compiled_spec": {"goal": "Prefer strategy source.", "checks": []},
            "strategy_source": {
                "roles": [{"id": "builder", "archetype": "builder"}],
                "steps": [{"id": "build", "role_id": "builder"}],
            },
            "workflow": {
                "roles": [{"id": "workflow_alias", "archetype": "inspector"}],
                "steps": [{"id": "inspect", "role_id": "workflow_alias"}],
            },
            "workflow_json": {
                "roles": [{"id": "storage_alias", "archetype": "gatekeeper"}],
                "steps": [{"id": "judge", "role_id": "storage_alias"}],
            },
        }
    )

    assert [role.id for role in definition.strategy.roles] == ["builder"]
    assert [step.id for step in definition.strategy.steps] == ["build"]
