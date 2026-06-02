from __future__ import annotations

from loopora.compiler import (
    LoopCompiler,
    LoopSource,
    LoopSourceKind,
    compile_markdown_contract_source,
)


MARKDOWN_SOURCE_MAX_ITERATIONS = 4


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
            "max_iters": MARKDOWN_SOURCE_MAX_ITERATIONS,
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
    assert definition.runtime_defaults.max_iterations == MARKDOWN_SOURCE_MAX_ITERATIONS
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
