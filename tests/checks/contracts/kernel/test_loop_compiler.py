from __future__ import annotations

from inspect import signature

import pytest

from loopora.bundles import load_bundle_text
from loopora.compiler import (
    LoopCompiler,
    LoopSource,
    LoopSourceKind,
    compile_agent_message_source,
    compile_existing_loop_record,
    compile_loop_contract,
    compile_loop_strategy,
    compile_loopfile_source,
    compile_markdown_contract_source,
    compile_strategy_template_source,
    compile_web_alignment_source,
)
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.kernel.contract import ResidualRiskPolicy


def test_strategy_compiler_accepts_strategy_source_boundary_name() -> None:
    parameters = signature(compile_loop_strategy).parameters

    assert "strategy_source" in parameters
    assert "workflow" not in parameters


def test_loop_compiler_contract_covers_current_source_kinds() -> None:
    assert set(LoopSourceKind) == {
        LoopSourceKind.AGENT_MESSAGE,
        LoopSourceKind.WEB_ALIGNMENT,
        LoopSourceKind.MARKDOWN_CONTRACT,
        LoopSourceKind.LOOPFILE,
        LoopSourceKind.STRATEGY_TEMPLATE,
        LoopSourceKind.EXISTING_LOOP_RECORD,
    }


def test_compiled_spec_compiles_to_loop_contract_without_workflow_state() -> None:
    contract = compile_loop_contract(
        "loop_refund",
        {
            "goal": "Ship refund safety.",
            "checks": [{"id": "permission", "title": "Permission proof"}],
            "success_surface": ["Refunds are auditable."],
            "fake_done_states": ["Happy path only."],
            "evidence_preferences": ["Prefer contract tests."],
            "residual_risk": {"policy": "disallow"},
        },
        completion_mode="rounds",
    )

    target_ids = {target.id for target in contract.evidence_targets}
    assert contract.task == "Ship refund safety."
    assert contract.done_when[0].id == "permission"
    assert contract.evidence_needed[0].label == "Prefer contract tests."
    assert contract.residual_risk_policy == ResidualRiskPolicy.DISALLOW
    assert {
        "done_when.permission",
        "success_surface.surface_001",
        "fake_done.risk_001",
        "evidence_preference.pref_001",
    } <= target_ids
    assert "gatekeeper.finish" not in target_ids


def test_strategy_source_compiles_to_loop_strategy_without_spec_state() -> None:
    strategy = compile_loop_strategy(
        "loop_refund",
        {
            "roles": [{"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"}],
            "steps": [
                {
                    "id": "judge",
                    "role_id": "gatekeeper",
                    "objective": "Judge closure.",
                    "action_policy": {"can_finish_run": True},
                }
            ],
            "required_target_ids": ["done_when.permission"],
        },
        max_iterations=4,
        max_step_retries=2,
        residual_risk_policy=ResidualRiskPolicy.DISALLOW,
    )

    assert strategy.roles[0].id == "gatekeeper"
    assert strategy.steps[0].id == "judge"
    assert strategy.evidence_flow.required_target_ids == ("done_when.permission",)
    assert strategy.evidence_flow.gatekeeper_step_id == "judge"
    assert strategy.iteration_policy.max_iterations == 4
    assert strategy.iteration_policy.max_step_retries == 2
    assert strategy.finish_policy.allow_residual_risk is False


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
            "max_iters": 3,
            "max_role_retries": 2,
        }
    )

    assert definition.id == "loop_refund"
    assert definition.contract.task == "Ship refund safety."
    assert definition.contract.done_when[0].id == "permission"
    assert definition.contract.evidence_targets[0].id == "done_when.permission"
    assert definition.strategy.roles[0].id == "builder"
    assert definition.strategy.steps[0].id == "build"
    assert definition.runtime_defaults.max_iterations == 3
    assert definition.metadata.source_kind == "existing_loop_record"


def test_loop_compiler_accepts_explicit_source_boundary() -> None:
    source = LoopSource(
        kind=LoopSourceKind.EXISTING_LOOP_RECORD,
        payload={
            "id": "loop_source",
            "name": "Source Loop",
            "compiled_spec": {"goal": "Compile through source.", "checks": []},
            "workflow": {"roles": [], "steps": []},
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loop_source"
    assert definition.metadata.source_kind == "existing_loop_record"


def test_loop_compiler_compiles_markdown_contract_source_to_loop_definition() -> None:
    source = LoopSource(
        kind=LoopSourceKind.MARKDOWN_CONTRACT,
        id="spec_refund",
        payload={
            "id": "loop_markdown",
            "name": "Markdown Loop",
            "markdown": """
# Task

Ship refund safety.

# Done When

- Permission proof
  - when: refunds are requested
  - expect: admin permission is verified

# Guardrails

Do not weaken auditability.

# Role Notes
""",
            "completion_mode": "rounds",
            "max_iters": 4,
            "max_role_retries": 2,
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loop_markdown"
    assert definition.name == "Markdown Loop"
    assert definition.contract.task == "Ship refund safety."
    assert definition.contract.done_when[0].title == "Permission proof"
    assert {target.id for target in definition.contract.evidence_targets} == {"done_when.check_001"}
    assert [step.id for step in definition.strategy.steps] == ["builder", "gatekeeper"]
    assert definition.runtime_defaults.max_iterations == 4
    assert definition.runtime_defaults.completion_mode == "rounds"
    assert definition.metadata.source_kind == "markdown_contract"
    assert definition.metadata.source_id == "spec_refund"


def test_compile_markdown_contract_source_accepts_spec_markdown_alias() -> None:
    definition = compile_markdown_contract_source(
        LoopSource(
            kind=LoopSourceKind.MARKDOWN_CONTRACT,
            payload={
                "id": "loop_markdown_alias",
                "spec_markdown": "# Task\n\nAlias source.\n\n# Done When\n",
            },
        )
    )

    assert definition.id == "loop_markdown_alias"
    assert definition.contract.task == "Alias source."


def test_loop_compiler_compiles_loopfile_yaml_source_to_loop_definition(sample_workdir) -> None:
    source = LoopSource(
        kind=LoopSourceKind.LOOPFILE,
        id="loopfile_source",
        payload={"bundle_yaml": alignment_bundle_yaml(str(sample_workdir.resolve()))},
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loopfile_source"
    assert definition.name == "Aligned Starter Bundle"
    assert definition.contract.task.startswith("Ship the focused starter experience")
    assert [role.archetype for role in definition.strategy.roles] == ["builder", "inspector", "inspector", "gatekeeper"]
    assert [step.id for step in definition.strategy.steps] == [
        "builder_step",
        "contract_inspection_step",
        "evidence_inspection_step",
        "gatekeeper_step",
    ]
    assert definition.strategy.evidence_flow.gatekeeper_step_id == "gatekeeper_step"
    assert definition.runtime_defaults.max_iterations == 4
    assert definition.runtime_defaults.max_step_retries == 1
    assert definition.runtime_defaults.completion_mode == "gatekeeper"
    assert definition.metadata.workdir == str(sample_workdir.resolve())
    assert definition.metadata.source_kind == "loopfile"
    assert definition.metadata.source_id == "loopfile_source"


def test_compile_loopfile_source_accepts_normalized_bundle_payload(sample_workdir) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    definition = compile_loopfile_source(
        LoopSource(
            kind=LoopSourceKind.LOOPFILE,
            payload={"id": "loopfile_bundle", "bundle": bundle},
        )
    )

    assert definition.id == "loopfile_bundle"
    assert definition.contract.done_when[0].title.startswith("The primary user flow works end to end")
    assert definition.strategy.roles[0].name == "Focused Builder"
    assert definition.strategy.roles[0].responsibility == "Implements the smallest maintainable change."


def test_loop_compiler_compiles_strategy_template_source_to_loop_definition() -> None:
    source = LoopSource(
        kind=LoopSourceKind.STRATEGY_TEMPLATE,
        id="template_source",
        payload={
            "id": "loop_template",
            "name": "Template Loop",
            "preset": "quality_gate",
            "spec_markdown": """
# Task

Ship with a quality gate.

# Done When

- Quality gate evidence is collected.
""",
            "max_iters": 5,
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loop_template"
    assert definition.name == "Template Loop"
    assert definition.contract.task == "Ship with a quality gate."
    assert [role.archetype for role in definition.strategy.roles] == ["builder", "inspector", "gatekeeper"]
    assert [step.id for step in definition.strategy.steps] == ["builder_step", "inspector_step", "gatekeeper_step"]
    assert definition.strategy.evidence_flow.gatekeeper_step_id == "gatekeeper_step"
    assert definition.runtime_defaults.max_iterations == 5
    assert definition.metadata.source_kind == "strategy_template"
    assert definition.metadata.source_id == "template_source"


def test_compile_strategy_template_source_accepts_compiled_spec_payload() -> None:
    definition = compile_strategy_template_source(
        LoopSource(
            kind=LoopSourceKind.STRATEGY_TEMPLATE,
            payload={
                "id": "loop_template_compiled",
                "preset": "fast_lane",
                "compiled_spec": {
                    "goal": "Use a compiled contract.",
                    "checks": [{"id": "proof", "title": "Proof"}],
                },
            },
        )
    )

    assert definition.contract.task == "Use a compiled contract."
    assert [step.id for step in definition.strategy.steps] == ["builder_step", "gatekeeper_step"]


def test_loop_compiler_compiles_agent_message_source_to_minimal_loop_definition() -> None:
    source = LoopSource(
        kind=LoopSourceKind.AGENT_MESSAGE,
        id="agent_message_source",
        payload={
            "name": "Agent Message Loop",
            "message": "Refactor the compiler source boundary without widening product concepts.",
            "max_iters": 2,
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "agent_message_source"
    assert definition.name == "Agent Message Loop"
    assert definition.contract.task == "Refactor the compiler source boundary without widening product concepts."
    assert definition.contract.done_when == ()
    assert [step.id for step in definition.strategy.steps] == ["builder", "gatekeeper"]
    assert definition.runtime_defaults.max_iterations == 2
    assert definition.metadata.source_kind == "agent_message"
    assert definition.metadata.source_id == "agent_message_source"


def test_compile_agent_message_source_accepts_markdown_payload() -> None:
    definition = compile_agent_message_source(
        LoopSource(
            kind=LoopSourceKind.AGENT_MESSAGE,
            payload={
                "id": "agent_markdown",
                "markdown": """
# Task

Use explicit markdown when the Agent already has it.

# Done When

- The explicit check is retained.
""",
            },
        )
    )

    assert definition.contract.task == "Use explicit markdown when the Agent already has it."
    assert definition.contract.done_when[0].title == "The explicit check is retained"


def test_loop_compiler_compiles_web_alignment_bundle_source_to_loop_definition(sample_workdir) -> None:
    source = LoopSource(
        kind=LoopSourceKind.WEB_ALIGNMENT,
        id="alignment_session",
        payload={"bundle_yaml": alignment_bundle_yaml(str(sample_workdir.resolve()))},
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "alignment_session"
    assert definition.contract.task.startswith("Ship the focused starter experience")
    assert definition.strategy.evidence_flow.gatekeeper_step_id == "gatekeeper_step"
    assert definition.metadata.source_kind == "web_alignment"
    assert definition.metadata.source_id == "alignment_session"


def test_compile_web_alignment_source_accepts_bundle_payload(sample_workdir) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    definition = compile_web_alignment_source(
        LoopSource(
            kind=LoopSourceKind.WEB_ALIGNMENT,
            payload={"id": "loop_alignment", "bundle": bundle},
        )
    )

    assert definition.id == "loop_alignment"
    assert definition.name == "Aligned Starter Bundle"
    assert [role.archetype for role in definition.strategy.roles] == ["builder", "inspector", "inspector", "gatekeeper"]


def test_loop_compiler_rejects_unknown_source_kinds() -> None:
    with pytest.raises(ValueError, match="unsupported Loop source kind"):
        LoopCompiler().compile(LoopSource(kind="unknown", payload={}))
