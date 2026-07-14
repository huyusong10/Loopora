from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora import cli_prompt_commands
from loopora.specs import SPEC_FILE_DIRECTORY_ERROR, SPEC_FILE_INIT_ERROR, SPEC_FILE_SAVE_ERROR
from loopora.strategy_source import StrategySourceError


def _result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def _assert_json_error(result, error: str, *, hidden_text: str = "") -> dict:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload == {"status": "error", "error": error}
    assert result.stderr == ""
    if hidden_text:
        assert hidden_text not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    return payload


def _assert_resource_recovery_action_projection(payload: dict) -> None:
    action_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["next_action_kinds"] == action_kinds
    assert payload["next_action_ready_now_kinds"] == action_kinds
    assert payload["next_action_ready_after_actions"] == {}


def _assert_spec_file_input_recovery(result, *, action: str, validation_error: str, hidden_text: str = "") -> dict:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_spec_file_input"
    assert payload["status"] == "blocked_by_spec_file"
    assert payload["resource"] == "Markdown spec"
    assert payload["action"] == action
    assert payload["validation_error"] == validation_error
    assert [item["kind"] for item in payload["next_actions"]] == [
        "repair_spec_file",
        "choose_spec_file",
        "create_starter_spec",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(payload)
    if action == "write":
        assert "loopora spec write <spec-path> --from-file <source-spec-path>" in payload["next_actions"][1]["command_template"]
    else:
        assert f"loopora spec {action} <spec-path>" in payload["next_actions"][1]["command_template"]
    assert "loopora spec init <spec-path>" in payload["next_actions"][2]["command_template"]
    assert "loopora start" in payload["next_actions"][3]["command"]
    assert "loopora fit" in payload["next_actions"][4]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in payload["next_actions"][5]["command"]
    assert result.stderr == ""
    if hidden_text:
        assert hidden_text not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    return payload


def _assert_missing_spec_write_source_recovery(result) -> dict:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "missing_spec_source_file_input"
    assert payload["status"] == "blocked_by_missing_spec_source_file"
    assert payload["resource"] == "Markdown spec source"
    assert payload["action"] == "write"
    assert payload["required_identifier"] == "source_spec_path"
    assert [item["kind"] for item in payload["next_actions"]] == [
        "choose_source_spec_file",
        "create_starter_source_spec",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora spec write <spec-path> --from-file <source-spec-path>" in payload["next_actions"][0]["command_template"]
    assert "loopora spec init <source-spec-path>" in payload["next_actions"][1]["command_template"]
    assert "loopora start" in payload["next_actions"][2]["command"]
    assert "loopora fit" in payload["next_actions"][3]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in payload["next_actions"][4]["command"]
    assert result.stderr == ""
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    return payload


def _assert_prompt_file_input_recovery(result, *, validation_error: str, hidden_text: str = "") -> dict:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_prompt_file_input"
    assert payload["status"] == "blocked_by_prompt_file"
    assert payload["resource"] == "Strategy Source prompt file"
    assert payload["action"] == "validate"
    assert payload["validation_error"] == validation_error
    assert [item["kind"] for item in payload["next_actions"]] == [
        "repair_prompt_file",
        "choose_prompt_file",
        "list_prompt_templates",
        "render_prompt_template",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(payload)
    assert "loopora prompts validate <prompt-file>" in payload["next_actions"][1]["command_template"]
    assert "loopora prompts list" in payload["next_actions"][2]["command"]
    assert "loopora prompts template <prompt-ref>" in payload["next_actions"][3]["command_template"]
    assert "loopora start" in payload["next_actions"][4]["command"]
    assert "loopora fit" in payload["next_actions"][5]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in payload["next_actions"][6]["command"]
    assert result.stderr == ""
    if hidden_text:
        assert hidden_text not in result.output
    assert "Invalid value" not in result.output
    assert "Usage:" not in result.output
    return payload


def _assert_contains_all(text: str, fragments: tuple[str, ...]) -> None:
    for fragment in fragments:
        assert fragment in text


def test_cli_spec_help_keeps_markdown_specs_as_expert_artifacts() -> None:
    runner = CliRunner()

    group_help = runner.invoke(cli.app, ["spec", "--help"])
    init_help = runner.invoke(cli.app, ["spec", "init", "--help"])
    validate_help = runner.invoke(cli.app, ["spec", "validate", "--help"])
    template_help = runner.invoke(cli.app, ["spec", "template", "--help"])
    read_help = runner.invoke(cli.app, ["spec", "read", "--help"])
    write_help = runner.invoke(cli.app, ["spec", "write", "--help"])

    normalized_group = " ".join(group_help.stdout.split())
    normalized_init = " ".join(init_help.stdout.split())
    normalized_validate = " ".join(validate_help.stdout.split())
    normalized_template = " ".join(template_help.stdout.split())
    normalized_read = " ".join(read_help.stdout.split())
    normalized_write = " ".join(write_help.stdout.split())
    for result in (group_help, init_help, validate_help, template_help, read_help, write_help):
        assert result.exit_code == 0, result.stdout
    _assert_contains_all(
        normalized_group,
        (
            "Markdown specs are expert/recovery artifacts",
            "direct create/run and reusable handoffs",
            "For a new task, leave this group",
            "loopora start",
            "loopora fit",
            "Fit Guide/Web choices path",
            "current-host same-Agent setup",
            "the matching entry",
            'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742',
            'loopora init <agent> --workdir "$PWD"',
            'loopora doctor --workdir "$PWD"',
            "/loopora-plan",
            "/loopora-run",
            "spec validate/read/write",
            "do not start runs",
        ),
    )
    assert normalized_group.index("Fit Guide/Web choices path") < normalized_group.index("current-host same-Agent setup")
    _assert_contains_all(
        normalized_init,
        (
            "Creates a starter spec for recovery or expert direct-run paths",
            "reviewed Markdown contract is needed",
            "does not replace first-use review",
            "loopora start",
            "loopora fit",
            "Fit Guide/Web choices path",
            "current-host same-Agent setup/readiness",
        ),
    )
    assert normalized_init.index("Fit Guide/Web choices path") < normalized_init.index("current-host same-Agent setup/readiness")
    _assert_contains_all(
        normalized_validate, ("Validation checks the Markdown artifact shape", "does not mean the task judgment has been reviewed", "the Loop is READY")
    )
    _assert_contains_all(
        normalized_template,
        (
            "Template renders a starter Markdown artifact to stdout",
            "using the selected Strategy Source",
            "route through `loopora start`, `loopora fit`, Fit Guide/Web choices, or same-Agent setup/readiness",
        ),
    )
    _assert_contains_all(normalized_read, ("Read is an inspection surface", "without changing the spec, Loop, or run state"))
    _assert_contains_all(
        normalized_write,
        (
            "Write is a repair surface",
            "use `loopora spec validate`, then review through Fit Guide/Web choices or same-Agent setup/readiness",
        ),
    )


def test_cli_prompt_help_keeps_prompt_assets_as_expert_artifacts() -> None:
    runner = CliRunner()

    group_help = runner.invoke(cli.app, ["prompts", "--help"])
    list_help = runner.invoke(cli.app, ["prompts", "list", "--help"])
    template_help = runner.invoke(cli.app, ["prompts", "template", "--help"])
    validate_help = runner.invoke(cli.app, ["prompts", "validate", "--help"])

    for result in (group_help, list_help, template_help, validate_help):
        assert result.exit_code == 0, result.stdout
    normalized_group = " ".join(group_help.stdout.split())
    normalized_list = " ".join(list_help.stdout.split())
    normalized_template = " ".join(template_help.stdout.split())
    normalized_validate = " ".join(validate_help.stdout.split())
    assert "Expert: inspect and validate Strategy Source prompt assets" in normalized_group
    assert "These commands create no Loops, perform no review, and start no runs" in normalized_group
    assert "For first-use planning, leave this group" in normalized_group
    assert "run `loopora start` for route choice" in normalized_group
    assert "use `loopora fit` when fit is uncertain" in normalized_group
    assert "Fit Guide/Web choices path" in normalized_group
    assert "current-host same-Agent setup" in normalized_group
    assert "the matching entry" in normalized_group
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in normalized_group
    assert 'loopora init <agent> --workdir "$PWD"' in normalized_group
    assert 'loopora doctor --workdir "$PWD"' in normalized_group
    assert "/loopora-plan" in normalized_group
    assert "/loopora-run" in normalized_group
    assert normalized_group.index("Fit Guide/Web choices path") < normalized_group.index("current-host same-Agent setup")
    assert "`loopora spec` remains an expert/recovery artifact surface" in normalized_group
    assert "not a shortcut to READY" in normalized_group
    assert "inventory surface only" in normalized_list
    assert "before running work" in normalized_list
    assert "not a runnable Loop by itself" in normalized_template
    assert "does not update saved role definitions" in normalized_template
    assert "expert asset check" in normalized_validate
    assert "does not prove the overall Loop is reviewed, READY, or safe to run" in normalized_validate


def test_cli_prompt_asset_commands_recover_missing_inputs() -> None:
    runner = CliRunner()

    template_result = runner.invoke(cli.app, ["prompts", "template"])
    assert template_result.exit_code == 1, template_result.output
    assert template_result.stderr == ""
    assert "Usage:" not in template_result.output
    assert "Missing argument" not in template_result.output
    template_payload = json.loads(template_result.stdout)
    assert template_payload["resource_recovery"] == "missing_prompt_template_ref"
    assert template_payload["status"] == "blocked_by_missing_prompt_template_ref"
    assert template_payload["resource"] == "Strategy Source prompt template"
    assert template_payload["action"] == "template"
    assert template_payload["required_identifier"] == "prompt_ref"
    assert [item["kind"] for item in template_payload["next_actions"]] == [
        "list_prompt_templates",
        "retry_after_prompt_ref_choice",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(template_payload)
    assert "loopora prompts list" in template_payload["next_actions"][0]["command"]
    assert "loopora prompts template <prompt-ref>" in template_payload["next_actions"][1]["command_template"]
    assert "loopora start" in template_payload["next_actions"][2]["command"]
    assert "loopora fit" in template_payload["next_actions"][3]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in template_payload["next_actions"][4]["command"]

    validate_result = runner.invoke(cli.app, ["prompts", "validate"])
    assert validate_result.exit_code == 1, validate_result.output
    assert validate_result.stderr == ""
    assert "Usage:" not in validate_result.output
    assert "Missing argument" not in validate_result.output
    validate_payload = json.loads(validate_result.stdout)
    assert validate_payload["resource_recovery"] == "missing_prompt_file_input"
    assert validate_payload["status"] == "blocked_by_missing_prompt_file"
    assert validate_payload["resource"] == "Strategy Source prompt file"
    assert validate_payload["action"] == "validate"
    assert validate_payload["required_identifier"] == "prompt_path"
    assert [item["kind"] for item in validate_payload["next_actions"]] == [
        "retry_after_prompt_file_choice",
        "list_prompt_templates",
        "render_prompt_template",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(validate_payload)
    assert "loopora prompts validate <prompt-file>" in validate_payload["next_actions"][0]["command_template"]
    assert "loopora prompts list" in validate_payload["next_actions"][1]["command"]
    assert "loopora prompts template <prompt-ref>" in validate_payload["next_actions"][2]["command_template"]
    assert "loopora start" in validate_payload["next_actions"][3]["command"]
    assert "loopora fit" in validate_payload["next_actions"][4]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in validate_payload["next_actions"][5]["command"]


def test_cli_spec_artifact_commands_recover_missing_path_inputs() -> None:
    runner = CliRunner()

    init_result = runner.invoke(cli.app, ["spec", "init"])
    assert init_result.exit_code == 1, init_result.output
    assert init_result.stderr == ""
    assert "Usage:" not in init_result.output
    assert "Missing argument" not in init_result.output
    init_payload = json.loads(init_result.stdout)
    assert init_payload["resource_recovery"] == "missing_spec_target_path"
    assert init_payload["status"] == "blocked_by_missing_spec_target_path"
    assert init_payload["resource"] == "Markdown spec"
    assert init_payload["action"] == "init"
    assert init_payload["required_identifier"] == "spec_path"
    assert [item["kind"] for item in init_payload["next_actions"]] == [
        "retry_after_spec_target_choice",
        "start_route_chooser",
        "check_fit_first",
        "open_web_creation_choices",
    ]
    _assert_resource_recovery_action_projection(init_payload)
    assert "loopora spec init <spec-path>" in init_payload["next_actions"][0]["command_template"]
    assert "loopora start" in init_payload["next_actions"][1]["command"]
    assert "loopora fit" in init_payload["next_actions"][2]["command"]
    assert 'loopora serve --open --workdir "$PWD"' in init_payload["next_actions"][3]["command"]

    for args, action, retry_fragment in (
        (["spec", "validate"], "validate", "loopora spec validate <spec-path>"),
        (["spec", "read"], "read", "loopora spec read <spec-path>"),
        (["spec", "write"], "write", "loopora spec write <spec-path> --from-file <source-spec-path>"),
    ):
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 1, result.output
        assert result.stderr == ""
        assert "Usage:" not in result.output
        assert "Missing argument" not in result.output
        payload = json.loads(result.stdout)
        assert payload["resource_recovery"] == "missing_spec_file_input"
        assert payload["status"] == "blocked_by_missing_spec_file"
        assert payload["resource"] == "Markdown spec"
        assert payload["action"] == action
        assert payload["required_identifier"] == "spec_path"
        assert [item["kind"] for item in payload["next_actions"]] == [
            "retry_after_spec_choice",
            "create_starter_spec",
            "start_route_chooser",
            "check_fit_first",
            "open_web_creation_choices",
        ]
        _assert_resource_recovery_action_projection(payload)
        assert retry_fragment in payload["next_actions"][0]["command_template"]
        assert "loopora spec init <spec-path>" in payload["next_actions"][1]["command_template"]
        assert "loopora start" in payload["next_actions"][2]["command"]
        assert "loopora fit" in payload["next_actions"][3]["command"]
        assert 'loopora serve --open --workdir "$PWD"' in payload["next_actions"][4]["command"]


def test_cli_spec_init_accepts_locale_and_validate_reports_check_mode(tmp_path: Path) -> None:
    spec_path = tmp_path / "created-spec.md"
    runner = CliRunner()

    init_result = runner.invoke(cli.app, ["spec", "init", "--locale", "en", str(spec_path)])

    assert init_result.exit_code == 0, init_result.stdout
    created_text = spec_path.read_text(encoding="utf-8")
    assert "# Task" in created_text
    assert "# Done When" in created_text
    assert "# Guardrails" in created_text
    assert "# Role Notes" in created_text
    assert "delete `# Done When`" in created_text

    validate_result = runner.invoke(cli.app, ["spec", "validate", str(spec_path)])

    assert validate_result.exit_code == 0, validate_result.stdout
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is True
    assert payload["check_mode"] == "specified"

    invalid_spec_path = tmp_path / "invalid-spec.md"
    invalid_spec_path.write_bytes(b"\xff")
    invalid_result = runner.invoke(cli.app, ["spec", "validate", str(invalid_spec_path)])
    _assert_spec_file_input_recovery(
        invalid_result,
        action="validate",
        validation_error="spec file must be UTF-8 encoded Markdown",
    )

    missing_spec_path = tmp_path / "missing-spec.md"
    missing_result = runner.invoke(cli.app, ["spec", "validate", str(missing_spec_path)])
    _assert_spec_file_input_recovery(
        missing_result,
        action="validate",
        validation_error="spec file does not exist",
        hidden_text=str(missing_spec_path),
    )


def test_cli_spec_init_accepts_workflow_preset(tmp_path: Path) -> None:
    spec_path = tmp_path / "repair-loop-spec.md"
    strategy_file = tmp_path / "strategy.yml"
    strategy_file.write_text(
        "roles:\n"
        "  - id: reviewer\n"
        "    name: Evidence Reviewer\n"
        "    archetype: inspector\n"
        "    prompt_ref: inspector.md\n"
        "steps:\n"
        "  - id: review\n"
        "    role_id: reviewer\n",
        encoding="utf-8",
    )
    strategy_file_spec_path = tmp_path / "strategy-file-spec.md"
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["spec", "init", "--locale", "en", "--workflow-preset", "repair_loop", str(spec_path)],
    )

    assert result.exit_code == 0, result.stdout
    created_text = spec_path.read_text(encoding="utf-8")
    assert "## Builder Notes" in created_text
    assert "## Regression Inspector Notes" in created_text
    assert "## Contract Inspector Notes" in created_text
    assert "## Guide Notes" in created_text
    assert "## GateKeeper Notes" in created_text
    assert created_text.count("## Builder Notes") == 1

    strategy_file_result = runner.invoke(
        cli.app,
        ["spec", "init", "--locale", "en", "--strategy-file", str(strategy_file), str(strategy_file_spec_path)],
    )
    assert strategy_file_result.exit_code == 0, strategy_file_result.stdout
    assert "## Evidence Reviewer Notes" in strategy_file_spec_path.read_text(encoding="utf-8")


def test_cli_spec_init_redacts_low_level_storage_errors(tmp_path: Path, monkeypatch) -> None:
    loopora_home = tmp_path.parent / "loopora-home-spec-init"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    spec_path = tmp_path / "private" / "created-spec.md"
    local_path = tmp_path / "private" / "loopora-state" / "created-spec.md"
    original_replace = Path.replace

    def fail_target_replace(self: Path, target: Path):
        if Path(target) == spec_path.resolve():
            raise OSError(f"permission denied: {local_path}")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_target_replace)

    result = CliRunner().invoke(cli.app, ["spec", "init", "--locale", "en", str(spec_path)])

    assert result.exit_code == 1
    assert "Loopora Markdown spec output target is blocked" in result.output
    assert "action: init" in result.output
    assert "output_state: write_failed" in result.output
    assert f"validation_error: {SPEC_FILE_INIT_ERROR}" in result.output
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert f"{command_prefix}loopora spec init <spec-path>" in result.output
    assert f"{command_prefix}loopora spec template" in result.output
    assert "permission denied" not in result.output
    assert str(local_path) not in result.output
    assert str(spec_path) not in result.output
    assert not spec_path.exists()
    assert list(spec_path.parent.glob(".created-spec.md.tmp.*")) == []


def test_cli_spec_write_redacts_low_level_storage_errors(tmp_path: Path, monkeypatch) -> None:
    loopora_home = tmp_path.parent / "loopora-home-spec-write"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    source_path = tmp_path / "source.md"
    source_path.write_text("# Task\n\nUpdated task.\n", encoding="utf-8")
    spec_path = tmp_path / "private" / "target-spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text("# Task\n\nOriginal task.\n", encoding="utf-8")
    local_path = tmp_path / "private" / "loopora-state" / "target-spec.md"
    original_replace = Path.replace

    def fail_target_replace(self: Path, target: Path):
        if Path(target) == spec_path.resolve():
            raise OSError(f"permission denied: {local_path}")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_target_replace)

    result = CliRunner().invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(source_path)])

    assert result.exit_code == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["resource_recovery"] == "invalid_spec_output_target"
    assert payload["status"] == "blocked_by_spec_output"
    assert payload["resource"] == "Markdown spec"
    assert payload["action"] == "write"
    assert payload["output_state"] == "write_failed"
    assert payload["validation_error"] == SPEC_FILE_SAVE_ERROR
    assert [item["kind"] for item in payload["next_actions"]] == [
        "choose_spec_output_file",
        "validate_source_spec",
        "create_starter_spec",
        "start_route_chooser",
    ]
    _assert_resource_recovery_action_projection(payload)
    command_prefix = f"LOOPORA_HOME={loopora_home.resolve()} "
    assert payload["next_actions"][0]["command_template"].startswith(command_prefix)
    assert "loopora spec write <spec-path> --from-file <source-spec-path>" in payload["next_actions"][0]["command_template"]
    assert payload["next_actions"][1]["command_template"].startswith(command_prefix)
    assert "loopora spec validate <source-spec-path>" in payload["next_actions"][1]["command_template"]
    assert "permission denied" not in result.output
    assert str(local_path) not in result.output
    assert str(spec_path) not in result.output
    assert spec_path.read_text(encoding="utf-8") == "# Task\n\nOriginal task.\n"
    assert list(spec_path.parent.glob(".target-spec.md.tmp.*")) == []


def test_cli_spec_commands_report_directory_paths_without_low_level_errors(tmp_path: Path) -> None:
    runner = CliRunner()
    source_path = tmp_path / "source.md"
    source_path.write_text("# Task\n\nUpdated task.\n", encoding="utf-8")
    target_dir = tmp_path / "target-dir"
    target_dir.mkdir()

    init_result = runner.invoke(cli.app, ["spec", "init", str(target_dir)])
    assert init_result.exit_code == 1
    init_error = init_result.output
    assert SPEC_FILE_DIRECTORY_ERROR in init_error
    assert "spec file already exists" not in init_error
    assert str(target_dir) not in init_error

    read_result = runner.invoke(cli.app, ["spec", "read", str(target_dir)])
    _assert_spec_file_input_recovery(
        read_result,
        action="read",
        validation_error=SPEC_FILE_DIRECTORY_ERROR,
        hidden_text=str(target_dir),
    )

    write_source_dir = runner.invoke(cli.app, ["spec", "write", str(tmp_path / "target.md"), "--from-file", str(target_dir)])
    _assert_spec_file_input_recovery(
        write_source_dir,
        action="write",
        validation_error=SPEC_FILE_DIRECTORY_ERROR,
        hidden_text=str(target_dir),
    )

    write_target_dir = runner.invoke(cli.app, ["spec", "write", str(target_dir), "--from-file", str(source_path)])
    assert write_target_dir.exit_code == 1
    write_target_payload = json.loads(write_target_dir.stdout)
    assert write_target_payload["resource_recovery"] == "invalid_spec_output_target"
    assert write_target_payload["status"] == "blocked_by_spec_output"
    assert write_target_payload["action"] == "write"
    assert write_target_payload["output_state"] == "directory"
    assert write_target_payload["validation_error"] == SPEC_FILE_DIRECTORY_ERROR
    _assert_resource_recovery_action_projection(write_target_payload)
    assert str(target_dir) not in write_target_dir.output


def test_cli_spec_template_read_and_write(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    spec_path = tmp_path / "spec.md"
    source_path = tmp_path / "source.md"
    source_path.write_text("# Task\n\nUpdated task.\n", encoding="utf-8")

    class FakeService:
        def get_orchestration(self, orchestration_id: str):
            assert orchestration_id == "builtin:repair_loop"
            return {"workflow_json": {"preset": "repair_loop"}}

    monkeypatch.setattr(cli, "create_service", FakeService)

    template_result = runner.invoke(
        cli.app,
        ["spec", "template", "--locale", "en", "--orchestration-id", "builtin:repair_loop", "--json"],
    )
    assert template_result.exit_code == 0, template_result.stdout
    template_payload = json.loads(template_result.stdout)
    assert "# Task" in template_payload["markdown"]
    assert any(item["heading"] == "Builder Notes" for item in template_payload["role_note_sections"])

    orchestration_init_path = tmp_path / "orchestration-spec.md"
    init_from_orchestration = runner.invoke(
        cli.app,
        ["spec", "init", "--locale", "en", "--orchestration-id", "builtin:repair_loop", str(orchestration_init_path)],
    )
    assert init_from_orchestration.exit_code == 0, init_from_orchestration.stdout
    orchestration_text = orchestration_init_path.read_text(encoding="utf-8")
    assert "## Regression Inspector Notes" in orchestration_text
    assert "## GateKeeper Notes" in orchestration_text

    write_result = runner.invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(source_path)])
    assert write_result.exit_code == 0, write_result.stdout
    write_payload = json.loads(write_result.stdout)
    assert write_payload["validation"]["ok"] is True

    read_result = runner.invoke(cli.app, ["spec", "read", str(spec_path)])
    assert read_result.exit_code == 0, read_result.stdout
    read_payload = json.loads(read_result.stdout)
    assert read_payload["content"] == "# Task\n\nUpdated task.\n"
    assert read_payload["validation"]["ok"] is True

    missing_write_source = runner.invoke(cli.app, ["spec", "write", str(spec_path)])
    _assert_missing_spec_write_source_recovery(missing_write_source)

    invalid_source_path = tmp_path / "invalid-source.md"
    invalid_source_path.write_bytes(b"\xff")
    invalid_read = runner.invoke(cli.app, ["spec", "read", str(invalid_source_path)])
    _assert_spec_file_input_recovery(
        invalid_read,
        action="read",
        validation_error="spec file must be UTF-8 encoded Markdown",
    )
    invalid_write = runner.invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(invalid_source_path)])
    _assert_spec_file_input_recovery(
        invalid_write,
        action="write",
        validation_error="spec file must be UTF-8 encoded Markdown",
    )
    missing_source_path = tmp_path / "missing-source.md"
    missing_read = runner.invoke(cli.app, ["spec", "read", str(missing_source_path)])
    _assert_spec_file_input_recovery(
        missing_read,
        action="read",
        validation_error="spec file does not exist",
        hidden_text=str(missing_source_path),
    )
    missing_write = runner.invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(missing_source_path)])
    _assert_spec_file_input_recovery(
        missing_write,
        action="write",
        validation_error="spec file does not exist",
        hidden_text=str(missing_source_path),
    )


def test_cli_spec_file_inputs_expand_home_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    env = {"HOME": str(home_dir)}
    runner = CliRunner()

    init_result = runner.invoke(cli.app, ["spec", "init", "--locale", "en", "~/created.md"], env=env)

    created_path = home_dir / "created.md"
    assert init_result.exit_code == 0, init_result.stdout
    assert created_path.exists()
    assert not (tmp_path / "~").exists()

    read_result = runner.invoke(cli.app, ["spec", "read", "~/created.md"], env=env)
    assert read_result.exit_code == 0, read_result.stdout
    read_payload = json.loads(read_result.stdout)
    assert read_payload["path"] == str(created_path.resolve())
    assert read_payload["validation"]["ok"] is True

    source_path = home_dir / "source.md"
    target_path = home_dir / "written.md"
    source_path.write_text("# Task\n\nHome sourced task.\n", encoding="utf-8")
    write_result = runner.invoke(cli.app, ["spec", "write", "~/written.md", "--from-file", "~/source.md"], env=env)
    assert write_result.exit_code == 0, write_result.stdout
    assert target_path.read_text(encoding="utf-8") == "# Task\n\nHome sourced task.\n"
    assert json.loads(write_result.stdout)["path"] == str(target_path.resolve())

    validate_result = runner.invoke(cli.app, ["spec", "validate", "~/written.md"], env=env)
    assert validate_result.exit_code == 0, validate_result.stdout
    assert json.loads(validate_result.stdout)["path"] == str(target_path.resolve())


def test_cli_spec_template_json_errors_are_structured(tmp_path: Path) -> None:
    missing_strategy = tmp_path / "missing-strategy.yml"

    result = CliRunner().invoke(cli.app, ["spec", "template", "--strategy-file", str(missing_strategy), "--json"])

    _assert_json_error(result, "strategy source file does not exist", hidden_text=str(missing_strategy))

    init_result = CliRunner().invoke(
        cli.app,
        ["spec", "init", "--strategy-file", str(missing_strategy), str(tmp_path / "created-spec.md")],
    )
    assert init_result.exit_code == 1
    init_error = _result_error_text(init_result)
    assert "strategy source file does not exist" in init_error
    assert str(missing_strategy) not in init_error
    assert "Usage:" not in init_result.output


def test_cli_prompts_list_template_and_validate(tmp_path: Path) -> None:
    runner = CliRunner()
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("---\nversion: 1\narchetype: builder\n---\nPrompt body.\n", encoding="utf-8")

    list_result = runner.invoke(cli.app, ["prompts", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert any(item["prompt_ref"] == "builder.md" for item in json.loads(list_result.stdout))

    template_result = runner.invoke(cli.app, ["prompts", "template", "builder.md", "--locale", "en"])
    assert template_result.exit_code == 0, template_result.stdout
    assert "version: 1" in template_result.stdout

    validate_result = runner.invoke(cli.app, ["prompts", "validate", str(prompt_path), "--archetype", "builder"])
    assert validate_result.exit_code == 0, validate_result.stdout
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is True
    assert payload["metadata"]["archetype"] == "builder"

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    home_prompt_path = home_dir / "prompt.md"
    home_prompt_path.write_text("---\nversion: 1\narchetype: builder\n---\nHome prompt body.\n", encoding="utf-8")
    validate_home_result = runner.invoke(
        cli.app,
        ["prompts", "validate", "~/prompt.md", "--archetype", "builder"],
        env={"HOME": str(home_dir)},
    )
    assert validate_home_result.exit_code == 0, validate_home_result.stdout
    assert json.loads(validate_home_result.stdout)["body"] == "Home prompt body."

    invalid_prompt_path = tmp_path / "invalid-prompt.md"
    invalid_prompt_path.write_bytes(b"\xff")
    invalid_result = runner.invoke(cli.app, ["prompts", "validate", str(invalid_prompt_path)])
    _assert_prompt_file_input_recovery(
        invalid_result,
        validation_error="prompt file must be UTF-8 encoded Markdown",
    )
    missing_prompt_path = tmp_path / "missing-prompt.md"
    missing_result = runner.invoke(cli.app, ["prompts", "validate", str(missing_prompt_path)])
    _assert_prompt_file_input_recovery(
        missing_result,
        validation_error="prompt file does not exist",
        hidden_text=str(missing_prompt_path),
    )
    prompt_dir = tmp_path / "prompt-dir"
    prompt_dir.mkdir()
    directory_result = runner.invoke(cli.app, ["prompts", "validate", str(prompt_dir)])
    _assert_prompt_file_input_recovery(
        directory_result,
        validation_error="prompt file could not be read",
        hidden_text=str(prompt_dir),
    )


def test_cli_prompts_list_json_errors_are_structured(monkeypatch) -> None:
    def fail_list():
        raise StrategySourceError("prompt catalog unavailable")

    monkeypatch.setattr(cli_prompt_commands, "available_strategy_prompt_templates", fail_list)

    result = CliRunner().invoke(cli.app, ["prompts", "list"])

    _assert_json_error(result, "prompt catalog unavailable")
