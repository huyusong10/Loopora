from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from loopora.bundles import load_bundle_file, load_bundle_text, normalize_bundle
from loopora.compiler._coercion import integer, mapping, mapping_list, text
from loopora.compiler.contract_compiler import compile_loop_contract, compile_residual_risk_policy
from loopora.compiler.sources import LoopSource, LoopSourceKind
from loopora.compiler.strategy_compiler import compile_loop_strategy
from loopora.kernel.definition import LoopDefinition, LoopMetadata, RuntimeDefaults
from loopora.specs import compile_markdown_spec
from loopora.workflows import build_preset_workflow


@dataclass(frozen=True, kw_only=True)
class _LoopDefinitionParts:
    loop_id: str
    name: str
    compiled_spec: Mapping[str, object]
    workflow: Mapping[str, object]
    runtime_defaults: RuntimeDefaults
    metadata: LoopMetadata


class LoopCompiler:
    def compile(self, source: LoopSource) -> LoopDefinition:
        if source.kind == LoopSourceKind.AGENT_MESSAGE:
            return compile_agent_message_source(source)
        if source.kind == LoopSourceKind.EXISTING_LOOP_RECORD:
            return compile_existing_loop_record(source.payload)
        if source.kind == LoopSourceKind.MARKDOWN_CONTRACT:
            return compile_markdown_contract_source(source)
        if source.kind == LoopSourceKind.LOOPFILE:
            return compile_loopfile_source(source)
        if source.kind == LoopSourceKind.STRATEGY_TEMPLATE:
            return compile_strategy_template_source(source)
        if source.kind == LoopSourceKind.WEB_ALIGNMENT:
            return compile_web_alignment_source(source)
        raise ValueError(f"unsupported Loop source kind: {source.kind}")


class ExistingLoopRecordCompiler:
    def compile(self, record: Mapping[str, object]) -> LoopDefinition:
        return compile_existing_loop_record(record)


def compile_agent_message_source(source: LoopSource) -> LoopDefinition:
    payload = source.payload
    loop_id = text(payload.get("id") or source.id, fallback="loop")
    completion_mode = text(payload.get("completion_mode"), fallback="gatekeeper")
    max_iterations = integer(payload.get("max_iters"), fallback=1)
    max_step_retries = integer(payload.get("max_role_retries"), fallback=1)
    return _compile_loop_definition(
        _LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=_compiled_spec_from_payload(
                payload,
                fallback_task=text(payload.get("message") or payload.get("task") or payload.get("goal")),
            ),
            workflow={},
            runtime_defaults=RuntimeDefaults(
                executor_kind=text(payload.get("executor_kind"), fallback="codex"),
                executor_mode=text(payload.get("executor_mode"), fallback="preset"),
                model=text(payload.get("model")),
                reasoning_effort=text(payload.get("reasoning_effort")),
                max_iterations=max_iterations,
                max_step_retries=max_step_retries,
                completion_mode=completion_mode,
            ),
            metadata=LoopMetadata(
                workdir=text(payload.get("workdir")),
                spec_path=text(payload.get("spec_path")),
                source_kind=LoopSourceKind.AGENT_MESSAGE.value,
                source_id=source.id or loop_id,
            ),
        )
    )


def compile_existing_loop_record(record: Mapping[str, object]) -> LoopDefinition:
    loop_id = text(record.get("id"), fallback="loop")
    compiled_spec = mapping(record.get("compiled_spec") or record.get("compiled_spec_json"))
    workflow = mapping(record.get("workflow") or record.get("workflow_json"))
    completion_mode = text(record.get("completion_mode"), fallback="gatekeeper")
    max_iterations = integer(record.get("max_iters"), fallback=1)
    max_step_retries = integer(record.get("max_role_retries"), fallback=1)
    return _compile_loop_definition(
        _LoopDefinitionParts(
            loop_id=loop_id,
            name=text(record.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            workflow=workflow,
            runtime_defaults=RuntimeDefaults(
                executor_kind=text(record.get("executor_kind"), fallback="codex"),
                executor_mode=text(record.get("executor_mode"), fallback="preset"),
                model=text(record.get("model")),
                reasoning_effort=text(record.get("reasoning_effort")),
                max_iterations=max_iterations,
                max_step_retries=max_step_retries,
                completion_mode=completion_mode,
            ),
            metadata=LoopMetadata(
                workdir=text(record.get("workdir")),
                spec_path=text(record.get("spec_path")),
                source_kind=LoopSourceKind.EXISTING_LOOP_RECORD.value,
                source_id=loop_id,
            ),
        )
    )


def _compile_loop_definition(parts: _LoopDefinitionParts) -> LoopDefinition:
    residual_risk_policy = compile_residual_risk_policy(parts.compiled_spec.get("residual_risk"))
    return LoopDefinition(
        id=parts.loop_id,
        name=parts.name,
        contract=compile_loop_contract(
            parts.loop_id,
            parts.compiled_spec,
            completion_mode=parts.runtime_defaults.completion_mode,
        ),
        strategy=compile_loop_strategy(
            parts.loop_id,
            parts.workflow,
            max_iterations=parts.runtime_defaults.max_iterations,
            max_step_retries=parts.runtime_defaults.max_step_retries,
            residual_risk_policy=residual_risk_policy,
        ),
        runtime_defaults=parts.runtime_defaults,
        metadata=parts.metadata,
    )


def compile_markdown_contract_source(source: LoopSource) -> LoopDefinition:
    payload = source.payload
    loop_id = text(payload.get("id") or source.id, fallback="loop")
    completion_mode = text(payload.get("completion_mode"), fallback="gatekeeper")
    compiled_spec = compile_markdown_spec(text(payload.get("markdown") or payload.get("spec_markdown")))
    max_iterations = integer(payload.get("max_iters"), fallback=1)
    max_step_retries = integer(payload.get("max_role_retries"), fallback=1)
    return _compile_loop_definition(
        _LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            workflow={},
            runtime_defaults=RuntimeDefaults(
                executor_kind=text(payload.get("executor_kind"), fallback="codex"),
                executor_mode=text(payload.get("executor_mode"), fallback="preset"),
                model=text(payload.get("model")),
                reasoning_effort=text(payload.get("reasoning_effort")),
                max_iterations=max_iterations,
                max_step_retries=max_step_retries,
                completion_mode=completion_mode,
            ),
            metadata=LoopMetadata(
                workdir=text(payload.get("workdir")),
                spec_path=text(payload.get("spec_path")),
                source_kind=LoopSourceKind.MARKDOWN_CONTRACT.value,
                source_id=source.id or loop_id,
            ),
        )
    )


def compile_loopfile_source(source: LoopSource) -> LoopDefinition:
    return _compile_bundle_source(source, source_kind=LoopSourceKind.LOOPFILE)


def compile_web_alignment_source(source: LoopSource) -> LoopDefinition:
    return _compile_bundle_source(source, source_kind=LoopSourceKind.WEB_ALIGNMENT)


def _compile_bundle_source(source: LoopSource, *, source_kind: LoopSourceKind) -> LoopDefinition:
    payload = source.payload
    bundle = _loopfile_bundle_from_source(source)
    metadata = mapping(bundle.get("metadata"))
    loop = mapping(bundle.get("loop"))
    spec = mapping(bundle.get("spec"))
    loop_id = text(payload.get("id") or metadata.get("bundle_id") or source.id, fallback="loop")
    completion_mode = text(loop.get("completion_mode"), fallback="gatekeeper")
    compiled_spec = compile_markdown_spec(text(spec.get("markdown")))
    max_iterations = integer(loop.get("max_iters"), fallback=1)
    max_step_retries = integer(loop.get("max_role_retries"), fallback=1)
    return _compile_loop_definition(
        _LoopDefinitionParts(
            loop_id=loop_id,
            name=text(loop.get("name") or metadata.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            workflow=_loopfile_strategy_workflow(bundle),
            runtime_defaults=RuntimeDefaults(
                executor_kind=text(loop.get("executor_kind"), fallback="codex"),
                executor_mode=text(loop.get("executor_mode"), fallback="preset"),
                model=text(loop.get("model")),
                reasoning_effort=text(loop.get("reasoning_effort")),
                max_iterations=max_iterations,
                max_step_retries=max_step_retries,
                completion_mode=completion_mode,
            ),
            metadata=LoopMetadata(
                workdir=text(loop.get("workdir")),
                spec_path=text(payload.get("spec_path") or payload.get("path")),
                source_kind=source_kind.value,
                source_id=text(source.id or metadata.get("bundle_id") or payload.get("path"), fallback=loop_id),
            ),
        )
    )


def compile_strategy_template_source(source: LoopSource) -> LoopDefinition:
    payload = source.payload
    loop_id = text(payload.get("id") or source.id, fallback="loop")
    preset = text(payload.get("preset") or payload.get("strategy_template"), fallback="build_first")
    completion_mode = text(payload.get("completion_mode"), fallback="gatekeeper")
    max_iterations = integer(payload.get("max_iters"), fallback=1)
    max_step_retries = integer(payload.get("max_role_retries"), fallback=1)
    return _compile_loop_definition(
        _LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=_compiled_spec_from_payload(payload),
            workflow=build_preset_workflow(preset),
            runtime_defaults=RuntimeDefaults(
                executor_kind=text(payload.get("executor_kind"), fallback="codex"),
                executor_mode=text(payload.get("executor_mode"), fallback="preset"),
                model=text(payload.get("model")),
                reasoning_effort=text(payload.get("reasoning_effort")),
                max_iterations=max_iterations,
                max_step_retries=max_step_retries,
                completion_mode=completion_mode,
            ),
            metadata=LoopMetadata(
                workdir=text(payload.get("workdir")),
                spec_path=text(payload.get("spec_path")),
                source_kind=LoopSourceKind.STRATEGY_TEMPLATE.value,
                source_id=source.id or preset,
            ),
        )
    )


def _compiled_spec_from_payload(payload: Mapping[str, object], *, fallback_task: str = "") -> Mapping[str, object]:
    compiled_spec = payload.get("compiled_spec") or payload.get("compiled_spec_json")
    if isinstance(compiled_spec, Mapping):
        return compiled_spec
    markdown = text(payload.get("markdown") or payload.get("spec_markdown"))
    if not markdown and fallback_task:
        markdown = f"# Task\n\n{fallback_task}\n"
    return compile_markdown_spec(markdown)


def _loopfile_bundle_from_source(source: LoopSource) -> dict:
    payload = source.payload
    raw_bundle = payload.get("bundle")
    if isinstance(raw_bundle, str):
        return load_bundle_text(raw_bundle)
    if isinstance(raw_bundle, Mapping):
        return normalize_bundle(raw_bundle)

    for key in ("bundle_yaml", "loopfile_yaml", "yaml", "raw_text", "text"):
        raw_text = text(payload.get(key))
        if raw_text:
            return load_bundle_text(raw_text)

    raw_path = text(payload.get("path") or payload.get("file_path"))
    if raw_path:
        return load_bundle_file(Path(raw_path).expanduser())

    return normalize_bundle(payload)


def _loopfile_strategy_workflow(bundle: Mapping[str, object]) -> dict[str, object]:
    workflow = mapping(bundle.get("workflow"))
    role_definitions = {
        text(role_definition.get("key")): role_definition
        for role_definition in mapping_list(bundle.get("role_definitions"))
        if text(role_definition.get("key"))
    }
    roles = []
    for role in mapping_list(workflow.get("roles")):
        role_definition = mapping(role_definitions.get(text(role.get("role_definition_key"))))
        role_id = text(role.get("id"))
        roles.append(
            {
                "id": role_id,
                "name": text(role_definition.get("name"), fallback=role_id),
                "archetype": text(role_definition.get("archetype")),
                "description": text(role_definition.get("description")),
                "posture": text(role_definition.get("posture_notes")),
            }
        )
    return {
        **dict(workflow),
        "roles": roles,
    }
