from __future__ import annotations

import json

from typer.testing import CliRunner

from loopora import cli


SHELL_RECOVERY_EXIT_CODE = 2


def _assert_plan_slash_shell_recovery(runner: CliRunner) -> None:
    plan_result = runner.invoke(cli.app, ["/loopora-plan"])
    assert plan_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in plan_result.output
    assert "slash_command_recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_result.stdout
    assert 'loopora init codex --workdir "$PWD"' in plan_result.stdout
    assert 'loopora init codex --workdir "$PWD" --check' in plan_result.stdout
    assert "refresh or restart that Agent" in plan_result.stdout
    assert "return to that Agent" in plan_result.stdout
    assert "first_task_message_example:" in plan_result.stdout
    assert "Goal:" in plan_result.stdout
    assert "Fake-done risks:" in plan_result.stdout
    assert "Required evidence:" in plan_result.stdout

    plan_help_result = runner.invoke(cli.app, ["/loopora-plan", "--help"])
    assert plan_help_result.exit_code == 0
    assert "Usage: " not in plan_help_result.stdout
    assert "slash_command_recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_help_result.stdout
    assert "debug_cli: loopora agent codex plan" in plan_help_result.stdout

    plan_without_slash_result = runner.invoke(cli.app, ["loopora-plan"])
    assert plan_without_slash_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in plan_without_slash_result.output
    assert "slash_command_recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_without_slash_result.stdout

    plan_json_result = runner.invoke(cli.app, ["/loopora-plan", "--json"])
    assert plan_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    plan_payload = json.loads(plan_json_result.stdout)
    assert next(iter(plan_payload)) == "slash_command_recovery_summary"
    assert plan_payload["slash_command_recovery_summary"]["slash_command_recovery"] == "agent_slash_command_in_shell"
    assert plan_payload["slash_command"] == "/loopora-plan"
    assert plan_payload["agent_command"] is True
    assert plan_payload["shell_subcommand"] is False
    assert plan_payload["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    assert "loopora agent codex plan" in plan_payload["debug_cli"]


def _assert_run_slash_shell_recovery(runner: CliRunner) -> None:
    run_result = runner.invoke(cli.app, ["/loopora-run"])
    assert run_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in run_result.output
    assert "slash_command_recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_result.stdout
    assert 'loopora init codex --workdir "$PWD" --check' in run_result.stdout
    assert "same Agent session" in run_result.stdout
    assert 'loopora agent codex run --workdir "$PWD"' in run_result.stdout

    run_help_result = runner.invoke(cli.app, ["/loopora-run", "--help"])
    assert run_help_result.exit_code == 0
    assert "Usage: " not in run_help_result.stdout
    assert "slash_command_recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_help_result.stdout
    assert 'loopora agent codex run --workdir "$PWD"' in run_help_result.stdout

    run_without_slash_result = runner.invoke(cli.app, ["loopora-run"])
    assert run_without_slash_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in run_without_slash_result.output
    assert "slash_command_recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_without_slash_result.stdout

    run_json_result = runner.invoke(cli.app, ["loopora-run", "--json"])
    assert run_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    run_payload = json.loads(run_json_result.stdout)
    assert next(iter(run_payload)) == "slash_command_recovery_summary"
    assert run_payload["slash_command_recovery_summary"]["slash_command_recovery"] == "agent_slash_command_in_shell"
    assert run_payload["slash_command"] == "/loopora-run"
    assert run_payload["next_step"].startswith("run /loopora-run inside the same Agent session")
    assert "loopora agent codex run" in run_payload["debug_cli"]


def _assert_next_slash_shell_recovery(runner: CliRunner) -> None:
    next_result = runner.invoke(cli.app, ["/next"])
    assert next_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in next_result.output
    assert "Loopora does not install a top-level /next slash command" in next_result.stdout
    assert "use /loopora-run inside the Agent" in next_result.stdout
    assert 'loopora agent codex next --workdir "$PWD" --run-id <run_id>' in next_result.stdout

    next_json_result = runner.invoke(cli.app, ["/next", "--json"])
    assert next_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    next_payload = json.loads(next_json_result.stdout)
    assert next_payload["slash_command_recovery"] == "unsupported_loopora_slash_command"
    assert next_payload["slash_command"] == "/next"


def test_cli_recovers_when_agent_slash_command_is_typed_in_shell() -> None:
    runner = CliRunner()
    _assert_plan_slash_shell_recovery(runner)
    _assert_run_slash_shell_recovery(runner)
    _assert_next_slash_shell_recovery(runner)
