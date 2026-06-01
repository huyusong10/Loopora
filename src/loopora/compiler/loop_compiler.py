from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from loopora.bundles import load_bundle_file, load_bundle_text, normalize_bundle
from loopora.compiler._coercion import mapping, mapping_list, text
from loopora.compiler.loop_definition_builder import (
    LoopDefinitionParts,
    compile_loop_definition,
    runtime_defaults_from_payload,
)
from loopora.compiler.sources import LoopSource, LoopSourceKind
from loopora.kernel.definition import LoopDefinition, LoopMetadata
from loopora.specs import compile_markdown_spec
from loopora.strategy_source import build_preset_strategy_source, strategy_source_from_record


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
    return compile_loop_definition(
        LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=_compiled_spec_from_payload(
                payload,
                fallback_task=text(payload.get("message") or payload.get("task") or payload.get("goal")),
            ),
            strategy_source={},
            runtime_defaults=runtime_defaults_from_payload(payload),
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
    strategy_source = _existing_loop_record_strategy_source(record)
    return compile_loop_definition(
        LoopDefinitionParts(
            loop_id=loop_id,
            name=text(record.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            strategy_source=strategy_source,
            runtime_defaults=runtime_defaults_from_payload(record),
            metadata=LoopMetadata(
                workdir=text(record.get("workdir")),
                spec_path=text(record.get("spec_path")),
                source_kind=LoopSourceKind.EXISTING_LOOP_RECORD.value,
                source_id=loop_id,
            ),
        )
    )


def _existing_loop_record_strategy_source(record: Mapping[str, object]) -> Mapping[str, object]:
    strategy_source = record.get("strategy_source")
    if strategy_source is not None:
        return mapping(strategy_source)
    strategy_source_alias = record.get("workflow")
    if strategy_source_alias is not None:
        return mapping(strategy_source_alias)
    return mapping(strategy_source_from_record(record))


def compile_markdown_contract_source(source: LoopSource) -> LoopDefinition:
    payload = source.payload
    loop_id = text(payload.get("id") or source.id, fallback="loop")
    compiled_spec = compile_markdown_spec(text(payload.get("markdown") or payload.get("spec_markdown")))
    return compile_loop_definition(
        LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            strategy_source={},
            runtime_defaults=runtime_defaults_from_payload(payload),
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
    compiled_spec = compile_markdown_spec(text(spec.get("markdown")))
    return compile_loop_definition(
        LoopDefinitionParts(
            loop_id=loop_id,
            name=text(loop.get("name") or metadata.get("name"), fallback=loop_id),
            compiled_spec=compiled_spec,
            strategy_source=_loopfile_strategy_source(bundle),
            runtime_defaults=runtime_defaults_from_payload(loop),
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
    return compile_loop_definition(
        LoopDefinitionParts(
            loop_id=loop_id,
            name=text(payload.get("name"), fallback=loop_id),
            compiled_spec=_compiled_spec_from_payload(payload),
            strategy_source=build_preset_strategy_source(preset),
            runtime_defaults=runtime_defaults_from_payload(payload),
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


def _loopfile_strategy_source(bundle: Mapping[str, object]) -> dict[str, object]:
    strategy_source_payload = mapping(bundle.get("workflow"))
    role_definitions = {
        text(role_definition.get("key")): role_definition
        for role_definition in mapping_list(bundle.get("role_definitions"))
        if text(role_definition.get("key"))
    }
    roles = []
    for role in mapping_list(strategy_source_payload.get("roles")):
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
        **dict(strategy_source_payload),
        "roles": roles,
    }
