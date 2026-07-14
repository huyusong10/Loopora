from __future__ import annotations

import typer

from loopora.asset_errors import asset_mutation_error_message
from loopora.cli_orchestration_strategy_file_recovery import exit_with_orchestration_strategy_file_recovery
from loopora.cli_resource_recovery import (
    MissingResourceIdentifierRecovery,
    MissingResourceNameRecovery,
    exit_with_missing_resource_identifier_recovery,
    exit_with_missing_resource_name_recovery,
    normalize_cli_identifier,
)
from loopora.cli_resource_projection import orchestration_list_rows, project_orchestration_delete_preview
from loopora.cli_shared import (
    JsonOutputOption,
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

ORCHESTRATIONS_HELP_EPILOG = (
    "Orchestrations are reusable run-flow assets for teams that need to customize or share the reviewed workflow. "
    "For a new task, run `loopora start` first, use `loopora fit` when fit is uncertain, then choose the "
    'Fit Guide/Web choices path with `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or the '
    'same-Agent path with `loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before '
    "`/loopora-plan`, using the default Builder -> Inspector/Guide -> GateKeeper path before creating custom flows."
)
ORCHESTRATIONS_CREATE_HELP_EPILOG = (
    "Creates a reusable workflow asset from a preset or strategy file. Use this after the desired workflow shape has "
    "been reviewed; it is not required for first use, and it does not start a run."
)
ORCHESTRATIONS_DERIVE_HELP_EPILOG = (
    "Derive copies a built-in or custom orchestration into a new saved custom flow for later reviewed Loops. "
    "It does not update the source orchestration, existing Loops, or any running work."
)
ORCHESTRATIONS_UPDATE_HELP_EPILOG = (
    "Update edits one saved custom flow for future Loop previews. Existing Loop definitions and runs keep the "
    "strategy source they were created with; review a new preview before relying on the changed flow."
)
ORCHESTRATIONS_DELETE_HELP_EPILOG = (
    "Delete removes one saved custom flow from the reusable library. It does not remove built-in flows, rewrite "
    "existing Loops, or change run history. Use --dry-run to preview Loop references before deleting anything."
)


def _handle_orchestration_mutation_error(exc: BaseException, *, action: str = "saved") -> None:
    handle_error(LooporaError(asset_mutation_error_message(exc, asset_label="orchestration", action=action)), json_output=True)


def _resolve_orchestration_strategy_source(
    *,
    strategy_file,
    strategy_preset: str,
    action: str,
    fallback_strategy_source: dict | None = None,
    fallback_prompt_files: dict[str, str] | None = None,
) -> tuple[dict | None, dict[str, str]]:
    try:
        return resolve_strategy_source_bundle(
            strategy_file=strategy_file,
            strategy_preset=strategy_preset,
            fallback_strategy_source=fallback_strategy_source,
            fallback_prompt_files=fallback_prompt_files,
        )
    except (StrategySourceError, OSError, ValueError) as exc:
        exit_with_orchestration_strategy_file_recovery(str(exc), action=action)


def register_orchestration_commands(orchestrations_app: typer.Typer) -> None:
    _register_orchestration_list_command(orchestrations_app)
    _register_orchestration_get_command(orchestrations_app)
    _register_orchestration_create_command(orchestrations_app)
    _register_orchestration_update_command(orchestrations_app)
    _register_orchestration_derive_command(orchestrations_app)
    _register_orchestration_delete_command(orchestrations_app)


def _register_orchestration_list_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("list")
    def list_orchestrations(*, json_output: JsonOutputOption = False) -> None:
        """List saved orchestrations."""
        try:
            service = get_service()
            orchestrations = service.list_orchestrations()
            if json_output:
                echo_json({"status": "ok", "count": len(orchestrations), "orchestrations": orchestrations})
                return
            for row in orchestration_list_rows(orchestrations):
                typer.echo(row)
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_orchestration_get_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("get")
    def get_orchestration(orchestration_id: str | None = typer.Argument(None, help="Saved orchestration id.")) -> None:
        """Show one orchestration as JSON."""
        orchestration_id_value = normalize_cli_identifier(orchestration_id)
        if not orchestration_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Flow",
                    action="get",
                    required_identifier="orchestration_id",
                    required_identifier_label="Flow ID",
                    list_command="loopora orchestrations list",
                    list_label="List Flows",
                    retry_template="loopora orchestrations get <flow-id>",
                    web_label="Open Web Flow library",
                    json_output=True,
                )
            )
        try:
            echo_json(get_service().get_orchestration(orchestration_id_value))
        except LooporaError as exc:
            handle_error(exc, json_output=True)


def _register_orchestration_create_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("create", epilog=ORCHESTRATIONS_CREATE_HELP_EPILOG)
    def create_orchestration(
        name: str | None = typer.Option(None, help="Orchestration name."),
        description: str = typer.Option("", help="Optional orchestration description."),
        strategy_preset: StrategyPresetOption = DEFAULT_STRATEGY_SOURCE_PRESET,
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Create a saved orchestration."""
        name_value = normalize_cli_identifier(name)
        if not name_value:
            exit_with_missing_resource_name_recovery(
                MissingResourceNameRecovery(
                    resource_label="Flow",
                    required_identifier_label="Flow name",
                    list_command="loopora orchestrations list",
                    list_label="List existing Flows",
                    retry_template="loopora orchestrations create --name '<flow-name>'",
                    web_label="Open Web Flow library",
                    json_output=True,
                )
            )
        try:
            strategy_source, prompt_files = _resolve_orchestration_strategy_source(
                strategy_file=strategy_file,
                strategy_preset=strategy_preset,
                action="create",
            )
            service = get_service()
            orchestration = service.create_orchestration(
                name=name_value,
                description=description,
                strategy_source=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model),
            )
            echo_json(orchestration)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_orchestration_mutation_error(exc)


def _register_orchestration_update_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("update", epilog=ORCHESTRATIONS_UPDATE_HELP_EPILOG)
    def update_orchestration(
        orchestration_id: str | None = typer.Argument(None, help="Custom orchestration id."),
        name: str | None = typer.Option(None, help="Override the orchestration name."),
        description: str | None = typer.Option(None, help="Override the orchestration description."),
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Update a saved custom orchestration."""
        orchestration_id_value = normalize_cli_identifier(orchestration_id)
        if not orchestration_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Flow",
                    action="update",
                    required_identifier="orchestration_id",
                    required_identifier_label="Flow ID",
                    list_command="loopora orchestrations list",
                    list_label="List Flows",
                    retry_template="loopora orchestrations update <flow-id>",
                    web_label="Open Web Flow library",
                    json_output=True,
                )
            )
        try:
            if strategy_file is not None:
                strategy_source, prompt_files = _resolve_orchestration_strategy_source(
                    strategy_file=strategy_file,
                    strategy_preset=strategy_preset,
                    action="update",
                )
                service = get_service()
                current = service.get_orchestration(orchestration_id_value)
            else:
                service = get_service()
                current = service.get_orchestration(orchestration_id_value)
                current_strategy_source, current_prompt_files = strategy_source_bundle_from_entity(current)
                strategy_source, prompt_files = _resolve_orchestration_strategy_source(
                    strategy_file=strategy_file,
                    strategy_preset=strategy_preset,
                    action="update",
                    fallback_strategy_source=current_strategy_source,
                    fallback_prompt_files=current_prompt_files,
                )
            orchestration = service.update_orchestration(
                orchestration_id_value,
                name=name if name is not None else current["name"],
                description=description if description is not None else str(current.get("description", "")),
                strategy_source=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model) or current.get("role_models_json") or current.get("role_models") or {},
            )
            echo_json(orchestration)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_orchestration_mutation_error(exc)


def _register_orchestration_derive_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("derive", epilog=ORCHESTRATIONS_DERIVE_HELP_EPILOG)
    def derive_orchestration(
        source_id: str | None = typer.Argument(None, help="Built-in or custom orchestration id to derive from."),
        name: str | None = typer.Option(None, help="Name for the new derived orchestration."),
        description: str | None = typer.Option(None, help="Description for the new derived orchestration."),
        strategy_preset: StrategyPresetOption = "",
        strategy_file: StrategyFileOption = None,
        role_model: RoleModelOption = None,
    ) -> None:
        """Create a new orchestration derived from an existing one."""
        source_id_value = normalize_cli_identifier(source_id)
        if not source_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Flow",
                    action="derive",
                    required_identifier="orchestration_id",
                    required_identifier_label="Flow ID",
                    list_command="loopora orchestrations list",
                    list_label="List Flows",
                    retry_template="loopora orchestrations derive <flow-id>",
                    web_label="Open Web Flow library",
                    json_output=True,
                )
            )
        try:
            if strategy_file is not None:
                strategy_source, prompt_files = _resolve_orchestration_strategy_source(
                    strategy_file=strategy_file,
                    strategy_preset=strategy_preset,
                    action="derive",
                )
                service = get_service()
                source = service.get_orchestration(source_id_value)
            else:
                service = get_service()
                source = service.get_orchestration(source_id_value)
                source_strategy_source, source_prompt_files = strategy_source_bundle_from_entity(source)
                strategy_source, prompt_files = _resolve_orchestration_strategy_source(
                    strategy_file=strategy_file,
                    strategy_preset=strategy_preset,
                    action="derive",
                    fallback_strategy_source=source_strategy_source,
                    fallback_prompt_files=source_prompt_files,
                )
            orchestration = service.create_orchestration(
                name=name or f"{source['name']} Copy",
                description=description if description is not None else str(source.get("description", "")),
                strategy_source=strategy_source,
                prompt_files=prompt_files,
                role_models=parse_role_models(role_model) or source.get("role_models_json") or source.get("role_models") or {},
            )
            echo_json(orchestration)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_orchestration_mutation_error(exc)


def _register_orchestration_delete_command(orchestrations_app: typer.Typer) -> None:
    @orchestrations_app.command("delete", epilog=ORCHESTRATIONS_DELETE_HELP_EPILOG)
    def delete_orchestration(
        orchestration_id: str | None = typer.Argument(None, help="Custom orchestration id."),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview delete scope without deleting local state."),
    ) -> None:
        """Delete a saved custom orchestration."""
        orchestration_id_value = normalize_cli_identifier(orchestration_id)
        if not orchestration_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Flow",
                    action="delete",
                    required_identifier="orchestration_id",
                    required_identifier_label="Flow ID",
                    list_command="loopora orchestrations list",
                    list_label="List Flows",
                    retry_template="loopora orchestrations delete <flow-id> --dry-run",
                    web_label="Open Web Flow library",
                    json_output=True,
                )
            )
        try:
            service = get_service()
            if dry_run:
                payload = project_orchestration_delete_preview(
                    service.preview_orchestration_delete(orchestration_id_value),
                    orchestration_id_value,
                )
                echo_json(payload)
                return
            echo_json(service.delete_orchestration(orchestration_id_value))
        except (LooporaError, OSError, ValueError) as exc:
            _handle_orchestration_mutation_error(exc, action="deleted")
