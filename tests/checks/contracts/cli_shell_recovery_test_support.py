from __future__ import annotations

import json
import socket
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION


SHELL_RECOVERY_EXIT_CODE = 2
PLAN_SLASH_NEXT_ACTION_KINDS = [
    "check_fit_first",
    "web_creation_path",
    "install_first",
    "if_missing_in_agent",
    "readiness_check",
    "next_step",
    "debug_cli",
]
RUN_SLASH_NEXT_ACTION_KINDS = [
    *PLAN_SLASH_NEXT_ACTION_KINDS[:5],
    "plan_first",
    *PLAN_SLASH_NEXT_ACTION_KINDS[5:],
]


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def create_future_app_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")


def app_db_table_names(path: Path) -> set[str]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {str(row[0]) for row in rows}


def assert_future_app_db_cli_recovery(result) -> None:
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["loop_recovery"] == "use_matching_loopora_version_or_reset"
    assert payload["status"] == "blocked_by_app_state"
    assert payload["app_state_status"] == "future_version"
    expected_actions = [
        "use_matching_loopora_version_or_reset",
        "inspect_app_state",
        "create_recovery_archive",
        "preview_app_database_reset",
    ]
    assert payload["app_state_recovery_summary"]["next_action_kinds"] == expected_actions
    assert payload["next_action_ready_now_kinds"] == expected_actions[:2]
    assert payload["app_state_recovery_summary"]["next_action_ready_after_actions"] == {
        "create_recovery_archive": "inspect_app_state",
        "preview_app_database_reset": "create_recovery_archive",
    }
    assert "matching or newer Loopora version" in payload["summary"]
    assert "Traceback" not in result.output
    assert result.stderr == ""


def public_confirm_readiness_summary(payload: dict) -> str:
    assert [item["kind"] for item in payload["next_action_summaries"]] == payload["next_actions"]
    assert payload["diagnose_doctor_public_summary"]["next_action_summaries"] == payload["next_action_summaries"]
    for item in payload["next_action_summaries"]:
        if item["kind"] == "confirm_readiness":
            return str(item["summary"])
    raise AssertionError("public doctor payload did not include confirm_readiness summary")


def public_readiness_axis(payload: dict, axis: str) -> dict:
    for item in payload["readiness_axes"]:
        if item["axis"] == axis:
            return item
    raise AssertionError(f"public doctor payload did not include {axis} readiness axis")


def public_readiness_axis_state(payload: dict, axis: str) -> tuple[object, object, object]:
    item = public_readiness_axis(payload, axis)
    return item["status"], item["ready"], item["needs_attention"]


def assert_public_workdir_confirm_summary(payload: dict, *, prerequisite: str) -> None:
    summary = public_confirm_readiness_summary(payload)
    assert prerequisite in summary
    assert "read-only readiness check" in summary
    assert "before returning to the Agent" not in summary


def assert_adapter_choice_text(text: str, command_template: str) -> None:
    assert all(command_template.format(adapter=adapter) in text for adapter in ("codex", "claude", "opencode"))


def assert_adapter_choice_payload(payload: dict, key: str, command_template: str) -> None:
    choices = payload[f"{key}_adapter_choices"]
    assert [choice["adapter"] for choice in choices] == ["codex", "claude", "opencode"]
    assert all(command_template.format(adapter=choice["adapter"]) in choice["command"] for choice in choices)


def assert_summary_fields_match(payload: dict, *keys: str) -> None:
    summary = payload["slash_command_recovery_summary"]
    assert all(summary[key] == payload[key] for key in keys)


def web_creation_command_fragment(workdir_arg: str) -> str:
    return f"loopora serve --open --workdir {workdir_arg} --host 127.0.0.1 --port 8742"


def assert_web_creation_path_text(text: str, workdir_arg: str = '"$PWD"') -> None:
    assert "Fit Guide/Web choices:" in text
    assert web_creation_command_fragment(workdir_arg) in text
    assert "outside an Agent session" in text
    assert "these Web paths do not require a same-Agent project entry or doctor check" in text


def assert_web_creation_path_payload(payload: dict, workdir_arg: str, *, action_index: int | None = None) -> None:
    assert payload["web_creation_path"].endswith(web_creation_command_fragment(workdir_arg))
    assert "outside an Agent session" in payload["web_creation_path_note"]
    assert payload["slash_command_recovery_summary"]["web_creation_path"] == payload["web_creation_path"]
    if action_index is not None:
        assert payload["next_actions"][action_index]["note"] == payload["web_creation_path_note"]


def assert_slash_next_actions_summary(payload: dict, expected: list[str]) -> None:
    kinds = [item["kind"] for item in payload["next_actions"]]
    summary = payload["slash_command_recovery_summary"]
    assert summary["next_action_kinds"] == payload["next_action_kinds"] == kinds == expected
    assert summary["next_action_ready_now_kinds"] == payload["next_action_ready_now_kinds"] == expected
    assert summary["next_action_ready_after_actions"] == payload["next_action_ready_after_actions"] == {}


def assert_plan_first_task_handoff_payload(payload: dict) -> None:
    assert payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert payload["first_task_message_example_state"]["copy_allowed"] is False
    assert payload["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert payload["first_task_handoff_policy"]["fit_command"].endswith('loopora fit --workdir "$PWD"')


def assert_plan_slash_shell_recovery(runner: CliRunner) -> None:
    plan_result = runner.invoke(cli.app, ["/loopora-plan"])
    assert plan_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in plan_result.output
    assert "slash command recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_result.stdout
    assert "check fit first:" in plan_result.stdout
    assert 'loopora fit --workdir "$PWD"' in plan_result.stdout
    assert_web_creation_path_text(plan_result.stdout)
    assert_adapter_choice_text(plan_result.stdout, 'loopora init {adapter} --workdir "$PWD"')
    assert_adapter_choice_text(plan_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')
    assert 'loopora init --workdir "$PWD"' not in plan_result.stdout
    assert 'loopora agent --workdir "$PWD"' not in plan_result.stdout
    assert "readiness check:" in plan_result.stdout
    assert 'loopora doctor --workdir "$PWD"' in plan_result.stdout
    assert plan_result.stdout.index("check fit first") < plan_result.stdout.index("Fit Guide/Web choices") < plan_result.stdout.index("install first")
    assert "refresh or restart that Agent" in plan_result.stdout
    assert "return to that Agent" in plan_result.stdout
    assert "first task message handoff:" in plan_result.stdout
    assert "completed fit review:" in plan_result.stdout
    assert "generic orientation example (not a completed review):" in plan_result.stdout
    assert plan_result.stdout.index("completed fit review:") < plan_result.stdout.index("generic orientation example")
    assert "Goal:" in plan_result.stdout
    assert "Fake-done risks:" in plan_result.stdout
    assert "Required evidence:" in plan_result.stdout

    plan_help_result = runner.invoke(cli.app, ["/loopora-plan", "--help"])
    assert plan_help_result.exit_code == 0
    assert "Usage: " not in plan_help_result.stdout
    assert "slash command recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_help_result.stdout
    assert "debug CLI:" in plan_help_result.stdout
    assert_adapter_choice_text(plan_help_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')

    plan_without_slash_result = runner.invoke(cli.app, ["loopora-plan"])
    assert plan_without_slash_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in plan_without_slash_result.output
    assert "slash command recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_without_slash_result.stdout

    plan_json_result = runner.invoke(cli.app, ["/loopora-plan", "--json"])
    assert plan_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    plan_payload = json.loads(plan_json_result.stdout)
    assert next(iter(plan_payload)) == "slash_command_recovery_summary"
    assert plan_payload["slash_command_recovery_summary"]["slash_command_recovery"] == "agent_slash_command_in_shell"
    assert plan_payload["slash_command"] == "/loopora-plan"
    assert (plan_payload["agent_command"], plan_payload["shell_subcommand"]) == (True, False)
    assert_slash_next_actions_summary(plan_payload, PLAN_SLASH_NEXT_ACTION_KINDS)
    assert plan_payload["slash_command_recovery_summary"]["check_fit_first"].endswith('loopora fit --workdir "$PWD"')
    assert plan_payload["check_fit_first"].endswith('loopora fit --workdir "$PWD"')
    assert_web_creation_path_payload(plan_payload, '"$PWD"')
    assert plan_payload["slash_command_recovery_summary"]["readiness_check"].endswith('loopora doctor --workdir "$PWD"')
    assert plan_payload["readiness_check"].endswith('loopora doctor --workdir "$PWD"')
    assert_plan_first_task_handoff_payload(plan_payload)
    assert_summary_fields_match(
        plan_payload,
        "first_task_message_example_state",
        "first_task_handoff_policy",
        "install_first_adapter_choices",
        "if_missing_in_agent_adapter_choices",
        "debug_cli_adapter_choices",
    )
    assert plan_payload["debug_cli"].endswith('loopora agent --workdir "$PWD"')
    assert_adapter_choice_payload(plan_payload, "debug_cli", 'loopora agent {adapter} check --workdir "$PWD"')


def assert_run_slash_shell_recovery(runner: CliRunner) -> None:
    run_result = runner.invoke(cli.app, ["/loopora-run"])
    assert run_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in run_result.output
    assert "slash command recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_result.stdout
    assert "check fit first:" in run_result.stdout
    assert 'loopora fit --workdir "$PWD"' in run_result.stdout
    assert_web_creation_path_text(run_result.stdout)
    assert_adapter_choice_text(run_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')
    assert 'loopora agent --workdir "$PWD"' not in run_result.stdout
    assert "readiness check:" in run_result.stdout
    assert 'loopora doctor --workdir "$PWD"' in run_result.stdout
    assert "plan first: run /loopora-plan inside the Agent" in run_result.stdout
    assert run_result.stdout.index("check fit first") < run_result.stdout.index("Fit Guide/Web choices")
    assert run_result.stdout.index("Fit Guide/Web choices") < run_result.stdout.index("choose or check same-Agent project entry")
    assert run_result.stdout.index("readiness check") < run_result.stdout.index("plan first")
    assert run_result.stdout.index("plan first") < run_result.stdout.index("next step")
    assert "same Agent session" in run_result.stdout
    assert_adapter_choice_text(run_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')

    run_help_result = runner.invoke(cli.app, ["/loopora-run", "--help"])
    assert run_help_result.exit_code == 0
    assert "Usage: " not in run_help_result.stdout
    assert "slash command recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_help_result.stdout
    assert_adapter_choice_text(run_help_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')

    run_without_slash_result = runner.invoke(cli.app, ["loopora-run"])
    assert run_without_slash_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in run_without_slash_result.output
    assert "slash command recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_without_slash_result.stdout

    run_json_result = runner.invoke(cli.app, ["loopora-run", "--json"])
    assert run_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    run_payload = json.loads(run_json_result.stdout)
    assert next(iter(run_payload)) == "slash_command_recovery_summary"
    assert run_payload["slash_command_recovery_summary"]["slash_command_recovery"] == "agent_slash_command_in_shell"
    assert run_payload["slash_command"] == "/loopora-run"
    assert_slash_next_actions_summary(run_payload, RUN_SLASH_NEXT_ACTION_KINDS)
    assert run_payload["slash_command_recovery_summary"]["check_fit_first"].endswith('loopora fit --workdir "$PWD"')
    assert_web_creation_path_payload(run_payload, '"$PWD"', action_index=1)
    assert run_payload["slash_command_recovery_summary"]["readiness_check"].endswith('loopora doctor --workdir "$PWD"')
    assert "READY preview" in run_payload["slash_command_recovery_summary"]["plan_first"]
    assert run_payload["plan_first"] == run_payload["slash_command_recovery_summary"]["plan_first"]
    assert run_payload["slash_command_recovery_summary"]["debug_cli_adapter_choices"] == run_payload["debug_cli_adapter_choices"]
    assert run_payload["next_step"].startswith("run /loopora-run inside the same Agent session")
    assert run_payload["debug_cli"].endswith('loopora agent --workdir "$PWD"')
    assert_adapter_choice_payload(run_payload, "debug_cli", 'loopora agent {adapter} check --workdir "$PWD"')


def assert_next_slash_shell_recovery(runner: CliRunner) -> None:
    next_result = runner.invoke(cli.app, ["/next"])
    assert next_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert "No such command" not in next_result.output
    assert "Loopora does not install a top-level /next slash command" in next_result.stdout
    assert "use /loopora-run inside the Agent" in next_result.stdout
    assert_adapter_choice_text(next_result.stdout, 'loopora agent {adapter} check --workdir "$PWD"')
    assert 'loopora agent --workdir "$PWD"' not in next_result.stdout

    next_json_result = runner.invoke(cli.app, ["/next", "--json"])
    assert next_json_result.exit_code == SHELL_RECOVERY_EXIT_CODE
    next_payload = json.loads(next_json_result.stdout)
    assert next_payload["slash_command_recovery"] == "unsupported_loopora_slash_command"
    assert next_payload["slash_command"] == "/next"
    assert_slash_next_actions_summary(next_payload, ["next_step", "debug_cli"])
