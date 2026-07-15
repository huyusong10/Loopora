from __future__ import annotations

from loopora.cli_common import call_spawn_background_worker, echo_json, get_service, handle_error, logger
from loopora.cli_run_support import (
    LoopCreateRequest,
    background_worker_command,
    create_and_maybe_start_loop,
    print_loop_created,
    print_run_contract_summary,
    print_run_result,
    print_task_verdict,
    spawn_background_worker,
    start_run,
)
from loopora.cli_strategy_source_support import (
    LoopBuildRequest,
    RoleDefinitionBuildRequest,
    build_loop_kwargs,
    build_role_definition_kwargs,
    command_args_text_from_values,
    parse_role_models,
    read_prompt_markdown,
    resolve_strategy_source_bundle,
    strategy_source_bundle_from_entity,
)

from pathlib import Path

from typing import Annotated

import typer

from loopora.strategy_source import strategy_source_preset_names


from loopora.markdown_tools import render_safe_markdown_html

from loopora.specs import SpecError, compile_markdown_spec

from loopora.strategy_source import (
    load_strategy_source_file,
    normalize_strategy_role_display_name,
    normalize_strategy_source,
    strategy_source_from_record,
)


def spec_validation_from_markdown(markdown_text: str) -> dict[str, object]:
    try:
        compiled = compile_markdown_spec(markdown_text)
    except SpecError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "check_count": 0,
            "check_mode": "",
        }
    return {
        "ok": True,
        "error": "",
        "check_count": len(compiled["checks"]),
        "check_mode": compiled["check_mode"],
    }

def spec_document_payload(path: Path, markdown_text: str) -> dict[str, object]:
    return {
        "ok": True,
        "path": str(path.resolve()),
        "content": markdown_text,
        "rendered_html": render_safe_markdown_html(markdown_text),
        "validation": spec_validation_from_markdown(markdown_text),
    }

def resolve_spec_template_strategy_source(
    *,
    orchestration_id: str,
    strategy_preset: str,
    strategy_file: Path | None,
) -> dict | None:
    if strategy_file is not None:
        strategy_source, _ = load_strategy_source_file(strategy_file)
        return normalize_strategy_source(strategy_source) if strategy_source else None
    if orchestration_id.strip():
        orchestration = get_service().get_orchestration(orchestration_id.strip())
        strategy_source = strategy_source_from_record(orchestration)
        return normalize_strategy_source(strategy_source) if strategy_source else None
    if strategy_preset.strip():
        return normalize_strategy_source({"preset": strategy_preset.strip()})
    return None

def role_note_sections_for_strategy_source(strategy_source: dict | None) -> list[dict[str, str]]:
    if not strategy_source:
        return []
    sections: list[dict[str, str]] = []
    seen: set[str] = set()
    for role in strategy_source.get("roles", []):
        if not isinstance(role, dict):
            continue
        label = normalize_strategy_role_display_name(role.get("name"), archetype=role.get("archetype")) or str(
            role.get("name", "")
        ).strip()
        normalized = label.lower()
        if not label or normalized in seen:
            continue
        seen.add(normalized)
        sections.append({"heading": f"{label} Notes", "role_name": label})
    return sections

SpecOption = Annotated[Path, typer.Option(..., exists=True, help="Path to the Markdown spec.")]

WorkdirOption = Annotated[Path, typer.Option(..., exists=True, file_okay=False, dir_okay=True, help="Target workdir.")]

ExecutorOption = Annotated[str, typer.Option("--executor", help="Execution tool: codex, claude, opencode, or custom.")]

ExecutorModeOption = Annotated[str, typer.Option("--executor-mode", help="Execution mode: preset or command.")]

ModelOption = Annotated[str, typer.Option(help="Default model or alias for the selected execution tool.")]

ReasoningOption = Annotated[str, typer.Option(help="Reasoning effort or variant for the selected execution tool.")]

CommandCliOption = Annotated[str, typer.Option("--command-cli", help="Executable to invoke in command mode. Defaults to the selected tool CLI.")]

CommandArgOption = Annotated[
    list[str] | None,
    typer.Option(
        "--command-arg",
        help="One command-mode argv template entry. Repeat once per argument. Supports placeholders like {workdir}, {schema_path}, {output_path}, {json_schema}, {sandbox}, {prompt}, {model}, and {reasoning_effort}.",
    ),
]

CompletionModeOption = Annotated[
    str,
    typer.Option("--completion-mode", help="Completion mode: gatekeeper or rounds."),
]

IterationIntervalOption = Annotated[
    float,
    typer.Option("--iteration-interval-seconds", min=0.0, help="Wait this many seconds between iterations."),
]

MaxItersOption = Annotated[int, typer.Option(min=0, help="Maximum orchestration iterations. Use 0 to keep iterating until you stop it.")]

MaxRoleRetriesOption = Annotated[int, typer.Option(min=0, help="Retries per role before aborting.")]

DeltaThresholdOption = Annotated[float, typer.Option(min=0.0, help="Plateau threshold.")]

TriggerWindowOption = Annotated[int, typer.Option(min=1, help="Plateau trigger window.")]

RegressionWindowOption = Annotated[int, typer.Option(min=1, help="Regression trigger window.")]

NameOption = Annotated[str | None, typer.Option(help="Optional loop name.")]

RoleModelOption = Annotated[
    list[str] | None,
    typer.Option(
        "--role-model",
        help="Per-role model override like builder=gpt-5.4-mini. Legacy names like generator/verifier still work.",
    ),
]

StrategyPresetOption = Annotated[
    str,
    typer.Option(
        "--strategy-preset",
        "--workflow-preset",
        help=f"Strategy preset: {', '.join(strategy_source_preset_names())}.",
    ),
]

WorkflowPresetOption = StrategyPresetOption

OrchestrationIdOption = Annotated[
    str,
    typer.Option(
        "--orchestration-id",
        help="Use a saved orchestration id, such as builtin:quality_gate or a custom orchestration id.",
    ),
]

StrategyFileOption = Annotated[
    Path | None,
    typer.Option(
        "--strategy-file",
        "--workflow-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to a JSON or YAML strategy source. Supports {workflow, prompt_files} or a raw strategy object.",
    ),
]

WorkflowFileOption = StrategyFileOption

BundleFileOption = Annotated[
    Path,
    typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to a Loop plan file (YAML).",
    ),
]

BundleOutputOption = Annotated[
    Path | None,
    typer.Option(
        "--output",
        file_okay=True,
        dir_okay=False,
        help="Write the Loop plan file to this path instead of printing it.",
    ),
]

StartOption = Annotated[bool, typer.Option("--start", help="Start a run immediately after creating the loop definition.")]

BackgroundOption = Annotated[bool, typer.Option("--background", help="Queue the run and return immediately instead of waiting for it to finish.")]

LocaleOption = Annotated[str, typer.Option("--locale", help="Template locale: zh or en.")]

PromptFileOption = Annotated[
    Path | None,
    typer.Option(
        "--prompt-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to a Markdown prompt file.",
    ),
]

PromptTemplateOption = Annotated[
    str,
    typer.Option("--prompt-template", help="Built-in prompt template ref such as builder.md."),
]

ArchetypeOption = Annotated[
    str,
    typer.Option("--archetype", help="Role archetype: builder, inspector, gatekeeper, guide, or custom."),
]

JsonOutputOption = Annotated[bool, typer.Option("--json", help="Print structured JSON instead of plain text.")]

FromFileOption = Annotated[
    Path | None,
    typer.Option(
        "--from-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Read Markdown content from this file.",
    ),
]

__all__ = [
    "ArchetypeOption",
    "BackgroundOption",
    "BundleFileOption",
    "BundleOutputOption",
    "CommandArgOption",
    "CommandCliOption",
    "CompletionModeOption",
    "DeltaThresholdOption",
    "ExecutorModeOption",
    "ExecutorOption",
    "FromFileOption",
    "IterationIntervalOption",
    "JsonOutputOption",
    "LocaleOption",
    "LoopBuildRequest",
    "LoopCreateRequest",
    "MaxItersOption",
    "MaxRoleRetriesOption",
    "ModelOption",
    "NameOption",
    "OrchestrationIdOption",
    "PromptFileOption",
    "PromptTemplateOption",
    "ReasoningOption",
    "RegressionWindowOption",
    "RoleDefinitionBuildRequest",
    "RoleModelOption",
    "SpecOption",
    "StartOption",
    "StrategyFileOption",
    "StrategyPresetOption",
    "TriggerWindowOption",
    "WorkdirOption",
    "WorkflowFileOption",
    "WorkflowPresetOption",
    "background_worker_command",
    "build_loop_kwargs",
    "build_role_definition_kwargs",
    "call_spawn_background_worker",
    "command_args_text_from_values",
    "create_and_maybe_start_loop",
    "echo_json",
    "get_service",
    "handle_error",
    "logger",
    "parse_role_models",
    "print_loop_created",
    "print_run_contract_summary",
    "print_run_result",
    "print_task_verdict",
    "read_prompt_markdown",
    "resolve_spec_template_strategy_source",
    "resolve_strategy_source_bundle",
    "role_note_sections_for_strategy_source",
    "spawn_background_worker",
    "spec_document_payload",
    "spec_validation_from_markdown",
    "start_run",
    "strategy_source_bundle_from_entity",
]
