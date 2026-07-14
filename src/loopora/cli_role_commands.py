from __future__ import annotations


import typer

from loopora.asset_errors import asset_mutation_error_message
from loopora.cli_resource_recovery import (
    MissingResourceIdentifierRecovery,
    MissingResourceNameRecovery,
    exit_with_missing_resource_identifier_recovery,
    exit_with_missing_resource_name_recovery,
    normalize_cli_identifier,
)
from loopora.cli_resource_projection import project_role_definition_delete_preview, role_definition_list_rows
from loopora.cli_role_prompt_file_recovery import (
    exit_with_role_prompt_file_recovery,
    role_prompt_file_input_error,
)
from loopora.cli_shared import (
    ArchetypeOption,
    CommandArgOption,
    CommandCliOption,
    ExecutorModeOption,
    ExecutorOption,
    JsonOutputOption,
    get_service,
    LocaleOption,
    ModelOption,
    PromptFileOption,
    PromptTemplateOption,
    ReasoningOption,
    RoleDefinitionBuildRequest,
    build_role_definition_kwargs,
    echo_json,
    handle_error,
)
from loopora.service import LooporaError
from loopora.strategy_source import StrategySourceError

ROLES_HELP_EPILOG = (
    "Role definitions are reusable execution/persona assets for advanced workflow customization. "
    "For a new task, run `loopora start` first, use `loopora fit` when fit is uncertain, then choose the "
    'Fit Guide/Web choices path with `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or the '
    'same-Agent path with `loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before '
    "`/loopora-plan`, using the default Builder -> Inspector/Guide -> GateKeeper roles; create custom roles only "
    "after the reviewed Loop shows a stable reusable responsibility."
)
ROLES_CREATE_HELP_EPILOG = (
    "Creates a reusable role asset for future workflows. It should capture a reviewed responsibility and prompt "
    "boundary; it is not the first step for a new task and it does not start a run."
)
ROLES_DERIVE_HELP_EPILOG = (
    "Derive copies a built-in or custom role into a new saved custom role for later reviewed workflows. "
    "It does not update the source role, existing Loops, or any running work."
)
ROLES_UPDATE_HELP_EPILOG = (
    "Update edits one saved custom role asset for future workflows. Existing Loop definitions and runs keep the "
    "role contract they were created with; review a new Loop preview before relying on the changed role."
)
ROLES_DELETE_HELP_EPILOG = (
    "Delete removes one saved custom role asset from the reusable library. It does not remove built-in roles, "
    "rewrite existing Loops, or change run history. Use --dry-run to preview Flow references before deleting anything."
)


def _handle_role_mutation_error(
    exc: BaseException,
    *,
    action: str = "saved",
    role_action: str = "create",
) -> None:
    prompt_file_error = role_prompt_file_input_error(exc)
    if prompt_file_error:
        exit_with_role_prompt_file_recovery(prompt_file_error, action=role_action)
    handle_error(LooporaError(asset_mutation_error_message(exc, asset_label="role definition", action=action)), json_output=True)


def register_role_commands(roles_app: typer.Typer) -> None:
    _register_role_list_command(roles_app)
    _register_role_get_command(roles_app)
    _register_role_create_command(roles_app)
    _register_role_derive_command(roles_app)
    _register_role_update_command(roles_app)
    _register_role_delete_command(roles_app)


def _register_role_list_command(roles_app: typer.Typer) -> None:
    @roles_app.command("list")
    def list_roles(*, json_output: JsonOutputOption = False) -> None:
        """List built-in and custom role definitions."""
        try:
            definitions = get_service().list_role_definitions()
            if json_output:
                echo_json({"status": "ok", "count": len(definitions), "role_definitions": definitions})
                return
            for row in role_definition_list_rows(definitions):
                typer.echo(row)
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_role_get_command(roles_app: typer.Typer) -> None:
    @roles_app.command("get")
    def get_role(role_definition_id: str | None = typer.Argument(None, help="Built-in or custom role definition id.")) -> None:
        """Show one role definition as JSON."""
        role_definition_id_value = normalize_cli_identifier(role_definition_id)
        if not role_definition_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="role definition",
                    action="get",
                    required_identifier="role_definition_id",
                    required_identifier_label="Role definition ID",
                    list_command="loopora roles list",
                    list_label="List role definitions",
                    retry_template="loopora roles get <role-definition-id>",
                    web_label="Open Web role library",
                    json_output=True,
                )
            )
        try:
            echo_json(get_service().get_role_definition(role_definition_id_value))
        except LooporaError as exc:
            handle_error(exc, json_output=True)


def _register_role_create_command(roles_app: typer.Typer) -> None:
    @roles_app.command("create", epilog=ROLES_CREATE_HELP_EPILOG)
    def create_role(
        name: str | None = typer.Option(None, help="Role definition name."),
        archetype: ArchetypeOption = "builder",
        description: str = typer.Option("", help="Optional role description."),
        posture_notes: str = typer.Option("", help="Optional task-scoped posture notes for this role."),
        prompt_file: PromptFileOption = None,
        prompt_template: PromptTemplateOption = "",
        locale: LocaleOption = "zh",
        executor_kind: ExecutorOption = "codex",
        executor_mode: ExecutorModeOption = "preset",
        command_cli: CommandCliOption = "",
        command_arg: CommandArgOption = None,
        model: ModelOption = "",
        reasoning_effort: ReasoningOption = "",
    ) -> None:
        """Create a saved role definition."""
        name_value = normalize_cli_identifier(name)
        if not name_value:
            exit_with_missing_resource_name_recovery(
                MissingResourceNameRecovery(
                    resource_label="role definition",
                    required_identifier_label="Role definition name",
                    list_command="loopora roles list",
                    list_label="List existing role definitions",
                    retry_template="loopora roles create --name '<role-name>'",
                    web_label="Open Web role library",
                    json_output=True,
                )
            )
        try:
            payload = build_role_definition_kwargs(
                RoleDefinitionBuildRequest(
                    archetype=archetype,
                    prompt_file=prompt_file,
                    prompt_template=prompt_template,
                    locale=locale,
                    posture_notes=posture_notes,
                    executor_kind=executor_kind,
                    executor_mode=executor_mode,
                    command_cli=command_cli,
                    command_arg=command_arg,
                    model=model,
                    reasoning_effort=reasoning_effort,
                )
            )
            role_definition = get_service().create_role_definition(
                name=name_value,
                description=description,
                **payload,
            )
            echo_json(role_definition)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_role_mutation_error(exc, role_action="create")


def _register_role_derive_command(roles_app: typer.Typer) -> None:
    @roles_app.command("derive", epilog=ROLES_DERIVE_HELP_EPILOG)
    def derive_role(
        source_id: str | None = typer.Argument(None, help="Built-in or custom role definition id to derive from."),
        name: str | None = typer.Option(None, help="Name for the new role definition."),
        description: str | None = typer.Option(None, help="Description for the new role definition."),
        posture_notes: str = typer.Option("", help="Optional task-scoped posture notes for this role."),
        prompt_file: PromptFileOption = None,
        prompt_template: PromptTemplateOption = "",
        locale: LocaleOption = "zh",
        executor_kind: ExecutorOption = "",
        executor_mode: ExecutorModeOption = "",
        command_cli: CommandCliOption = "",
        command_arg: CommandArgOption = None,
        model: ModelOption = "",
        reasoning_effort: ReasoningOption = "",
    ) -> None:
        """Create a new role definition derived from an existing one."""
        source_id_value = normalize_cli_identifier(source_id)
        if not source_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="role definition",
                    action="derive",
                    required_identifier="role_definition_id",
                    required_identifier_label="Role definition ID",
                    list_command="loopora roles list",
                    list_label="List role definitions",
                    retry_template="loopora roles derive <role-definition-id>",
                    web_label="Open Web role library",
                    json_output=True,
                )
            )
        try:
            service = get_service()
            source = service.get_role_definition(source_id_value)
            payload = build_role_definition_kwargs(
                RoleDefinitionBuildRequest(
                    archetype=str(source.get("archetype", "builder") or "builder"),
                    prompt_file=prompt_file,
                    prompt_template=prompt_template,
                    locale=locale,
                    posture_notes=posture_notes,
                    executor_kind=executor_kind,
                    executor_mode=executor_mode,
                    command_cli=command_cli,
                    command_arg=command_arg,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    fallback=source,
                )
            )
            role_definition = service.create_role_definition(
                name=name or f"{source['name']} Copy",
                description=description if description is not None else str(source.get("description", "")),
                **payload,
            )
            echo_json(role_definition)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_role_mutation_error(exc, role_action="derive")


def _register_role_update_command(roles_app: typer.Typer) -> None:
    @roles_app.command("update", epilog=ROLES_UPDATE_HELP_EPILOG)
    def update_role(
        role_definition_id: str | None = typer.Argument(None, help="Custom role definition id."),
        name: str | None = typer.Option(None, help="Override the role name."),
        description: str | None = typer.Option(None, help="Override the role description."),
        posture_notes: str = typer.Option("", help="Optional task-scoped posture notes for this role."),
        prompt_file: PromptFileOption = None,
        prompt_template: PromptTemplateOption = "",
        locale: LocaleOption = "zh",
        executor_kind: ExecutorOption = "",
        executor_mode: ExecutorModeOption = "",
        command_cli: CommandCliOption = "",
        command_arg: CommandArgOption = None,
        model: ModelOption = "",
        reasoning_effort: ReasoningOption = "",
    ) -> None:
        """Update a saved custom role definition."""
        role_definition_id_value = normalize_cli_identifier(role_definition_id)
        if not role_definition_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="role definition",
                    action="update",
                    required_identifier="role_definition_id",
                    required_identifier_label="Role definition ID",
                    list_command="loopora roles list",
                    list_label="List role definitions",
                    retry_template="loopora roles update <role-definition-id>",
                    web_label="Open Web role library",
                    json_output=True,
                )
            )
        try:
            service = get_service()
            current = service.get_role_definition(role_definition_id_value)
            payload = build_role_definition_kwargs(
                RoleDefinitionBuildRequest(
                    archetype=str(current.get("archetype", "builder") or "builder"),
                    prompt_file=prompt_file,
                    prompt_template=prompt_template,
                    locale=locale,
                    posture_notes=posture_notes,
                    executor_kind=executor_kind,
                    executor_mode=executor_mode,
                    command_cli=command_cli,
                    command_arg=command_arg,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    fallback=current,
                )
            )
            role_definition = service.update_role_definition(
                role_definition_id_value,
                name=name if name is not None else current["name"],
                description=description if description is not None else str(current.get("description", "")),
                prompt_ref=str(current.get("prompt_ref", "")),
                **payload,
            )
            echo_json(role_definition)
        except (LooporaError, StrategySourceError, OSError, ValueError) as exc:
            _handle_role_mutation_error(exc, role_action="update")


def _register_role_delete_command(roles_app: typer.Typer) -> None:
    @roles_app.command("delete", epilog=ROLES_DELETE_HELP_EPILOG)
    def delete_role(
        role_definition_id: str | None = typer.Argument(None, help="Custom role definition id."),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview delete scope without deleting local state."),
    ) -> None:
        """Delete a saved custom role definition."""
        role_definition_id_value = normalize_cli_identifier(role_definition_id)
        if not role_definition_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="role definition",
                    action="delete",
                    required_identifier="role_definition_id",
                    required_identifier_label="Role definition ID",
                    list_command="loopora roles list",
                    list_label="List role definitions",
                    retry_template="loopora roles delete <role-definition-id> --dry-run",
                    web_label="Open Web role library",
                    json_output=True,
                )
            )
        try:
            service = get_service()
            if dry_run:
                payload = project_role_definition_delete_preview(
                    service.preview_role_definition_delete(role_definition_id_value),
                    role_definition_id_value,
                )
                echo_json(payload)
                return
            echo_json(service.delete_role_definition(role_definition_id_value))
        except (LooporaError, OSError, ValueError) as exc:
            _handle_role_mutation_error(exc, action="deleted")
