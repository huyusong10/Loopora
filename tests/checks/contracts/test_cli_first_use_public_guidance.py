from __future__ import annotations

import errno
import json
import re
from pathlib import Path

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli, web_bind_preflight
from loopora.cli_fit_output import fit_cli_entry
from loopora.start_guidance import start_guidance_lines, start_guidance_payload

from cli_first_use_docs_test_support import (
    assert_alignment_language_assets,
    assert_documented_cli_entries_available,
    assert_public_anchor_default_language,
    assert_readme_entry_points,
    assert_start_and_fit_app_state_reset_recovery,
    complete_fit_review_cli_args,
    result_error_text,
)


def test_public_first_use_docs_match_cli_entries() -> None:
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
    governance_scenario = (root / "tests" / "scenarios" / "long_running_governance_loop.md").read_text(encoding="utf-8")
    documented_adapters = [set(re.findall(r"\bloopora init ([a-z]+)\b", readme)) - {"current"} for readme in readmes]

    assert_readme_entry_points(readmes, documented_adapters)
    assert "Pick the route before you install same-Agent project entries or create a Loop:" in english_readme
    assert "先选路线，再安装同一 Agent 项目入口或创建 Loop：" in chinese_readme
    english_quick_start = english_readme.split("## Quick Start", 1)[1].split("## How `/loopora-plan` Plans", 1)[0]
    chinese_quick_start = chinese_readme.split("## 快速开始", 1)[1].split("## `/loopora-plan` 如何规划", 1)[0]
    for snippet, text in (
        ("Bare `uv run loopora start` and `uv run loopora fit` print a target-project rerun command", english_quick_start),
        ("裸 `uv run loopora start` 和 `uv run loopora fit`", chinese_quick_start),
        ("Use the route chooser output as the next-step authority.", english_readme),
        ("If you are already working inside Codex, Claude Code, or OpenCode", english_readme),
        ("Web conversation, Plan File import, and manual expert paths enter the same local records", english_readme),
        ("把路线向导输出作为下一步依据。", chinese_readme),
        ("如果你已经在 Codex、Claude Code 或 OpenCode 里工作", chinese_readme),
        ("Web 对话、Plan File 导入和手动专家路径都会进入同一套本地记录", chinese_readme),
    ):
        assert snippet in text
    for earlier, later, text in (
        ("uv run loopora --version", "uv tool install .", english_quick_start), ("uv run loopora fit", "uv tool install .", english_quick_start),
        ("uv tool install .", "uv tool install --editable .", english_quick_start), ("uv run loopora --version", "uv tool install .", chinese_quick_start),
        ("uv run loopora fit --language zh", "uv tool install .", chinese_quick_start), ("uv tool install .", "uv tool install --editable .", chinese_quick_start),
        ("loopora serve", "loopora init codex", english_quick_start),
        ("loopora serve", "loopora init codex", chinese_quick_start),
        ("/loopora-plan", "READY preview", english_quick_start),
        ("READY preview", "/loopora-run", english_quick_start),
        ("/loopora-plan", "预览看起来正确", chinese_quick_start),
        ("预览看起来正确", "/loopora-run", chinese_quick_start),
    ):
        assert text.index(earlier) < text.index(later)
    for readme in readmes:
        for snippet in (
            "uv tool install .", "uv tool install --editable .",
            "uv tool install --force .", "uv tool install --force --editable .",
            'loopora doctor --workdir "$PWD"',
            "/loopora-plan",
            "/loopora-run",
                'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742',
        ):
            assert snippet in readme
        assert readme.count("\nuv tool install .\n") == 1
        assert readme.count("uv tool install --editable .") == 1
    assert_public_anchor_default_language(english_readme, chinese_readme, human_shaped_loop_docs)
    assert_alignment_language_assets(design_docs, governance_scenario)
    assert_documented_cli_entries_available(documented_adapters)


def test_cli_start_preflights_default_web_port_for_public_first_route(monkeypatch, tmp_path: Path) -> None:
    probed_ports: list[int] = []

    def fake_probe(_host: str, port: int) -> None:
        probed_ports.append(port)
        if port == 8742:
            raise OSError(errno.EADDRINUSE, "in use")

    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", fake_probe)
    monkeypatch.setattr("loopora.start_guidance_actions.matching_configured_web_service", lambda *_args: False)
    monkeypatch.setattr("loopora.fit_guidance_web_route.matching_configured_web_service", lambda *_args: False)
    result = CliRunner().invoke(cli.app, ["start", "--workdir", str(tmp_path), "--json"])
    plain = CliRunner().invoke(cli.app, ["start", "--workdir", str(tmp_path), *complete_fit_review_cli_args(), "--details"])
    payload = json.loads(result.stdout)
    actions = {action["kind"]: action for action in payload["route_actions_after_strong_fit"]}
    assert (
        result.exit_code,
        plain.exit_code,
        payload["start_guidance_summary"]["web_route_preflight_status"],
        actions["open_web_creation_choices"]["requested_port"],
        actions["open_web_creation_choices"]["port"],
    ) == (0, 0, "default_port_in_use_with_suggestion", 8742, 8743)
    assert (
        "--web-host 127.0.0.1 --web-port 8743" in actions["confirm_readiness"]["command"],
        "--web-host 127.0.0.1 --web-port 8743" in actions["support"]["command"],
    ) == (True, True)
    assert "Default Web port 8742 is already in use; this route uses available port 8743." in plain.stdout
    assert probed_ports[:2] == [8742, 8743]
    monkeypatch.setattr(web_bind_preflight, "next_available_web_port", lambda **_kwargs: None)
    blocked_result = CliRunner().invoke(cli.app, ["start", "--workdir", str(tmp_path), "--json"])
    blocked_plain = CliRunner().invoke(cli.app, ["start", "--workdir", str(tmp_path), *complete_fit_review_cli_args(), "--details"])
    blocked_payload = json.loads(blocked_result.stdout)
    blocked_summary = blocked_payload["start_guidance_summary"]
    blocked_fit = blocked_payload["fit_guidance"]
    blocked_fit_summary = blocked_fit["fit_guidance_summary"]
    assert (
        blocked_summary["web_route_preflight_status"],
        blocked_fit_summary["web_route_preflight_status"],
        blocked_fit["web_route_preflight"]["preflight_status"],
        blocked_fit_summary["web_route_command_ready"],
        blocked_fit_summary["route_action_blocked_kinds"],
        blocked_summary["web_route_command_ready"],
        blocked_summary["route_action_blocked_kinds"],
        blocked_summary["route_action_command_blockers"]["open_web_creation_choices"],
    ) == (
        "default_port_in_use_no_suggestion",
        "default_port_in_use_no_suggestion",
        "default_port_in_use_no_suggestion",
        False,
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review"],
        False,
        ["open_web_creation_choices", "install_agent_entry", "confirm_readiness", "return_to_agent", "run_after_review"],
        ["fit_review_required", "web_port_unavailable"],
    )
    assert all(
        fragment in blocked_plain.stdout
        for fragment in (
            "Fit Guide/Web choices",
            "blocked until a usable local Web port is chosen",
            "Requested Web command, currently unavailable:",
        )
    )


def test_cli_fit_source_checkout_entry_keeps_first_use_commands_copyable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/.venv/bin/loopora"])
    cli_entry = fit_cli_entry()
    assert cli_entry == agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    monkeypatch.chdir(tmp_path)
    root = str(tmp_path.resolve())
    bare = start_guidance_payload(cli_entry=cli_entry)
    assert (
        bare["start_guidance_summary"]["workdir_ready"],
        bare["setup_allowed"],
        bare["setup_commands_ready"],
        bare["setup_command_blockers"],
        bare["route_preview_executable"],
        bare["route_preview_blockers"],
        bare["setup_gate_ready"],
        bare["setup_gate_blockers"],
        bare["start_guidance_summary"]["setup_gate_ready"],
        bare["fit_guidance"]["setup_gate_blockers"],
    ) == (
        False,
        False,
        False,
        ["target_project_required"],
        False,
        ["target_project_required"],
        False,
        ["fit_review_required", "target_project_required"],
        False,
        ["fit_review_required", "target_project_required"],
    )
    assert (
        [action["kind"] for action in bare["next_actions"]],
        bare["next_actions"][1]["command"],
        bare["next_actions"][1]["command_ready"],
        bare["next_actions"][1]["command_blockers"],
        bare["next_actions"][2]["command"],
    ) == (["check_fit_first", "choose_workdir", "support"], f'{cli_entry} start --workdir "$PWD"', True, [], f"{cli_entry} support")
    bare_text = "\n".join(start_guidance_lines(bare))
    assert all(
        text in bare_text
        for text in (
            "Choose target project:",
            "Target project: not supplied; rerun start from the target project",
            "Route choices stay hidden until the fit review is complete.",
        )
    )
    assert not any(
        text in bare_text
        for text in ("replace <project-dir> in route commands", "Route shape after choosing a usable target project:", "Fit Guide/Web choices", "loopora init")
    )
    zh_bare = start_guidance_payload(language="zh", cli_entry=cli_entry)
    assert (
        zh_bare["next_actions"][1]["command"],
        zh_bare["next_actions"][1]["note"],
        zh_bare["next_actions"][1]["command_ready"],
        zh_bare["next_actions"][1]["command_blockers"],
        "Choose a target project" not in "\n".join(start_guidance_lines(zh_bare)),
    ) == (f'{cli_entry} start --language zh --workdir "$PWD"', "请先进入目标项目目录，再运行此命令获取路线命令。", True, [], True)
    start = start_guidance_payload(workdir=Path(), cli_entry=cli_entry)
    route_commands = [item.get("command", "") for item in start["route_actions_after_strong_fit"]]
    assert (
        start["workdir"],
        start["workdir_arg"],
        start["workdir_state"]["workdir"],
        start["target_project_required"],
        start["route_commands_are_placeholders"],
        start["setup_commands_ready"],
        start["setup_command_blockers"],
        start["route_preview_executable"],
        start["route_preview_blockers"],
        start["route_actions_after_strong_fit"][2]["adapter_choices"][0]["local_only"],
        start["setup_gate_ready"],
        start["setup_gate_blockers"],
        start["start_guidance_summary"]["setup_gate_ready"],
        start["fit_guidance"]["setup_gate_ready"],
        start["fit_guidance"]["setup_gate_blockers"],
    ) == (root, root, root, False, False, True, [], True, [], True, False, ["fit_review_required"], False, False, ["fit_review_required"])
    assert (
        start["fit_review_recommended_before_setup"],
        start["setup_command_readiness_scope"],
        start["start_guidance_summary"]["fit_review_recommended_before_setup"],
        start["fit_guidance"]["setup_command_readiness_scope"],
        "Recommended next action: complete the fit review before setup:" in "\n".join(start_guidance_lines(start)),
        "--task '<task goal>'" in start["next_actions"][0]["command_template"],
        "Route choices stay hidden until the fit review is complete." in "\n".join(start_guidance_lines(start)),
        "Fit Guide/Web choices" not in "\n".join(start_guidance_lines(start)),
    ) == (True, "target_project_gate_fit_review_not_recorded", True, "target_project_gate_fit_review_not_recorded", True, True, True, True)
    assert (route_commands[0], f"{cli_entry} serve --open --workdir {root} --host 127.0.0.1 --port 8742" in route_commands) == (
        f"{cli_entry} fit --workdir {root}",
        True,
    )
    assert "Preview only:" not in "\n".join(start_guidance_lines(start))
    assert (
        [action["kind"] for action in start["next_actions"]],
        "command" in start["next_actions"][0],
        start["next_actions"][0]["command_ready"],
        start["fit_guidance"]["next_actions"][0]["command_template"],
    ) == (["complete_review_inputs"], False, False, start["next_actions"][0]["command_template"])
    missing = str((tmp_path / "missing").resolve())
    blocked = start_guidance_payload({"task": "Migrate billing callbacks"}, workdir=Path("missing"), cli_entry=cli_entry)
    assert (
        blocked["setup_allowed"],
        blocked["workdir_state"]["workdir"],
        blocked["workdir_arg"],
        blocked["target_project_required"],
        blocked["route_commands_are_placeholders"],
        blocked["setup_commands_ready"],
        blocked["setup_command_blockers"],
        blocked["route_preview_executable"],
        blocked["route_preview_blockers"],
    ) == (
        False,
        missing,
        missing,
        False,
        False,
        False,
        ["review_inputs_required", "target_project_unready"],
        False,
        ["review_inputs_required", "target_project_unready"],
    )
    assert (
        [action["kind"] for action in blocked["next_actions"]],
        blocked["next_actions"][0]["command_template"].startswith(f"{cli_entry} fit --workdir {missing} --task "),
        "command" in blocked["next_actions"][0],
        blocked["next_actions"][0]["command_ready"],
    ) == (["complete_review_inputs", "create_workdir", "confirm_readiness", "support", "continue_if_strong_fit"], True, False, False)
    assert (
        blocked["next_actions"][1]["command"],
        blocked["next_actions"][2]["command"],
        blocked["next_actions"][3]["command_ready"],
        blocked["next_actions"][3]["command_blockers"],
    ) == (f"mkdir -p {missing}", f"{cli_entry} doctor --workdir {missing}", True, [])
    assert "Route choices stay hidden until the fit review is complete." in "\n".join(start_guidance_lines(blocked))
    assert (
        "\n".join(start_guidance_lines(blocked)).count("Usage/setup help:"),
        "support --workdir" in "\n".join(start_guidance_lines(blocked)),
        "Complete review inputs:" in "\n".join(start_guidance_lines(blocked)),
    ) == (1, True, True)
    zh_blocked_text = "\n".join(
        start_guidance_lines(start_guidance_payload({"task": "迁移账单回调"}, workdir=Path("missing"), language="zh", cli_entry=cli_entry))
    )
    assert ("补齐判断输入:" in zh_blocked_text, "创建目标目录:" not in zh_blocked_text) == (True, True)
    file_target = tmp_path / "not-a-project"
    file_target.write_text("not a directory\n", encoding="utf-8")
    unusable = start_guidance_payload(workdir=file_target, cli_entry=cli_entry)
    assert (
        unusable["workdir_arg"],
        unusable["target_project_required"],
        unusable["route_commands_are_placeholders"],
        unusable["setup_commands_ready"],
        unusable["setup_command_blockers"],
        unusable["route_preview_executable"],
        unusable["route_preview_blockers"],
    ) == ("'<project-dir>'", True, True, False, ["target_project_required"], False, ["target_project_required"])
    assert str(file_target.resolve()) not in unusable["route_actions_after_strong_fit"][1]["command"]
    assert (
        [action["kind"] for action in unusable["next_actions"]],
        "<project-dir>" not in json.dumps(unusable["next_actions"]),
        unusable["next_actions"][1]["command_ready"],
        unusable["next_actions"][2]["command_ready"],
        unusable["next_actions"][2]["command_blockers"],
    ) == (["check_fit_first", "choose_workdir", "support"], True, True, True, [])
    assert_start_and_fit_app_state_reset_recovery(monkeypatch, tmp_path)


def test_cli_fit_zh_review_keeps_language_neutral_state_and_localized_heading() -> None:
    runner = CliRunner()
    json_result = runner.invoke(cli.app, ["fit", "--language", "zh", "--task", "迁移账单回调", "--json"])
    plain_result = runner.invoke(cli.app, ["fit", "--language", "zh", "--task", "迁移账单回调", "--details"])
    assert json_result.exit_code == 0, result_error_text(json_result)
    payload = json.loads(json_result.stdout)
    assert payload["language"] == "zh"
    assert payload["primary_first_task_message_status"] == "preview_only_until_review_inputs_complete"
    assert payload["primary_first_task_message_copy_allowed"] is False
    assert payload["task_fit_review"]["task_fit_review_summary"]["draft_first_task_message_status"] == ("preview_only_until_review_inputs_complete")
    assert plain_result.exit_code == 0, result_error_text(plain_result)
    assert "第一条 /loopora-plan 消息：判断输入补齐前仅作预览。" in plain_result.stdout
    assert "第一条任务消息预览（复制前先补齐判断输入）:" in plain_result.stdout
    assert "可复制的第一条任务消息:" not in plain_result.stdout


def _assert_contains_all(text: str, terms: tuple[str, ...]) -> None:
    for term in terms:
        assert term in text


def test_cli_fit_review_accepts_semantic_option_aliases_without_spreading_them() -> None:
    runner = CliRunner()
    complete = runner.invoke(
        cli.app,
        [
            "fit",
            "--task",
            "Migrate billing callbacks",
            "--strong-fit-signal",
            "Needs replay governance",
            "--fake-done-risks",
            "Retry remains unproven",
            "--required-evidence",
            "Replay proof",
            "--judgment-tradeoffs",
            "Fail closed",
            "--why-not-direct",
            "Unit tests alone miss replay ordering",
            "--json",
        ],
    )
    partial = runner.invoke(cli.app, ["fit", "--task", "Migrate billing callbacks", "--fake-done-risks", "Retry", "--json"])
    help_result = runner.invoke(cli.app, ["fit", "--help"])

    assert complete.exit_code == 0, complete.stdout
    complete_payload = json.loads(complete.stdout)
    review = complete_payload["task_fit_review"]
    assert review["review_inputs"]["loopora_fit_reason"] == "Needs replay governance"
    assert review["review_inputs"]["fake_done_risks"] == "Retry remains unproven"
    assert review["review_inputs"]["required_evidence"] == "Replay proof"
    assert review["review_inputs"]["judgment_tradeoffs"] == "Fail closed"
    assert (
        review["review_inputs"]["direct_path_check"],
        "Unit tests alone miss replay ordering" not in complete_payload["direct_path_next_actions"][0]["command_template"],
    ) == ("Unit tests alone miss replay ordering", True)
    assert partial.exit_code == 0, partial.stdout
    completion_command = json.loads(partial.stdout)["task_fit_review"]["review_completion_command"]
    assert all(alias not in completion_command for alias in ("--strong-fit-signal", "--fake-done-risks", "--required-evidence", "--judgment-tradeoffs"))
    assert all(option in completion_command for option in ("--fit-reason", "--fake-done", "--evidence", "--tradeoffs"))
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    for alias in ("--strong-fit-signal", "--fake-done-risks", "--required-evidence", "--judgment-tradeoffs", "--why-not-direct"):
        assert alias in normalized_help


def _assert_partial_fit_review_result(partial, partial_json) -> None:
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    assert partial.exit_code == 0, partial.stdout
    _assert_contains_all(
        partial.stdout,
        (
            "First /loopora-plan message: preview only until review inputs are complete.",
            "Setup: blocked until the missing review inputs are complete.",
            "Missing review inputs:",
            "Loopora fit reason (--fit-reason)",
            "fake-done risks (--fake-done)",
            "required evidence (--evidence)",
            "judgment tradeoffs (--tradeoffs)",
            "Completion command:",
            "loopora fit --task",
            "Next before setup:",
            f"Complete review inputs: {cli_entry} fit --task",
            "Route choices stay hidden until the fit review is complete.",
            "If review says Loopora is not needed:",
            "do not install same-Agent project entries",
        ),
    )
    assert "setup_gate:" not in partial.stdout
    assert "first_task_message_status:" not in partial.stdout
    assert "Next if fit is strong:" not in partial.stdout
    assert "Preview first task message (complete review inputs before copying):" in partial.stdout
    assert "Copyable one-message /loopora-plan handoff:" not in partial.stdout
    assert 'loopora init codex --workdir "$PWD"' not in partial.stdout
    assert "/loopora-run" not in partial.stdout
    assert all(option in partial.stdout for option in ("--fit-reason", "--fake-done", "--evidence", "--tradeoffs"))
    assert "<how this could look done while core risk remains unproven>" in partial.stdout
    assert partial_json.exit_code == 0, partial_json.stdout
    partial_payload = json.loads(partial_json.stdout)
    partial_review = partial_payload["task_fit_review"]
    assert partial_payload["primary_first_task_message"] == partial_review["draft_first_task_message"]
    assert partial_payload["primary_first_task_message_source"] == "task_review_draft"
    assert partial_payload["primary_first_task_message_status"] == "preview_only_until_review_inputs_complete"
    assert (
        partial_payload["primary_first_task_message_ready"],
        partial_payload["fit_guidance_summary"]["primary_first_task_message_state"]["copy_allowed"],
    ) == (False, False)
    assert partial_payload["primary_first_task_message_copy_allowed"] is False
    assert [item["kind"] for item in partial_payload["direct_path_next_actions"]] == ["record_direct_decision", "use_direct_agent_or_hard_checks"]
    assert [item["kind"] for item in partial_payload["next_actions"]] == ["complete_review_inputs", "choose_workdir", "support", "continue_if_strong_fit"]
    assert (
        partial_payload["next_actions"][0]["command_template"],
        "command" in partial_payload["next_actions"][0],
        partial_payload["next_actions"][0]["command_ready"],
        partial_payload["next_actions"][0]["command_blockers"],
    ) == (partial_review["review_completion_command"], False, False, ["review_inputs_required"])
    assert all(
        item["kind"] not in {"install_agent_entry", "return_to_agent", "open_web_creation_choices", "run_after_review"}
        for item in partial_payload["next_actions"]
    )
    assert partial_review["task_fit_review_summary"]["ready_for_loopora_plan_message"] is False
    assert partial_review["task_fit_review_summary"]["draft_first_task_message_status"] == "preview_only_until_review_inputs_complete"
    assert partial_review["task_fit_review_summary"]["draft_first_task_message_copy_allowed"] is False
    assert partial_review["task_fit_review_summary"]["setup_allowed"] is False
    assert partial_review["task_fit_review_summary"]["setup_gate"] == "blocked_until_review_inputs_complete"
    assert partial_review["task_fit_review_summary"]["setup_blocker"] == "missing_review_inputs"
    assert partial_review["task_fit_review_summary"]["missing_input_count"] == 4
    assert partial_review["task_fit_review_summary"]["review_completion_command_available"] is True
    assert partial_review["missing_first_task_input_ids"] == ["loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert partial_review["next_review_action"] == "fill_missing_judgment_before_setup"
    assert partial_review["review_completion_command"].startswith(f"{cli_entry} fit --task ")
    assert "--fit-reason" in partial_review["review_completion_command"]
    assert "--fake-done" in partial_review["review_completion_command"]
    assert "--evidence" in partial_review["review_completion_command"]
    assert "--tradeoffs" in partial_review["review_completion_command"]
    assert "<how this could look done while core risk remains unproven>" in partial_review["review_completion_command"]
    assert "<tests, probes, artifacts, browser/API proof, or reviewer-readable evidence>" in partial_review["review_completion_command"]


def _assert_complete_fit_review_plain(plain, review: dict[str, str]) -> None:
    assert plain.exit_code == 0, plain.stdout
    task = review["task"]
    fit_reason = review["fit_reason"]
    fake_done = review["fake_done"]
    evidence = review["evidence"]
    tradeoffs = review["tradeoffs"]
    _assert_contains_all(
        plain.stdout,
        (
            "Task fit review",
            "Review required: yes; Loopora does not classify the task automatically.",
            "First /loopora-plan handoff: ready to paste as one Agent message after you confirm the review.",
            "Setup: blocked until a usable target project is supplied.",
            "Missing review inputs: none",
            "Target project: not supplied; rerun fit from the target project before copying route commands.",
            "If review says Loopora is not needed:",
            "do not install same-Agent project entries",
            "Route preview: hidden until you choose a usable target project; rerun fit from that project before copying Web/init/doctor commands.",
            "Copyable one-message /loopora-plan handoff:",
            "- goal: " + task,
            "- Loopora fit reason: " + fit_reason,
            "- fake-done risks: " + fake_done,
            "- required evidence: " + evidence,
            "- judgment tradeoffs: " + tradeoffs,
            f"Loopora fit: {fit_reason};",
            f"Goal: {task};",
            f"Fake-done risks: {fake_done};",
            f"Required evidence: {evidence};",
            f"Judgment tradeoffs: {tradeoffs}.",
        ),
    )
    assert "Completion command:" not in plain.stdout
    assert "setup_gate:" not in plain.stdout
    assert plain.stdout.index("If review says Loopora is not needed:") < plain.stdout.index("Target project: not supplied;")
    assert plain.stdout.index("Target project: not supplied;") < plain.stdout.index("Route preview: hidden until you choose a usable target project")
    assert not any(
        item in plain.stdout
        for item in (
            "Route shape if fit is strong:",
            "Choose the route that matches where you are:",
            "Fit Guide/Web choices: loopora serve --open --workdir '<project-dir>'",
            "loopora init codex --workdir '<project-dir>'",
            "loopora doctor --workdir '<project-dir>'",
            "After the READY preview matches the task judgment:",
        )
    )
    assert not any(item in plain.stdout for item in ("Next before setup:", "Answer before setup:", "Which strong-fit signal"))
    assert "Preview first task message (complete review inputs before copying):" not in plain.stdout
    assert "<how this could look done while core risk remains unproven>" not in plain.stdout
    assert "First task message shape:" not in plain.stdout


def _assert_complete_fit_review_json(json_result, review_fields: dict[str, str]) -> None:
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert next(iter(payload)) == "fit_guidance_summary"
    review = payload["task_fit_review"]
    task = review_fields["task"]
    fit_reason = review_fields["fit_reason"]
    fake_done = review_fields["fake_done"]
    evidence = review_fields["evidence"]
    tradeoffs = review_fields["tradeoffs"]
    assert payload["primary_first_task_message"] == review["draft_first_task_message"]
    assert payload["primary_first_task_message_source"] == "task_review_draft"
    assert payload["primary_first_task_message_status"] == "copyable_after_review_inputs_complete"
    assert (
        payload["primary_first_task_message_ready"],
        payload["fit_guidance_summary"]["primary_first_task_message_state"]["completed_review"],
        payload["fit_review_recommended_before_setup"],
        payload["setup_command_readiness_scope"],
        payload["fit_guidance_summary"]["fit_review_recommended_before_setup"],
        payload["fit_guidance_summary"]["setup_command_readiness_scope"],
    ) == (True, True, False, "target_project_and_fit_review", False, "target_project_and_fit_review")
    assert (
        payload["setup_gate_ready"],
        payload["setup_gate_blockers"],
        payload["fit_guidance_summary"]["setup_gate_ready"],
        payload["fit_guidance_summary"]["setup_gate_blockers"],
    ) == (False, ["target_project_required"], False, ["target_project_required"])
    assert payload["primary_first_task_message_copy_allowed"] is True
    assert review["task_fit_review_summary"]["human_judgment_required"] is True
    assert review["task_fit_review_summary"]["not_a_classifier"] is True
    assert review["task_fit_review_summary"]["complete_first_task_message"] is True
    assert review["task_fit_review_summary"]["ready_for_loopora_plan_message"] is True
    assert review["task_fit_review_summary"]["draft_first_task_message_status"] == ("copyable_after_review_inputs_complete")
    assert review["task_fit_review_summary"]["draft_first_task_message_copy_allowed"] is True
    assert (
        review["task_fit_review_summary"]["setup_allowed"],
        review["task_fit_review_summary"]["setup_gate"],
        review["task_fit_review_summary"]["setup_blocker"],
        review["task_fit_review_summary"]["setup_command_blockers"],
    ) == (False, "blocked_until_target_project", "target_project_required", ["target_project_required"])
    assert review["task_fit_review_summary"]["missing_input_count"] == 0
    assert review["task_fit_review_summary"]["review_completion_command_available"] is False
    assert review["required_first_task_input_ids"] == ["task", "loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert review["missing_first_task_input_ids"] == []
    assert review["next_review_action"] == "copy_draft_after_review"
    assert review["task"] == task
    assert review["review_inputs"] == {
        "task": task,
        "loopora_fit_reason": fit_reason,
        "fake_done_risks": fake_done,
        "required_evidence": evidence,
        "judgment_tradeoffs": tradeoffs,
        "direct_path_check": "",
    }
    assert review["review_completion_command"] == ""
    assert [item["kind"] for item in payload["direct_path_next_actions"]] == ["record_direct_decision", "use_direct_agent_or_hard_checks"]
    assert "direct Agent, /goal, hard checks" in payload["direct_path_next_actions"][1]["note"]
    assert (
        [item["kind"] for item in payload["next_actions"]],
        payload["next_actions"][0]["command"].startswith(f'{cli_entry} fit --workdir "$PWD" --task '),
        all(value in payload["next_actions"][0]["command"] for value in (task, fit_reason, fake_done, evidence, tradeoffs)),
        payload["next_actions"][0]["command_ready"],
        payload["next_actions"][0]["command_blockers"],
        payload["next_actions"][1]["command"],
    ) == (["choose_workdir", "support"], True, True, True, [], f"{cli_entry} support")
    route_actions = payload["route_actions_after_strong_fit"]
    assert [item["kind"] for item in route_actions] == [
        "open_web_creation_choices",
        "install_agent_entry",
        "confirm_readiness",
        "return_to_agent",
        "run_after_review",
        "support",
    ]
    assert route_actions[0]["command"] == f"{cli_entry} serve --open --workdir '<project-dir>' --host 127.0.0.1 --port 8742"
    assert (route_actions[1]["selection_required"], route_actions[2]["after_action"]) == (True, "install_agent_entry")
    assert [choice["adapter"] for choice in route_actions[1]["adapter_choices"]] == ["codex", "claude", "opencode"]
    assert (
        [item["id"] for item in payload["fit_review_input_fields"]],
        payload["fit_review_input_fields"][-1]["placeholder_en"],
        payload["fit_review_input_fields"][-1]["direct_decision_label_en"],
        payload["fit_review_input_fields"][-1]["direct_decision_placeholder_en"],
    ) == (
        ["task", "loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs", "direct_path_check"],
        "Why direct Agent work, /goal, hard checks, or project workflow is not enough here",
        "Direct-path decision",
        "Which direct Agent, /goal, hard checks, or project process is enough here",
    )
    assert review["strong_fit_signal_ids"] == ["multi_round_evidence", "slow_feedback", "fake_done_risk", "retained_judgment"]
    assert review["direct_path_signal_ids"] == ["one_pass_review", "hard_checks_complete", "fast_feedback", "project_specific_workflow"]
    assert [item["id"] for item in review["review_questions"]] == [
        "strong_fit_signal",
        "direct_path_escape",
        "evidence_needed",
        "closure_blocker",
    ]
    assert review["draft_first_task_message"].startswith(f"/loopora-plan\n\nLoopora fit: {fit_reason}; Goal: {task};")


def _assert_chinese_default_fit_output(plain, plain_json) -> None:
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    assert plain.exit_code == 0, plain.stdout
    text = plain.stdout
    _assert_contains_all(
        text,
        (
            "Loopora 适配指南",
            "设置前先回答:",
            "这个任务到底命中了哪一个强适配信号？",
            "还没有第一条 /loopora-plan 消息：",
            "设置前下一步:",
            f'{cli_entry} fit --language zh --workdir "$PWD"',
            "适配审查补齐前，路线选择保持隐藏。",
        ),
    )
    assert not any(
        item in text
        for item in (
            "选择符合当前上下文的路线:",
            "适用性判断/Web 选择: loopora serve --open --workdir '<project-dir>'",
            "loopora init codex --workdir '<project-dir>'",
            "READY 预览符合任务判断后:",
        )
    )
    assert "/loopora-plan\n\nLoopora 适配：" not in text
    assert plain_json.exit_code == 0, plain_json.stdout
    plain_payload = json.loads(plain_json.stdout)
    assert (
        plain_payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora 适配："),
        plain_payload["first_task_message_example_state"]["completed_review"],
    ) == (True, False)
    assert "Fake-done risks:" not in plain_payload["first_task_message_example"]
    assert (plain_payload["primary_first_task_message"], plain_payload["primary_first_task_message_source"]) == ("", "not_available_until_review")
    assert plain_payload["next_actions"][0]["kind"] == "choose_workdir"
    assert (
        plain_payload["next_actions"][0]["command"],
        plain_payload["next_actions"][0]["note"],
        plain_payload["next_actions"][0]["command_ready"],
        plain_payload["next_actions"][0]["command_blockers"],
    ) == (f'{cli_entry} fit --language zh --workdir "$PWD"', "请先进入目标项目目录，再运行此命令获取路线命令。", True, [])
    route_action = plain_payload["route_actions_after_strong_fit"][0]
    assert route_action["kind"] == "open_web_creation_choices"
    assert route_action["note"].startswith("不在 Agent 会话中时，先选择适用性判断/Web 选择")
    assert "只有当前已经在 Agent 宿主中时才选择同一 Agent 设置" in route_action["note"]
    assert plain_payload["route_actions_after_strong_fit"][-1]["command"].startswith(f"{cli_entry} support --language zh --workdir ")


def _assert_chinese_partial_fit_review(partial, partial_json, start_json) -> None:
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    assert partial.exit_code == 0, partial.stdout
    _assert_contains_all(
        partial.stdout,
        (
            "Loopora 适配指南",
            "多轮 Agent 工作，每轮都要产生或评估新证据",
            "任务适配审查",
            "第一条 /loopora-plan 消息：判断输入补齐前仅作预览。",
            "设置：已阻止；请先补齐缺失的判断输入。",
            "设置前先回答:",
            "这个任务到底命中了哪一个强适配信号？",
            "补全命令:",
            "loopora fit --language zh --task",
            "<命中的强适配信号，以及为什么需要 Loopora>",
            "<看起来完成但核心风险未证明的方式>",
            "第一条任务消息预览（复制前先补齐判断输入）:",
            "/loopora-plan\n\nLoopora 适配：",
            "如果审查显示不需要 Loopora:",
            "不要安装同一 Agent 项目入口",
            "设置前下一步:",
            f"补齐判断输入: {cli_entry} fit --language zh --task",
            "适配审查补齐前，路线选择保持隐藏。",
        ),
    )
    text = partial.stdout
    assert "first_task_message_status:" not in text
    assert "可复制的第一条任务消息:" not in text
    assert "Which strong-fit signal" not in text
    assert "/loopora-plan\n\nGoal:" not in text
    assert partial_json.exit_code == start_json.exit_code == 0, partial_json.stdout
    payload = json.loads(partial_json.stdout)
    review = payload["task_fit_review"]
    assert payload["language"] == "zh"
    assert payload["fit_guidance_summary"]["language"] == "zh"
    assert payload["strong_fit_signals"][0] == "多轮 Agent 工作，每轮都要产生或评估新证据"
    assert (
        payload["next_actions"][0]["command_template"].startswith(f"{cli_entry} fit --language zh --task "),
        "command" in payload["next_actions"][0],
        payload["next_actions"][0]["command_ready"],
    ) == (True, False, False)
    assert (
        payload["next_actions"][1]["kind"],
        payload["next_actions"][1]["command"].startswith(f'{cli_entry} fit --language zh --workdir "$PWD" --task '),
        review["task"] in payload["next_actions"][1]["command"],
        payload["next_actions"][1]["note"],
        payload["next_actions"][1]["command_ready"],
        payload["next_actions"][1]["command_blockers"],
        payload["next_actions"][2]["command"],
        payload["next_actions"][3]["note"],
        json.loads(start_json.stdout)["next_actions"][1]["command"].startswith(f"{cli_entry} support --language zh --workdir "),
    ) == (
        "choose_workdir",
        True,
        True,
        "请先进入目标项目目录，再运行此命令获取路线命令。",
        True,
        [],
        f"{cli_entry} support --language zh",
        "只有补全后的审查仍显示 Loopora 很适合时才继续",
        True,
    )
    assert payload["direct_path_next_actions"][0]["kind"] == "record_direct_decision"
    assert "不要安装同一 Agent 项目入口" in payload["direct_path_next_actions"][1]["note"]
    assert review["review_completion_command"].startswith(f"{cli_entry} fit --language zh --task ")
    assert review["draft_first_task_message"].startswith("/loopora-plan\n\nLoopora 适配：<命中的强适配信号")
    assert payload["primary_first_task_message"] == review["draft_first_task_message"]
    assert payload["primary_first_task_message_source"] == "task_review_draft"
    assert payload["primary_first_task_message_status"] == "preview_only_until_review_inputs_complete"
    assert payload["primary_first_task_message_copy_allowed"] is False
    assert review["task_fit_review_summary"]["setup_gate"] == "blocked_until_review_inputs_complete"
    assert review["task_fit_review_summary"]["draft_first_task_message_status"] == ("preview_only_until_review_inputs_complete")


def test_cli_fit_language_keeps_chinese_first_use_path_actionable(tmp_path: Path) -> None:
    runner = CliRunner()
    task = "迁移账单回调，同时保住幂等性和回滚证据"

    plain = runner.invoke(cli.app, ["fit", "--language", "zh", "--details"])
    plain_json = runner.invoke(cli.app, ["fit", "--language", "zh", "--json"])
    partial = runner.invoke(cli.app, ["fit", "--language", "zh", "--task", task, "--details"])
    partial_json = runner.invoke(cli.app, ["fit", "--language", "zh", "--task", task, "--json"])
    start_json = runner.invoke(cli.app, ["start", "--language", "zh", "--workdir", str(tmp_path), "--task", task, "--json"])

    _assert_chinese_default_fit_output(plain, plain_json)
    _assert_chinese_partial_fit_review(partial, partial_json, start_json)


def test_cli_fit_task_review_keeps_human_judgment_boundary() -> None:
    runner = CliRunner()
    task = "Migrate billing callbacks without losing idempotency or rollback evidence"
    fit_reason = "Multi-round idempotency and rollback evidence is needed"
    fake_done = "Happy-path callback works but retry and duplicate delivery are unproven"
    evidence = "Idempotency tests, replay proof, rollback dry-run, and reviewer-readable summary"
    tradeoffs = "Keep scope narrow and fail closed on unproven rollback behavior"
    review = {
        "task": task,
        "fit_reason": fit_reason,
        "fake_done": fake_done,
        "evidence": evidence,
        "tradeoffs": tradeoffs,
    }

    partial = runner.invoke(cli.app, ["fit", "--task", task, "--details"])
    partial_json = runner.invoke(cli.app, ["fit", "--task", task, "--json"])
    plain = runner.invoke(
        cli.app,
        [
            "fit",
            "--task",
            task,
            "--fit-reason",
            fit_reason,
            "--fake-done",
            fake_done,
            "--evidence",
            evidence,
            "--tradeoffs",
            tradeoffs,
            "--details",
        ],
    )
    json_result = runner.invoke(
        cli.app,
        [
            "fit",
            "--task",
            task,
            "--fit-reason",
            fit_reason,
            "--fake-done",
            fake_done,
            "--evidence",
            evidence,
            "--tradeoffs",
            tradeoffs,
            "--json",
        ],
    )
    _assert_partial_fit_review_result(partial, partial_json)
    _assert_complete_fit_review_plain(plain, review)
    _assert_complete_fit_review_json(json_result, review)
