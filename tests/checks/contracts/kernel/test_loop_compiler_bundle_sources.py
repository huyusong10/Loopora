from __future__ import annotations

from loopora.bundles import load_bundle_text
from loopora.compiler import (
    LoopCompiler,
    LoopSource,
    LoopSourceKind,
    compile_loopfile_source,
    compile_web_alignment_source,
)
from loopora.executor_fake_payloads import alignment_bundle_yaml


BUNDLE_SOURCE_MAX_ITERATIONS = 4


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
    assert definition.runtime_defaults.max_iterations == BUNDLE_SOURCE_MAX_ITERATIONS
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
    assert definition.contract.done_when[0].title.startswith("The primary user-facing flow works end to end")
    assert definition.strategy.roles[0].name == "Focused Builder"
    assert definition.strategy.roles[0].responsibility == "Implements the smallest maintainable change."


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
