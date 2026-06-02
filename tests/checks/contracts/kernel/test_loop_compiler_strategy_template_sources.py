from __future__ import annotations

from loopora.compiler import (
    LoopCompiler,
    LoopSource,
    LoopSourceKind,
    compile_strategy_template_source,
)


STRATEGY_TEMPLATE_MAX_ITERATIONS = 5


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
            "max_iters": STRATEGY_TEMPLATE_MAX_ITERATIONS,
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loop_template"
    assert definition.name == "Template Loop"
    assert definition.contract.task == "Ship with a quality gate."
    assert [role.archetype for role in definition.strategy.roles] == ["builder", "inspector", "gatekeeper"]
    assert [step.id for step in definition.strategy.steps] == ["builder_step", "inspector_step", "gatekeeper_step"]
    assert definition.strategy.evidence_flow.gatekeeper_step_id == "gatekeeper_step"
    assert definition.runtime_defaults.max_iterations == STRATEGY_TEMPLATE_MAX_ITERATIONS
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
