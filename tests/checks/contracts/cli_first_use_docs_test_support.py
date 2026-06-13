from __future__ import annotations

import re

from typer.testing import CliRunner

from loopora import cli


def result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def assert_readme_entry_points(readmes: list[str], documented_adapters: list[set[str]]) -> None:
    assert documented_adapters == [{"codex", "claude", "opencode"}, {"codex", "claude", "opencode"}]
    assert all("loopora serve " in readme for readme in readmes)
    assert all('loopora doctor --workdir "$PWD"' in readme for readme in readmes)
    assert all("loopora diagnose doctor" in readme for readme in readmes)
    assert "After the preview looks right, run `/loopora-run`" in readmes[0]
    assert "预览看起来正确后，运行 `/loopora-run`" in readmes[1]
    assert all("confirmed Loop" not in readme for readme in readmes)


def assert_public_anchor_default_language(
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


def assert_alignment_language_assets(design_docs: dict[str, str], governance_scenario: str) -> None:
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


def assert_documented_cli_entries_available(documented_adapters: list[set[str]]) -> None:
    runner = CliRunner()
    for adapter in sorted(documented_adapters[0]):
        result = runner.invoke(cli.app, ["init", adapter, "--help"])
        assert result.exit_code == 0, result_error_text(result)
        assert "task goal" in result.stdout
        assert "fake-done risk" in result.stdout
        assert "required" in result.stdout
        assert "evidence" in result.stdout
        assert "/loopora-plan" in result.stdout
        assert "READY Loop preview" in result.stdout
        assert "/loopora-run" in result.stdout
        assert "same Agent session" in result.stdout

    serve_result = runner.invoke(cli.app, ["serve", "--help"])
    assert serve_result.exit_code == 0, result_error_text(serve_result)

    help_result = runner.invoke(cli.app, ["--help"])
    assert help_result.exit_code == 0, result_error_text(help_result)
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    assert "Start here:" in help_result.stdout
    assert re.search(r"loopora\s+init\s+codex", help_result.stdout)
    assert "task goal" in normalized_help
    assert "fake-done risk" in help_result.stdout
    assert "required evidence" in normalized_help
    assert "loopora doctor" in normalized_help
    assert "/loopora-plan" in help_result.stdout
    assert "/loopora-run" in help_result.stdout
    assert "same" in help_result.stdout
    assert "Agent session" in help_result.stdout
    assert help_result.stdout.index("Start here:") < help_result.stdout.index("Expert: create and run")
    assert help_result.stdout.index("│ init") < help_result.stdout.index("│ run")
    assert help_result.stdout.index("│ init") < help_result.stdout.index("│ doctor") < help_result.stdout.index("│ serve")
    assert help_result.stdout.index("│ serve") < help_result.stdout.index("│ run")
    assert help_result.stdout.index("Install /loopora-plan") < help_result.stdout.index(
        "Expert: create and inspect reusable run flows"
    )


def assert_cli_agent_entry_help(runner: CliRunner) -> None:
    init_group_help = runner.invoke(cli.app, ["init", "--help"])
    assert init_group_help.exit_code == 0, result_error_text(init_group_help)
    assert "task goal, fake-done risk, and required evidence" in init_group_help.stdout

    init_help = runner.invoke(cli.app, ["init", "codex", "--help"])
    assert init_help.exit_code == 0, result_error_text(init_help)
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
    assert uninstall_help.exit_code == 0, result_error_text(uninstall_help)
    assert "Remove the Loopora-managed Codex project entry." in uninstall_help.stdout
    assert "Project directory where the Coding Agent will" in uninstall_help.stdout
    assert "work." in uninstall_help.stdout
    assert "adapter" not in uninstall_help.stdout.lower()

    agent_help = runner.invoke(cli.app, ["agent", "codex", "plan", "--help"])
    assert agent_help.exit_code == 0, result_error_text(agent_help)
    assert "Validate a generated Loop plan and return the Loop preview URL." in agent_help.stdout
    assert "Candidate Loop plan file" in agent_help.stdout
    assert "produced by the Coding Agent." in agent_help.stdout
    assert "--plan-file" in agent_help.stdout
    assert "Candidate Loopora bundle YAML" not in agent_help.stdout

    agent_group_help = runner.invoke(cli.app, ["agent", "codex", "--help"])
    assert agent_group_help.exit_code == 0, result_error_text(agent_group_help)
    assert "Internal Codex runtime used by Loopora project entries" in agent_group_help.stdout
    assert " plan" in agent_group_help.stdout
    assert " run" in agent_group_help.stdout
    assert "adapter runtime" not in agent_group_help.stdout.lower()


def assert_cli_bundle_import_help(runner: CliRunner) -> None:
    import_help = runner.invoke(cli.app, ["bundles", "import", "--help"])
    assert import_help.exit_code == 0, result_error_text(import_help)
    assert "Import one Loop plan file and materialize its run-ready assets." in import_help.stdout
    assert "Path to a Loop plan file" in import_help.stdout
    assert "YAML bundle" not in import_help.stdout
