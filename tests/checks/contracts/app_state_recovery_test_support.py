from __future__ import annotations

import json
from pathlib import Path
import shlex
import socket
import sqlite3

from typer.testing import CliRunner

from loopora import cli
from loopora.branding import APP_HOME_ENV
from loopora.service import LOCAL_APP_STATE_OPEN_ERROR


APP_STATE_NOT_READY_BLOCKER = {
    "kind": "app_state_not_ready",
    "status": "development_reset_required",
    "recovery_action": "preview_app_database_reset",
}
READY_WITH_APP_WARNING_ACTION_KINDS = [
    "create_recovery_archive",
    "preview_app_database_reset",
    "use_temporary_app_home",
    "confirm_readiness",
    "return_to_agent",
    "confirm_agent_visibility",
    "run_loopora_plan",
    "review_ready_loop_preview",
    "run_loopora_run",
    "support",
]


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def create_legacy_app_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE loop_definitions (id TEXT PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("PRAGMA user_version = 1")


def assert_local_app_state_open_failure_text(text: str, *blocked_fragments: object) -> None:
    assert LOCAL_APP_STATE_OPEN_ERROR in text
    assert "loopora doctor --workdir <project>" in text
    assert APP_HOME_ENV in text
    blocked = (
        *blocked_fragments,
        "unable to open",
        "permission denied",
        "db.connect.failed",
        "service.create.local_app_state_open_failed",
        "Traceback",
    )
    for fragment in blocked:
        assert str(fragment) not in text


def assert_doctor_public_gates_web_start_before_adapter_install(
    app_home: Path,
    workdir: Path,
    *,
    web_port: int,
) -> None:
    public = CliRunner().invoke(
        cli.app,
        ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--public-json"],
    )
    public_payload = json.loads(public.stdout)

    assert public.exit_code == 1, public.stdout
    assert public_payload["app_state"]["status"] == "development_reset_required"
    assert public_payload["app_state"]["next_action"] == "preview_dev_reset_before_web"
    assert public_payload["diagnose_doctor_public_summary"]["web_readiness_blockers"] == public_payload["web"]["readiness_blockers"]
    assert public_payload["web"]["readiness_blockers"][0] == APP_STATE_NOT_READY_BLOCKER
    assert "use_temporary_app_home" in public_payload["next_actions"]
    assert_public_doctor_redacts_app_paths(public_payload, app_home=app_home, workdir=workdir)
    assert_public_doctor_combines_app_and_port_recovery(workdir)


def assert_public_doctor_redacts_app_paths(public_payload: dict, *, app_home: Path, workdir: Path) -> None:
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert all(text not in public_encoded for text in (str(app_home), str(workdir), "commands", "temporary_serve", APP_HOME_ENV))


def assert_public_doctor_combines_app_and_port_recovery(workdir: Path) -> None:
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    occupied_port = int(occupied.getsockname()[1])
    args = ["doctor", "--workdir", str(workdir), "--web-port", str(occupied_port)]
    try:
        blocked_public = CliRunner().invoke(cli.app, [*args, "--public-json"])
        blocked_plain = CliRunner().invoke(cli.app, args)
        blocked_private = CliRunner().invoke(cli.app, [*args, "--json"])
    finally:
        occupied.close()
    blocked_payload = json.loads(blocked_public.stdout)
    public_summary, web = blocked_payload["diagnose_doctor_public_summary"], blocked_payload["web"]
    assert (
        blocked_public.exit_code,
        web["start_blocked_reason"],
        [item["kind"] for item in web["readiness_blockers"]],
        public_summary["web_readiness_blockers"],
        public_summary["web_recovery_action"],
        web["recovery_action"],
        public_summary["web_recovery_actions"],
        web["recovery_actions"],
    ) == (
        1,
        "port_in_use",
        ["app_state_not_ready", "port_in_use"],
        web["readiness_blockers"],
        "multiple_actions_required",
        "multiple_actions_required",
        ["preview_app_database_reset", "use_suggested_free_port_or_choose_another_port"],
        ["preview_app_database_reset", "use_suggested_free_port_or_choose_another_port"],
    )
    assert "After App readiness is recovered, choose a free Web port" in json.dumps(
        blocked_payload["next_action_summaries"],
        ensure_ascii=False,
    )
    assert str(occupied_port) not in json.dumps(blocked_payload, ensure_ascii=False)
    assert blocked_plain.exit_code == 1, blocked_plain.stdout
    assert all(
        text in blocked_plain.stdout
        for text in (
            "requested web start blocked until App readiness:",
            f"--port {occupied_port}",
            "After App state is ready, choose a free Web port",
        )
    )
    assert (
        "use_temporary_app_home" in blocked_payload["next_actions"],
        "resolve_web_port" in blocked_payload["next_actions"],
        "temporary Web preview:" in blocked_plain.stdout,
        "web start after readiness:" in blocked_plain.stdout,
    ) == (False, True, False, True)
    assert "web start after readiness unavailable:" not in blocked_plain.stdout
    blocked_private_payload = json.loads(blocked_private.stdout)
    web_action = next(item for item in blocked_private_payload["next_action_items"] if item["kind"] == "resolve_web_port")
    assert (web_action["command_ready"], web_action["command_blockers"], web_action["blocked_until"]) == (
        False,
        ["app_state_not_ready"],
        ["app_state_ready"],
    )


def assert_doctor_plain_gates_web_start_before_adapter_install(workdir: Path, *, web_port: int) -> None:
    plain = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(web_port)])

    assert plain.exit_code == 1, plain.stdout
    assert "Loopora doctor: not_ready" in plain.stdout
    assert "App state: development_reset_required (Web ready: no)" in plain.stdout
    assert "reset preview:" in plain.stdout
    assert "reset apply after review:" in plain.stdout
    assert "loopora dev reset --scope app --workdir" in plain.stdout
    assert "--yes" in plain.stdout
    assert 'temporary Web preview: LOOPORA_HOME="$(mktemp -d)" loopora serve --open --host 127.0.0.1 --port' in plain.stdout
    assert "temporary Web note: uses a new empty App home" in plain.stdout
    assert "it does not delete, migrate, or repair the blocked App database" in plain.stdout
    assert "apply: rerun that command with --yes" not in plain.stdout
    assert f"web: http://127.0.0.1:{web_port} (blocked until App state is ready;" in plain.stdout
    assert "web start after readiness:" in plain.stdout
    assert f"loopora serve --open --host 127.0.0.1 --port {web_port}" in plain.stdout
    assert f"web start: loopora serve --open --host 127.0.0.1 --port {web_port}" not in plain.stdout
    assert plain.stdout.index("App state: development_reset_required") < plain.stdout.index("web start after readiness:")


def assert_doctor_reports_legacy_app_state_before_adapter_install(result, payload: dict) -> None:
    assert result.exit_code == 1
    assert result.stderr == ""
    assert payload["diagnose_doctor_summary"]["status"] == "not_ready"
    assert payload["diagnose_doctor_summary"]["agent_entry_ready"] is False
    assert payload["diagnose_doctor_summary"]["strict_ready"] is False
    assert payload["diagnose_doctor_summary"]["app_state_status"] == "development_reset_required"
    assert payload["diagnose_doctor_summary"]["app_state_web_ready"] is False
    assert payload["diagnose_doctor_summary"]["first_task_guidance_available"] is True
    assert payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert payload["app_state"]["status"] == "development_reset_required"
    assert payload["app_state"]["schema_version"] == 1
    assert payload["app_state"]["web_ready"] is False
    assert payload["app_state"]["needs_attention"] is True
    assert payload["app_state"]["next_action"] == "preview_dev_reset_before_web"
    assert payload["diagnose_doctor_summary"]["web_readiness_blockers"] == payload["web"]["readiness_blockers"]
    assert payload["web"]["readiness_blockers"][0] == APP_STATE_NOT_READY_BLOCKER
    assert "loopora recovery create --workdir" in payload["app_state"]["commands"]["recovery_archive"]
    assert "loopora dev reset --scope app --workdir" in payload["app_state"]["commands"]["reset"]
    assert payload["app_state"]["commands"]["preview_reset"] == payload["app_state"]["commands"]["reset"]
    assert payload["app_state"]["commands"]["apply_reset"].endswith(" --yes")
    assert " serve --open --host 127.0.0.1 --port" in payload["app_state"]["commands"]["temporary_serve"]
    assert any("loopora dev reset --scope app --workdir" in step for step in payload["next_steps"])
    assert any("preview the App database reset scope" in step for step in payload["next_steps"])
    assert any("temporary empty App home" in step for step in payload["next_steps"])
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "create_recovery_archive",
        "preview_app_database_reset",
        "use_temporary_app_home",
        "confirm_readiness",
        "check_fit_first",
        "install_agent_entry",
        "run_loopora_plan",
        "support",
    ]
    assert payload["primary_next_action_kind"] == payload["diagnose_doctor_summary"]["primary_next_action_kind"] == "create_recovery_archive"
    fit_action = next(item for item in payload["next_action_items"] if item["kind"] == "check_fit_first")
    assert shlex.split(fit_action["command"])[-4:] == [
        "loopora",
        "fit",
        "--workdir",
        payload["workdir"],
    ]
    archive_index = [item["kind"] for item in payload["next_action_items"]].index("create_recovery_archive")
    reset_index = [item["kind"] for item in payload["next_action_items"]].index("preview_app_database_reset")
    temporary_index = [item["kind"] for item in payload["next_action_items"]].index("use_temporary_app_home")
    confirm_index = [item["kind"] for item in payload["next_action_items"]].index("confirm_readiness")
    run_index = [item["kind"] for item in payload["next_action_items"]].index("run_loopora_plan")
    archive_action = payload["next_action_items"][archive_index]
    assert archive_action["private_content"] is True
    assert archive_action["public_safe"] is False
    assert "loopora recovery create --workdir" in archive_action["command"]
    assert archive_index < reset_index < run_index
    assert "loopora dev reset --scope app --workdir" in payload["next_action_items"][reset_index]["command"]
    assert payload["next_action_items"][reset_index]["after_action"] == "create_recovery_archive"
    assert reset_index < temporary_index < confirm_index < run_index
    assert 'LOOPORA_HOME="$(mktemp -d)" loopora serve' in payload["next_action_items"][temporary_index]["command"]
    assert "loopora doctor --workdir" in payload["next_action_items"][confirm_index]["command"]
    install_action = next(item for item in payload["next_action_items"] if item["kind"] == "install_agent_entry")
    assert (
        install_action["selection_required"],
        f"loopora support --workdir {payload['workdir']}" in payload["next_action_items"][-1]["command"],
        "--web-port" in payload["next_action_items"][-1]["command"],
    ) == (True, True, True)
    assert payload["agent_entries"][0]["install_state"] == "not_installed"
    assert "Loopora v3 development reset required" not in result.stdout


def assert_ready_warning_recovery_queue(payload: dict) -> None:
    assert [item["kind"] for item in payload["next_action_items"]] == READY_WITH_APP_WARNING_ACTION_KINDS
    assert "loopora recovery create --workdir" in payload["next_action_items"][0]["command"]
    assert payload["next_action_items"][1]["after_action"] == "create_recovery_archive"
    assert "loopora dev reset --scope app --workdir" in payload["next_action_items"][1]["command"]
    assert payload["next_action_items"][3]["after_action"] == "preview_app_database_reset"
    assert "loopora doctor --workdir" in payload["next_action_items"][3]["command"]


def assert_ready_warning_public_recovery(workdir: Path, *, web_port: int) -> None:
    strict_public_warning = CliRunner().invoke(
        cli.app,
        ["diagnose", "doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--public-json", "--strict"],
    )
    assert strict_public_warning.exit_code == 1, strict_public_warning.stdout
    payload = json.loads(strict_public_warning.stdout)
    assert payload["diagnose_doctor_public_summary"]["status"] == "ready_with_warnings"
    assert payload["diagnose_doctor_public_summary"]["agent_entry_ready"] is True
    assert payload["diagnose_doctor_public_summary"]["strict_ready"] is False
    assert payload["next_actions"] == READY_WITH_APP_WARNING_ACTION_KINDS
    assert payload["next_action_summaries"][3]["summary"].startswith("After applying an acceptable App reset")


def assert_doctor_strict_mode_fails_ready_with_app_warning(workdir: Path, *, web_port: int) -> None:
    ready_with_warning = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--json"])
    ready_payload = json.loads(ready_with_warning.stdout)
    assert ready_with_warning.exit_code == 0, ready_with_warning.stdout
    assert ready_payload["status"] == "ready_with_warnings"
    assert ready_payload["ready"] is True
    assert ready_payload["agent_entry_ready"] is True
    assert ready_payload["strict_ready"] is False
    assert ready_payload["diagnose_doctor_summary"]["first_task_guidance_available"] is True
    assert ready_payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert ready_payload["app_state"]["status"] == "development_reset_required"
    assert any("preview the App database reset scope" in step for step in ready_payload["next_steps"])
    assert any("temporary empty App home" in step for step in ready_payload["next_steps"])
    assert_ready_warning_recovery_queue(ready_payload)

    plain_warning = CliRunner().invoke(cli.app, ["doctor", "--workdir", str(workdir), "--web-port", str(web_port)])
    assert plain_warning.exit_code == 0, plain_warning.stdout
    assert "Loopora doctor: ready_with_warnings" in plain_warning.stdout
    assert "same-Agent project entry ready: yes" in plain_warning.stdout
    assert "App state: development_reset_required (Web ready: no)" in plain_warning.stdout
    assert "reset preview:" in plain_warning.stdout
    assert "reset apply after review:" in plain_warning.stdout
    assert "loopora dev reset --scope app --workdir" in plain_warning.stdout
    assert "apply: rerun that command with --yes" not in plain_warning.stdout
    assert "web start after readiness:" in plain_warning.stdout
    assert f"loopora serve --open --host 127.0.0.1 --port {web_port}" in plain_warning.stdout
    assert f"web start: loopora serve --open --host 127.0.0.1 --port {web_port}" not in plain_warning.stdout
    assert plain_warning.stdout.index("App state: development_reset_required") < plain_warning.stdout.index("web start after readiness:")
    assert "Create and inspect a private exact-path archive before deleting useful local history:" in plain_warning.stdout
    assert "After the private recovery archive succeeds, preview the App database reset scope:" in plain_warning.stdout
    assert "To preview Web without changing blocked App state, start a temporary empty App home:" in plain_warning.stdout
    assert "After applying an acceptable App reset, re-run doctor to confirm App/Web readiness:" in plain_warning.stdout
    assert "loopora dev reset --scope app --workdir" in plain_warning.stdout
    assert "ready: yes" not in plain_warning.stdout.splitlines()

    strict_plain_warning = CliRunner().invoke(
        cli.app,
        ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--strict"],
    )
    assert strict_plain_warning.exit_code == 1, strict_plain_warning.stdout
    assert "Loopora doctor: ready_with_warnings" in strict_plain_warning.stdout
    assert "same-Agent project entry ready: yes" in strict_plain_warning.stdout
    assert "strict readiness: no" in strict_plain_warning.stdout

    strict_json_warning = CliRunner().invoke(
        cli.app,
        ["doctor", "--workdir", str(workdir), "--web-port", str(web_port), "--json", "--strict"],
    )
    assert strict_json_warning.exit_code == 1, strict_json_warning.stdout
    strict_json_payload = json.loads(strict_json_warning.stdout)
    assert strict_json_payload["status"] == "ready_with_warnings"
    assert strict_json_payload["agent_entry_ready"] is True
    assert strict_json_payload["strict_ready"] is False

    assert_ready_warning_public_recovery(workdir, web_port=web_port)
