from __future__ import annotations

import typer

from loopora.cli_shared import (
    RoleModelOption,
    StrategyFileOption,
    StrategyPresetOption,
    echo_json,
    get_service,
    handle_error,
    parse_role_models,
    resolve_strategy_source_bundle,
    strategy_source_bundle_from_entity,
)
from loopora.service import LooporaError
from loopora.strategy_source import DEFAULT_STRATEGY_SOURCE_PRESET, StrategySourceError


def register_orchestration_commands(orchestrations_app: typer.Typer) -> None:
    _register_orchestration_list_command(orchestrations_app)
    _register_orchestration_get_command(orchestrations_app)
    _register_orchestration_create_command(orchestrations_app)
    _register_orchestration_update_command(orchestrations_app)
    _register_orchestration_derive_command(orchestrations_app)
    _register_orchestration_delete_command(orchestrations_app)


def _register_orchestration_list_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("list")
    def list_orchestrations() -> None:
        """List saved orchestrations."""
        try:
            service = get_service()
            orchestrations = service.list_orchestrations()
            for item in orchestrations:
                typer.echo(
                    f"{item['id']}  {item['name']}  "
                    f"source={item.get('source', 'custom')}  "
                    f"roles={len(item.get('workflow_json', {}).get('roles', []))}  "
                    f"steps={len(item.get('workflow_json', {}).get('steps', []))}"
                )
        except LooporaError as exc:
            handle_error(exc)


def _register_orchestration_get_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("get")
    def get_orchestration(orchestration_id: str = typer.Argument(..., help="Saved orchestration id.")) -> None:
        """Show one orchestration as JSON."""
        try:
            echo_json(get_service().get_orchestration(orchestration_id))
        except LooporaError as exc:
            handle_error(exc)


def _register_orchestration_create_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("create")
    def create_orchestration(
        name: str = typer.Option(..., help="Orchestration name."),
        description: str = typer.Option("", help="Optional orchestration description."),
        strategy_preset: StrategyPresetOption = DEFAULT_STRATEGY_SOURCE_PRESET,
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Create a saved orchestration."""
        try:
            service = get_service()
            strategy_source, prompt_files = resolve_strategy_source_bundle(
                strategy_file=strategy_file,
                strategy_preset=strategy_preset,
            )
            orchestration = service.create_orchestration(
                name=name,
                description=description,
                workflow=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model),
            )
            echo_json(orchestration)
        except LooporaError as exc:
            handle_error(exc)


def _register_orchestration_update_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("update")
    def update_orchestration(
        orchestration_id: str = typer.Argument(..., help="Custom orchestration id."),
        name: str | None = typer.Option(None, help="Override the orchestration name."),
        description: str | None = typer.Option(None, help="Override the orchestration description."),
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Update a saved custom orchestration."""
        try:
            service = get_service()
            current = service.get_orchestration(orchestration_id)
            current_strategy_source, current_prompt_files = strategy_source_bundle_from_entity(current)
            strategy_source, prompt_files = resolve_strategy_source_bundle(
                strategy_file=strategy_file,
                strategy_preset=strategy_preset,
                fallback_strategy_source=current_strategy_source,
                fallback_prompt_files=current_prompt_files,
            )
            orchestration = service.update_orchestration(
                orchestration_id,
                name=name if name is not None else current["name"],
                description=description if description is not None else str(current.get("description", "")),
                workflow=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model) or current.get("role_models_json") or current.get("role_models") or {},
            )
            echo_json(orchestration)
        except (LooporaError, StrategySourceError) as exc:
            handle_error(exc)


def _register_orchestration_derive_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("derive")
    def derive_orchestration(
        source_id: str = typer.Argument(..., help="Built-in or custom orchestration id to derive from."),
        name: str | None = typer.Option(None, help="Name for the new derived orchestration."),
        description: str | None = typer.Option(None, help="Description for the new derived orchestration."),
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Create a new orchestration derived from an existing one."""
        try:
            service = get_service()
            source = service.get_orchestration(source_id)
            source_strategy_source, source_prompt_files = strategy_source_bundle_from_entity(source)
            strategy_source, prompt_files = resolve_strategy_source_bundle(
                strategy_file=strategy_file,
                strategy_preset=strategy_preset,
                fallback_strategy_source=source_strategy_source,
                fallback_prompt_files=source_prompt_files,
            )
            orchestration = service.create_orchestration(
                name=name or f"{source['name']} Copy",
                description=description if description is not None else str(source.get("description", "")),
                workflow=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model) or source.get("role_models_json") or source.get("role_models") or {},
            )
            echo_json(orchestration)
        except (LooporaError, StrategySourceError) as exc:
            handle_error(exc)


def _register_orchestration_delete_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("delete")
    def delete_orchestration(orchestration_id: str = typer.Argument(..., help="Custom orchestration id.")) -> None:
        """Delete a saved custom orchestration."""
        try:
            echo_json(get_service().delete_orchestration(orchestration_id))
        except LooporaError as exc:
            handle_error(exc)
