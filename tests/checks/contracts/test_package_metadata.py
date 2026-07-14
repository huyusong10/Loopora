from __future__ import annotations

from io import BytesIO
import json
import tarfile
import threading
import tomllib
from pathlib import Path
from zipfile import ZipFile

from typer.testing import CliRunner

import loopora
from loopora import cli, dev_check as dev_check_module, diagnose_doctor_identity, package_source_provenance
from loopora import agent_adapter_command_prefix
from loopora.cli_dev_commands import _dev_check_pr_evidence_payload, _print_dev_check_pr_evidence_summary
from loopora.dev_check import DevCheckCommandResult, run_dev_check
from loopora.dev_check_package_provenance import package_source_provenance_errors

from cli_dev_command_test_support import write_package_artifacts


ROOT = Path(__file__).resolve().parents[3]
VALID_PROVENANCE = {"schema_version": 1, "revision": "0123456789ab", "tree_status": "clean"}


def test_package_metadata_supports_public_discovery_without_license_claim() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert set(project["keywords"]) >= {
        "ai-agents",
        "agent-workflows",
        "evidence",
        "fastapi",
        "local-first",
    }
    assert set(project["classifiers"]) >= {
        "Development Status :: 3 - Alpha",
        "Framework :: FastAPI",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    }
    assert project["urls"] == {
        "Changelog": "https://github.com/huyusong10/Loopora/blob/dev/CHANGELOG.md",
        "Homepage": "https://github.com/huyusong10/Loopora",
        "Repository": "https://github.com/huyusong10/Loopora",
        "Issues": "https://github.com/huyusong10/Loopora/issues",
        "Community": "https://github.com/huyusong10/Loopora/blob/dev/CODE_OF_CONDUCT.md",
        "Documentation": "https://github.com/huyusong10/Loopora/blob/dev/README.md",
        "Governance": "https://github.com/huyusong10/Loopora/blob/dev/GOVERNANCE.md",
        "Security": "https://github.com/huyusong10/Loopora/security/policy",
        "Support": "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md",
    }
    assert project["authors"] == [{"name": "Loopora contributors"}]
    assert project["maintainers"] == [{"name": "Loopora maintainers"}]

    assert "license" not in project
    assert not any(str(classifier).startswith("License ::") for classifier in project["classifiers"])


def test_runtime_version_matches_project_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert loopora.__version__ == project["version"]


def test_dev_check_next_action_projection_has_dedicated_boundary() -> None:
    dev_check_source = (ROOT / "src" / "loopora" / "dev_check.py").read_text(encoding="utf-8")
    report_source = (ROOT / "src" / "loopora" / "dev_check_report.py").read_text(encoding="utf-8")
    next_actions_source = (ROOT / "src" / "loopora" / "dev_check_next_actions.py").read_text(encoding="utf-8")
    focused_evidence_source = (ROOT / "src" / "loopora" / "dev_check_focused_evidence_actions.py").read_text(encoding="utf-8")
    command_projection_source = (ROOT / "src" / "loopora" / "dev_check_command_projection.py").read_text(encoding="utf-8")
    pr_evidence_source = (ROOT / "src" / "loopora" / "cli_dev_pr_evidence.py").read_text(encoding="utf-8")
    recovery_source = (ROOT / "src" / "loopora" / "cli_dev_check_recovery.py").read_text(encoding="utf-8")
    release_plan_source = (ROOT / "src" / "loopora" / "cli_dev_release_plan.py").read_text(encoding="utf-8")
    types_source = (ROOT / "src" / "loopora" / "dev_check_types.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.dev_check_next_actions import dev_check_next_actions" in report_source
    assert "def _default_dev_check_next_actions" not in dev_check_source
    assert "def dev_check_next_actions" in next_actions_source
    assert "def _default_dev_check_next_actions" in next_actions_source
    assert "from loopora.dev_check_focused_evidence_actions import" in next_actions_source
    assert "def declared_focused_run_guide_ids" not in next_actions_source
    assert "def run_remaining_recommended_focused_checks_action" not in next_actions_source
    assert "def final_pr_evidence_gate_action" not in next_actions_source
    assert "def declared_focused_run_guide_ids" in focused_evidence_source
    assert "def run_remaining_recommended_focused_checks_action" in focused_evidence_source
    assert "def final_pr_evidence_gate_action" in focused_evidence_source
    assert "from loopora.dev_check_command_projection import" in next_actions_source
    assert "def _command_with_changed_files" not in next_actions_source
    assert "def _focused_selection_args" not in next_actions_source
    assert "def copyable_dev_check_command" in command_projection_source
    assert "def dev_check_focused_command" in command_projection_source
    assert "from loopora.dev_check_command_projection import copyable_dev_check_command" in pr_evidence_source
    assert "def copyable_dev_check_command" not in pr_evidence_source
    assert "from loopora.dev_check_command_projection import copyable_dev_check_command" in recovery_source
    assert "from loopora.dev_check_command_projection import copyable_dev_check_command" in release_plan_source
    assert "class DevCheckReportContext" in types_source
    assert "dev_check_focused_evidence_actions.py" in service_boundaries
    assert "dev_check_next_actions.py" in service_boundaries
    assert "dev_check_command_projection.py" in service_boundaries


def test_dev_check_package_build_has_dedicated_boundaries() -> None:
    package_source = (ROOT / "src" / "loopora" / "dev_check_package.py").read_text(encoding="utf-8")
    lifecycle_source = (ROOT / "src" / "loopora" / "dev_check_package_lifecycle.py").read_text(encoding="utf-8")
    contents_source = (ROOT / "src" / "loopora" / "dev_check_package_contents.py").read_text(encoding="utf-8")
    metadata_source = (ROOT / "src" / "loopora" / "dev_check_package_metadata.py").read_text(encoding="utf-8")
    provenance_source = (ROOT / "src" / "loopora" / "dev_check_package_provenance.py").read_text(encoding="utf-8")
    policy_source = (ROOT / "src" / "loopora" / "dev_check_package_policy.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "def run_package_build_step" in package_source
    assert "def _verify_installed_wheel_cli" in package_source
    assert '("uv", "run", "--isolated", "--no-project", "--offline", "--with"' in package_source
    for module_name in (
        "dev_check_package_lifecycle",
        "dev_check_package_contents",
        "dev_check_package_metadata",
        "dev_check_package_provenance",
        "dev_check_package_policy",
    ):
        assert f"from loopora.{module_name} import" in package_source
        assert f"{module_name}.py" in service_boundaries
    for marker in (
        "def package_build_lock",
        "def cleanup_package_build_output",
        "def cleanup_generated_package_metadata",
    ):
        assert marker in lifecycle_source
        assert marker not in package_source
    for marker in (
        "def runtime_package_asset_files",
        "def missing_wheel_runtime_assets",
        "def forbidden_sdist_distribution_entries",
    ):
        assert marker in contents_source
        assert marker not in package_source
    for marker in (
        "def project_public_positioning_errors",
        "def missing_wheel_install_metadata",
        "def missing_sdist_install_metadata",
    ):
        assert marker in metadata_source
        assert marker not in package_source
    for marker in (
        "PACKAGE_RUNTIME_ASSET_ROOTS",
        "PACKAGE_PUBLIC_URLS",
        "PACKAGE_FORBIDDEN_DISTRIBUTION_PREFIXES",
    ):
        assert marker in policy_source
    assert "def package_source_provenance_errors" in provenance_source
    assert "package_source_provenance.py" in service_boundaries


def test_runtime_source_provenance_prefers_live_checkout_and_falls_back_to_build_record(monkeypatch, tmp_path: Path) -> None:
    packaged_path = tmp_path / "_build_provenance.json"
    package_source_provenance.write_source_provenance(
        packaged_path,
        {"revision": "abcdef012345", "tree_status": "dirty"},
    )
    monkeypatch.setattr(
        package_source_provenance,
        "git_source_provenance",
        lambda _root: {"revision": "123456789abc", "tree_status": "clean"},
    )
    assert package_source_provenance.package_source_provenance(source_root=tmp_path, packaged_path=packaged_path) == {
        "revision": "123456789abc",
        "tree_status": "clean",
    }

    monkeypatch.setattr(
        package_source_provenance,
        "git_source_provenance",
        lambda _root: {"revision": "unknown", "tree_status": "unknown"},
    )
    assert package_source_provenance.package_source_provenance(source_root=tmp_path, packaged_path=packaged_path) == {
        "revision": "abcdef012345",
        "tree_status": "dirty",
    }


def test_runtime_source_provenance_does_not_adopt_an_install_host_repository(monkeypatch, tmp_path: Path) -> None:
    source_root = tmp_path / "target-project" / ".venv" / "lib" / "python"
    source_root.mkdir(parents=True)
    packaged_path = source_root / "loopora" / "_build_provenance.json"
    package_source_provenance.write_source_provenance(
        packaged_path,
        {"revision": "abcdef012345", "tree_status": "clean"},
    )

    def fake_git_output(args: tuple[str, ...], *, cwd: Path) -> str:
        assert cwd == source_root
        return {
            ("rev-parse", "--is-inside-work-tree"): "true",
            ("rev-parse", "--show-toplevel"): str(tmp_path / "target-project"),
        }.get(args, "123456789abc")

    monkeypatch.setattr(package_source_provenance, "_git_output", fake_git_output)

    assert package_source_provenance.package_source_provenance(
        source_root=source_root,
        packaged_path=packaged_path,
    ) == {"revision": "abcdef012345", "tree_status": "clean"}


def test_package_identity_uses_path_free_build_source_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnose_doctor_identity,
        "package_source_provenance",
        lambda **_kwargs: {"revision": "abcdef012345", "tree_status": "dirty"},
    )

    package = diagnose_doctor_identity.package_identity_report()

    assert package["source_revision"] == "abcdef012345"
    assert package["source_tree_status"] == "dirty"
    assert diagnose_doctor_identity.package_source_label(package) == "source abcdef012345 dirty"


def test_package_provenance_gate_requires_matching_minimal_wheel_and_sdist_records(tmp_path: Path) -> None:
    wheel, sdist = _write_provenance_artifacts(tmp_path, VALID_PROVENANCE, VALID_PROVENANCE)
    assert package_source_provenance_errors(wheel, sdist) == []

    wheel, sdist = _write_provenance_artifacts(
        tmp_path / "mismatch",
        VALID_PROVENANCE,
        {**VALID_PROVENANCE, "tree_status": "dirty"},
    )
    assert package_source_provenance_errors(wheel, sdist) == ["wheel and sdist source provenance do not match"]

    wheel, sdist = _write_provenance_artifacts(
        tmp_path / "leak",
        {**VALID_PROVENANCE, "source_path": "/private/checkout"},
        VALID_PROVENANCE,
    )
    assert package_source_provenance_errors(wheel, sdist) == [
        "wheel source provenance must contain only schema_version, revision, and tree_status"
    ]


def test_package_build_writes_provenance_only_to_artifact_trees() -> None:
    setup_source = (ROOT / "setup.py").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    policy = (ROOT / "src" / "loopora" / "dev_check_package_policy.py").read_text(encoding="utf-8")

    assert all(
        fragment in setup_source
        for fragment in (
            "class BuildPyWithSourceProvenance",
            'Path(self.build_lib) / "loopora" / module.SOURCE_PROVENANCE_FILENAME',
            "class SdistWithSourceProvenance",
            'Path(base_dir) / "src" / "loopora" / module.SOURCE_PROVENANCE_FILENAME',
        )
    )
    assert "include setup.py" in manifest
    assert 'Path("setup.py")' in policy
    assert not (ROOT / "src" / "loopora" / "_build_provenance.json").exists()


def _write_provenance_artifacts(root: Path, wheel_payload: dict, sdist_payload: dict) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    wheel_path = root / "loopora.whl"
    sdist_path = root / "loopora.tar.gz"
    with ZipFile(wheel_path, "w") as wheel:
        wheel.writestr("loopora/_build_provenance.json", json.dumps(wheel_payload))
    encoded = json.dumps(sdist_payload).encode("utf-8")
    with tarfile.open(sdist_path, "w:gz") as sdist:
        info = tarfile.TarInfo("loopora-0.1.0/src/loopora/_build_provenance.json")
        info.size = len(encoded)
        sdist.addfile(info, BytesIO(encoded))
    return wheel_path, sdist_path


def test_dev_check_execution_and_report_have_dedicated_boundaries() -> None:
    dev_check_source = (ROOT / "src" / "loopora" / "dev_check.py").read_text(encoding="utf-8")
    execution_source = (ROOT / "src" / "loopora" / "dev_check_execution.py").read_text(encoding="utf-8")
    report_source = (ROOT / "src" / "loopora" / "dev_check_report.py").read_text(encoding="utf-8")
    service_boundaries = (ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.dev_check_execution import" in dev_check_source
    assert "from loopora.dev_check_report import build_dev_check_report" in dev_check_source
    assert "_run_subprocess = run_subprocess" in dev_check_source
    for marker in (
        "def run_default_step",
        "def run_focused_step",
        "def run_static_js_check",
        "def emit_dev_check_progress",
        "def run_subprocess",
    ):
        assert marker in execution_source
    for marker in (
        "def _run_step",
        "def _run_focused_step",
        "def _run_static_js_check",
        "def _emit_dev_check_progress",
        "def _report",
    ):
        assert marker not in dev_check_source
    assert "def build_dev_check_report" in report_source
    assert "project_next_action_readiness_contract" in report_source
    assert "def build_dev_check_report" not in dev_check_source
    assert "dev_check_execution.py" in service_boundaries
    assert "dev_check_report.py" in service_boundaries


def test_dev_release_plan_blocks_without_candidate_or_supported_status(tmp_path: Path) -> None:
    args = ["dev", "release-plan", "--workdir", str(tmp_path)]
    plain = CliRunner().invoke(cli.app, args)
    result = CliRunner().invoke(cli.app, [*args, "--json"])
    payload = json.loads(result.stdout)
    summary = payload["release_plan_summary"]
    assert plain.exit_code == result.exit_code == 0
    assert (payload["status"], payload["ready"], summary["ready"]) == ("blocked", False, False)
    assert summary["workdir_state"] == "ready"
    assert (summary["probe_ref"], summary["probe_ref_source"]) == ("", "candidate")
    assert summary["blocker_kinds"] == ["candidate_required", "supported_status_required"]
    assert (summary["next_action_kinds"], summary["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (
        ["choose_release_candidate", "decide_supported_status"],
        ["choose_release_candidate", "decide_supported_status"],
        {},
    )
    assert payload["next_actions"][0]["command_template"].endswith(
        f"release-plan --candidate <version-or-tag> --supported-status <supported-status> --workdir {tmp_path.resolve()}"
    )
    assert payload["next_actions"][1]["command_template"].endswith(
        f"release-plan --candidate <version-or-tag> --supported-status <supported-status> --workdir {tmp_path.resolve()}"
    )
    assert "collect_release_decision_evidence" not in plain.stdout
    assert "run_final_release_pr_evidence" not in plain.stdout
    assert "run_release_real_probe_suite" not in plain.stdout


def test_dev_release_plan_blocker_rerun_template_preserves_supplied_candidate(tmp_path: Path) -> None:
    result = CliRunner().invoke(cli.app, ["dev", "release-plan", "--workdir", str(tmp_path), "--candidate", "v0.2.0", "--json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert payload["release_plan_summary"]["blocker_kinds"] == ["supported_status_required"]
    assert payload["release_plan_summary"]["workdir_state"] == "ready"
    assert payload["release_plan_summary"]["next_action_kinds"] == ["decide_supported_status"]
    assert payload["next_actions"][0]["command_template"].endswith(
        f"release-plan --candidate v0.2.0 --supported-status <supported-status> --workdir {tmp_path.resolve()}"
    )


def test_dev_release_plan_blocker_rerun_template_preserves_supplied_probe_ref(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli.app,
        [
            "dev",
            "release-plan",
            "--workdir",
            str(tmp_path),
            "--candidate",
            "release candidate 1",
            "--probe-ref",
            "release/v0.2.0 beta",
            "--json",
        ],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["release_plan_summary"]["blocker_kinds"] == ["supported_status_required"]
    assert payload["release_plan_summary"]["probe_ref"] == "release/v0.2.0 beta"
    assert payload["release_plan_summary"]["probe_ref_source"] == "provided"
    assert payload["next_actions"][0]["command_template"].endswith(
        f"release-plan --candidate 'release candidate 1' --supported-status <supported-status> --probe-ref 'release/v0.2.0 beta' --workdir {tmp_path.resolve()}"
    )


def test_dev_release_plan_blocks_evidence_commands_for_unusable_workdir(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    file_target = tmp_path / "not-a-dir"
    file_target.write_text("not a directory\n", encoding="utf-8")

    for target, expected_state in ((missing, "missing"), (file_target, "not_directory")):
        result = CliRunner().invoke(
            cli.app,
            ["dev", "release-plan", "--workdir", str(target), "--candidate", "v0.2.0", "--supported-status", "supported", "--json"],
        )
        payload = json.loads(result.stdout)
        action_kinds = [action["kind"] for action in payload["next_actions"]]
        assert result.exit_code == 0
        assert payload["status"] == "blocked"
        assert payload["workdir_state"]["status"] == expected_state
        assert payload["release_plan_summary"]["blocker_kinds"] == [f"workdir_{expected_state}"]
        assert (action_kinds, payload["next_action_ready_now_kinds"], payload["release_plan_summary"]["next_action_ready_after_actions"]) == (
            ["choose_release_workdir"],
            ["choose_release_workdir"],
            {},
        )
        assert payload["next_actions"][0]["command_template"].endswith(
            "release-plan --candidate v0.2.0 --supported-status supported --workdir '<Loopora checkout>'"
        )


def test_dev_release_plan_surfaces_complete_release_evidence_without_running_checks(tmp_path: Path) -> None:
    args = ["dev", "release-plan", "--workdir", str(tmp_path), "--candidate", "v0.2.0", "--supported-status", "supported"]
    plain = CliRunner().invoke(cli.app, args)
    structured = CliRunner().invoke(cli.app, [*args, "--json"])
    payload = json.loads(structured.stdout)
    assert plain.exit_code == structured.exit_code == 0
    assert all(text in plain.stdout for text in ("status: ready", "candidate: v0.2.0", "run_release_real_probe_suite"))
    decision_evidence = next(action for action in payload["next_actions"] if action["kind"] == "collect_release_decision_evidence")
    focused_evidence = next(action for action in payload["next_actions"] if action["kind"] == "run_release_focused_evidence")
    final_pr_evidence = next(action for action in payload["next_actions"] if action["kind"] == "run_final_release_pr_evidence")
    web_journey = next(action for action in payload["next_actions"] if action["kind"] == "run_web_journey_checks_if_web_changed")
    real_probe = next(action for action in payload["next_actions"] if action["kind"] == "run_release_real_probe_suite")
    assert payload["release_plan_summary"] == {
        "schema_version": 1,
        "candidate": "v0.2.0",
        "probe_ref": "v0.2.0",
        "probe_ref_source": "candidate",
        "supported_status": "supported",
        "workdir_state": "ready",
        "ready": True,
        "blocker_kinds": [],
        "next_action_kinds": [action["kind"] for action in payload["next_actions"]],
        "next_action_ready_kinds": [action["kind"] for action in payload["next_actions"]],
        "next_action_ready_now_kinds": [action["kind"] for action in payload["next_actions"]],
        "next_action_ready_after_actions": {},
        "next_action_blocked_kinds": [],
        "next_action_command_blockers": {},
    }
    assert decision_evidence["command"].endswith(f"dev check --list --pr-evidence --workdir {tmp_path.resolve()}")
    assert focused_evidence["command"].endswith(f"dev check --focused recommended --workdir {tmp_path.resolve()}")
    assert final_pr_evidence["command"].endswith(f"dev check --pr-evidence --focused-ran recommended --workdir {tmp_path.resolve()}")
    assert web_journey["command"] == f"uv --directory {tmp_path.resolve()} run pytest -q tests/checks/journeys"
    assert all(
        command in plain.stdout
        for command in (
            decision_evidence["command"],
            focused_evidence["command"],
            final_pr_evidence["command"],
        )
    )
    assert real_probe == {
        "kind": "run_release_real_probe_suite",
        "command": "gh workflow run real-provider-probe.yml --ref v0.2.0 -f suites=release",
        "workflow": ".github/workflows/real-provider-probe.yml",
        "dispatch": "workflow_dispatch",
        "ref": "v0.2.0",
        "artifact": ".loopora/real-probes/",
        "opt_in": True,
    }
    assert payload["next_actions"][-1] == {
        "kind": "verify_package_distribution_boundary",
        "covered_by": "package_build",
        "no_license_boundary": True,
    }


def test_dev_release_plan_allows_probe_ref_to_differ_from_release_candidate(tmp_path: Path) -> None:
    args = [
        "dev",
        "release-plan",
        "--workdir",
        str(tmp_path),
        "--candidate",
        "0.2.0",
        "--probe-ref",
        "v0.2.0",
        "--supported-status",
        "supported",
    ]
    plain = CliRunner().invoke(cli.app, args)
    structured = CliRunner().invoke(cli.app, [*args, "--json"])
    payload = json.loads(structured.stdout)
    real_probe = next(action for action in payload["next_actions"] if action["kind"] == "run_release_real_probe_suite")

    assert plain.exit_code == structured.exit_code == 0
    assert "release probe ref: v0.2.0 (provided)" in plain.stdout
    assert payload["release_plan_summary"]["candidate"] == "0.2.0"
    assert payload["release_plan_summary"]["probe_ref"] == "v0.2.0"
    assert payload["release_plan_summary"]["probe_ref_source"] == "provided"
    assert real_probe["command"] == "gh workflow run real-provider-probe.yml --ref v0.2.0 -f suites=release"
    assert real_probe["ref"] == "v0.2.0"


def test_cli_dev_check_plain_execution_shows_progress_without_polluting_json(tmp_path: Path, monkeypatch) -> None:
    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        assert command == ("uv", "sync", "--locked", "--dry-run")
        return DevCheckCommandResult(returncode=17, stdout="lock drift\n", stderr="refresh lock\n")

    monkeypatch.setattr(dev_check_module, "_run_subprocess", fake_runner)
    runner = CliRunner()

    plain = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path)])

    assert plain.exit_code == 1, plain.stdout
    assert "progress: running dependency_sync - uv sync --locked --dry-run" in plain.stdout
    assert "progress: fail dependency_sync" in plain.stdout
    assert plain.stdout.index("progress: running dependency_sync") < plain.stdout.index("Loopora dev check: default-fast")

    structured = runner.invoke(cli.app, ["dev", "check", "--workdir", str(tmp_path), "--json"])

    assert structured.exit_code == 1
    assert "progress:" not in structured.stdout
    assert json.loads(structured.stdout)["dev_check_summary"]["failed_step_id"] == "dependency_sync"


def test_cli_dev_check_accepts_positional_changed_paths_for_list(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()

    result = CliRunner().invoke(
        cli.app,
        [
            "dev",
            "check",
            "--workdir",
            str(workdir),
            "--list",
            "src/loopora/dev_check.py",
            "README.md",
            "../outside.md",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "changes: provided changed files (2 file(s))" in result.stdout
    assert "ignored changed files: ../outside.md" in result.stdout
    assert "- open_source_collaboration (focused): Open-source collaboration and distribution" in result.stdout
    assert "matched: README.md, src/loopora/dev_check.py" in result.stdout
    assert "Got unexpected extra arguments" not in result.stdout


def test_cli_dev_check_positional_changed_paths_match_json_surface(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()

    result = CliRunner().invoke(
        cli.app,
        ["dev", "check", "--workdir", str(workdir), "--list", "--json", "src/loopora/cli_dev_commands.py"],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 0, result.stdout
    assert payload["changed_file_detection"] == {"source": "provided", "status": "provided", "count": 1}
    assert [guide["id"] for guide in payload["recommended_focused_guides"]] == ["open_source_collaboration"]
    assert payload["recommended_focused_guides"][0]["matched_files"] == ["src/loopora/cli_dev_commands.py"]
    assert payload["next_actions"][0]["guide_ids"] == ["open_source_collaboration"]
    assert (
        payload["dev_check_summary"]["changed_file_source"],
        payload["dev_check_summary"]["changed_file_status"],
        payload["dev_check_summary"]["changed_file_count"],
    ) == ("provided", "provided", 1)


def test_cli_dev_check_positional_changed_paths_survive_option_recovery(tmp_path: Path) -> None:
    workdir = tmp_path / "project with space"
    workdir.mkdir()

    result = CliRunner().invoke(
        cli.app,
        [
            "dev",
            "check",
            "--workdir",
            str(workdir),
            "--focused",
            "nope",
            "README.md",
            "src/loopora/dev_check.py",
        ],
    )

    expected_list = (
        f"{agent_adapter_command_prefix.copyable_loopora_command('loopora dev check --list')} "
        "--changed-file README.md "
        "--changed-file src/loopora/dev_check.py "
        f"--workdir '{workdir.resolve()}'"
    )
    assert result.exit_code == 1
    assert "unsupported focused check guide: 'nope'" in result.output
    assert f"next: list focused check guides: {expected_list}" in result.output
    assert f"show dev check help: {agent_adapter_command_prefix.copyable_loopora_command('loopora dev check --help')}" in result.output


def test_dev_check_package_build_serializes_concurrent_same_workdir_runs(tmp_path: Path) -> None:
    probe = _ConcurrentPackageBuildProbe(tmp_path)
    probe.run()

    assert probe.thread_errors == []
    assert len(probe.results) == 2
    assert all(result["status"] == "pass" for result in probe.results)
    assert probe.build_entries == 2
    assert probe.max_active_builds == 1
    assert not any((tmp_path / path).exists() for path in ("tmp/package-check", "src/loopora.egg-info"))


def test_dev_check_pr_evidence_failure_summary_includes_local_failed_step_output(capsys, tmp_path: Path) -> None:
    def fake_runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        if command == ("uv", "pip", "check"):
            return DevCheckCommandResult(returncode=7, stdout="dependency conflict\n", stderr="broken lock\n")
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    result = run_dev_check(workdir=tmp_path, command_runner=fake_runner)

    _print_dev_check_pr_evidence_summary(result)

    output = capsys.readouterr().out
    evidence_block = output.split("copyable PR evidence block:", 1)[1]
    assert "failed step: dependency_compatibility (exit 7): uv pip check" in output
    assert all(fragment in output for fragment in ("failed step output:", "stdout:", "dependency conflict", "stderr:", "broken lock"))
    assert "dependency conflict" not in evidence_block
    assert "broken lock" not in evidence_block


def test_dev_check_pr_evidence_command_source_redacts_source_checkout(monkeypatch, tmp_path: Path) -> None:
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")

    summary = _dev_check_pr_evidence_payload(run_dev_check(workdir=tmp_path, list_only=True, changed_files=["src/loopora/dev_check.py"]))

    assert summary["evidence_command_source"] == "uv --directory <Loopora checkout> run loopora dev check"
    assert "- Evidence command source: `uv --directory <Loopora checkout> run loopora dev check`" in summary["template_markdown"]
    assert str(source_root) not in summary["template_markdown"]


def test_release_plan_docs_keep_maintainer_owned_read_only_boundary() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    assert all(
        text in contributing
        for text in (
            "uv run loopora dev release-plan",
            "read-only release evidence plan",
            "blocks on an unusable `--workdir`",
            "missing candidate, or missing support status before emitting evidence commands",
            "`--probe-ref <branch-or-tag>`",
            "`--focused-ran recommended`",
            "does not run checks, publish artifacts, or decide support status for maintainers",
        )
    )
    assert all(
        text in contracts
        for text in (
            "Dev release-readiness plan",
            "`loopora dev release-plan` is a read-only maintainer planning surface",
            "requires a usable release workdir",
            "before reporting ready or emitting evidence commands",
            "preserve the release workdir in local evidence commands",
            "without running checks or approving a release",
        )
    )


class _ConcurrentPackageBuildProbe:
    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.first_build_entered = threading.Event()
        self.release_first_build = threading.Event()
        self.second_runner_started = threading.Event()
        self.second_build_entered_before_release = threading.Event()
        self.active_lock = threading.Lock()
        self.active_builds = 0
        self.build_entries = 0
        self.max_active_builds = 0
        self.results: list[dict] = []
        self.thread_errors: list[Exception] = []

    def run(self) -> None:
        first = threading.Thread(target=self._run_check, name="first-dev-check")
        second = threading.Thread(target=self._run_check, name="second-dev-check")
        first.start()
        assert self.first_build_entered.wait(timeout=5)
        second.start()
        assert self.second_runner_started.wait(timeout=5)
        assert not self.second_build_entered_before_release.wait(timeout=0.2)
        self.release_first_build.set()
        first.join(timeout=5)
        second.join(timeout=5)
        assert not first.is_alive()
        assert not second.is_alive()

    def _run_check(self) -> None:
        try:
            self.results.append(run_dev_check(workdir=self.workdir, command_runner=self.runner))
        except Exception as exc:  # noqa: BLE001 - surfaced through main-thread assertions.
            self.thread_errors.append(exc)

    def runner(self, command: tuple[str, ...], cwd: Path) -> DevCheckCommandResult:
        if self._second_dev_check_started(command):
            self.second_runner_started.set()
        if command == ("uv", "build", "--out-dir", "tmp/package-check"):
            self._record_build_entry()
            self._block_first_build_until_second_is_waiting()
            write_package_artifacts(cwd)
            self._record_build_exit()
        return DevCheckCommandResult(returncode=0, stdout="ok\n")

    def _second_dev_check_started(self, command: tuple[str, ...]) -> bool:
        return command == ("uv", "sync", "--locked", "--dry-run") and threading.current_thread().name == "second-dev-check"

    def _record_build_entry(self) -> None:
        with self.active_lock:
            self.active_builds += 1
            self.build_entries += 1
            self.max_active_builds = max(self.max_active_builds, self.active_builds)

    def _block_first_build_until_second_is_waiting(self) -> None:
        if self.build_entries == 1:
            self.first_build_entered.set()
            assert self.release_first_build.wait(timeout=5)
        elif not self.release_first_build.is_set():
            self.second_build_entered_before_release.set()

    def _record_build_exit(self) -> None:
        with self.active_lock:
            self.active_builds -= 1
