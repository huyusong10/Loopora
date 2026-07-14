from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli
from loopora.branding import APP_HOME_ENV
from loopora.cli_dev_commands import DEV_RESET_SUMMARY_SCHEMA_VERSION, _dev_check_pr_evidence_payload
from loopora.db import LooporaRepository
from loopora.dev_check import (
    DEFAULT_FAST_COMMANDS,
    DEV_CHECK_SCHEMA_VERSION,
    FOCUSED_PROFILE,
    FOCUSED_CHECK_GUIDES,
    DevCheckCommandResult,
    focused_check_selection_choices,
    run_dev_check,
)
from cli_dev_command_test_support import (
    cli_dev_check_command,
    create_reset_fixture,
    dev_check_command,
    dev_workdir_error_payload,
    focused_dev_check_command,
    package_metadata_text,
    result_error_text,
    write_package_artifacts,
    write_text,
)


def test_cli_dev_check_lists_default_fast_gate_without_running(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--list", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = payload["dev_check_summary"]
    assert summary["schema_version"] == DEV_CHECK_SCHEMA_VERSION
    assert summary["profile"] == "default-fast"
    assert summary["status"] == "listed"
    assert summary["ready"] is True
    assert summary["workdir"] == str(tmp_path.resolve())
    assert summary["focused_guide_count"] == len(FOCUSED_CHECK_GUIDES)
    assert summary["changed_file_count"] == 0
    assert summary["changed_file_source"] == "git"
    assert summary["changed_file_status"] == "unavailable"
    assert summary["recommended_focused_guide_count"] == 0
    assert summary["unmatched_changed_file_count"] == 0
    assert summary["next_action_kinds"] == [
        "no_recommended_focused_checks",
        "review_focused_check_guide",
        "run_default_fast_gate",
    ]
    assert [step["id"] for step in payload["steps"]] == [step[0] for step in DEFAULT_FAST_COMMANDS]
    assert [step["command"] for step in payload["steps"]] == [step[2] for step in DEFAULT_FAST_COMMANDS]
    assert all(step["status"] == "listed" for step in payload["steps"])
    assert [guide["id"] for guide in payload["focused_guides"]] == [guide.id for guide in FOCUSED_CHECK_GUIDES]
    assert [guide["command"] for guide in payload["focused_guides"]] == [guide.command for guide in FOCUSED_CHECK_GUIDES]
    assert payload["focused_selection_choices"] == list(focused_check_selection_choices())
    assert {guide["evidence_type"] for guide in payload["focused_guides"]} >= {"focused", "journey"}
    assert all(guide["path_patterns"] for guide in payload["focused_guides"])
    assert payload["changed_files"] == []
    assert payload["changed_file_detection"] == {"source": "git", "status": "unavailable", "count": 0}
    assert payload["recommended_focused_guides"] == []
    assert payload["unmatched_changed_file_count"] == 0
    assert payload["unmatched_changed_files"] == []
    assert payload["omitted_unmatched_changed_file_count"] == 0
    assert payload["next_actions"] == [
        {
            "kind": "no_recommended_focused_checks",
            "reason": "git_unavailable",
            "changed_file_source": "git",
            "changed_file_status": "unavailable",
            "changed_file_count": 0,
            "ignored_changed_file_count": 0,
            "unmatched_changed_file_count": 0,
        },
        {"kind": "review_focused_check_guide"},
        {"kind": "run_default_fast_gate", "command": cli_dev_check_command(tmp_path)},
    ]

    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--list"])
    plain_text = plain.stdout
    assert plain.exit_code == 0, plain.stdout
    assert all(
        fragment in plain_text
        for fragment in (
            "Loopora dev check: default-fast",
            "changes: Git changed-file detection unavailable (0 file(s))",
            f"focused selectors: {', '.join(focused_check_selection_choices())}",
            "uv run pytest -q tests/checks/contracts",
            "focused check guide:",
            "recommended focused checks for current changes: none",
            "Git changed-file detection is unavailable",
            "PR evidence:",
            "changed-file detection status",
            "ignored changed files",
            "unmatched changed files",
            "before choosing checks",
            "next: no recommended focused checks for current changes",
        )
    )


def test_cli_dev_check_pr_evidence_summary_is_copyable(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    for path in (".github/pull_request_template.md", "docs/notes.md"): write_text(workdir / path, "# touched\n")
    subprocess.run(("git", "init"), cwd=workdir, text=True, capture_output=True, check=True)
    runner = CliRunner()
    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list", "--pr-evidence", "--focused-ran", "recommended"])
    structured = runner.invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list", "--pr-evidence", "--focused-ran", "recommended", "--json"])
    assert plain.exit_code == 0, plain.stdout
    assert all(snippet in plain.stdout for snippet in ("Loopora PR evidence summary", "evidence stage: decision", "evidence command source: loopora dev check", "recommended focused guide IDs: open_source_collaboration", "focused guide IDs run: not run by this command", "skipped focused guide IDs: not recorded by this command", "focused-ran decision note: received focused-ran values (recommended)", "unmatched changed files: docs/notes.md", "Public evidence: paste redacted diagnostic output only", "copyable PR evidence block:", "- PR evidence stage: decision"))
    assert "focused check guide:" not in plain.stdout
    payload = json.loads(structured.stdout); summary = payload["pr_evidence_summary"]
    assert (payload["dev_check_summary"]["focused_ran_guide_ids"], payload["focused_ran_guide_ids"]) == ([], [])
    focused_summary = _dev_check_pr_evidence_payload(run_dev_check(workdir=workdir, focused="open_source_collaboration", changed_files=[".github/pull_request_template.md"], command_runner=lambda *_: DevCheckCommandResult(returncode=0)))
    assert (focused_summary["evidence_stage"], focused_summary["skipped_focused_guide_ids"]) == ("focused_passed", [])
    assert (summary["evidence_stage"], summary["evidence_command_source"], summary["recommended_focused_guide_ids"], summary["focused_guide_ids_run"], summary["skipped_focused_guide_ids"], summary["focused_ran_decision_note"]) == ("decision", "loopora dev check", ["open_source_collaboration"], [], None, "received focused-ran values (recommended); --list decision evidence does not count them until the final non-list PR evidence command")
    assert all(snippet in summary["template_markdown"] for snippet in ("- PR evidence stage: decision", "- Evidence command source: `loopora dev check`", "- Decision scope evidence: collected by this list-stage PR evidence command", "- Recommended focused guide IDs: open_source_collaboration", "- Focused guide IDs run: not run by this command", "- Skipped recommended or boundary-relevant guide IDs: not recorded by this command", "- Focused-ran decision note: received focused-ran values (recommended)", "- Final dev-check result: not run by this command", "- Package-build cleanup: tmp/package-check absent; src/loopora.egg-info absent", "- Public evidence reminder:", "<project-dir>", "<Loopora checkout>", "<redacted>"))


def test_cli_dev_check_missing_workdir_reports_stable_error_without_typer_path(tmp_path: Path) -> None:
    runner = CliRunner()
    missing_workdir = tmp_path / "missing project"

    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(missing_workdir), "--list"])
    json_result = runner.invoke(cli.app, ["dev", "check", "--workdir", str(missing_workdir), "--list", "--json"])

    plain_error = result_error_text(plain)
    assert plain.exit_code == 1
    assert "workdir does not exist" in plain_error
    assert "Invalid value" not in plain_error
    assert str(missing_workdir) not in plain.output

    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    assert payload == dev_workdir_error_payload("check")
    assert "Invalid value" not in json_result.output
    assert str(missing_workdir) not in json_result.output


def test_dev_check_runs_recommended_focused_guides_from_changed_paths(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0, stdout="focused ok\n")

    result = run_dev_check(
        workdir=tmp_path,
        focused="recommended",
            changed_files=["src/loopora/diagnose_doctor.py", ".github/pull_request_template.md"],
            command_runner=fake_runner,
        )
    assert (result["profile"], result["status"], result["ready"], result["focused_selection"]) == (FOCUSED_PROFILE, "pass", True, "recommended")
    assert result["dev_check_summary"]["selected_focused_guide_count"] == 2
    assert result["dev_check_summary"]["next_action_kinds"] == ["focused_checks_passed", "run_final_pr_evidence_gate", "run_default_fast_gate"]
    assert [step["id"] for step in result["steps"]] == [
        "focused:first_use_readiness",
        "focused:open_source_collaboration",
    ]
    assert all(step["status"] == "pass" for step in result["steps"])
    assert calls == [
        tuple(shlex.split(guide.command))
        for guide in FOCUSED_CHECK_GUIDES
        if guide.id in {"first_use_readiness", "open_source_collaboration"}
    ]
    assert (result["next_actions"][1]["guide_ids"], "--pr-evidence" in result["next_actions"][1]["command"], "--focused-ran first_use_readiness --focused-ran open_source_collaboration" in result["next_actions"][1]["command"]) == (["first_use_readiness", "open_source_collaboration"], True, True)
    partial = run_dev_check(workdir=tmp_path, focused="first_use_readiness", changed_files=["src/loopora/diagnose_doctor.py", ".github/pull_request_template.md"], command_runner=fake_runner)
    assert partial["dev_check_summary"]["next_action_kinds"] == ["focused_checks_passed", "run_remaining_recommended_focused_checks", "run_default_fast_gate"]
    assert (partial["next_actions"][1]["guide_ids"], partial["next_actions"][1]["already_ran_guide_ids"]) == (["open_source_collaboration"], ["first_use_readiness"])
    remaining = run_dev_check(workdir=tmp_path, focused="open_source_collaboration", changed_files=["src/loopora/diagnose_doctor.py", ".github/pull_request_template.md"], focused_ran=["first_use_readiness"], command_runner=fake_runner)
    assert ("--focused open_source_collaboration" in partial["next_actions"][1]["command"], "--focused-ran first_use_readiness" in partial["next_actions"][1]["command"], remaining["dev_check_summary"]["next_action_kinds"], remaining["next_actions"][1]["guide_ids"]) == (True, True, ["focused_checks_passed", "run_final_pr_evidence_gate", "run_default_fast_gate"], ["first_use_readiness", "open_source_collaboration"])


def test_dev_check_focused_failure_stops_and_reports_rerun_command(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=9, stdout="journey failed\n", stderr="web route broken\n")

    result = run_dev_check(
        workdir=tmp_path,
        focused="web_surfaces,open_source_collaboration",
        command_runner=fake_runner,
    )
    steps = result["steps"]

    assert result["profile"] == FOCUSED_PROFILE
    assert result["status"] == "fail"
    assert result["dev_check_summary"]["failed_step_id"] == "focused:web_surfaces"
    assert (result["next_action_kinds"], result["dev_check_summary"]["next_action_kinds"], result["next_action_ready_now_kinds"], result["dev_check_summary"]["next_action_ready_now_kinds"], result["next_action_ready_after_actions"], result["next_action_blocked_kinds"]) == (["fix_failed_step", "rerun_focused_checks"], ["fix_failed_step", "rerun_focused_checks"], ["fix_failed_step", "rerun_focused_checks"], ["fix_failed_step", "rerun_focused_checks"], {}, [])
    assert [step["status"] for step in steps] == ["fail", "skipped"]
    assert "web route broken" in steps[0]["stderr"]
    assert len(calls) == 1
    assert result["next_actions"][0]["failed_step"] == {"id": "focused:web_surfaces", "label": "Web routes, templates, and static assets", "command": steps[0]["command"], "returncode": 9}
    assert result["next_actions"][1] == {"kind": "rerun_focused_checks", "command": focused_dev_check_command(tmp_path, "web_surfaces,open_source_collaboration")}
    assert _dev_check_pr_evidence_payload(result)["failed_step"].startswith("focused:web_surfaces (exit 9): uv run pytest")
    assert _dev_check_pr_evidence_payload(result, focused_ran=["all"])["focused_guide_ids_run"] == ["web_surfaces"]


def test_cli_dev_check_list_explains_clean_git_tree_without_recommendations(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    subprocess.run(("git", "init"), cwd=workdir, text=True, capture_output=True, check=True)

    result = CliRunner().invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list", "--json"])
    payload = json.loads(result.stdout)
    plain = CliRunner().invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list"])

    assert result.exit_code == 0, result.stdout
    assert payload["dev_check_summary"]["changed_file_source"] == "git"
    assert payload["dev_check_summary"]["changed_file_status"] == "clean"
    assert payload["dev_check_summary"]["no_recommended_focused_check_reason"] == "git_clean"
    assert payload["no_recommended_focused_check_reason"] == {
        "reason": "git_clean",
        "changed_file_source": "git",
        "changed_file_status": "clean",
        "changed_file_count": 0,
        "ignored_changed_file_count": 0,
        "unmatched_changed_file_count": 0,
    }
    assert payload["changed_file_detection"] == {"source": "git", "status": "clean", "count": 0}
    assert payload["recommended_focused_guides"] == []
    assert plain.exit_code == 0, plain.stdout
    assert "changes: Git tree clean (0 file(s))" in plain.stdout
    assert "recommended focused checks for current changes: none" in plain.stdout
    assert "no current Git changes detected" in plain.stdout
    assert "PR evidence: record the changed-file detection status" in plain.stdout


def test_cli_dev_check_focused_recommended_skips_without_changed_file_detection(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--focused", "recommended", "--json"])
    payload = json.loads(result.stdout)
    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--focused", "recommended"])

    assert result.exit_code == 0, result.stdout
    assert payload["profile"] == FOCUSED_PROFILE
    assert payload["status"] == "skipped"
    assert payload["dev_check_summary"]["no_recommended_focused_check_reason"] == "git_unavailable"
    assert payload["no_recommended_focused_check_reason"] == {
        "reason": "git_unavailable",
        "changed_file_source": "git",
        "changed_file_status": "unavailable",
        "changed_file_count": 0,
        "ignored_changed_file_count": 0,
        "unmatched_changed_file_count": 0,
    }
    assert payload["dev_check_summary"]["next_action_kinds"] == [
        "no_recommended_focused_checks",
        "review_focused_check_guide",
        "run_default_fast_gate",
    ]
    assert payload["next_actions"] == [
        {
            "kind": "no_recommended_focused_checks",
            "reason": "git_unavailable",
            "changed_file_source": "git",
            "changed_file_status": "unavailable",
            "changed_file_count": 0,
            "ignored_changed_file_count": 0,
            "unmatched_changed_file_count": 0,
        },
        {"kind": "review_focused_check_guide", "command": cli_dev_check_command(tmp_path, "--list")},
        {"kind": "run_default_fast_gate", "command": cli_dev_check_command(tmp_path)},
    ]
    assert payload["steps"] == []
    assert plain.exit_code == 0, plain.stdout
    assert "Loopora dev check: focused" in plain.stdout
    assert "status: skipped" in plain.stdout
    assert "changes: Git changed-file detection unavailable (0 file(s))" in plain.stdout
    assert "recommended focused checks for current changes: none" in plain.stdout
    assert "next: no recommended focused checks for current changes" in plain.stdout
    assert f"inspect the focused check guide: {cli_dev_check_command(tmp_path, '--list')}" in plain.stdout
    assert f"run {cli_dev_check_command(tmp_path)}" in plain.stdout
    assert f"--workdir {tmp_path.resolve()}" in plain.stdout


def test_cli_dev_check_list_shows_omitted_matched_files_count(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    for index in range(6):
        touched_file = workdir / "src" / "loopora" / f"cli_agent_generated_{index}.py"
        touched_file.parent.mkdir(parents=True, exist_ok=True)
        touched_file.write_text("# touched\n", encoding="utf-8")
    subprocess.run(("git", "init"), cwd=workdir, text=True, capture_output=True, check=True)

    result = CliRunner().invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list"])

    assert result.exit_code == 0, result.stdout
    recommended_index = result.stdout.index("recommended focused checks for current changes:")
    guide_index = result.stdout.index("focused check guide:")
    recommended_output = result.stdout[recommended_index:guide_index]
    assert "agent_native" in recommended_output
    assert "(+2 more)" in recommended_output
    assert "unmatched changed files: none" in result.stdout
    assert "PR evidence: record recommended guide IDs (agent_native)" in result.stdout


def test_dev_check_stops_after_first_failed_step_and_reports_command(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        if command == ("uv", "pip", "check"):
            return DevCheckCommandResult(returncode=7, stdout="dependency conflict\n", stderr="broken lock\n")
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)
    steps = {step["id"]: step for step in result["steps"]}

    assert result["status"] == "fail"
    assert result["ready"] is False
    assert result["dev_check_summary"]["failed_step_id"] == "dependency_compatibility"
    assert (result["next_action_kinds"], result["dev_check_summary"]["next_action_kinds"], result["next_action_ready_now_kinds"], result["dev_check_summary"]["next_action_ready_now_kinds"], result["next_action_ready_after_actions"], result["next_action_blocked_kinds"]) == (["fix_failed_step", "rerun_default_fast_gate"], ["fix_failed_step", "rerun_default_fast_gate"], ["fix_failed_step", "rerun_default_fast_gate"], ["fix_failed_step", "rerun_default_fast_gate"], {}, [])
    assert result["next_actions"][0] == {"kind": "fix_failed_step", "step_id": "dependency_compatibility", "failed_step": {"id": "dependency_compatibility", "label": "Check dependency compatibility", "command": "uv pip check", "returncode": 7}}
    assert result["next_actions"][1] == {"kind": "rerun_default_fast_gate", "command": dev_check_command(tmp_path)}
    assert "- Failed step: dependency_compatibility (exit 7): uv pip check" in _dev_check_pr_evidence_payload(result)["template_markdown"]
    assert steps["dependency_sync"]["status"] == "pass"
    assert steps["dependency_compatibility"]["status"] == "fail"
    assert steps["dependency_compatibility"]["returncode"] == 7
    assert "broken lock" in steps["dependency_compatibility"]["stderr"]
    assert steps["static_js_syntax"]["status"] == "skipped"
    assert calls == [("uv", "sync", "--locked", "--dry-run"), ("uv", "pip", "check")]

def test_dev_check_package_build_cleans_generated_package_artifacts(tmp_path: Path) -> None:
    for stale_file in (
        tmp_path / "src" / "loopora.egg-info" / "PKG-INFO",
        tmp_path / "tmp" / "package-check" / "stale.whl",
    ):
        write_text(stale_file, "stale\n")

    def fake_runner(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
        if command == ("uv", "build", "--out-dir", "tmp/package-check"):
            assert not (cwd / "src" / "loopora.egg-info").exists()
            assert not (cwd / "tmp" / "package-check" / "stale.whl").exists()
            write_text(cwd / "src" / "loopora.egg-info" / "PKG-INFO", "generated\n")
            write_package_artifacts(cwd)
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner, changed_files=["src/loopora/dev_check.py"])
    covered = run_dev_check(workdir=tmp_path, command_runner=fake_runner, changed_files=["src/loopora/dev_check.py"], focused_ran=["open_source_collaboration"])
    assert result["status"] == covered["status"] == "pass"
    assert [action["kind"] for action in result["next_actions"]] == ["default_fast_gate_passed", "run_recommended_focused_checks"]
    assert [action["kind"] for action in covered["next_actions"]] == ["default_fast_gate_passed", "pr_evidence_ready"]
    assert (result["next_actions"][1]["guide_ids"], "--changed-file src/loopora/dev_check.py" in result["next_actions"][1]["command"]) == (["open_source_collaboration"], True)
    assert all(snippet in _dev_check_pr_evidence_payload(covered, focused_ran=["open_source_collaboration"])[key] for key, snippet in (("next", "PR evidence is ready to copy"), ("decision_scope_evidence", "using the same changed-file"), ("template_markdown", "- Decision scope evidence: collected by this PR evidence command")))
    assert not any((tmp_path / path).exists() for path in ("tmp/package-check", "src/loopora.egg-info"))

def test_dev_check_package_build_fails_when_runtime_assets_are_missing_from_distribution(tmp_path: Path) -> None:
    write_text(tmp_path / "MANIFEST.in", "include README.md\n")
    write_text(tmp_path / "design" / "README.md", "# Design\n")
    write_text(tmp_path / "src" / "loopora" / "templates" / "base.html", "<html></html>\n")
    def fake_runner(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
        if command == ("uv", "build", "--out-dir", "tmp/package-check"):
            write_package_artifacts(cwd)
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)
    failed = {step["id"]: step for step in result["steps"]}["package_build"]

    assert result["dev_check_summary"]["failed_step_id"] == "package_build"
    assert "package content verification failed" in failed["stderr"]
    assert "wheel missing runtime asset: loopora/templates/base.html" in failed["stderr"]
    assert "sdist missing runtime asset: src/loopora/templates/base.html" in failed["stderr"]
    assert "sdist missing public asset: MANIFEST.in" in failed["stderr"]
    assert "sdist missing public asset: design/README.md" in failed["stderr"]
    assert not (tmp_path / "tmp" / "package-check").exists()


def test_dev_check_package_build_fails_when_installed_wheel_cli_cannot_start(tmp_path: Path) -> None:
    smoke_commands: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
        if command == ("uv", "build", "--out-dir", "tmp/package-check"):
            write_package_artifacts(cwd)
            return DevCheckCommandResult(returncode=0, stdout="built\n")
        if command[-2:] == ("loopora", "--version"):
            smoke_commands.append(command)
            return DevCheckCommandResult(returncode=9, stdout="", stderr="entry failed\n")
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)
    failed = {step["id"]: step for step in result["steps"]}["package_build"]

    assert result["dev_check_summary"]["failed_step_id"] == "package_build"
    assert smoke_commands == [
        (
            "uv", "run", "--isolated", "--no-project", "--offline", "--with",
            str(tmp_path / "tmp" / "package-check" / "loopora-0.1.0-py3-none-any.whl"), "loopora", "--version",
        )
    ]
    assert "installed wheel CLI smoke check failed: loopora --version" in failed["stderr"]
    assert "entry failed" in failed["stderr"]
    assert not (tmp_path / "tmp" / "package-check").exists()


def test_dev_check_package_build_fails_when_entry_metadata_is_missing(tmp_path: Path) -> None:
    cases = (
        ({"include_entry_points": False}, ("wheel missing console entry points: entry_points.txt",)),
        ({"include_module_entry": False}, ("wheel missing runtime asset: loopora/__main__.py", "sdist missing runtime asset: src/loopora/__main__.py")),
        ({"metadata_text": package_metadata_text().replace("Keywords:", "RemovedKeyword:", 1)}, ("wheel METADATA missing: Keywords:",)),
        ({"metadata_text": package_metadata_text().replace("Requires-Dist:", "Removed-Dist:", 1)}, ("wheel METADATA missing: Requires-Dist: fastapi>=0.115.0",)),
        ({"include_forbidden_artifacts": True}, ("wheel must not include local/test artifact: tests/private.py", "sdist must not include local/test artifact: tests/private.py")),
    )
    for index, (artifact_kwargs, expected_errors) in enumerate(cases):
        case_dir = tmp_path / f"case-{index}"
        case_dir.mkdir()
        def fake_runner(command: tuple[str, ...], cwd: Path, artifact_kwargs=artifact_kwargs) -> DevCheckCommandResult:
            if command == ("uv", "build", "--out-dir", "tmp/package-check"):
                write_package_artifacts(cwd, **artifact_kwargs)
            return DevCheckCommandResult(returncode=0, stdout="ok\n")
        result = run_dev_check(workdir=case_dir, command_runner=fake_runner)
        failed = {step["id"]: step for step in result["steps"]}["package_build"]
        assert result["dev_check_summary"]["failed_step_id"] == "package_build"
        assert all(error in failed["stderr"] for error in expected_errors)

def test_cli_dev_help_surfaces_check_as_default_contributor_gate() -> None:
    runner = CliRunner()
    root_help = runner.invoke(cli.app, ["--help"])
    dev_help = runner.invoke(cli.app, ["dev", "--help"])
    check_help = runner.invoke(cli.app, ["dev", "check", "--help"]); multi_focus = runner.invoke(cli.app, ["dev", "check", "--focused", "first_use_readiness", "--focused", "open_source_collaboration", "--list", "--json"])
    normalized_check_help = re.sub(r"\s+", " ", check_help.stdout)
    assert root_help.exit_code == 0, root_help.stdout
    assert "run local checks" in root_help.stdout
    assert dev_help.exit_code == 0, dev_help.stdout
    assert "check" in dev_help.stdout
    assert "Run the local default-fast verification gate" in dev_help.stdout
    assert (check_help.exit_code, multi_focus.exit_code, [guide["id"] for guide in json.loads(multi_focus.stdout)["selected_focused_guides"]]) == (0, 0, ["first_use_readiness", "open_source_collaboration"]), check_help.stdout
    assert "Advanced profile selector" in check_help.stdout
    assert "default-fast" in normalized_check_help
    assert "full local gate" in normalized_check_help
    assert "use --focused to run" in normalized_check_help
    assert "focused checks" in normalized_check_help
    assert "--list" in normalized_check_help
    assert "--focused" in normalized_check_help
    assert all(text in normalized_check_help for text in ("--pr-evidence", "copyable PR summary", "remaining focused or final", "evidence commands", "Repeat --focused"))
    assert "recommended" in normalized_check_help
    assert "all" in normalized_check_help
    for guide in FOCUSED_CHECK_GUIDES:
        assert guide.id in normalized_check_help
    assert "focused check" in normalized_check_help
    assert "guidance" in normalized_check_help
    assert "commands" in normalized_check_help


def test_cli_dev_reset_help_surfaces_app_scope() -> None:
    runner = CliRunner()

    reset_help = runner.invoke(cli.app, ["dev", "reset", "--help"])
    normalized_reset_help = re.sub(r"\s+", " ", reset_help.stdout)
    invalid = runner.invoke(cli.app, ["dev", "reset", "--language", "fr", "--json"])

    assert reset_help.exit_code == 0, reset_help.stdout
    assert all(term in normalized_reset_help for term in ("--scope", "[all|app]", "--language", "zh-CN"))
    assert invalid.exit_code == 1
    assert json.loads(invalid.stdout)["error"].startswith("invalid --language: expected one of: en, zh")


def test_cli_dev_reset_rejects_unknown_scope_before_planning_deletions(tmp_path: Path) -> None:
    runner = CliRunner()
    paths = create_reset_fixture(tmp_path)

    result = runner.invoke(cli.app, ["dev", "reset", "--scope", "workspace", "--workdir", str(paths["workdir"])])
    error_text = result_error_text(result)

    assert result.exit_code == 2
    assert "Invalid value for '--scope'" in error_text
    assert "'all', 'app'" in error_text
    assert "planned:" not in result.stdout


def test_cli_dev_reset_app_scope_missing_workdir_recovers_app_state_without_project_state(tmp_path: Path) -> None:
    runner, home = CliRunner(), tmp_path / "home"; home.mkdir()
    db, missing_workdir = home / "app.db", tmp_path / "missing project"
    db.write_text("legacy-db", encoding="utf-8"); common = ["dev", "reset", "--scope", "app", "--workdir", str(missing_workdir), "--json"]
    blocked = runner.invoke(cli.app, ["dev", "reset", "--workdir", str(missing_workdir), "--yes", "--json"], env={APP_HOME_ENV: str(home)})
    preview = runner.invoke(cli.app, common, env={APP_HOME_ENV: str(home)})
    result = runner.invoke(cli.app, [*common[:-1], "--yes", "--json"], env={APP_HOME_ENV: str(home)})
    assert blocked.exit_code == 1
    assert json.loads(blocked.stdout) == dev_workdir_error_payload("reset")
    assert preview.exit_code == 0, result_error_text(preview)
    preview_payload = json.loads(preview.stdout)
    assert preview_payload["workdir_state"]["status"] == "missing"
    assert (preview_payload["dev_reset_summary"]["next_action_kinds"], preview_payload["next_action_ready_now_kinds"], preview_payload["dev_reset_summary"]["next_action_ready_after_actions"]) == (["review_reset_scope", "apply_reset_after_review", "choose_project_for_readiness"], ["review_reset_scope"], {"apply_reset_after_review": "review_reset_scope", "choose_project_for_readiness": "apply_reset_after_review"})
    assert str(db) in preview_payload["planned"]
    assert result.exit_code == 0, result_error_text(result)
    payload = json.loads(result.stdout)
    assert (payload["dev_reset_summary"]["next_action_kinds"], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (["choose_project_for_readiness"], ["choose_project_for_readiness"], {})
    assert str(db) in payload["removed"]
    assert not db.exists()
    assert not missing_workdir.exists()


def test_cli_dev_reset_previews_then_removes_v3_development_state_without_deleting_unmanaged_files(tmp_path: Path) -> None:
    runner = CliRunner()
    paths = create_reset_fixture(tmp_path, include_unmanaged=True)
    workdir = paths["workdir"]
    home = paths["home"]
    db = paths["db"]
    managed_file = paths["managed"]
    unmanaged_file = paths["unmanaged"]

    preview = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert preview.exit_code == 0, result_error_text(preview)
    preview_payload = json.loads(preview.stdout)
    planned = set(preview_payload["planned"])
    skipped = set(preview_payload["skipped"])
    assert preview_payload["dev_reset_summary"]["schema_version"] == DEV_RESET_SUMMARY_SCHEMA_VERSION
    assert preview_payload["dev_reset_summary"]["scope"] == "all"
    preview_actions = preview_payload["next_actions"]
    assert preview_payload["dev_reset_summary"]["next_action_kinds"] == [action["kind"] for action in preview_actions] == [
        "review_reset_scope", "create_recovery_archive", "apply_reset_after_review", "confirm_readiness_after_reset",
    ]
    assert "unowned host files are skipped" in preview_actions[0]["scope_description"]
    assert (preview_actions[1]["private_content"], preview_actions[2]["destructive"]) == (True, True)
    assert (preview_actions[2]["after_action"], preview_payload["next_action_ready_now_kinds"], preview_payload["dev_reset_summary"]["next_action_ready_after_actions"]) == ("create_recovery_archive", ["review_reset_scope"], {"create_recovery_archive": "review_reset_scope", "apply_reset_after_review": "create_recovery_archive", "confirm_readiness_after_reset": "apply_reset_after_review"})
    assert "loopora dev reset --scope all --workdir" in preview_actions[2]["command"]
    assert "loopora doctor --workdir" in preview_actions[3]["command"]
    assert str(db) in planned
    assert str(workdir / ".loopora") in planned
    assert str(managed_file) in planned
    assert str(unmanaged_file) in skipped

    result = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--yes", "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert result.exit_code == 0, result_error_text(result)
    payload = json.loads(result.stdout)
    removed = set(payload["removed"])
    skipped = set(payload["skipped"])
    assert payload["dev_reset_summary"]["scope"] == "all"
    action = payload["next_actions"][0]
    assert (payload["dev_reset_summary"]["next_action_kinds"], [action["kind"]], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (["confirm_readiness"], ["confirm_readiness"], ["confirm_readiness"], {})
    assert "loopora doctor --workdir" in action["command"]
    assert str(db) in removed
    assert str(workdir / ".loopora") in removed
    assert str(managed_file) in removed
    assert str(unmanaged_file) in skipped
    assert not db.exists()
    assert not (workdir / ".loopora").exists()
    assert not managed_file.exists()
    assert unmanaged_file.exists()


def test_cli_dev_reset_app_scope_only_resets_local_app_database(tmp_path: Path) -> None:
    runner = CliRunner()
    paths = create_reset_fixture(tmp_path, include_wal=True)
    workdir = paths["workdir"]
    home = paths["home"]
    db = paths["db"]
    wal = paths["wal"]
    state_sentinel = paths["state"]
    managed_file = paths["managed"]

    preview = runner.invoke(
        cli.app,
        ["dev", "reset", "--scope", "app", "--workdir", str(workdir), "--language", "zh-CN", "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert preview.exit_code == 0, result_error_text(preview)
    preview_payload = json.loads(preview.stdout)
    planned = set(preview_payload["planned"])
    assert (preview_payload["dev_reset_summary"]["scope"], "language" in preview_payload) == ("app", False)
    assert "managed Agent entries are left alone" in preview_payload["scope_description"]
    assert str(db) in planned
    assert str(wal) in planned
    assert str(workdir / ".loopora") not in planned
    assert str(managed_file) not in planned
    assert db.exists()
    assert wal.exists()
    assert state_sentinel.exists()
    assert managed_file.exists()

    result = runner.invoke(
        cli.app,
        ["dev", "reset", "--scope", "app", "--workdir", str(workdir), "--yes", "--language", "中文", "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert result.exit_code == 0, result_error_text(result)
    payload = json.loads(result.stdout)
    removed = set(payload["removed"])
    assert (payload["dev_reset_summary"]["scope"], "language" in payload) == ("app", False)
    assert str(db) in removed
    assert str(wal) in removed
    assert str(workdir / ".loopora") not in removed
    assert str(managed_file) not in removed
    assert not db.exists()
    assert not wal.exists()
    assert state_sentinel.exists()
    assert managed_file.exists()


def test_cli_dev_reset_app_scope_plain_output_names_database_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
    runner, paths = CliRunner(), create_reset_fixture(tmp_path)

    args = ["dev", "reset", "--scope", "app", "--workdir", str(paths["workdir"])]
    result = runner.invoke(cli.app, args, env={APP_HOME_ENV: str(paths["home"])})
    localized = runner.invoke(cli.app, [*args, "--language", "zh-CN"], env={APP_HOME_ENV: str(paths["home"])})
    assert result.exit_code == localized.exit_code == 0, result_error_text(result)
    assert all(snippet in result.stdout for snippet in ("scope: app", "planned local App database files", "scope_boundary:", "managed Agent entries are left alone", "recovery_archive_before_reset:", "apply only after it succeeds:", "then confirm readiness:"))
    assert all(snippet in localized.stdout for snippet in ("开发状态重置预览", "范围边界：", "重置前私有恢复归档：", "检查成功后才能应用", "然后确认就绪"))
    assert localized.stdout.count("--language zh") >= 3
    assert (
        f"{APP_HOME_ENV}={shlex.quote(str(paths['home']))} {source_entry} dev reset "
        f"--scope app --workdir {shlex.quote(str(paths['workdir']))} --yes"
    ) in result.stdout


def test_cli_dev_reset_apply_returns_to_doctor_readiness_checkpoint(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
    runner, paths = CliRunner(), create_reset_fixture(tmp_path)
    args = ["dev", "reset", "--scope", "app", "--workdir", str(paths["workdir"]), "--yes"]
    result = runner.invoke(cli.app, args, env={APP_HOME_ENV: str(paths["home"])})

    assert result.exit_code == 0, result_error_text(result)
    assert "Loopora v3 development reset complete" in result.stdout
    assert "removed_count: 1" in result.stdout
    assert "next: rerun " in result.stdout
    assert f"{APP_HOME_ENV}={shlex.quote(str(paths['home']))}" in result.stdout
    assert f"{source_entry} doctor --workdir {paths['workdir']}" in result.stdout
    assert "confirm local readiness before opening Web or running /loopora-plan" in result.stdout


def test_cli_dev_reset_preview_with_no_planned_items_does_not_prompt_apply(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir, home = tmp_path / "project", tmp_path / "home"
    workdir.mkdir()
    home.mkdir()

    app_scope = runner.invoke(
        cli.app,
        ["dev", "reset", "--scope", "app", "--workdir", str(workdir), "--json"],
        env={APP_HOME_ENV: str(home)},
    )
    all_scope = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir)],
        env={APP_HOME_ENV: str(home)},
    )

    assert app_scope.exit_code == 0, result_error_text(app_scope)
    app_payload = json.loads(app_scope.stdout)
    assert (app_payload["dev_reset_summary"]["next_action_kinds"], app_payload["next_action_ready_now_kinds"], app_payload["next_action_ready_after_actions"]) == (["no_reset_needed"], ["no_reset_needed"], {})
    assert app_payload["next_actions"] == [{"kind": "no_reset_needed"}]

    assert all_scope.exit_code == 0, result_error_text(all_scope)
    assert all(
        snippet in all_scope.stdout
        for snippet in ("planned_count: 0", "next: nothing to delete; no --yes reset is needed for Loopora-owned development state")
    )
    assert all(snippet not in all_scope.stdout for snippet in ("apply only if acceptable:", "rerun with --yes"))


def test_cli_dev_reset_apply_noop_still_points_back_to_readiness(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "project"
    home = tmp_path / "home"
    workdir.mkdir()
    home.mkdir()

    result = runner.invoke(
        cli.app,
        ["dev", "reset", "--scope", "app", "--workdir", str(workdir), "--yes"],
        env={APP_HOME_ENV: str(home)},
    )

    assert result.exit_code == 0, result_error_text(result)
    assert "removed_count: 0" in result.stdout
    assert "next: no files were removed; rerun " in result.stdout
    assert f"{APP_HOME_ENV}={shlex.quote(str(home))}" in result.stdout
    assert f"loopora doctor --workdir {workdir}" in result.stdout


def test_cli_recovery_archive_round_trip_keeps_unknown_state_and_refuses_conflicts(monkeypatch, tmp_path: Path) -> None:
    home, workdir, archive = tmp_path / "home", tmp_path / "project", tmp_path / "recovery.zip"
    workdir.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    LooporaRepository(home / "app.db")
    (home / "bundles" / "bundle_demo").mkdir(parents=True)
    (home / "bundles" / "bundle_demo" / "bundle.yml").write_text("bundle\n", encoding="utf-8")
    (home / "logs").mkdir()
    (home / "logs" / "service.log").write_text("private log\n", encoding="utf-8")
    managed = workdir / ".loopora" / "runs" / "run_demo" / "summary.md"
    managed.parent.mkdir(parents=True)
    managed.write_text("evidence\n", encoding="utf-8")
    unknown = workdir / ".loopora" / "visual-review" / "screenshot.txt"
    unknown.parent.mkdir(parents=True)
    unknown.write_text("keep me\n", encoding="utf-8")
    runner = CliRunner()
    root_help = runner.invoke(cli.app, ["--help"])
    assert root_help.exit_code == 0
    assert "recovery" in root_help.stdout
    assert f"{agent_adapter_command_prefix.current_project_file_loopora_cli_entry()} recovery" in " ".join(root_help.stdout.split())

    created = runner.invoke(
        cli.app,
        ["recovery", "create", "--workdir", str(workdir), "--output", str(archive), "--json"],
    )
    assert created.exit_code == 0, result_error_text(created)
    payload = json.loads(created.stdout)
    assert (payload["status"], payload["public_safe"], payload["content_scope"]) == (
        "created",
        False,
        "private_full_recovery",
    )
    with ZipFile(archive) as recovery_zip:
        names = set(recovery_zip.namelist())
    assert "app/app.db" in names
    assert "app/bundles/bundle_demo/bundle.yml" in names
    assert "project/.loopora/runs/run_demo/summary.md" in names
    assert all("logs" not in name and "visual-review" not in name for name in names)

    inspected = runner.invoke(cli.app, ["recovery", "inspect", str(archive), "--json"])
    assert inspected.exit_code == 0, result_error_text(inspected)
    assert json.loads(inspected.stdout)["database_schema_version"] == 3
    (home / "app.db").unlink()
    shutil.rmtree(home / "bundles")
    shutil.rmtree(workdir / ".loopora" / "runs")
    preview = runner.invoke(
        cli.app,
        ["recovery", "restore", str(archive), "--workdir", str(workdir), "--json"],
    )
    assert preview.exit_code == 0, result_error_text(preview)
    assert json.loads(preview.stdout)["status"] == "preview"
    assert not (home / "app.db").exists()
    restored = runner.invoke(
        cli.app,
        ["recovery", "restore", str(archive), "--workdir", str(workdir), "--yes", "--json"],
    )
    assert restored.exit_code == 0, result_error_text(restored)
    assert json.loads(restored.stdout)["status"] == "restored"
    assert managed.read_text(encoding="utf-8") == "evidence\n"
    assert unknown.read_text(encoding="utf-8") == "keep me\n"

    managed.write_text("newer evidence\n", encoding="utf-8")
    blocked = runner.invoke(
        cli.app,
        ["recovery", "restore", str(archive), "--workdir", str(workdir), "--yes", "--json"],
    )
    assert blocked.exit_code == 1
    assert json.loads(blocked.stdout)["status"] == "blocked"
    assert managed.read_text(encoding="utf-8") == "newer evidence\n"


def test_cli_recovery_inspect_rejects_tampered_content(monkeypatch, tmp_path: Path) -> None:
    home, workdir = tmp_path / "home", tmp_path / "project"
    workdir.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    LooporaRepository(home / "app.db")
    archive, tampered = tmp_path / "recovery.zip", tmp_path / "tampered.zip"
    result = CliRunner().invoke(
        cli.app,
        ["recovery", "create", "--workdir", str(workdir), "--output", str(archive), "--json"],
    )
    assert result.exit_code == 0, result_error_text(result)
    with ZipFile(archive) as source, ZipFile(tampered, "w", compression=ZIP_DEFLATED) as target:
        for name in source.namelist():
            content = b"not sqlite" if name == "app/app.db" else source.read(name)
            target.writestr(name, content)
    inspected = CliRunner().invoke(cli.app, ["recovery", "inspect", str(tampered), "--json"])
    assert inspected.exit_code == 1
    assert "mismatch: app/app.db" in inspected.stdout
    active_home = tmp_path / "active-home"
    active_home.mkdir()
    with sqlite3.connect(active_home / "app.db") as connection:
        connection.executescript("CREATE TABLE loop_runs (status TEXT); INSERT INTO loop_runs VALUES ('running');")
    monkeypatch.setenv(APP_HOME_ENV, str(active_home))
    blocked = CliRunner().invoke(cli.app, ["recovery", "create", "--workdir", str(workdir), "--json"])
    assert blocked.exit_code == 1
    assert "stop active Runs" in blocked.stdout
