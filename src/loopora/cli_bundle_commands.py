from __future__ import annotations

import shlex
from pathlib import Path

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_bundle_file_recovery import (
    BundleImportFileArgument,
    PlanFileOutputRecovery,
    exit_with_missing_plan_file_import_recovery,
    exit_with_plan_file_output_write_recovery_if_known,
    validated_bundle_import_file,
    validated_plan_file_output_path,
)
from loopora.cli_resource_recovery import (
    MissingResourceIdentifierRecovery,
    exit_with_missing_resource_identifier_recovery,
    normalize_cli_identifier,
)
from loopora.cli_resource_projection import bundle_list_rows, project_bundle_delete_preview
from loopora.cli_shared import BundleOutputOption, JsonOutputOption, echo_json, get_service, handle_error
from loopora.service import LooporaError
from loopora.service_bundle_export import write_plan_file_yaml

BUNDLES_HELP_EPILOG = (
    "Plan Files are reviewed Loop artifacts for reuse, import/export, and collaboration handoff. "
    "For a new task, leave this group: run `loopora start` as the read-only route chooser; when fit is uncertain, "
    "use `loopora fit` before choosing the Fit Guide/Web choices path with "
    '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or the same-Agent path with '
    '`loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before `/loopora-plan`; '
    "then use `bundles import/export/derive` to move that reviewed plan across projects or sessions."
)
BUNDLES_IMPORT_HELP_EPILOG = (
    "Import expects an existing reviewed Loop plan file. It materializes run-ready local assets and records, "
    "but it does not create or review a new task. For first use, leave this import command: run `loopora start` "
    "as the read-only route chooser; when fit is uncertain, run `loopora fit`; then choose the Fit Guide/Web "
    'choices path with `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` or the '
    'same-Agent path with `loopora init <agent> --workdir "$PWD"` and `loopora doctor --workdir "$PWD"` before '
    "`/loopora-plan` and `/loopora-run`. Use --replace-bundle-id only when intentionally updating an imported "
    "plan file in place."
)
BUNDLES_EXPORT_HELP_EPILOG = (
    "Export prints an imported reviewed Plan File as the YAML artifact stream when --output is omitted. "
    "Use --output when the next step is sharing, versioning, or moving the reviewed plan file; export reads the "
    "imported Plan File record and leaves Loop/run state unchanged."
)
BUNDLES_DERIVE_HELP_EPILOG = (
    "Derive turns an existing reviewed Loop definition into a Plan File artifact for handoff or reuse. "
    "When --output is omitted, stdout is the YAML artifact stream; --name, --description, and "
    "--collaboration-summary only shape exported artifact metadata and leave the source Loop/run state unchanged."
)
BUNDLES_DELETE_HELP_EPILOG = (
    "Delete removes one imported Plan File record and its Loopora-managed imported asset group. It does not delete "
    "the original exported YAML file, source Loop, source project workdir, or run history. Use --dry-run to preview "
    "the imported asset graph, active-run blockers, and follow-up delete command without deleting anything."
)


def register_bundle_commands(bundles_app: typer.Typer) -> None:
    _register_bundle_list_command(bundles_app)
    _register_bundle_get_command(bundles_app)
    _register_bundle_import_command(bundles_app)
    _register_bundle_export_command(bundles_app)
    _register_bundle_derive_command(bundles_app)
    _register_bundle_delete_command(bundles_app)


def _register_bundle_list_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("list")
    def list_bundles(*, json_output: JsonOutputOption = False) -> None:
        """List imported Loop plan files."""
        try:
            bundles = get_service().list_bundles()
            if json_output:
                echo_json({"status": "ok", "count": len(bundles), "bundles": bundles})
                return
            if not bundles:
                typer.echo("No Plan Files found.")
                return
            for row in bundle_list_rows(bundles):
                typer.echo(row)
        except LooporaError as exc:
            handle_error(exc, json_output=json_output)


def _register_bundle_get_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("get")
    def get_bundle(bundle_id: str | None = typer.Argument(None, help="Imported bundle id.")) -> None:
        """Show one imported plan file record as JSON."""
        bundle_id_value = normalize_cli_identifier(bundle_id)
        if not bundle_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Plan File",
                    action="get",
                    required_identifier="bundle_id",
                    required_identifier_label="Plan File ID",
                    list_command="loopora bundles list",
                    list_label="List imported Plan Files",
                    retry_template="loopora bundles get <bundle-id>",
                    web_label="Open Web Plan File library",
                    json_output=True,
                )
            )
        try:
            echo_json(get_service().get_bundle(bundle_id_value))
        except LooporaError as exc:
            handle_error(exc, json_output=True)


def _register_bundle_import_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("import", epilog=rewrite_loopora_help_commands(BUNDLES_IMPORT_HELP_EPILOG))
    def import_bundle(
        bundle_file: BundleImportFileArgument = None,
        replace_bundle_id: str = typer.Option("", help="Replace an existing imported plan file id in place."),
    ) -> None:
        """Import one Loop plan file and materialize its run-ready assets."""
        if bundle_file is None:
            exit_with_missing_plan_file_import_recovery()
        bundle_file = validated_bundle_import_file(bundle_file)
        try:
            echo_json(
                get_service().import_bundle_file(
                    bundle_file,
                    replace_bundle_id=replace_bundle_id.strip() or None,
                )
            )
        except LooporaError as exc:
            handle_error(exc, json_output=True)


def _register_bundle_export_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("export", epilog=BUNDLES_EXPORT_HELP_EPILOG)
    def export_bundle(
        bundle_id: str | None = typer.Argument(None, help="Imported plan file id."),
        output: BundleOutputOption = None,
    ) -> None:
        """Export one imported Loop plan file."""
        bundle_id_value = normalize_cli_identifier(bundle_id)
        if not bundle_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Plan File",
                    action="export",
                    required_identifier="bundle_id",
                    required_identifier_label="Plan File ID",
                    list_command="loopora bundles list",
                    list_label="List imported Plan Files",
                    retry_template="loopora bundles export <bundle-id>",
                    web_label="Open Web Plan File library",
                    json_output=False,
                )
            )
        output_recovery: PlanFileOutputRecovery | None = None
        if output is not None:
            output_recovery = PlanFileOutputRecovery(
                action="export",
                retry_template=f"loopora bundles export {shlex.quote(bundle_id_value)} --output <plan-file>",
                stream_template=f"loopora bundles export {shlex.quote(bundle_id_value)}",
                list_command="loopora bundles list",
                list_label="List imported Plan Files",
            )
            output = validated_plan_file_output_path(
                output,
                output_recovery,
            )
        try:
            service = get_service()
            if output is None:
                typer.echo(service.export_bundle_yaml(bundle_id_value))
                return
            written = service.write_bundle_file(bundle_id_value, output)
            typer.echo(str(written.resolve()))
        except LooporaError as exc:
            if output_recovery is not None:
                exit_with_plan_file_output_write_recovery_if_known(exc, output_recovery)
            handle_error(exc)


def _register_bundle_derive_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("derive", epilog=BUNDLES_DERIVE_HELP_EPILOG)
    def derive_bundle(
        loop_id: str | None = typer.Argument(None, help="Loop definition id to export as a plan file."),
        output: BundleOutputOption = None,
        name: str | None = typer.Option(None, help="Override the exported plan file name."),
        description: str = typer.Option("", help="Optional plan file description."),
        collaboration_summary: str = typer.Option("", help="Optional readable collaboration summary."),
    ) -> None:
        """Derive a Loop plan file from an existing loop definition."""
        loop_id_value = normalize_cli_identifier(loop_id)
        if not loop_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="saved Loop",
                    action="derive_plan_file",
                    required_identifier="loop_id",
                    required_identifier_label="Loop ID",
                    list_command="loopora loops list",
                    list_label="List saved Loops",
                    retry_template="loopora bundles derive <loop-id>",
                    web_label="Open Web saved Loop library",
                    json_output=False,
                )
            )
        output_recovery: PlanFileOutputRecovery | None = None
        if output is not None:
            output_recovery = PlanFileOutputRecovery(
                action="derive",
                retry_template=f"loopora bundles derive {shlex.quote(loop_id_value)} --output <plan-file>",
                stream_template=f"loopora bundles derive {shlex.quote(loop_id_value)}",
                list_command="loopora loops list",
                list_label="List saved Loops",
            )
            output = validated_plan_file_output_path(
                output,
                output_recovery,
            )
        try:
            service = get_service()
            bundle = service.derive_bundle_from_loop(
                loop_id_value,
                name=name,
                description=description,
                collaboration_summary=collaboration_summary,
            )
            if output is None:
                from loopora.bundles import bundle_to_yaml

                typer.echo(bundle_to_yaml(bundle))
                return
            from loopora.bundles import bundle_to_yaml

            written = write_plan_file_yaml(Path(output), bundle_to_yaml(bundle))
            typer.echo(str(written.resolve()))
        except LooporaError as exc:
            if output_recovery is not None:
                exit_with_plan_file_output_write_recovery_if_known(exc, output_recovery)
            handle_error(exc)


def _register_bundle_delete_command(bundles_app: typer.Typer) -> None:
    @bundles_app.command("delete", epilog=BUNDLES_DELETE_HELP_EPILOG)
    def delete_bundle(
        bundle_id: str | None = typer.Argument(None, help="Imported plan file id."),
        *,
        dry_run: bool = typer.Option(default=False, help="Preview delete scope without deleting local state."),
    ) -> None:
        """Delete one imported plan file and its imported asset group."""
        bundle_id_value = normalize_cli_identifier(bundle_id)
        if not bundle_id_value:
            exit_with_missing_resource_identifier_recovery(
                MissingResourceIdentifierRecovery(
                    resource_label="Plan File",
                    action="delete",
                    required_identifier="bundle_id",
                    required_identifier_label="Plan File ID",
                    list_command="loopora bundles list",
                    list_label="List imported Plan Files",
                    retry_template="loopora bundles delete <bundle-id> --dry-run",
                    web_label="Open Web Plan File library",
                    json_output=True,
                )
            )
        try:
            service = get_service()
            if dry_run:
                payload = project_bundle_delete_preview(service.preview_bundle_delete(bundle_id_value), bundle_id_value)
                echo_json(payload)
                return
            echo_json(service.delete_bundle(bundle_id_value))
        except LooporaError as exc:
            handle_error(exc, json_output=True)
