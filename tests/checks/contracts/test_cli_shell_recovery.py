from __future__ import annotations

import json
import shlex
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli
from loopora.branding import APP_HOME_ENV
from loopora.cli_first_task_handoff import first_task_handoff_lines
from loopora.diagnose_doctor import doctor_public_json_payload

from cli_bundle_commands_test_support import write_cli_bundle
from cli_shell_recovery_test_support import (
    RUN_SLASH_NEXT_ACTION_KINDS,
    SHELL_RECOVERY_EXIT_CODE,
    app_db_table_names,
    assert_adapter_choice_payload,
    assert_future_app_db_cli_recovery,
    assert_next_slash_shell_recovery,
    assert_plan_slash_shell_recovery,
    assert_public_workdir_confirm_summary,
    assert_run_slash_shell_recovery,
    assert_slash_next_actions_summary,
    assert_web_creation_path_payload,
    create_future_app_db,
    free_local_port,
    public_readiness_axis,
    public_readiness_axis_state,
)


ROOT = Path(__file__).resolve().parents[3]
DEV_CHECK_GUIDE_CATALOG_FILES = (
    "dev_check_guides.py",
    "dev_check_guide_first_use.py",
    "dev_check_guide_open_source.py",
)


def _dev_check_guide_catalog_source() -> str:
    return "\n".join((ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8") for filename in DEV_CHECK_GUIDE_CATALOG_FILES)


def test_cli_first_task_handoff_lines_are_canonical_and_transformable() -> None:
    payload = {
        "first_task_message_example": "/loopora-plan\n\nLoopora fit: ...",
        "first_task_handoff_blockers": ["same_agent_entry_required"],
        "first_task_handoff_policy": {
            "copy_rule": "If you completed loopora fit, paste its copyable /loopora-plan handoff as one Agent message.",
        },
    }

    lines = first_task_handoff_lines(
        payload,
        copy_rule_transform=lambda _policy, rule: rule.replace("loopora fit", "uv run loopora fit"),
    )

    assert lines == [
        "first task message handoff:",
        "- preview only: /loopora-plan handoff is not ready yet; first resolve: same-Agent project entry.",
        "- completed fit review: If you completed uv run loopora fit, paste its copyable /loopora-plan handoff as one Agent message.",
        "- generic orientation example (not a completed review):",
        "/loopora-plan\n\nLoopora fit: ...",
    ]
    assert first_task_handoff_lines({"first_task_message_example": ""}) == []


def test_doctor_next_action_projection_has_dedicated_boundary() -> None:
    doctor_source = (ROOT / "src" / "loopora" / "diagnose_doctor.py").read_text(encoding="utf-8")
    action_source = (ROOT / "src" / "loopora" / "diagnose_doctor_actions.py").read_text(encoding="utf-8")
    workdir_source = (ROOT / "src" / "loopora" / "diagnose_doctor_workdir_state.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.diagnose_doctor_actions import" in doctor_source
    assert "from loopora.diagnose_doctor_workdir_state import" in doctor_source
    assert "def _next_action_items" not in doctor_source
    assert "def _workdir_state" not in doctor_source
    assert "def _agent_entry_blocked_by_workdir" not in doctor_source
    assert "def doctor_next_action_items" in action_source
    assert "def _web_start_action" in action_source
    assert "def doctor_workdir_state" in workdir_source
    assert "def agent_entry_blocked_by_workdir" in workdir_source
    assert "src/loopora/diagnose_doctor*.py" in dev_check_guides
    assert "diagnose_doctor_actions.py" in service_boundaries
    assert "diagnose_doctor_workdir_state.py" in service_boundaries


def test_public_doctor_action_taxonomy_has_dedicated_boundary() -> None:
    public_source = (ROOT / "src" / "loopora" / "diagnose_doctor_public.py").read_text(encoding="utf-8")
    actions_source = (ROOT / "src" / "loopora" / "diagnose_doctor_public_actions.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.diagnose_doctor_public_actions import" in public_source
    assert "def public_next_actions" in actions_source
    assert "def public_readiness_axes" in actions_source
    assert "def _public_next_actions" not in public_source
    assert "src/loopora/diagnose_doctor_public*.py" in dev_check_guides
    assert "diagnose_doctor_public_actions.py" in service_boundaries


def test_doctor_terminal_output_has_dedicated_section_boundaries() -> None:
    output_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_output.py").read_text(encoding="utf-8")
    summary_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_summary_output.py").read_text(encoding="utf-8")
    app_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_app_output.py").read_text(encoding="utf-8")
    web_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_web_output.py").read_text(encoding="utf-8")
    entries_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_entries_output.py").read_text(encoding="utf-8")
    next_steps_source = (ROOT / "src" / "loopora" / "cli_diagnose_doctor_next_steps_output.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.cli_diagnose_doctor_summary_output import" in output_source
    assert "from loopora.cli_diagnose_doctor_app_output import print_doctor_app_state" in output_source
    assert "from loopora.cli_diagnose_doctor_web_output import print_doctor_web" in output_source
    assert "from loopora.cli_diagnose_doctor_entries_output import print_doctor_entries" in output_source
    assert "from loopora.cli_diagnose_doctor_next_steps_output import print_doctor_next_steps" in output_source
    for marker in (
        "def _doctor_readiness_summary",
        "def _print_doctor_web_unavailable",
        "def _doctor_entry_detail",
        "def _doctor_action_adapter_choices",
    ):
        assert marker not in output_source
    assert "def _doctor_readiness_summary" in summary_source
    assert "def print_doctor_app_state" in app_source
    assert "def _print_doctor_web_unavailable" in web_source
    assert "def _doctor_entry_detail" in entries_source
    assert "def _doctor_action_adapter_choices" in next_steps_source
    assert "src/loopora/cli_diagnose_doctor*_output.py" in dev_check_guides
    for filename in (
        "cli_diagnose_doctor_summary_output.py",
        "cli_diagnose_doctor_app_output.py",
        "cli_diagnose_doctor_web_output.py",
        "cli_diagnose_doctor_entries_output.py",
        "cli_diagnose_doctor_next_steps_output.py",
    ):
        assert filename in service_boundaries


def test_support_issue_routes_have_dedicated_boundary() -> None:
    support_source = (ROOT / "src" / "loopora" / "support_guidance.py").read_text(encoding="utf-8")
    action_source = (ROOT / "src" / "loopora" / "support_guidance_actions.py").read_text(encoding="utf-8")
    routes_source = (ROOT / "src" / "loopora" / "support_guidance_routes.py").read_text(encoding="utf-8")
    output_source = (ROOT / "src" / "loopora" / "support_guidance_output.py").read_text(encoding="utf-8")
    text_source = (ROOT / "src" / "loopora" / "support_guidance_text.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.support_guidance_routes import support_issue_routes" in support_source
    assert "from loopora.support_guidance_routes import support_issue_route_actions" in action_source
    assert "from loopora.support_guidance_text import" in support_source
    assert "from loopora.support_guidance_text import" in output_source
    assert "def support_issue_routes" in routes_source
    assert "def support_posting_guidance_text" in text_source
    assert "def support_target_project_status_label" in text_source
    assert "def _support_issue_routes" not in action_source
    assert "def support_posting_guidance_text" not in support_source
    assert "src/loopora/support_guidance*.py" in dev_check_guides
    assert "support_guidance_routes.py" in service_boundaries
    assert "support_guidance_text.py" in service_boundaries


def test_fit_web_route_preflight_has_dedicated_boundary() -> None:
    fit_actions_source = (ROOT / "src" / "loopora" / "fit_guidance_actions.py").read_text(encoding="utf-8")
    web_route_source = (ROOT / "src" / "loopora" / "fit_guidance_web_route.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "_fit_web_route_context = _fit_web_route.fit_web_route_context" in fit_actions_source
    assert "def _fit_web_route_context" not in fit_actions_source
    assert "def fit_web_route_context" in web_route_source
    assert "def fit_web_route_action" in web_route_source
    assert "src/loopora/fit_guidance*.py" in dev_check_guides
    assert "fit_guidance_web_route.py" in service_boundaries


def test_fit_workdir_recovery_has_dedicated_boundary() -> None:
    fit_source = (ROOT / "src" / "loopora" / "fit_guidance.py").read_text(encoding="utf-8")
    projection_source = (ROOT / "src" / "loopora" / "fit_guidance_projection.py").read_text(encoding="utf-8")
    action_source = (ROOT / "src" / "loopora" / "fit_guidance_actions.py").read_text(encoding="utf-8")
    workdir_source = (ROOT / "src" / "loopora" / "fit_guidance_workdir_actions.py").read_text(encoding="utf-8")
    dev_check_guides = _dev_check_guide_catalog_source()
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.fit_guidance_workdir_actions import" in fit_source
    assert "from loopora.fit_guidance_workdir_actions import" in projection_source
    assert "def _fit_workdir_recovery_actions" in workdir_source
    assert "def _fit_setup_command_blockers" in workdir_source
    assert "def _fit_workdir_recovery_actions" not in action_source
    assert "def _fit_choose_workdir_action" not in action_source
    assert "src/loopora/fit_guidance*.py" in dev_check_guides
    assert "fit_guidance_workdir_actions.py" in service_boundaries


def test_cli_recovers_when_agent_slash_command_is_typed_in_shell() -> None:
    runner = CliRunner()
    assert_plan_slash_shell_recovery(runner)
    assert_run_slash_shell_recovery(runner)
    assert_next_slash_shell_recovery(runner)


def test_cli_agent_slash_recovery_preserves_explicit_workdir(tmp_path: Path) -> None:
    runner = CliRunner()
    ready_workdir = tmp_path / "ready project"
    missing_workdir = tmp_path / "missing project"
    ready_workdir.mkdir()
    ready_arg = shlex.quote(str(ready_workdir.resolve()))
    missing_arg = shlex.quote(str(missing_workdir.resolve()))

    plan = runner.invoke(cli.app, ["/loopora-plan", "--workdir", str(ready_workdir), "--json"])
    run = runner.invoke(cli.app, ["/loopora-run", "--workdir", str(missing_workdir), "--json"])

    assert plan.exit_code == SHELL_RECOVERY_EXIT_CODE, plan.output
    plan_payload = json.loads(plan.stdout)
    assert (
        plan_payload["workdir"],
        plan_payload["workdir_state"]["status"],
        plan_payload["slash_command_recovery_summary"]["workdir"],
    ) == (str(ready_workdir.resolve()), "ready", str(ready_workdir.resolve()))
    assert plan_payload["check_fit_first"].endswith(f"loopora fit --workdir {ready_arg}")
    assert_web_creation_path_payload(plan_payload, ready_arg)
    assert plan_payload["first_task_handoff_policy"]["fit_command"].endswith(f"loopora fit --workdir {ready_arg}")
    assert plan_payload["install_first"].endswith(f"loopora init --workdir {ready_arg}")
    assert_adapter_choice_payload(plan_payload, "install_first", f"loopora init {{adapter}} --workdir {ready_arg}")
    assert all(" # " not in str(plan_payload[key]) for key in ("check_fit_first", "install_first", "if_missing_in_agent", "debug_cli"))
    assert plan_payload["readiness_check"].endswith(f"loopora doctor --workdir {ready_arg}")
    assert plan_payload["if_missing_in_agent"].endswith(f"loopora agent --workdir {ready_arg}")
    assert_adapter_choice_payload(plan_payload, "if_missing_in_agent", f"loopora agent {{adapter}} check --workdir {ready_arg}")
    assert plan_payload["debug_cli"].endswith(f"loopora agent --workdir {ready_arg}")
    assert 'loopora doctor --workdir "$PWD"' not in plan.stdout

    assert run.exit_code == SHELL_RECOVERY_EXIT_CODE, run.output
    assert not missing_workdir.exists()
    run_payload = json.loads(run.stdout)
    assert run_payload["workdir"] == str(missing_workdir.resolve())
    assert run_payload["workdir_state"]["status"] == "missing"
    assert run_payload["create_workdir"] == f"mkdir -p {missing_arg}"
    assert_slash_next_actions_summary(run_payload, ["create_workdir", *RUN_SLASH_NEXT_ACTION_KINDS])
    assert run_payload["check_fit_first"].endswith(f"loopora fit --workdir {missing_arg}")
    assert_web_creation_path_payload(run_payload, missing_arg)
    assert run_payload["slash_command_recovery_summary"]["create_workdir"] == run_payload["create_workdir"]
    assert run_payload["if_missing_in_agent"].endswith(f"loopora agent --workdir {missing_arg}")
    assert_adapter_choice_payload(run_payload, "if_missing_in_agent", f"loopora agent {{adapter}} check --workdir {missing_arg}")
    assert all(" # " not in str(run_payload[key]) for key in ("if_missing_in_agent", "readiness_check", "debug_cli"))
    assert run_payload["readiness_check"].endswith(f"loopora doctor --workdir {missing_arg}")
    assert run_payload["debug_cli"].endswith(f"loopora agent --workdir {missing_arg}")
    assert_adapter_choice_payload(run_payload, "debug_cli", f"loopora agent {{adapter}} check --workdir {missing_arg}")

    next_result = runner.invoke(cli.app, ["/next", "--workdir", str(missing_workdir), "--json"])
    assert next_result.exit_code == SHELL_RECOVERY_EXIT_CODE, next_result.output
    next_payload = json.loads(next_result.stdout)
    assert next_payload["slash_command_recovery"] == "unsupported_loopora_slash_command"
    assert next_payload["workdir_state"]["status"] == "missing"
    assert next_payload["create_workdir"] == f"mkdir -p {missing_arg}"
    assert next_payload["slash_command_recovery_summary"]["create_workdir"] == next_payload["create_workdir"]
    assert_slash_next_actions_summary(next_payload, ["create_workdir", "next_step", "debug_cli"])
    assert next_payload["debug_cli"].endswith(f"loopora agent --workdir {missing_arg}")
    assert_adapter_choice_payload(next_payload, "debug_cli", f"loopora agent {{adapter}} check --workdir {missing_arg}")
    assert "create_workdir" in next_payload["slash_command_recovery_summary"]


def test_cli_agent_slash_recovery_gates_unusable_workdir(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    bad_arg = shlex.quote(str(workdir_file.resolve()))

    plain = runner.invoke(cli.app, ["/loopora-plan", "--workdir", str(workdir_file)])
    structured = runner.invoke(cli.app, ["/loopora-run", "--workdir", str(workdir_file), "--json"])

    assert plain.exit_code == SHELL_RECOVERY_EXIT_CODE, plain.output
    assert "project directory state: not_directory" in plain.stdout
    assert "Choose an existing project directory" in plain.stdout
    assert f"--workdir {bad_arg}" not in plain.stdout
    assert "loopora doctor --workdir" not in plain.stdout
    assert "loopora serve --open --workdir" not in plain.stdout
    assert "debug CLI:" not in plain.stdout

    assert structured.exit_code == SHELL_RECOVERY_EXIT_CODE, structured.output
    payload = json.loads(structured.stdout)
    assert payload["workdir"] == str(workdir_file.resolve())
    assert payload["workdir_state"]["status"] == "not_directory"
    assert payload["choose_workdir"] == "Choose an existing project directory before managing Agent entries."
    assert payload["slash_command_recovery_summary"]["choose_workdir"] == payload["choose_workdir"]
    assert_slash_next_actions_summary(payload, ["choose_workdir", "check_fit_first", "plan_first", "next_step"])
    assert "web_creation_path" not in payload
    assert "readiness_check" not in payload
    assert "if_missing_in_agent" not in payload
    assert "debug_cli" not in payload
    assert f"--workdir {bad_arg}" not in structured.stdout


def test_cli_diagnose_doctor_reports_missing_workdir_as_read_only_next_action(tmp_path: Path) -> None:
    runner = CliRunner()
    missing_workdir = tmp_path / "missing project"
    web_port = free_local_port()

    json_result = runner.invoke(
        cli.app,
        ["doctor", "--workdir", str(missing_workdir), "--web-port", str(web_port), "--json"],
    )
    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(missing_workdir), "--web-port", str(web_port)])
    public = runner.invoke(
        cli.app,
        ["diagnose", "doctor", "--workdir", str(missing_workdir), "--web-port", str(web_port), "--public-json"],
    )

    assert json_result.exit_code == 1, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert payload["workdir"] == str(missing_workdir.resolve())
    assert payload["workdir_state"]["status"] == "missing"
    assert payload["workdir_state"]["usable_for_agent_entries"] is False
    assert payload["workdir_state"]["needs_attention"] is True
    assert payload["workdir_state"]["commands"]["create"] == f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}"
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "create_workdir",
        "confirm_readiness",
        "support",
    ]
    assert payload["next_action_items"][0]["command"] == payload["workdir_state"]["commands"]["create"]
    assert payload["agent_entries"][0]["install_state"] == "blocked_by_workdir"
    assert payload["agent_entries"][0]["next_action"] == "create_workdir"
    assert payload["next_action_items"][1]["after_action"] == "create_workdir"
    assert all(
        needle in payload["next_action_items"][index]["command"] for index, needle in ((1, "loopora doctor --workdir"), (2, "loopora support --workdir"))
    )
    assert "loopora init codex" not in json.dumps(payload["next_action_items"], ensure_ascii=False)

    assert plain.exit_code == 1, plain.stdout
    assert "Invalid value for '--workdir'" not in plain.output
    assert "project directory state: missing" in plain.stdout
    assert f"create directory: mkdir -p {shlex.quote(str(missing_workdir.resolve()))}" in plain.stdout
    assert "blocked by project directory: Codex (codex)" not in plain.stdout
    assert "waiting for a usable project directory" not in plain.stdout
    assert "next: create project directory" not in plain.stdout
    assert "blocked options: Codex, Claude Code, OpenCode" in plain.stdout
    assert "Create the target project directory" in plain.stdout
    assert "After creating the project directory, re-run doctor to continue readiness checks:" in plain.stdout
    assert "Confirm readiness before returning to Agent:" not in plain.stdout
    assert "recommended install:" not in plain.stdout
    assert "Install the recommended entry:" not in plain.stdout
    assert "loopora init codex" not in plain.stdout

    assert public.exit_code == 1, public.stdout
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["project_directory_status"] == "missing"
    assert public_payload["diagnose_doctor_public_summary"]["project_directory_status"] == "missing"
    assert public_payload["diagnose_doctor_public_summary"]["readiness_axes"] == public_payload["readiness_axes"]
    assert public_readiness_axis_state(public_payload, "project_directory") == ("missing", False, True)
    assert public_payload["next_actions"] == ["create_project_directory", "confirm_readiness", "support"]
    assert public_payload["agent_entries"][0]["install_state"] == "blocked_by_project_directory"
    assert public_payload["agent_entries"][0]["next_action"] == "create_project_directory"
    assert "install_agent_entry" not in public_payload["next_actions"]
    assert_public_workdir_confirm_summary(public_payload, prerequisite="After creating the project directory")
    assert str(missing_workdir) not in public_encoded
    assert "workdir" not in public_encoded
    assert "mkdir" not in public_encoded
    assert "commands" not in public_encoded


def test_doctor_public_report_readiness_axes_summarize_major_blockers_without_repair_commands() -> None:
    payload = doctor_public_json_payload(
        {
            "schema_version": 2,
            "status": "not_ready",
            "ready": False,
            "agent_entry_ready": False,
            "strict_ready": False,
            "package": {},
            "app_state": {"status": "development_reset_required", "web_ready": False, "needs_attention": True},
            "web": {
                "start_available": True,
                "readiness_blockers": [
                    {
                        "kind": "app_state_not_ready",
                        "status": "development_reset_required",
                        "recovery_action": "preview_app_database_reset",
                    }
                ],
                "recovery_action": "preview_app_database_reset",
            },
            "workdir_state": {"status": "ready"},
            "agent_entries": [{"adapter": "codex", "ready": False, "next_action": "install_agent_entry"}],
            "first_task_handoff_executable": False,
            "first_task_handoff_blockers": ["same_agent_entry_required", "app_state_not_ready"],
            "next_action_items": [],
        }
    )

    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["diagnose_doctor_public_summary"]["readiness_axes"] == payload["readiness_axes"]
    assert public_readiness_axis_state(payload, "app_state") == ("development_reset_required", False, True)
    assert public_readiness_axis(payload, "web_start") == {
        "axis": "web_start",
        "status": "blocked",
        "ready": False,
        "blockers": ["app_state_not_ready"],
        "recovery_actions": ["preview_app_database_reset"],
        "recovery_action": "preview_app_database_reset",
    }
    first_task_axis = public_readiness_axis(payload, "first_task_handoff")
    assert first_task_axis["blockers"] == ["same_agent_entry_required", "app_state_not_ready"]
    assert "commands" not in encoded
    assert "loopora doctor" not in encoded


def test_doctor_public_report_projects_future_app_state_recovery() -> None:
    payload = doctor_public_json_payload(
        {
            "schema_version": 2,
            "status": "not_ready",
            "ready": False,
            "agent_entry_ready": False,
            "strict_ready": False,
            "package": {},
            "app_state": {
                "status": "future_version",
                "web_ready": False,
                "needs_attention": True,
                "next_action": "use_matching_loopora_version_or_reset",
            },
            "web": {
                "start_available": True,
                "readiness_blockers": [
                    {
                        "kind": "app_state_not_ready",
                        "status": "future_version",
                        "recovery_action": "use_matching_loopora_version_or_reset",
                    }
                ],
                "recovery_action": "use_matching_loopora_version_or_reset",
            },
            "workdir_state": {"status": "ready"},
            "agent_entries": [{"adapter": "codex", "ready": False, "next_action": "install_agent_entry"}],
            "first_task_handoff_executable": False,
            "first_task_handoff_blockers": ["same_agent_entry_required", "app_state_not_ready"],
            "next_action_items": [{"kind": "install_agent_entry"}, {"kind": "preview_app_database_reset"}, {"kind": "confirm_readiness"}],
        }
    )

    assert payload["next_actions"] == ["install_agent_entry", "use_matching_loopora_version_or_reset", "confirm_readiness"]
    assert "preview_app_database_reset" not in payload["next_actions"]
    assert "matching or newer Loopora version" in json.dumps(payload["next_action_summaries"], ensure_ascii=False)
    assert public_readiness_axis(payload, "web_start")["recovery_action"] == "use_matching_loopora_version_or_reset"


def test_direct_loop_commands_reject_future_app_db_before_writes(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    app_db = tmp_path / "loopora-home" / "app.db"
    workdir = tmp_path / "project"
    spec = tmp_path / "spec.md"
    workdir.mkdir()
    spec.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    create_future_app_db(app_db)
    monkeypatch.setenv(APP_HOME_ENV, str(app_db.parent))

    for args in (
        ["loops", "create", "--spec", str(spec), "--workdir", str(workdir), "--json"],
        ["run", "--spec", str(spec), "--workdir", str(workdir), "--json", "--background"],
    ):
        result = runner.invoke(cli.app, args)
        assert_future_app_db_cli_recovery(result)

    assert "loop_definitions" not in app_db_table_names(app_db)


def test_json_artifact_resource_mutations_reject_future_app_db_before_writes(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    app_db = tmp_path / "loopora-home" / "app.db"
    prompt = tmp_path / "builder.md"
    bundle = tmp_path / "bundle.yml"
    workdir = tmp_path / "project"
    workdir.mkdir()
    prompt.write_text("---\nversion: 1\narchetype: builder\n---\nBuilder body\n", encoding="utf-8")
    write_cli_bundle(bundle, workdir)
    create_future_app_db(app_db)
    monkeypatch.setenv(APP_HOME_ENV, str(app_db.parent))

    for args in (
        ["roles", "create", "--name", "New Builder", "--prompt-file", str(prompt)],
        ["orchestrations", "create", "--name", "Custom"],
        ["bundles", "import", str(bundle)],
    ):
        result = runner.invoke(cli.app, args)
        assert_future_app_db_cli_recovery(result)

    assert not (app_db_table_names(app_db) & {"role_definitions", "orchestrations", "bundle_definitions"})


def test_cli_diagnose_doctor_rejects_file_workdir_before_install_guidance(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")

    json_result = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir_file), "--json"])
    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir_file)])
    public = runner.invoke(cli.app, ["doctor", "--workdir", str(workdir_file), "--public-json"])

    assert json_result.exit_code == 1, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert payload["workdir_state"]["status"] == "not_directory"
    assert payload["workdir_state"]["usable_for_agent_entries"] is False
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "choose_workdir",
        "confirm_readiness",
        "support",
    ]
    assert payload["agent_entries"][0]["install_state"] == "blocked_by_workdir"
    assert payload["agent_entries"][0]["next_action"] == "choose_workdir"
    assert payload["next_action_items"][1]["after_action"] == "choose_workdir"
    assert "command" not in payload["next_action_items"][1]
    assert "loopora support --workdir" in payload["next_action_items"][2]["command"]
    assert "loopora init codex" not in json.dumps(payload["next_action_items"], ensure_ascii=False)

    assert plain.exit_code == 1, plain.stdout
    assert "project directory state: not_directory" in plain.stdout
    assert "blocked by project directory: Codex (codex)" not in plain.stdout
    assert "waiting for a usable project directory" not in plain.stdout
    assert "next: choose project directory" not in plain.stdout
    assert "blocked options: Codex, Claude Code, OpenCode" in plain.stdout
    assert "Choose a project directory path" in plain.stdout
    assert "After choosing a usable project directory, re-run doctor to continue readiness checks." in plain.stdout
    assert "Confirm readiness before returning to Agent." not in plain.stdout
    assert "recommended install:" not in plain.stdout
    assert "Install the recommended entry:" not in plain.stdout
    assert "loopora init codex" not in plain.stdout

    assert public.exit_code == 1, public.stdout
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["project_directory_status"] == "not_directory"
    assert public_payload["next_actions"] == ["choose_project_directory", "confirm_readiness", "support"]
    assert public_payload["agent_entries"][0]["install_state"] == "blocked_by_project_directory"
    assert public_payload["agent_entries"][0]["next_action"] == "choose_project_directory"
    assert "install_agent_entry" not in public_payload["next_actions"]
    assert_public_workdir_confirm_summary(public_payload, prerequisite="After choosing a usable project directory")
    assert str(workdir_file) not in public_encoded
    assert "workdir" not in public_encoded
    assert "commands" not in public_encoded
    assert workdir_file.read_text(encoding="utf-8") == "not a directory\n"


def test_cli_diagnose_doctor_redacts_uninspectable_workdir_before_install_guidance(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    blocked_workdir = tmp_path / "blocked-project"
    private_path = tmp_path / "private" / "blocked-project"
    blocked_resolved = blocked_workdir.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {private_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    json_result = runner.invoke(cli.app, ["doctor", "--workdir", str(blocked_workdir), "--json"])
    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(blocked_workdir)])
    public = runner.invoke(cli.app, ["doctor", "--workdir", str(blocked_workdir), "--public-json"])

    assert json_result.exit_code == 1, json_result.stdout
    payload = json.loads(json_result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["workdir_state"]["status"] == "unavailable"
    assert payload["workdir_state"]["error"] == "workdir could not be inspected"
    assert payload["workdir_state"]["usable_for_agent_entries"] is False
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "choose_workdir",
        "confirm_readiness",
        "support",
    ]
    assert payload["next_action_items"][1]["after_action"] == "choose_workdir"
    assert "command" not in payload["next_action_items"][1]
    assert payload["agent_entries"][0]["install_state"] == "blocked_by_workdir"
    assert payload["agent_entries"][0]["next_action"] == "choose_workdir"
    assert "loopora init codex" not in json.dumps(payload["next_action_items"], ensure_ascii=False)
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded

    assert plain.exit_code == 1, plain.stdout
    assert "project directory state: unavailable" in plain.stdout
    assert "Target project directory cannot be inspected" in plain.stdout
    assert "Choose a project directory path" in plain.stdout
    assert "After choosing a usable project directory, re-run doctor to continue readiness checks." in plain.stdout
    assert "recommended install:" not in plain.stdout
    assert "loopora init codex" not in plain.stdout
    assert "permission denied" not in plain.stdout
    assert str(private_path) not in plain.stdout

    assert public.exit_code == 1, public.stdout
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["project_directory_status"] == "unavailable"
    assert public_payload["next_actions"] == ["choose_project_directory", "confirm_readiness", "support"]
    assert public_payload["agent_entries"][0]["install_state"] == "blocked_by_project_directory"
    assert public_payload["agent_entries"][0]["next_action"] == "choose_project_directory"
    assert "install_agent_entry" not in public_payload["next_actions"]
    assert_public_workdir_confirm_summary(public_payload, prerequisite="After choosing a usable project directory")
    assert str(blocked_workdir) not in public_encoded
    assert "workdir" not in public_encoded
    assert "permission denied" not in public_encoded
    assert str(private_path) not in public_encoded


def test_cli_diagnose_doctor_handles_workdir_resolve_failure_before_install_guidance(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    blocked_workdir = tmp_path / "resolve-blocked-project"
    private_path = tmp_path / "private" / "resolve-blocked-project"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *args, **kwargs) -> Path:
        if path == blocked_workdir:
            raise OSError(f"permission denied: {private_path}")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fail_resolve)

    json_result = runner.invoke(cli.app, ["doctor", "--workdir", str(blocked_workdir), "--json"])
    public = runner.invoke(cli.app, ["doctor", "--workdir", str(blocked_workdir), "--public-json"])

    assert json_result.exit_code == 1, json_result.stdout
    payload = json.loads(json_result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["workdir_state"]["status"] == "unavailable"
    assert payload["workdir_state"]["error"] == "workdir could not be inspected"
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "choose_workdir",
        "confirm_readiness",
        "support",
    ]
    assert payload["next_action_items"][1]["after_action"] == "choose_workdir"
    assert "command" not in payload["next_action_items"][1]
    assert "loopora init codex" not in json.dumps(payload["next_action_items"], ensure_ascii=False)
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded

    assert public.exit_code == 1, public.stdout
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["project_directory_status"] == "unavailable"
    assert public_payload["next_actions"] == ["choose_project_directory", "confirm_readiness", "support"]
    assert "install_agent_entry" not in public_payload["next_actions"]
    assert_public_workdir_confirm_summary(public_payload, prerequisite="After choosing a usable project directory")
    assert str(blocked_workdir) not in public_encoded
    assert "permission denied" not in public_encoded
    assert str(private_path) not in public_encoded


def test_cli_doctor_json_mode_conflict_is_structured() -> None:
    runner = CliRunner()
    expected = {"status": "error", "error": "choose either --json or --public-json, not both"}

    root = runner.invoke(cli.app, ["doctor", "--json", "--public-json"])
    grouped = runner.invoke(cli.app, ["diagnose", "doctor", "--json", "--public-json"])

    assert root.exit_code == 1
    assert json.loads(root.stdout) == expected
    assert root.stderr == ""
    assert grouped.exit_code == 1
    assert json.loads(grouped.stdout) == expected
    assert grouped.stderr == ""


def test_cli_doctor_json_web_port_errors_are_structured() -> None:
    runner = CliRunner()

    root_json = runner.invoke(cli.app, ["doctor", "--web-port", "70000", "--json"])
    grouped_public = runner.invoke(cli.app, ["diagnose", "doctor", "--web-port", "70000", "--public-json"])
    root_text = runner.invoke(cli.app, ["doctor", "--web-port", "nope", "--json"])
    plain = runner.invoke(cli.app, ["doctor", "--web-port", "70000"])

    range_expected = {"status": "error", "error": "invalid --web-port: must be between 1 and 65535"}
    type_expected = {
        "status": "error",
        "error": "invalid --web-port: must be an integer between 1 and 65535",
    }

    assert root_json.exit_code == 1
    assert json.loads(root_json.stdout) == range_expected
    assert root_json.stderr == ""
    assert "Usage:" not in root_json.output
    assert "Invalid value" not in root_json.output

    assert grouped_public.exit_code == 1
    assert json.loads(grouped_public.stdout) == range_expected
    assert grouped_public.stderr == ""
    assert "Usage:" not in grouped_public.output
    assert "Invalid value" not in grouped_public.output

    assert root_text.exit_code == 1
    assert json.loads(root_text.stdout) == type_expected
    assert root_text.stderr == ""
    assert "Usage:" not in root_text.output
    assert "Invalid value" not in root_text.output

    assert plain.exit_code == SHELL_RECOVERY_EXIT_CODE
    assert plain.stdout == ""
    assert "invalid --web-port: must be between 1 and 65535" in plain.stderr
    assert "Usage:" not in plain.output
    assert "Invalid value" not in plain.output
