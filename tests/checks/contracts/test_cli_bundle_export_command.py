from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.bundles import bundle_to_yaml
from loopora.service import LooporaError
from loopora.service_bundle_export import (
    PLAN_FILE_EXPORT_ERROR,
    PLAN_FILE_OUTPUT_DIRECTORY_ERROR,
    ServiceBundleExportMixin,
)
from loopora.service_bundle_import import PLAN_FILE_IMPORT_ERROR

from cli_bundle_commands_test_support import install_cli_bundle_service, write_cli_bundle


ROOT = Path(__file__).resolve().parents[3]


def _assert_resource_recovery_action_projection(payload: dict) -> None:
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["next_action_kinds"] == action_kinds
    assert payload["next_action_ready_now_kinds"] == action_kinds
    assert payload["next_action_ready_after_actions"] == {}


def test_cli_bundle_file_recovery_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_bundle_commands.py").read_text(encoding="utf-8")
    recovery_source = (ROOT / "src" / "loopora" / "cli_bundle_file_recovery.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    dev_check_guide = (ROOT / "src" / "loopora" / "dev_check_guide_alignment.py").read_text(encoding="utf-8")

    assert "from loopora.cli_bundle_file_recovery import" in commands_source
    assert "missing_plan_file_input" not in commands_source
    assert "invalid_plan_file_input" not in commands_source
    assert "invalid_plan_file_output_target" not in commands_source
    assert "def validated_bundle_import_file" in recovery_source
    assert "def validated_plan_file_output_path" in recovery_source
    assert "def exit_with_plan_file_output_write_recovery_if_known" in recovery_source
    assert "cli_bundle_file_recovery.py" in service_boundaries
    assert "cli_bundle_file_recovery.py" in contracts
    assert "src/loopora/cli_bundle*.py" in dev_check_guide


def test_cli_bundle_resource_projection_has_dedicated_boundary() -> None:
    commands_source = (ROOT / "src" / "loopora" / "cli_bundle_commands.py").read_text(encoding="utf-8")
    projection_source = (ROOT / "src" / "loopora" / "cli_resource_projection.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_resource_projection import" in commands_source
    assert "def bundle_list_rows" in projection_source
    assert "def project_bundle_delete_preview" in projection_source
    assert "def _cli_bundle_delete_next_actions" not in commands_source
    assert "project_resource_recovery_action_contract" not in commands_source
    assert "copyable_loopora_command" not in commands_source
    assert "cli_resource_projection.py" in service_boundaries
    assert "cli_resource_projection.py" in contracts


def test_cli_bundles_help_keeps_plan_files_as_reviewed_artifacts() -> None:
    runner = CliRunner()

    group_help = runner.invoke(cli.app, ["bundles", "--help"])
    import_help = runner.invoke(cli.app, ["bundles", "import", "--help"])
    export_help = runner.invoke(cli.app, ["bundles", "export", "--help"])
    derive_help = runner.invoke(cli.app, ["bundles", "derive", "--help"])
    delete_help = runner.invoke(cli.app, ["bundles", "delete", "--help"])

    normalized_group = " ".join(group_help.stdout.split())
    normalized_import = " ".join(import_help.stdout.split())
    normalized_export = " ".join(export_help.stdout.split())
    normalized_derive = " ".join(derive_help.stdout.split())
    normalized_delete = " ".join(delete_help.stdout.split())
    assert group_help.exit_code == 0, group_help.stdout
    assert import_help.exit_code == 0, import_help.stdout
    assert export_help.exit_code == 0, export_help.stdout
    assert derive_help.exit_code == 0, derive_help.stdout
    assert delete_help.exit_code == 0, delete_help.stdout
    assert "Plan Files are reviewed Loop artifacts" in normalized_group
    assert "reuse, import/export, and collaboration handoff" in normalized_group
    assert "run `loopora start` as the read-only route chooser" in normalized_group
    assert "when fit is uncertain" in normalized_group
    assert "Fit Guide/Web choices path" in normalized_group
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in normalized_group
    assert 'loopora init <agent> --workdir "$PWD"' in normalized_group
    assert 'loopora doctor --workdir "$PWD"' in normalized_group
    assert normalized_group.index("Fit Guide/Web choices path") < normalized_group.index("same-Agent path")
    assert normalized_group.index("same-Agent path") < normalized_group.index("/loopora-plan")
    assert "bundles import/export/derive" in normalized_group
    assert "Import expects an existing reviewed Loop plan file" in normalized_import
    assert "materializes run-ready local assets and records" in normalized_import
    assert "does not create or review a new task" in normalized_import
    assert "For first use, leave this import command" in normalized_import
    assert all(
        term in normalized_import
        for term in (
            "loopora start",
            "loopora fit",
            "Fit Guide/Web choices path",
            'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742',
            "same-Agent path",
            'loopora init <agent> --workdir "$PWD"',
            'loopora doctor --workdir "$PWD"',
            "/loopora-plan",
            "/loopora-run",
        )
    )
    assert normalized_import.index("Fit Guide/Web choices path") < normalized_import.index("same-Agent path")
    assert normalized_import.index("same-Agent path") < normalized_import.index("/loopora-plan")
    assert "Use --replace-bundle-id only when intentionally updating" in normalized_import
    assert "Export prints an imported reviewed Plan File as the YAML artifact stream" in normalized_export
    assert "leaves Loop/run state unchanged" in normalized_export
    assert "Derive turns an existing reviewed Loop definition into a Plan File artifact" in normalized_derive
    assert "stdout is the YAML artifact stream" in normalized_derive
    assert "--collaboration-summary only shape exported artifact metadata" in normalized_derive
    assert "Delete removes one imported Plan File record" in normalized_delete
    assert "does not delete the original exported YAML file" in normalized_delete
    assert "source Loop, source project workdir, or run history" in normalized_delete
    assert "--dry-run to preview the imported asset graph" in normalized_delete


def test_cli_bundles_list_can_print_json(monkeypatch, tmp_path: Path) -> None:
    install_cli_bundle_service(monkeypatch, tmp_path)

    result = CliRunner().invoke(cli.app, ["bundles", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["count"] == 1
    assert payload["bundles"][0]["id"] == "bundle_cli"
    assert payload["bundles"][0]["revision"] == 2
    assert "revision=" not in result.stdout


@pytest.mark.parametrize(
    "case",
    [
        {
            "args": ["bundles", "export"],
            "required_identifier": "bundle_id",
            "list_command": "loopora bundles list",
            "retry_template": "loopora bundles export <bundle-id>",
            "expects_json": False,
        },
        {
            "args": ["bundles", "derive"],
            "required_identifier": "loop_id",
            "list_command": "loopora loops list",
            "retry_template": "loopora bundles derive <loop-id>",
            "expects_json": False,
        },
        {
            "args": ["bundles", "delete"],
            "required_identifier": "bundle_id",
            "list_command": "loopora bundles list",
            "retry_template": "loopora bundles delete <bundle-id> --dry-run",
            "expects_json": True,
        },
    ],
)
def test_cli_bundles_selected_resource_commands_recover_when_identifier_is_missing(
    monkeypatch,
    case: dict,
) -> None:
    def fail_service():
        raise AssertionError("missing resource id recovery must not call service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    result = CliRunner().invoke(cli.app, case["args"])

    assert result.exit_code == 1
    assert "Missing argument" not in result.output
    assert "Usage:" not in result.output
    if case["expects_json"]:
        payload = json.loads(result.stdout)
        assert payload["resource_recovery"] == "missing_resource_identifier"
        assert payload["required_identifier"] == case["required_identifier"]
        _assert_resource_recovery_action_projection(payload)
        assert case["list_command"] in payload["next_actions"][0]["command"]
        assert payload["next_actions"][2]["command_template"] == case["retry_template"]
        return
    assert "Loopora resource command needs an id" in result.output
    assert f'required_identifier": "{case["required_identifier"]}"' not in result.output
    assert case["list_command"] in result.output
    assert case["retry_template"] in result.output


def test_cli_bundles_list_reports_human_empty_state(monkeypatch) -> None:
    class EmptyBundleService:
        def list_bundles(self):
            return []

    monkeypatch.setattr(cli, "create_service", EmptyBundleService)

    result = CliRunner().invoke(cli.app, ["bundles", "list"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout == "No Plan Files found.\n"
    assert result.stderr == ""


def test_cli_bundles_list_json_errors_are_structured(monkeypatch) -> None:
    class FailingService:
        def list_bundles(self):
            raise LooporaError("bundle list unavailable")

    monkeypatch.setattr(cli, "create_service", FailingService)

    result = CliRunner().invoke(cli.app, ["bundles", "list", "--json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"status": "error", "error": "bundle list unavailable"}
    assert result.stderr == ""


def _assert_plan_file_import_input_recovery(result, *, validation_error: str) -> None:
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_plan_file_input"
    assert payload["status"] == "blocked_by_invalid_plan_file"
    assert payload["required_identifier"] == "bundle_file"
    assert payload["validation_error"] == validation_error
    assert "before Loopora opens local App state" in payload["summary"]
    assert [item["kind"] for item in payload["next_actions"]] == [
        "choose_readable_plan_file",
        "repair_plan_file",
        "start_route_chooser",
    ]
    _assert_resource_recovery_action_projection(payload)


def test_cli_bundles_import_reports_missing_file_without_usage_or_local_path(monkeypatch, tmp_path: Path) -> None:
    bundle_path = tmp_path / "missing.loopora.yml"

    def fail_service():
        raise AssertionError("missing Plan File input must be blocked before service access")

    monkeypatch.setattr(cli, "create_service", fail_service)

    result = CliRunner().invoke(cli.app, ["bundles", "import", str(bundle_path)])

    assert result.exit_code == 1
    _assert_plan_file_import_input_recovery(result, validation_error="bundle file does not exist")
    assert result.stderr == ""
    assert str(bundle_path) not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output


def test_cli_bundles_import_directory_reports_structured_file_error(monkeypatch, tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle-dir"
    bundle_dir.mkdir()

    def fail_service():
        raise AssertionError("directory-shaped Plan File input must be blocked before service access")

    monkeypatch.setattr(cli, "create_service", fail_service)

    result = CliRunner().invoke(cli.app, ["bundles", "import", str(bundle_dir)])

    assert result.exit_code == 1
    _assert_plan_file_import_input_recovery(result, validation_error="bundle file could not be read")
    assert result.stderr == ""
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    assert "is a directory" not in result.output


def test_cli_bundles_import_malformed_yaml_reports_stable_file_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "app-home"))
    bundle_path = tmp_path / "bad.loopora.yml"
    bundle_path.write_text("version: 1\nmetadata: [\n", encoding="utf-8")

    def fail_service():
        raise AssertionError("malformed Plan File input must be blocked before service access")

    monkeypatch.setattr(cli, "create_service", fail_service)

    result = CliRunner().invoke(cli.app, ["bundles", "import", str(bundle_path)])

    assert result.exit_code == 1
    _assert_plan_file_import_input_recovery(
        result,
        validation_error="invalid bundle YAML: check Plan File YAML syntax",
    )
    assert "while parsing" not in result.output
    assert "<unicode string>" not in result.output
    assert str(bundle_path) not in result.output
    assert "Invalid value" not in result.output


def test_cli_bundles_import_storage_failure_is_structured_without_local_path(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "app-home"
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    monkeypatch.setenv("LOOPORA_HOME", str(app_home))
    bundle_path = tmp_path / "bundle.loopora.yml"
    write_cli_bundle(bundle_path, workdir)
    original_replace = Path.replace

    def fail_import_bundle_yaml_replace(path: Path, target: Path) -> Path:
        if Path(target).name == "bundle.yml":
            raise OSError(f"permission denied: {target}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_import_bundle_yaml_replace)

    result = CliRunner().invoke(cli.app, ["bundles", "import", str(bundle_path)])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"status": "error", "error": PLAN_FILE_IMPORT_ERROR}
    assert result.stderr == ""
    assert "permission denied" not in result.output
    assert str(app_home) not in result.output
    assert str(bundle_path) not in result.output
    bundles_dir = app_home / "bundles"
    if bundles_dir.exists():
        assert not list(bundles_dir.iterdir())


def test_cli_bundles_import_expands_home_path_with_real_service(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "workdir"
    home.mkdir()
    workdir.mkdir()
    bundle_path = home / "home-plan.yml"
    write_cli_bundle(bundle_path, workdir)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "app-home"))

    result = CliRunner().invoke(cli.app, ["bundles", "import", f"~/{bundle_path.name}"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["name"] == "CLI Bundle"
    assert payload["imported_from_path"] == str(bundle_path.resolve())


def test_cli_bundles_export_writes_requested_output_path(monkeypatch, tmp_path: Path) -> None:
    calls = install_cli_bundle_service(monkeypatch, tmp_path)
    export_path = tmp_path / "exported.yml"

    result = CliRunner().invoke(cli.app, ["bundles", "export", "bundle_cli", "--output", str(export_path)])

    assert result.exit_code == 0, result.stdout
    assert calls["write"] == {"bundle_id": "bundle_cli", "path": str(export_path)}
    assert export_path.read_text(encoding="utf-8").startswith("version: 1")


def _assert_plan_file_output_target_recovery(
    result,
    expected: dict[str, str],
) -> None:
    assert result.exit_code == 1
    assert "Loopora Plan File output target is blocked" in result.output
    assert f"action: {expected['action']}" in result.output
    assert f"output_state: {expected['output_state']}" in result.output
    assert f"validation_error: {expected['validation_error']}" in result.output
    assert expected["retry_template"] in result.output
    assert expected["stream_template"] in result.output
    assert "Usage:" not in result.output
    assert "Invalid value" not in result.output


def test_cli_bundles_export_output_directory_recovers_before_service(monkeypatch, tmp_path: Path) -> None:
    loopora_home = tmp_path.parent / "loopora-home-export"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))

    def fail_service():
        raise AssertionError("directory output target recovery must not access service")

    monkeypatch.setattr(cli, "create_service", fail_service)

    result = CliRunner().invoke(cli.app, ["bundles", "export", "bundle_cli", "--output", str(tmp_path)])

    _assert_plan_file_output_target_recovery(
        result,
        {
            "action": "export",
            "output_state": "directory",
            "validation_error": PLAN_FILE_OUTPUT_DIRECTORY_ERROR,
            "retry_template": "loopora bundles export bundle_cli --output <plan-file>",
            "stream_template": "loopora bundles export bundle_cli",
        },
    )
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert f"{command_prefix}loopora bundles export bundle_cli --output <plan-file>" in result.output
    assert f"{command_prefix}loopora bundles export bundle_cli" in result.output
    assert f"{command_prefix}loopora bundles list" in result.output
    assert str(tmp_path) not in result.output


def test_service_bundle_export_write_failure_uses_stable_error(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Service Export Failure Source",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    bundle = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Service Export Failure Bundle",
                collaboration_summary="Export errors stay stable.",
            )
        )
    )
    output_path = tmp_path / "private" / "exported.yml"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("previous export\n", encoding="utf-8")
    original_replace = Path.replace

    def fail_export_replace(path: Path, target: Path) -> Path:
        if Path(target) == output_path:
            raise OSError(f"permission denied: {output_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_export_replace)

    with pytest.raises(LooporaError) as exc_info:
        service.write_bundle_file(bundle["id"], output_path)

    assert str(exc_info.value) == PLAN_FILE_EXPORT_ERROR
    assert "permission denied" not in str(exc_info.value)
    assert str(output_path) not in str(exc_info.value)
    assert output_path.read_text(encoding="utf-8") == "previous export\n"
    assert not list(output_path.parent.glob(f".{output_path.name}.tmp.*"))


def test_service_bundle_export_rejects_output_directory_with_stable_error(tmp_path: Path) -> None:
    class FakeExportService(ServiceBundleExportMixin):
        def export_bundle_yaml(self, bundle_id: str) -> str:
            assert bundle_id == "bundle_cli"
            return "version: 1\nmetadata:\n  name: CLI Bundle\n"

    with pytest.raises(LooporaError) as exc_info:
        FakeExportService().write_bundle_file("bundle_cli", tmp_path)

    assert str(exc_info.value) == PLAN_FILE_OUTPUT_DIRECTORY_ERROR
    assert str(tmp_path) not in str(exc_info.value)


def test_cli_bundles_export_output_write_failure_uses_stable_error(monkeypatch, tmp_path: Path) -> None:
    loopora_home = tmp_path.parent / "loopora-home-export-write"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    private_path = tmp_path / "private" / "exported.yml"

    class FakeService:
        def write_bundle_file(self, bundle_id: str, path: Path):
            assert bundle_id == "bundle_cli"
            assert path == private_path
            raise LooporaError(PLAN_FILE_EXPORT_ERROR) from OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    result = CliRunner().invoke(cli.app, ["bundles", "export", "bundle_cli", "--output", str(private_path)])

    _assert_plan_file_output_target_recovery(
        result,
        {
            "action": "export",
            "output_state": "write_failed",
            "validation_error": PLAN_FILE_EXPORT_ERROR,
            "retry_template": "loopora bundles export bundle_cli --output <plan-file>",
            "stream_template": "loopora bundles export bundle_cli",
        },
    )
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert f"{command_prefix}loopora bundles export bundle_cli --output <plan-file>" in result.output
    assert f"{command_prefix}loopora bundles export bundle_cli" in result.output
    assert f"{command_prefix}loopora bundles list" in result.output
    assert "permission denied" not in result.output
    assert str(private_path) not in result.output


def test_cli_bundles_derive_output_write_failure_uses_stable_error(monkeypatch, tmp_path: Path) -> None:
    loopora_home = tmp_path.parent / "loopora-home-derive-write"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    install_cli_bundle_service(monkeypatch, tmp_path)
    output_path = tmp_path / "private" / "derived.yml"
    original_replace = Path.replace

    def fail_export_replace(path: Path, target: Path) -> Path:
        if Path(target) == output_path:
            raise OSError(f"permission denied: {output_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_export_replace)

    result = CliRunner().invoke(
        cli.app,
        ["bundles", "derive", "loop_cli", "--output", str(output_path)],
    )

    _assert_plan_file_output_target_recovery(
        result,
        {
            "action": "derive",
            "output_state": "write_failed",
            "validation_error": PLAN_FILE_EXPORT_ERROR,
            "retry_template": "loopora bundles derive loop_cli --output <plan-file>",
            "stream_template": "loopora bundles derive loop_cli",
        },
    )
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert f"{command_prefix}loopora bundles derive loop_cli --output <plan-file>" in result.output
    assert f"{command_prefix}loopora bundles derive loop_cli" in result.output
    assert f"{command_prefix}loopora loops list" in result.output
    assert "permission denied" not in result.output
    assert str(output_path) not in result.output
    assert not output_path.exists()


def test_cli_bundles_derive_output_directory_reports_stable_error(monkeypatch, tmp_path: Path) -> None:
    loopora_home = tmp_path.parent / "loopora-home-derive"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))

    def fail_service():
        raise AssertionError("directory output target recovery must not access service")

    monkeypatch.setattr(cli, "create_service", fail_service)

    result = CliRunner().invoke(
        cli.app,
        ["bundles", "derive", "loop_cli", "--output", str(tmp_path)],
    )

    _assert_plan_file_output_target_recovery(
        result,
        {
            "action": "derive",
            "output_state": "directory",
            "validation_error": PLAN_FILE_OUTPUT_DIRECTORY_ERROR,
            "retry_template": "loopora bundles derive loop_cli --output <plan-file>",
            "stream_template": "loopora bundles derive loop_cli",
        },
    )
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert f"{command_prefix}loopora bundles derive loop_cli --output <plan-file>" in result.output
    assert f"{command_prefix}loopora bundles derive loop_cli" in result.output
    assert f"{command_prefix}loopora loops list" in result.output
    assert str(tmp_path) not in result.output
