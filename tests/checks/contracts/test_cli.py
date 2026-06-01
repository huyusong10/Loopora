from __future__ import annotations

import json
import re
from importlib.metadata import distribution
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.agent_adapter_templates import managed_templates
from loopora.branding import APP_HOME_ENV


def _result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def _assert_cli_list(output: str, key: str, *items: str) -> None:
    assert f"{key}:\n" in output
    assert f"{key}: [" not in output
    for item in items:
        assert f"- {item}" in output


def _assert_readme_entry_points(readmes: list[str], documented_adapters: list[set[str]]) -> None:
    assert documented_adapters == [{"codex", "claude", "opencode"}, {"codex", "claude", "opencode"}]
    assert all("loopora serve " in readme for readme in readmes)
    assert "After the preview looks right, run `/loopora-run`" in readmes[0]
    assert "预览看起来正确后，运行 `/loopora-run`" in readmes[1]
    assert all("confirmed Loop" not in readme for readme in readmes)


def _assert_public_anchor_default_language(
    english_readme: str,
    chinese_readme: str,
    human_shaped_loop_docs: list[str],
) -> None:
    readmes = [english_readme, chinese_readme]
    assert all("judgment_contract" not in readme for readme in readmes)
    assert all("GateKeeper" not in readme for readme in readmes)
    assert "automated proof" in english_readme
    for forbidden in ("benchmark or proof harness", "benchmarks", "proof harness"):
        assert forbidden not in english_readme
    assert "基准评测" in chinese_readme
    assert "证明脚本" in chinese_readme
    for forbidden in ("benchmark", "proof harness", "required coverage", "run contract"):
        assert forbidden not in chinese_readme
    assert "Readers do not need to understand Loopora's internal terms first" in human_shaped_loop_docs[0]
    assert "读者不需要先理解 Loopora 的内部名词" in human_shaped_loop_docs[1]
    for doc in human_shaped_loop_docs:
        for forbidden in ("judgment_contract", "run contract", "step capsule", "GateKeeper", "Builder", "Inspector"):
            assert forbidden not in doc
    hsl_intro = human_shaped_loop_docs[1].split("## 2.", 1)[0]
    for forbidden in ("happy path", "coverage", "artifact 引用", "workflow handoff", "GateKeeper", "blocking issue"):
        assert forbidden not in hsl_intro


def _assert_alignment_language_assets(design_docs: dict[str, str], governance_scenario: str) -> None:
    contracts = design_docs["contracts"]
    assert "Web composer and Agent Runner are peer entry surfaces" in contracts
    assert "`contracts.md`" in design_docs["readme"]
    assert "Web is full-function" in contracts
    assert "same Core" in contracts
    assert "Run status and Loop verdict are separate" in contracts
    assert "evidence-bearing control points" in contracts
    assert "`/loopora-plan -> /loopora-run`" in contracts
    assert "`/loopora-plan` creates, revises, repairs, or tightens reviewed Loop previews" in contracts
    assert "`/loopora-run` starts, resumes, replays, or continues evidence" in contracts
    assert "明确确认工作约定后进入 READY" in governance_scenario
    assert "确认方案后进入 READY" not in governance_scenario


def _assert_documented_cli_entries_available(documented_adapters: list[set[str]]) -> None:
    runner = CliRunner()
    for adapter in sorted(documented_adapters[0]):
        result = runner.invoke(cli.app, ["init", adapter, "--help"])
        assert result.exit_code == 0, _result_error_text(result)
        assert "task goal" in result.stdout
        assert "fake-done risk" in result.stdout
        assert "required" in result.stdout
        assert "evidence" in result.stdout
        assert "/loopora-plan" in result.stdout
        assert "READY Loop preview" in result.stdout
        assert "/loopora-run" in result.stdout
        assert "same Agent session" in result.stdout

    serve_result = runner.invoke(cli.app, ["serve", "--help"])
    assert serve_result.exit_code == 0, _result_error_text(serve_result)

    help_result = runner.invoke(cli.app, ["--help"])
    assert help_result.exit_code == 0, _result_error_text(help_result)
    assert "Start here:" in help_result.stdout
    assert re.search(r"loopora\s+init\s+codex", help_result.stdout)
    assert "task goal" in help_result.stdout
    assert "fake-done risk" in help_result.stdout
    assert "required evidence" in help_result.stdout
    assert "/loopora-plan" in help_result.stdout
    assert "/loopora-run" in help_result.stdout
    assert "same" in help_result.stdout
    assert "Agent session" in help_result.stdout
    assert help_result.stdout.index("Start here:") < help_result.stdout.index("Expert: create and run")
    assert help_result.stdout.index("│ init") < help_result.stdout.index("│ run")
    assert help_result.stdout.index("│ serve") < help_result.stdout.index("│ run")
    assert help_result.stdout.index("Install /loopora-plan") < help_result.stdout.index(
        "Expert: create and inspect reusable run flows"
    )


def _assert_plan_slash_shell_recovery(runner: CliRunner) -> None:
    plan_result = runner.invoke(cli.app, ["/loopora-plan"])
    assert plan_result.exit_code == 2
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
    assert plan_without_slash_result.exit_code == 2
    assert "No such command" not in plan_without_slash_result.output
    assert "slash_command_recovery: /loopora-plan is an Agent slash command, not a shell subcommand." in plan_without_slash_result.stdout

    plan_json_result = runner.invoke(cli.app, ["/loopora-plan", "--json"])
    assert plan_json_result.exit_code == 2
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
    assert run_result.exit_code == 2
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
    assert run_without_slash_result.exit_code == 2
    assert "No such command" not in run_without_slash_result.output
    assert "slash_command_recovery: /loopora-run is an Agent slash command, not a shell subcommand." in run_without_slash_result.stdout

    run_json_result = runner.invoke(cli.app, ["loopora-run", "--json"])
    assert run_json_result.exit_code == 2
    run_payload = json.loads(run_json_result.stdout)
    assert next(iter(run_payload)) == "slash_command_recovery_summary"
    assert run_payload["slash_command_recovery_summary"]["slash_command_recovery"] == "agent_slash_command_in_shell"
    assert run_payload["slash_command"] == "/loopora-run"
    assert run_payload["next_step"].startswith("run /loopora-run inside the same Agent session")
    assert "loopora agent codex run" in run_payload["debug_cli"]


def _assert_next_slash_shell_recovery(runner: CliRunner) -> None:
    next_result = runner.invoke(cli.app, ["/next"])
    assert next_result.exit_code == 2
    assert "No such command" not in next_result.output
    assert "Loopora does not install a top-level /next slash command" in next_result.stdout
    assert "use /loopora-run inside the Agent" in next_result.stdout
    assert 'loopora agent codex next --workdir "$PWD" --run-id <run_id>' in next_result.stdout

    next_json_result = runner.invoke(cli.app, ["/next", "--json"])
    assert next_json_result.exit_code == 2
    next_payload = json.loads(next_json_result.stdout)
    assert next_payload["slash_command_recovery"] == "unsupported_loopora_slash_command"
    assert next_payload["slash_command"] == "/next"


def test_cli_recovers_when_agent_slash_command_is_typed_in_shell() -> None:
    runner = CliRunner()
    _assert_plan_slash_shell_recovery(runner)
    _assert_run_slash_shell_recovery(runner)
    _assert_next_slash_shell_recovery(runner)


def test_cli_package_exposes_loopora_console_script() -> None:
    console_scripts = {
        entry_point.name: entry_point.value
        for entry_point in distribution("loopora").entry_points
        if entry_point.group == "console_scripts"
    }

    assert console_scripts["loopora"] == "loopora.cli:app"


def test_readme_first_use_commands_match_cli_entries() -> None:
    root = Path(__file__).resolve().parents[3]
    english_readme = (root / "README.md").read_text(encoding="utf-8")
    chinese_readme = (root / "README.zh-CN.md").read_text(encoding="utf-8")
    readmes = [english_readme, chinese_readme]
    human_shaped_loop_docs = [
        (root / "HUMAN-SHAPED-LOOP.md").read_text(encoding="utf-8"),
        (root / "HUMAN-SHAPED-LOOP.zh-CN.md").read_text(encoding="utf-8"),
    ]
    design_docs = {
        "readme": (root / "design" / "README.md").read_text(encoding="utf-8"),
        "contracts": (root / "design" / "contracts.md").read_text(encoding="utf-8"),
    }
    governance_scenario = (root / "tests" / "scenarios" / "long_running_governance_loop.md").read_text(
        encoding="utf-8"
    )
    documented_adapters = [set(re.findall(r"\bloopora init ([a-z]+)\b", readme)) for readme in readmes]

    _assert_readme_entry_points(readmes, documented_adapters)
    _assert_public_anchor_default_language(english_readme, chinese_readme, human_shaped_loop_docs)
    _assert_alignment_language_assets(design_docs, governance_scenario)
    _assert_documented_cli_entries_available(documented_adapters)


def test_cli_help_keeps_first_use_language_on_plan_files() -> None:
    runner = CliRunner()

    root_help = runner.invoke(cli.app, ["--help"])
    assert root_help.exit_code == 0, _result_error_text(root_help)
    assert "Import, export, and manage Loop plan files" in root_help.stdout
    assert "Install /loopora-plan and /loopora-run project entries" in root_help.stdout
    assert "task goal, fake-done risk, and required evidence" in root_help.stdout
    assert "Remove Loopora-managed Coding Agent project entries" in root_help.stdout
    assert "Internal runtime used by /loopora-plan and /loopora-run" in root_help.stdout
    assert "project entries" in root_help.stdout
    assert "Import and manage YAML bundles" not in root_help.stdout
    assert "Coding Agent adapters" not in root_help.stdout

    _assert_cli_agent_entry_help(runner)
    _assert_cli_bundle_import_help(runner)


def test_cli_dev_reset_previews_then_removes_v3_development_state_without_deleting_unmanaged_files(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "project"
    home = tmp_path / "home"
    workdir.mkdir()
    home.mkdir()
    db = home / "app.db"
    db.write_text("legacy-db", encoding="utf-8")
    state_sentinel = workdir / ".loopora" / "runs" / "run_old" / "state.json"
    state_sentinel.parent.mkdir(parents=True)
    state_sentinel.write_text("{}", encoding="utf-8")
    templates = managed_templates("codex")
    managed_relative = ".codex/agents/loopora-builder.toml"
    managed_file = workdir / managed_relative
    managed_file.parent.mkdir(parents=True)
    managed_file.write_text(templates[managed_relative], encoding="utf-8")
    unmanaged_relative = ".agents/skills/loopora-plan/SKILL.md"
    unmanaged_file = workdir / unmanaged_relative
    unmanaged_file.parent.mkdir(parents=True)
    unmanaged_file.write_text("# user-owned file\n", encoding="utf-8")

    preview = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert preview.exit_code == 0, _result_error_text(preview)
    preview_payload = json.loads(preview.stdout)
    planned = set(preview_payload["planned"])
    skipped = set(preview_payload["skipped"])
    assert preview_payload["dev_reset_summary"]["schema_version"] == 3
    assert preview_payload["dev_reset_summary"]["dry_run"] is True
    assert str(db) in planned
    assert str(workdir / ".loopora") in planned
    assert str(managed_file) in planned
    assert str(unmanaged_file) in skipped
    assert db.exists()
    assert (workdir / ".loopora").exists()
    assert managed_file.exists()
    assert unmanaged_file.exists()

    result = runner.invoke(
        cli.app,
        ["dev", "reset", "--workdir", str(workdir), "--yes", "--json"],
        env={APP_HOME_ENV: str(home)},
    )

    assert result.exit_code == 0, _result_error_text(result)
    payload = json.loads(result.stdout)
    removed = set(payload["removed"])
    skipped = set(payload["skipped"])
    assert payload["dev_reset_summary"]["schema_version"] == 3
    assert payload["dev_reset_summary"]["dry_run"] is False
    assert str(db) in removed
    assert str(workdir / ".loopora") in removed
    assert str(managed_file) in removed
    assert str(unmanaged_file) in skipped
    assert not db.exists()
    assert not (workdir / ".loopora").exists()
    assert not managed_file.exists()
    assert unmanaged_file.exists()


def _assert_cli_agent_entry_help(runner: CliRunner) -> None:
    init_group_help = runner.invoke(cli.app, ["init", "--help"])
    assert init_group_help.exit_code == 0, _result_error_text(init_group_help)
    assert "task goal, fake-done risk, and required evidence" in init_group_help.stdout

    init_help = runner.invoke(cli.app, ["init", "codex", "--help"])
    assert init_help.exit_code == 0, _result_error_text(init_help)
    assert "Install or update the Codex project entry for task-judgment first" in init_help.stdout
    assert "task goal" in init_help.stdout
    assert "fake-done risk" in init_help.stdout
    assert "required" in init_help.stdout
    assert "evidence" in init_help.stdout
    assert "/loopora-plan" in init_help.stdout
    assert "READY Loop preview" in init_help.stdout
    assert "/loopora-run" in init_help.stdout
    assert "same Agent session" in init_help.stdout
    assert "Project directory where the Coding Agent will" in init_help.stdout
    assert "work." in init_help.stdout
    assert "adapter" not in init_help.stdout.lower()

    uninstall_help = runner.invoke(cli.app, ["uninstall", "codex", "--help"])
    assert uninstall_help.exit_code == 0, _result_error_text(uninstall_help)
    assert "Remove the Loopora-managed Codex project entry." in uninstall_help.stdout
    assert "Project directory where the Coding Agent will" in uninstall_help.stdout
    assert "work." in uninstall_help.stdout
    assert "adapter" not in uninstall_help.stdout.lower()

    agent_help = runner.invoke(cli.app, ["agent", "codex", "plan", "--help"])
    assert agent_help.exit_code == 0, _result_error_text(agent_help)
    assert "Validate a generated Loop plan and return the Loop preview URL." in agent_help.stdout
    assert "Candidate Loop plan file" in agent_help.stdout
    assert "produced by the Coding Agent." in agent_help.stdout
    assert "--plan-file" in agent_help.stdout
    assert "Candidate Loopora bundle YAML" not in agent_help.stdout

    agent_group_help = runner.invoke(cli.app, ["agent", "codex", "--help"])
    assert agent_group_help.exit_code == 0, _result_error_text(agent_group_help)
    assert "Internal Codex runtime used by Loopora project entries" in agent_group_help.stdout
    assert " plan" in agent_group_help.stdout
    assert " run" in agent_group_help.stdout
    assert "adapter runtime" not in agent_group_help.stdout.lower()


def _assert_cli_bundle_import_help(runner: CliRunner) -> None:
    import_help = runner.invoke(cli.app, ["bundles", "import", "--help"])
    assert import_help.exit_code == 0, _result_error_text(import_help)
    assert "Import one Loop plan file and materialize its run-ready assets." in import_help.stdout
    assert "Path to a Loop plan file" in import_help.stdout
    assert "YAML bundle" not in import_help.stdout


@pytest.mark.parametrize("old_action", ["gen", "loop"])
def test_agent_runtime_does_not_keep_old_plan_run_aliases(old_action: str) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "codex", old_action, "--help"])

    assert result.exit_code != 0


def test_design_main_workflow_anchors_separate_run_status_and_loop_verdict() -> None:
    root = Path(__file__).resolve().parents[3]
    design_sources = {
        "design/README.md": (root / "design" / "README.md").read_text(encoding="utf-8"),
        "design/contracts.md": (root / "design" / "contracts.md").read_text(encoding="utf-8"),
    }

    contracts = design_sources["design/contracts.md"]
    assert "Web is full-function" in contracts
    assert "READY preview must reflect current canonical content" in contracts
    assert "Run status and Loop verdict are separate" in contracts
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "Loopora only owns `.loopora/` state" in contracts
    assert "Loopora-managed host entry files" in contracts
    assert "Public adapter names stay `loopora-*`" in contracts

    for source in design_sources.values():
        assert "bundle library" not in source.lower()
        assert "Web 只是观察面" not in source


def test_design_tree_stays_small_and_current() -> None:
    root = Path(__file__).resolve().parents[3]
    design_files = sorted(path.relative_to(root).as_posix() for path in (root / "design").rglob("*.md"))

    assert "design/core-ideas/product-principle.md" not in design_files
    assert "design/detailed-design/09-web-bundle-alignment.md" not in design_files
    assert {"design/contracts.md", "design/loopora_loop_kernel_refactor.md"} <= set(design_files)
    assert len(design_files) <= 4


def test_workflow_design_default_is_linear_with_advanced_compatibility() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime_design = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "Builder -> optional Inspector/Guide -> GateKeeper" in runtime_design
    assert "Advanced parallel/control fields are compatibility or expert-only surfaces" in runtime_design


def test_compiler_design_keeps_web_and_agent_on_same_core() -> None:
    root = Path(__file__).resolve().parents[3]
    contracts = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "same Core" in contracts
    assert "One shared success path and one shared failure path across Web/Agent" in contracts
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "model/provider defaults" in contracts
