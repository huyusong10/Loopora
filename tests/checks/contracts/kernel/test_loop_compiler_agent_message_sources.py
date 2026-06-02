from __future__ import annotations

from loopora.compiler import (
    LoopCompiler,
    LoopSource,
    LoopSourceKind,
    compile_agent_message_source,
)


AGENT_MESSAGE_MAX_ITERATIONS = 2


def test_loop_compiler_compiles_agent_message_source_to_minimal_loop_definition() -> None:
    source = LoopSource(
        kind=LoopSourceKind.AGENT_MESSAGE,
        id="agent_message_source",
        payload={
            "name": "Agent Message Loop",
            "message": "Refactor the compiler source boundary without widening product concepts.",
            "max_iters": AGENT_MESSAGE_MAX_ITERATIONS,
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "agent_message_source"
    assert definition.name == "Agent Message Loop"
    assert definition.contract.task == "Refactor the compiler source boundary without widening product concepts."
    assert definition.contract.done_when == ()
    assert [step.id for step in definition.strategy.steps] == ["builder", "gatekeeper"]
    assert definition.runtime_defaults.max_iterations == AGENT_MESSAGE_MAX_ITERATIONS
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
