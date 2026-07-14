from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix
from loopora import cli, dev_check as dev_check_module
from loopora.dev_check import FOCUSED_CHECK_GUIDES, FOCUSED_PROFILE, DevCheckCommandResult, run_dev_check
from cli_dev_command_test_support import (
    cli_dev_check_command as _cli_dev_check_command,
    cli_focused_dev_check_command as _cli_focused_dev_check_command,
    dev_check_command as _dev_check_command,
    dev_check_list_command as _dev_check_list_command,
    focused_command_targets as _focused_command_targets,
    focused_dev_check_command as _focused_dev_check_command,
)


ROOT = Path(__file__).resolve().parents[3]


def _paths(text: str) -> list[str]:
    return text.split()


def test_verification_map_keeps_default_fast_gate_aligned_with_ci() -> None:
    text = (ROOT / "tests" / "README.md").read_text(encoding="utf-8")

    missing_fragments = [
        fragment
        for fragment in (
            "Dependency compatibility, static JS syntax, Ruff, whitespace-safe diff, package build, and contract checks",
            "uv run loopora dev check",
            "loopora dev check --list",
            "uv run loopora dev check --focused recommended",
            "loopora dev check --focused recommended",
            "--focused <guide-id>",
            "focused selector choices",
            "current selectors: `recommended`, `all`, and guide IDs",
            "--changed-file <path>",
            "explicit paths instead of Git",
            "absolute paths under `--workdir`",
            "project-relative paths",
            "ignored changed files",
            "ignored changed files: none",
            "`PR evidence:` reminder",
            "recommended focused checks",
            "changed files that do not match any focused guide",
            "unmatched changed files: none",
            "paste the final `### Loopora PR Evidence` block",
            "remaining recommended guide IDs",
            "already-passed guide IDs",
            "main local evidence block for decision scope",
            "unmatched changed files",
            "additional focused, journey, review, or probe evidence",
            "boundary-relevant guide IDs you skipped with a reason",
            "changed-file detection status",
            "Focused Check Guide",
            "First-use readiness and local recovery",
            "Web routes, templates, and static assets",
            "Agent Native plan/run surfaces",
            "Alignment and bundle compiler behavior",
            "Core execution, context, and provider boundaries",
            "Run lifecycle and local runtime state",
            "Open-source collaboration, review/scenario evidence workflows, and distribution",
            "authoritative source for the current executable default-fast commands",
            "dependency lock dry-run",
            "dependency compatibility",
            "static JavaScript syntax",
            "Ruff",
            "whitespace-safe diff",
            "package build",
            "contract checks",
            "Run package-build through `loopora dev check`",
            "src/loopora.egg-info",
            "console script entry point",
            "python -m loopora",
            "module entry",
            "source package manifest",
            "public project URLs",
            "contributor/maintainer identity metadata",
            "public discovery keywords/classifiers",
            "public design documents",
            "Python requirement metadata",
            "runtime dependency metadata",
            "no-license-declared boundary",
        )
        if fragment not in text
    ]
    assert missing_fragments == []
    for guide_id in (
        "first_use_readiness",
        "web_surfaces",
        "agent_native",
        "alignment_bundle",
        "core_execution",
        "runtime_state",
        "open_source_collaboration",
    ):
        assert f"`{guide_id}`" in text
        assert f"uv run loopora dev check --focused {guide_id}" in text
    assert "prints the current expanded pytest commands" in text
    assert "tests/checks/contracts/test_agent_native_compacted_01.py tests/checks/contracts/test_cli_agent_compacted_01.py" not in text
    assert "tests/checks/contracts/test_runner_acceptance_architecture.py tests/checks/contracts/test_runner_recovery_architecture.py" not in text
    assert "uv run ruff check ." not in text
    assert "rm -rf tmp/package-check" not in text
    assert "mkdir -p tmp/package-check" not in text


def test_focused_check_guide_commands_reference_existing_targets() -> None:
    missing_targets = [
        f"{guide.id}: {target.as_posix()}"
        for guide in FOCUSED_CHECK_GUIDES
        for target in _focused_command_targets(guide.command)
        if not (ROOT / target).exists()
    ]

    assert missing_targets == []


def test_dev_check_recommends_focused_guides_for_changed_paths(tmp_path: Path) -> None:
    changed_files = _paths(
        "src/loopora/diagnose_doctor.py src/loopora/first_use_route_readiness.py src/loopora/cli_fit_output.py "
        "src/loopora/start_guidance.py src/loopora/static/pages/tools.js src/loopora/support_guidance.py "
        "tests/checks/contracts/app_state_recovery_test_support.py tests/checks/contracts/cli_shell_recovery_test_support.py "
        "src/loopora/service_run_lifecycle.py "
        "src/loopora/settings_recent_workdirs.py .github/pull_request_template.md CODE_OF_CONDUCT.md CHANGELOG.md "
        "CONTRIBUTING.md GOVERNANCE.md MANIFEST.in assets/diagrams/first-run-path.en.svg "
        "src/loopora/dev_check_guides.py tests/reviews/run.py docs/notes.md"
    )
    payload = run_dev_check(
        workdir=tmp_path,
        list_only=True,
        changed_files=changed_files,
    )

    recommended = payload["recommended_focused_guides"]
    assert payload["dev_check_summary"]["changed_file_count"] == 20
    assert payload["changed_file_detection"] == {"source": "provided", "status": "provided", "count": 20}
    assert payload["dev_check_summary"]["recommended_focused_guide_count"] == 4
    assert payload["dev_check_summary"]["unmatched_changed_file_count"] == 1
    expected_next_actions = ["review_unmatched_changed_files", "run_recommended_focused_checks", "run_default_fast_gate"]
    assert (
        payload["next_action_kinds"],
        payload["dev_check_summary"]["next_action_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["dev_check_summary"]["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
    ) == (
        expected_next_actions,
        expected_next_actions,
        expected_next_actions,
        expected_next_actions,
        {},
        [],
    )
    expected_guide_ids = [
        "first_use_readiness",
        "web_surfaces",
        "runtime_state",
        "open_source_collaboration",
    ]
    assert [guide["id"] for guide in recommended] == expected_guide_ids
    assert recommended[0]["matched_files"] == sorted(changed_files[:8])
    assert recommended[0]["matched_file_count"] == 8
    assert recommended[0]["omitted_matched_file_count"] == 0
    assert recommended[1]["matched_files"] == ["src/loopora/static/pages/tools.js"]
    assert recommended[1]["matched_file_count"] == 1
    assert recommended[1]["omitted_matched_file_count"] == 0
    assert recommended[2]["matched_files"] == ["src/loopora/service_run_lifecycle.py", "src/loopora/settings_recent_workdirs.py"]
    assert recommended[2]["matched_file_count"] == 2
    assert recommended[2]["omitted_matched_file_count"] == 0
    assert "assets/diagrams/first-run-path.en.svg" in recommended[3]["matched_files"]
    assert "CODE_OF_CONDUCT.md" in recommended[3]["matched_files"]
    assert "CHANGELOG.md" in recommended[3]["matched_files"]
    assert "GOVERNANCE.md" in recommended[3]["matched_files"]
    assert "src/loopora/dev_check_guides.py" in recommended[3]["matched_files"]
    assert "tests/reviews/run.py" in recommended[3]["matched_files"]
    assert recommended[3]["matched_file_count"] == 10
    assert recommended[3]["omitted_matched_file_count"] == 0
    assert "tests/checks/contracts/test_verification_map.py" in recommended[3]["command"]
    assert payload["unmatched_changed_files"] == ["docs/notes.md"]
    assert payload["unmatched_changed_file_count"] == 1
    assert payload["omitted_unmatched_changed_file_count"] == 0
    assert "uv run pytest" in recommended[0]["command"]
    assert payload["next_actions"][0] == {
        "kind": "review_unmatched_changed_files",
        "files": ["docs/notes.md"],
        "file_count": 1,
        "omitted_file_count": 0,
    }
    assert payload["next_actions"][1]["kind"] == "run_recommended_focused_checks"
    assert payload["next_actions"][1]["guide_ids"] == expected_guide_ids
    assert payload["next_actions"][1]["command"] == _focused_dev_check_command(
        tmp_path,
        "recommended",
        payload["changed_files"],
    )
    assert payload["next_actions"][2] == {"kind": "run_default_fast_gate", "command": _dev_check_command(tmp_path)}


def test_dev_check_focused_recommended_skips_when_no_guides_match(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0)

    result = run_dev_check(
        workdir=tmp_path,
        focused="recommended",
        changed_files=["docs/notes.md"],
        command_runner=fake_runner,
    )

    assert result["profile"] == FOCUSED_PROFILE
    assert result["status"] == "skipped"
    assert result["ready"] is True
    assert result["steps"] == []
    assert result["selected_focused_guides"] == []
    assert calls == []
    assert result["dev_check_summary"]["no_recommended_focused_check_reason"] == "unmatched_changed_files"
    assert result["no_recommended_focused_check_reason"] == {
        "reason": "unmatched_changed_files",
        "changed_file_source": "provided",
        "changed_file_status": "provided",
        "changed_file_count": 1,
        "ignored_changed_file_count": 0,
        "unmatched_changed_file_count": 1,
    }
    assert result["dev_check_summary"]["unmatched_changed_file_count"] == 1
    assert (
        result["next_action_kinds"],
        result["dev_check_summary"]["next_action_kinds"],
        result["next_action_ready_now_kinds"],
        result["dev_check_summary"]["next_action_ready_now_kinds"],
        result["next_action_ready_after_actions"],
    ) == (
        ["review_unmatched_changed_files", "no_recommended_focused_checks", "review_focused_check_guide", "run_default_fast_gate"],
        ["review_unmatched_changed_files", "no_recommended_focused_checks", "review_focused_check_guide", "run_default_fast_gate"],
        ["review_unmatched_changed_files", "no_recommended_focused_checks", "review_focused_check_guide", "run_default_fast_gate"],
        ["review_unmatched_changed_files", "no_recommended_focused_checks", "review_focused_check_guide", "run_default_fast_gate"],
        {},
    )
    assert result["next_actions"] == [
        {
            "kind": "review_unmatched_changed_files",
            "files": ["docs/notes.md"],
            "file_count": 1,
            "omitted_file_count": 0,
        },
        {
            "kind": "no_recommended_focused_checks",
            "reason": "unmatched_changed_files",
            "changed_file_source": "provided",
            "changed_file_status": "provided",
            "changed_file_count": 1,
            "ignored_changed_file_count": 0,
            "unmatched_changed_file_count": 1,
        },
        {"kind": "review_focused_check_guide", "command": _dev_check_list_command(tmp_path, ["docs/notes.md"])},
        {"kind": "run_default_fast_gate", "command": _dev_check_command(tmp_path)},
    ]


def test_cli_dev_check_accepts_provided_relative_and_absolute_changed_files_without_git(tmp_path: Path) -> None:
    absolute_changed_file = tmp_path / "src" / "loopora" / "diagnose_doctor.py"
    outside_changed_file = tmp_path.parent / "outside.py"
    changed_files = [str(absolute_changed_file), "docs/product notes.md", str(outside_changed_file)]
    changed_file_args = [item for path in changed_files for item in ("--changed-file", path)]
    normalized_changed_files = ["docs/product notes.md", "src/loopora/diagnose_doctor.py"]
    args = ["dev", "check", "--workdir", str(tmp_path), "--list", *changed_file_args]
    runner = CliRunner()

    json_result = runner.invoke(cli.app, [*args, "--json"])
    payload = json.loads(json_result.stdout)
    plain = runner.invoke(cli.app, args)

    assert json_result.exit_code == 0, json_result.stdout
    assert payload["changed_files"] == normalized_changed_files
    assert payload["changed_file_detection"] == {"source": "provided", "status": "provided", "count": 2}
    assert payload["dev_check_summary"]["changed_file_source"] == "provided"
    assert payload["dev_check_summary"]["changed_file_status"] == "provided"
    assert payload["ignored_changed_files"] == [str(outside_changed_file)]
    assert payload["ignored_changed_file_count"] == 1
    assert [guide["id"] for guide in payload["recommended_focused_guides"]] == ["first_use_readiness"]
    assert payload["recommended_focused_guides"][0]["matched_files"] == ["src/loopora/diagnose_doctor.py"]
    assert payload["unmatched_changed_files"] == ["docs/product notes.md"]
    assert payload["next_actions"][0]["kind"] == "review_ignored_changed_files"
    assert payload["next_actions"][1]["kind"] == "review_unmatched_changed_files"
    assert payload["next_actions"][2] == {
        "kind": "run_recommended_focused_checks",
        "guide_ids": ["first_use_readiness"],
        "command": _cli_focused_dev_check_command(tmp_path, "recommended", normalized_changed_files),
    }
    assert payload["next_actions"][3] == {"kind": "run_default_fast_gate", "command": _cli_dev_check_command(tmp_path)}

    assert plain.exit_code == 0, plain.stdout
    assert "changes: provided changed files (2 file(s))" in plain.stdout
    assert "ignored changed files:" in plain.stdout
    assert "- first_use_readiness (focused): First-use readiness and local recovery" in plain.stdout
    assert "matched: src/loopora/diagnose_doctor.py" in plain.stdout
    assert "unmatched changed files: docs/product notes.md" in plain.stdout
    assert "PR evidence: record recommended guide IDs (first_use_readiness)" in plain.stdout
    assert _cli_focused_dev_check_command(tmp_path, "recommended", normalized_changed_files) in plain.stdout
    assert str(tmp_path) not in plain.stdout.replace(str(tmp_path.resolve()), "")
    ignored_only = run_dev_check(workdir=tmp_path, focused="recommended", changed_files=[str(outside_changed_file)])
    assert ignored_only["no_recommended_focused_check_reason"]["reason"] == "ignored_changed_files"
    assert ignored_only["next_actions"][0]["kind"] == "review_ignored_changed_files"


def test_dev_check_git_detection_projects_exact_unstaged_renames_to_new_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    old = repo / "tests/checks/contracts" / ("test_public_agent_" + "runner_docs.py")
    new = repo / "tests/checks/contracts/test_public_agent_native_docs.py"
    old.parent.mkdir(parents=True)
    old.write_text("Agent Runner capability contract\nstable docs evidence\n", encoding="utf-8")
    subprocess.run(("git", "init"), cwd=repo, check=True, capture_output=True)
    subprocess.run(("git", "add", "."), cwd=repo, check=True, capture_output=True)
    subprocess.run(("git", "-c", "user.email=a@b.c", "-c", "user.name=Tester", "commit", "-m", "init"), cwd=repo, check=True, capture_output=True)
    old.rename(new)
    new.write_text("Agent Native capability contract\nstable docs evidence\n", encoding="utf-8")
    payload = run_dev_check(workdir=repo, list_only=True, focused_ran=["recommended"])
    assert payload["changed_files"] == ["tests/checks/contracts/test_public_agent_native_docs.py"]
    assert ([guide["id"] for guide in payload["recommended_focused_guides"]], payload["unmatched_changed_files"]) == (["open_source_collaboration"], [])
    assert (payload["focused_ran_guide_ids"], payload["dev_check_summary"]["focused_ran_guide_ids"]) == ([], [])


def test_dev_check_maps_runtime_state_and_group_help_to_existing_boundaries(tmp_path: Path) -> None:
    payload = run_dev_check(
        workdir=tmp_path,
        list_only=True,
        changed_files=_paths(
            "src/loopora/cli_group_help.py src/loopora/cli_common.py src/loopora/web.py src/loopora/token_security.py "
            "src/loopora/db_loop_records.py src/loopora/db.py src/loopora/service.py src/loopora/service_run_acceptance.py "
            "src/loopora/service_runner_failure_handling.py src/loopora/branding.py src/loopora/db_alignment_records.py "
            "src/loopora/db_bundle_graph_records.py src/loopora/db_bundle_records.py tests/checks/contracts/test_runner_failure_lifecycle.py "
            "tests/checks/contracts/agent_adapter_expected.py tests/checks/contracts/agent_native_cli_test_support.py "
            "tests/checks/contracts/alignment_test_support.py tests/checks/contracts/context_architecture_test_support.py "
            "tests/checks/contracts/executor_architecture_test_support.py tests/checks/contracts/kernel/kernel_architecture_test_support.py "
            "tests/checks/contracts/web_api_test_support.py"
        ),
    )
    recommended = payload["recommended_focused_guides"]

    assert [guide["id"] for guide in recommended] == [
        "first_use_readiness",
        "web_surfaces",
        "agent_native",
        "alignment_bundle",
        "core_execution",
        "runtime_state",
    ]
    commands = {guide["id"]: guide["command"] for guide in recommended}
    matched = {guide["id"]: set(guide["matched_files"]) for guide in recommended}
    assert matched["first_use_readiness"] >= {"src/loopora/cli_common.py", "src/loopora/cli_group_help.py"}
    assert matched["web_surfaces"] >= {"src/loopora/web.py", "tests/checks/contracts/web_api_test_support.py"}
    assert matched["agent_native"] >= {"tests/checks/contracts/agent_native_cli_test_support.py"}
    assert matched["alignment_bundle"] >= {"src/loopora/db_alignment_records.py", "tests/checks/contracts/alignment_test_support.py"}
    assert "tests/checks/contracts/context_architecture_test_support.py" in matched["core_execution"]
    assert "tests/checks/contracts/test_executor_alignment_fixture_architecture.py" in commands["core_execution"]
    assert matched["runtime_state"] >= {"src/loopora/db.py", "src/loopora/service_runner_failure_handling.py"}
    assert payload["unmatched_changed_files"] == []


def test_dev_check_recommends_loop_recovery_helper_boundaries(tmp_path: Path) -> None:
    loop_recovery_files = _paths(
        "src/loopora/cli_agent_runtime_commands.py src/loopora/cli_first_task_handoff.py "
        "src/loopora/cli_loop_spec_recovery.py src/loopora/cli_loop_workdir_recovery.py src/loopora/cli_options.py "
        "src/loopora/cli_shared.py tests/checks/contracts/cli_loop_resource_command_test_support.py "
        "tests/checks/contracts/test_cli_loop_resource_commands.py"
    )
    single_path_case = lambda path, guides: ([path], guides, {guide: [path] for guide in guides})
    cases = [
        (
            loop_recovery_files,
            ["first_use_readiness", "agent_native"],
            {"first_use_readiness": loop_recovery_files, "agent_native": loop_recovery_files[:2]},
        ),
        single_path_case("src/loopora/workdir_inputs.py", ["first_use_readiness", "web_surfaces", "runtime_state"]),
        single_path_case("src/loopora/cli_resource_projection.py", ["first_use_readiness", "alignment_bundle"]),
        single_path_case("src/loopora/cli_resource_recovery.py", ["first_use_readiness", "alignment_bundle"]),
        single_path_case("src/loopora/cli_status_commands.py", ["first_use_readiness", "runtime_state"]),
        single_path_case("src/loopora/existing_work_status.py", ["first_use_readiness", "web_surfaces", "alignment_bundle", "runtime_state"]),
        single_path_case("tests/checks/contracts/test_task_role_governance_asset_contract.py", ["alignment_bundle"]),
    ]
    cases.extend(
        single_path_case(path, ["first_use_readiness", "web_surfaces"])
        for path in ("src/loopora/spec_recovery_commands.py", "src/loopora/first_use_web_guidance.py")
    )
    cases.append(single_path_case("src/loopora/action_readiness_projection.py", ["first_use_readiness", "web_surfaces", "alignment_bundle", "runtime_state"]))
    for changed_files, expected_guide_ids, expected_matches in cases:
        payload = run_dev_check(workdir=tmp_path, list_only=True, changed_files=changed_files)
        recommended = payload["recommended_focused_guides"]
        assert [guide["id"] for guide in recommended] == expected_guide_ids
        assert payload["unmatched_changed_files"] == []
        assert {guide["id"]: guide["matched_files"] for guide in recommended} == expected_matches


def test_dev_check_recommends_runtime_state_for_run_start_error_boundaries(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0, stdout="runtime ok\n")

    result = run_dev_check(
        workdir=tmp_path,
        focused="recommended",
        changed_files=_paths(
            "src/loopora/run_result_recording.py src/loopora/run_worker_start.py "
            "src/loopora/service_runner_failure_handling.py src/loopora/service_types.py "
            "tests/checks/contracts/test_cli_run_task_verdict_output.py tests/checks/contracts/test_runner_failure_lifecycle.py "
            "tests/checks/contracts/test_runner_run_registration_cleanup.py docs/notes.md"
        ),
        command_runner=fake_runner,
    )

    assert (result["profile"], result["status"], result["dev_check_summary"]["unmatched_changed_file_count"]) == (FOCUSED_PROFILE, "pass", 1)
    assert [guide["id"] for guide in result["selected_focused_guides"]] == ["runtime_state"]
    assert [step["id"] for step in result["steps"]] == ["focused:runtime_state"]
    assert len(calls) == 1
    assert "tests/checks/contracts/test_cli_run_task_verdict_output.py" in calls[0]
    assert "tests/checks/contracts/test_runner_failure_lifecycle.py" in calls[0]
    assert "tests/checks/contracts/test_runner_run_registration_cleanup.py" in calls[0]
    next_actions = result["next_actions"]
    assert [action["kind"] for action in next_actions] == [
        "focused_checks_passed",
        "review_unmatched_changed_files",
        "run_final_pr_evidence_gate",
        "run_default_fast_gate",
    ]
    assert (next_actions[1]["files"], next_actions[2]["guide_ids"]) == (["docs/notes.md"], ["runtime_state"])
    assert all(fragment in next_actions[2]["command"] for fragment in ("--pr-evidence", "--changed-file docs/notes.md", "--focused-ran runtime_state"))
    run_web_files = _paths(
        "src/loopora/web_home_attention.py src/loopora/web_route_run_api.py src/loopora/web_run_artifact_api.py "
        "src/loopora/web_run_dispatch.py src/loopora/web_task_verdict_overviews.py src/loopora/web_timeline_run_events.py"
    )
    payload = run_dev_check(workdir=tmp_path, list_only=True, changed_files=run_web_files)
    matches = {guide["id"]: guide["matched_files"] for guide in payload["recommended_focused_guides"]}
    assert [guide["id"] for guide in payload["recommended_focused_guides"]] == ["web_surfaces", "alignment_bundle", "runtime_state"]
    assert (matches["alignment_bundle"], matches["runtime_state"], payload["unmatched_changed_files"]) == (["src/loopora/web_home_attention.py"], run_web_files, [])


def test_dev_check_recommends_runtime_state_for_local_state_splits(tmp_path: Path) -> None:
    changed_files = _paths(
        "src/loopora/db_local_asset_records.py src/loopora/db_run_slots.py src/loopora/event_redaction_audit_files.py "
        "src/loopora/local_workdir_artifacts.py src/loopora/service_local_asset_diagnostics.py "
        "src/loopora/service_local_asset_orphans.py src/loopora/service_loop_prompt_files.py src/loopora/utils.py "
        "tests/checks/contracts/test_cleanup_diagnostics.py tests/checks/contracts/test_event_redaction_audit_architecture.py "
        "tests/checks/contracts/test_runner_inspect_first_workflow_preset.py "
        "tests/checks/contracts/test_runner_local_execution.py tests/checks/contracts/test_runner_prompt_artifact_recovery.py "
        "tests/checks/contracts/test_runner_triage_fast_lane_workflow_presets.py "
        "tests/checks/contracts/test_settings_payload_normalization.py"
    )
    payload = run_dev_check(workdir=tmp_path, list_only=True, changed_files=changed_files)

    recommended = payload["recommended_focused_guides"]
    assert [guide["id"] for guide in recommended] == ["runtime_state"]
    assert (recommended[0]["matched_file_count"], recommended[0]["omitted_matched_file_count"]) == (len(changed_files), 3)
    assert set(recommended[0]["matched_files"]) <= set(changed_files)
    assert "tests/checks/contracts/test_cleanup_diagnostics.py" in recommended[0]["matched_files"]
    assert (payload["unmatched_changed_files"], payload["dev_check_summary"]["unmatched_changed_file_count"]) == ([], 0)
    command = recommended[0]["command"]
    assert "tests/checks/contracts/test_cleanup_diagnostics.py" in command
    assert "tests/checks/contracts/test_web_local_asset_diagnostics.py" in command
    assert "tests/checks/contracts/test_cli_diagnose_event_redaction_fix.py" in command
    assert "tests/checks/contracts/test_cli_diagnose_event_redaction_orphans.py" in command
    assert "tests/checks/contracts/test_event_redaction_audit_architecture.py" in command
    assert "tests/checks/contracts/test_settings_payload_normalization.py" in command
    assert "tests/checks/contracts/test_runner_prompt_artifact_recovery.py" in command


def test_dev_check_maps_app_state_readiness_to_cli_web_and_runtime_boundaries(tmp_path: Path) -> None:
    path = "src/loopora/app_state_readiness.py"
    payload = run_dev_check(workdir=tmp_path, list_only=True, changed_files=[path])

    matches = {guide["id"]: guide["matched_files"] for guide in payload["recommended_focused_guides"]}
    assert list(matches) == ["first_use_readiness", "web_surfaces", "runtime_state"]
    assert matches == {guide_id: [path] for guide_id in matches}
    assert (payload["unmatched_changed_files"], payload["dev_check_summary"]["unmatched_changed_file_count"]) == ([], 0)


def test_dev_check_recommends_agent_native_for_agent_run_recovery_boundaries(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0, stdout="agent recovery ok\n")

    result = run_dev_check(
        workdir=tmp_path,
        focused="recommended",
        changed_files=_paths(
            "src/loopora/service_agent_entry_projection.py src/loopora/service_agent_loop_start.py "
            "src/loopora/service_agent_loop_start_bindings.py tests/checks/contracts/test_agent_next_dispatch_recovery_commands.py "
            "tests/checks/contracts/test_agent_run_context_choice_payloads.py tests/checks/contracts/test_system_prompt_asset_ownership.py "
            "tests/checks/contracts/test_agent_work_panel_task_proof.py"
        ),
        command_runner=fake_runner,
    )

    assert (result["profile"], result["status"], result["dev_check_summary"]["unmatched_changed_file_count"]) == (FOCUSED_PROFILE, "pass", 0)
    assert ([guide["id"] for guide in result["selected_focused_guides"]], [step["id"] for step in result["steps"]]) == (
        ["agent_native"],
        ["focused:agent_native"],
    )
    assert len(calls) == 1
    assert all(
        target in calls[0]
        for target in (
            "tests/checks/contracts/test_agent_native_compacted_01.py",
            "tests/checks/contracts/test_agent_next_dispatch_recovery_commands.py",
            "tests/checks/contracts/test_agent_run_context_choice_payloads.py",
            "tests/checks/contracts/test_agent_run_context_choice_recovery_projection.py",
            "tests/checks/contracts/test_cli_recoverable_context_terminal_choices.py",
            "tests/checks/contracts/test_system_prompt_asset_ownership.py",
            "tests/checks/contracts/test_agent_work_panel_task_proof.py",
        )
    )
    assert ([action["kind"] for action in result["next_actions"]], result["next_actions"][1]["guide_ids"]) == (
        ["focused_checks_passed", "run_final_pr_evidence_gate", "run_default_fast_gate"],
        ["agent_native"],
    )
    assert all(flag in result["next_actions"][1]["command"] for flag in ("--pr-evidence", "--focused-ran agent_native"))


def test_dev_check_maps_compose_runtime_and_resource_paths_to_existing_boundaries(tmp_path: Path) -> None:
    payload = run_dev_check(
        workdir=tmp_path,
        list_only=True,
        changed_files=_paths(
            "src/loopora/cli_orchestration_commands.py src/loopora/cli_role_commands.py "
            "src/loopora/cli_spec_commands.py src/loopora/cli_spec_recovery.py "
            "src/loopora/service_loop_create_inputs.py src/loopora/specs.py src/loopora/system_dialogs.py "
            "tests/checks/contracts/test_cli_loop_create_strategy_and_logs.py tests/checks/contracts/test_system_dialogs.py "
            "src/loopora/service_agent_bundle_candidates.py src/loopora/service_agent_run_context_binding.py "
            "tests/checks/contracts/test_agent_cli_step_dispatch_output.py tests/checks/contracts/test_agent_context_binding_scope.py "
            "tests/checks/contracts/agent_bundle_candidates_test_support.py src/loopora/asset_errors.py src/loopora/cli_bundle_commands.py "
            "src/loopora/cli_resource_projection.py src/loopora/service_bundle_export.py src/loopora/service_bundle_loop_snapshot.py src/loopora/strategy_source_files.py "
            "src/loopora/strategy_source_prompt_assets.py src/loopora/loop_compose_validation.py "
            "tests/checks/contracts/test_cli_bundle_delete_command.py tests/checks/contracts/test_cli_bundle_export_command.py "
            "tests/checks/contracts/test_cli_bundle_import_command.py tests/checks/contracts/test_strategy_source.py "
            "tests/checks/contracts/test_workflow_file_loading.py src/loopora/cli_run_support.py src/loopora/db_run_records.py "
            "src/loopora/run_worker_start.py src/loopora/runner_role_execution_settings.py "
            "tests/checks/contracts/test_api_file_preview_read_errors.py tests/checks/contracts/test_cli_background_worker_runtime.py "
            "tests/checks/contracts/test_cli_run_task_verdict_output.py tests/checks/contracts/test_db_run_constraints.py "
            "tests/checks/contracts/test_run_artifact_download_path_escape.py tests/checks/contracts/test_runner_role_runtime_architecture.py "
            "tests/checks/contracts/test_runner_runtime_number_contracts.py tests/checks/contracts/test_runner_workspace_guard.py "
            "tests/checks/contracts/test_web_loop_compacted_01.py"
        ),
    )

    recommended = payload["recommended_focused_guides"]

    assert [guide["id"] for guide in recommended] == [
        "first_use_readiness",
        "web_surfaces",
        "agent_native",
        "alignment_bundle",
        "runtime_state",
    ]
    assert payload["unmatched_changed_files"] == []
    assert payload["dev_check_summary"]["unmatched_changed_file_count"] == 0
    commands = {guide["id"]: guide["command"] for guide in recommended}
    matched_files = {guide["id"]: guide["matched_files"] for guide in recommended}
    assert set(matched_files["first_use_readiness"]) >= {
        "src/loopora/cli_orchestration_commands.py",
        "src/loopora/cli_resource_projection.py",
        "src/loopora/cli_spec_recovery.py",
        "src/loopora/service_loop_create_inputs.py",
        "tests/checks/contracts/test_cli_loop_create_strategy_and_logs.py",
    }
    assert set(matched_files["web_surfaces"]) >= {
        "src/loopora/system_dialogs.py",
        "tests/checks/contracts/test_system_dialogs.py",
        "tests/checks/contracts/test_web_loop_compacted_01.py",
    }
    adapter_command_targets = sorted(path.name for path in (ROOT / "tests/checks/contracts").glob("test_agent_adapter*.py"))
    first_use_command_targets = ("test_cli_loop_create_strategy_and_logs.py", "test_cli_orchestration_resource_commands.py", *adapter_command_targets)
    assert all(f"tests/checks/contracts/{path}" in commands["first_use_readiness"] for path in first_use_command_targets)
    assert all(
        f"tests/checks/contracts/{path}" in commands["web_surfaces"]
        for path in ("test_system_dialogs.py", "test_web_loop_compacted_01.py", "test_web_run_lifecycle_api.py", "test_web_run_rerun_api.py")
    )
    assert all(
        f"tests/checks/contracts/{path}" in commands["agent_native"]
        for path in ("test_agent_context_binding_scope.py", "test_agent_cli_step_dispatch_output.py")
    )
    assert "tests/checks/contracts/test_agent_cli_step_dispatch_output.py" in matched_files["agent_native"]
    assert "tests/checks/contracts/agent_bundle_candidates_test_support.py" in matched_files["alignment_bundle"]
    assert "src/loopora/cli_resource_projection.py" in matched_files["alignment_bundle"]
    alignment_command_targets = (
        "test_alignment_import.py",
        "test_alignment_session_api_bundle_lifecycle.py",
        "test_cli_bundle_delete_command.py",
        "test_cli_bundle_export_command.py",
        "test_cli_bundle_import_command.py",
        "test_strategy_source.py",
        "test_workflow_file_loading.py",
    )
    assert all(f"tests/checks/contracts/{path}" in commands["alignment_bundle"] for path in alignment_command_targets)
    alignment_guide = next(guide for guide in recommended if guide["id"] == "alignment_bundle")
    assert alignment_guide["matched_file_count"] >= len(matched_files["alignment_bundle"])
    runtime_command_targets = (
        "test_cli_background_worker_runtime.py",
        "test_cli_run_task_verdict_output.py",
        "test_runner_local_execution.py",
        "test_runner_role_runtime_architecture.py",
        "test_runner_workspace_guard.py",
        "test_service_asset_call_errors.py",
        "test_service_component_boundaries.py",
        "test_service_private_import_inventory.py",
    )
    assert all(f"tests/checks/contracts/{path}" in commands["runtime_state"] for path in runtime_command_targets)


def test_dev_check_recommended_guides_report_omitted_matched_file_count(tmp_path: Path) -> None:
    matched_files = [f"src/loopora/cli_agent_generated_{index}.py" for index in range(14)]
    unmatched_files = [f"docs/unmatched-{index:02d}.md" for index in range(14)]
    changed_files = [*matched_files, *unmatched_files]
    payload = run_dev_check(workdir=tmp_path, list_only=True, changed_files=changed_files)
    recommended = payload["recommended_focused_guides"]
    assert [guide["id"] for guide in recommended] == ["agent_native"]
    assert recommended[0]["matched_file_count"] == 14
    assert recommended[0]["omitted_matched_file_count"] == 2
    assert recommended[0]["matched_files"] == sorted(matched_files)[:12]
    assert payload["unmatched_changed_file_count"] == 14
    assert payload["omitted_unmatched_changed_file_count"] == 2
    assert payload["unmatched_changed_files"] == unmatched_files[:12]


def test_dev_check_lists_selected_focused_guides_without_running(tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0)

    result = run_dev_check(
        workdir=tmp_path,
        list_only=True,
        focused="first_use_readiness,open_source_collaboration",
        command_runner=fake_runner,
    )
    assert result["profile"] == FOCUSED_PROFILE
    assert result["status"] == "listed"
    assert calls == []
    assert [guide["id"] for guide in result["selected_focused_guides"]] == [
        "first_use_readiness",
        "open_source_collaboration",
    ]
    assert [step["id"] for step in result["steps"]] == [
        "focused:first_use_readiness",
        "focused:open_source_collaboration",
    ]
    assert result["next_actions"] == [
        {
            "kind": "run_selected_focused_checks",
            "guide_ids": ["first_use_readiness", "open_source_collaboration"],
            "command": _focused_dev_check_command(tmp_path, "first_use_readiness,open_source_collaboration"),
        },
        {"kind": "run_default_fast_gate", "command": _dev_check_command(tmp_path)},
    ]


def test_cli_dev_check_focused_run_prioritizes_selected_guides(tmp_path: Path, monkeypatch) -> None:
    workdir = tmp_path / "repo"
    first_use_file = workdir / "src" / "loopora" / "diagnose_doctor.py"
    first_use_file.parent.mkdir(parents=True)
    first_use_file.write_text("# touched\n", encoding="utf-8")
    github_file = workdir / ".github" / "pull_request_template.md"
    github_file.parent.mkdir(parents=True)
    github_file.write_text("# touched\n", encoding="utf-8")
    subprocess.run(("git", "init"), cwd=workdir, text=True, capture_output=True, check=True)
    calls: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        calls.append(command)
        return DevCheckCommandResult(returncode=0, stdout="focused ok\n")

    monkeypatch.setattr(dev_check_module, "_run_subprocess", fake_runner)

    result = CliRunner().invoke(
        cli.app,
        ["dev", "check", "--workdir", str(workdir), "--focused", "open_source_collaboration", "--focused-ran", "first_use_readiness"],
    )

    assert result.exit_code == 0, result.stdout
    assert "selected focused checks:" in result.stdout
    assert "- open_source_collaboration (focused): Open-source collaboration and distribution" in result.stdout
    assert "\nrecommended focused checks for current changes:" not in result.stdout
    assert "other recommended focused checks for current changes" not in result.stdout
    assert "first_use_readiness: uv run pytest" not in result.stdout
    assert all(
        text in result.stdout
        for text in ("- pass: focused:open_source_collaboration", "--focused-ran first_use_readiness --focused-ran open_source_collaboration")
    )
    assert len(calls) == 1
    assert "tests/checks/contracts/test_verification_map.py" in calls[0]


def test_cli_dev_check_option_errors_are_recoverable(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    workdir = tmp_path / "project with space"
    workdir.mkdir()
    changed_files = [str(workdir / "src" / "loopora" / "diagnose_doctor.py"), "docs/product notes.md"]
    normalized_changed_files = ["docs/product notes.md", "src/loopora/diagnose_doctor.py"]
    changed_file_args = ["--changed-file", changed_files[0], "--changed-file", changed_files[1]]
    list_command = _cli_dev_check_command(workdir, "--list", normalized_changed_files)

    focused_plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(workdir), *changed_file_args, "--focused", "nope"])
    focused_json = runner.invoke(cli.app, ["dev", "check", "--workdir", str(workdir), *changed_file_args, "--focused", "nope", "--json"])
    profile_json = runner.invoke(cli.app, ["dev", "check", "--workdir", str(workdir), *changed_file_args, "--profile", "banana", "--json"])

    assert focused_plain.exit_code == 1
    assert "unsupported focused check guide: 'nope'" in focused_plain.output
    assert f"next: list focused check guides: {list_command}" in focused_plain.output
    assert f"uv --directory {shlex.quote(str(source_root))} run loopora dev check --list" in list_command
    assert not list_command.startswith("uv run loopora")
    assert f"show dev check help: {agent_adapter_command_prefix.copyable_loopora_command('loopora dev check --help')}" in focused_plain.output

    focused_payload = json.loads(focused_json.stdout)
    assert focused_json.exit_code == 1
    assert focused_payload["dev_command_error"]["state"] == "unsupported_focused_check_guide"
    assert focused_payload["next_actions"] == [
        {"kind": "list_focused_check_guides", "command": list_command},
        {"kind": "show_dev_check_help", "command": agent_adapter_command_prefix.copyable_loopora_command("loopora dev check --help")},
    ]

    profile_payload = json.loads(profile_json.stdout)
    assert profile_json.exit_code == 1
    assert profile_payload["dev_command_error"]["state"] == "unsupported_profile"
    assert profile_payload["next_actions"] == [
        {"kind": "run_default_fast_gate", "command": _cli_dev_check_command(workdir)},
        {"kind": "run_recommended_focused_checks", "command": _cli_focused_dev_check_command(workdir, "recommended", normalized_changed_files)},
        {"kind": "show_dev_check_help", "command": agent_adapter_command_prefix.copyable_loopora_command("loopora dev check --help")},
    ]


def test_cli_dev_check_list_prioritizes_recommended_guides_for_untracked_git_paths(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    touched_file = workdir / "src" / "loopora" / "diagnose_doctor.py"
    touched_file.parent.mkdir(parents=True)
    touched_file.write_text("# touched\n", encoding="utf-8")
    web_file = workdir / "src" / "loopora" / "static" / "pages" / "tools.js"
    web_file.parent.mkdir(parents=True)
    web_file.write_text("console.log('touched');\n", encoding="utf-8")
    runtime_file = workdir / "src" / "loopora" / "service_run_lifecycle.py"
    runtime_file.write_text("# touched\n", encoding="utf-8")
    github_file = workdir / ".github" / "pull_request_template.md"
    github_file.parent.mkdir(parents=True)
    github_file.write_text("# touched\n", encoding="utf-8")
    diagram_file = workdir / "assets" / "diagrams" / "first-run-path.en.svg"
    for svg_file in (diagram_file, workdir / "src" / "loopora" / "assets" / "logo" / "logo.svg"):
        svg_file.parent.mkdir(parents=True)
        svg_file.write_text("<svg></svg>\n", encoding="utf-8")
    unmatched_file = workdir / "docs" / "notes.md"
    unmatched_file.parent.mkdir(parents=True)
    unmatched_file.write_text("# notes\n", encoding="utf-8")
    subprocess.run(("git", "init"), cwd=workdir, text=True, capture_output=True, check=True)

    result = CliRunner().invoke(cli.app, ["dev", "check", "--workdir", str(workdir), "--list"])
    assert result.exit_code == 0, result.stdout
    assert "changes: Git changes detected (7 file(s))" in result.stdout
    recommended_index = result.stdout.index("recommended focused checks for current changes:")
    ignored_index = result.stdout.index("ignored changed files: none")
    unmatched_index = result.stdout.index("unmatched changed files:")
    default_step_index = result.stdout.index("- listed: dependency_sync")
    guide_index = result.stdout.index("focused check guide:")
    recommended_section = result.stdout[recommended_index:unmatched_index]
    assert recommended_index < default_step_index
    assert recommended_index < guide_index
    assert ignored_index < recommended_index
    assert recommended_index < unmatched_index < default_step_index
    assert "- first_use_readiness (focused): First-use readiness and local recovery" in recommended_section
    assert "src/loopora/diagnose_doctor.py" in recommended_section
    assert "- web_surfaces (journey): Web routes, templates, and static assets" in recommended_section
    assert "- runtime_state (focused): Run lifecycle and local runtime state" in recommended_section
    assert "- open_source_collaboration (focused): Open-source collaboration and distribution" in recommended_section
    assert "assets/diagrams/first-run-path.en.svg" in recommended_section
    assert "src/loopora/assets/logo/logo.svg" in recommended_section
    assert "uv run pytest -q" not in recommended_section
    assert "docs/notes.md" in result.stdout[unmatched_index:default_step_index]
    assert "assets/diagrams/first-run-path.en.svg" not in result.stdout[unmatched_index:default_step_index]
    assert "src/loopora/assets/logo/logo.svg" not in result.stdout[unmatched_index:default_step_index]
    assert "choose additional focused, journey, review, or probe evidence" in result.stdout[unmatched_index:default_step_index]
    assert "review unmatched changed files (docs/notes.md)" in result.stdout
    assert "next: review unmatched changed files" in result.stdout
    assert "loopora dev check --focused recommended" in result.stdout
    assert "(4 guides: first_use_readiness, web_surfaces, runtime_state, +1 more)" in result.stdout
