from __future__ import annotations

import errno
import json
import re
import shlex
import socket
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli, web_bind_preflight
from loopora.fit_guidance import fit_guidance_payload
from loopora.start_guidance import start_guidance_lines, start_guidance_payload

WEB_CREATION_CHOICE_TERMS = (
    "Fit Guide first, then creation choices: Web conversation outside an Agent session",
    "Plan File import",
    "manual expert paths",
    "review evidence, gaps, and verdicts",
)
DOCTOR_READY_WEB_TERMS = ("Open Fit Guide/Web choices in Web", *WEB_CREATION_CHOICE_TERMS)
COMPLETE_FIT_REVIEW = {
    "task": "Migrate billing callbacks",
    "fit_reason": "Multi-round replay evidence is required",
    "fake_done": "Happy path passes while retry behavior is unproven",
    "evidence": "Replay and rollback proof",
    "tradeoffs": "Fail closed on unproven rollback",
}


def complete_fit_review_cli_args() -> list[str]:
    return [part for key, value in COMPLETE_FIT_REVIEW.items() for part in (f"--{key.replace('_', '-')}", value)]


def complete_fit_guidance_payload(**kwargs) -> dict[str, object]:
    return fit_guidance_payload(
        COMPLETE_FIT_REVIEW["task"],
        loopora_fit_reason=COMPLETE_FIT_REVIEW["fit_reason"],
        fake_done_risks=COMPLETE_FIT_REVIEW["fake_done"],
        required_evidence=COMPLETE_FIT_REVIEW["evidence"],
        judgment_tradeoffs=COMPLETE_FIT_REVIEW["tradeoffs"],
        **kwargs,
    )


def result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def assert_ordered_fragments(output: str, fragments: tuple[str, ...]) -> None:
    previous = -1
    for fragment in fragments:
        assert fragment in output
        current = output.index(fragment)
        assert previous < current
        previous = current


def assert_root_help_scannable_first_use_path(output: str) -> None:
    assert len(output.splitlines()) <= 50
    assert_ordered_fragments(
        re.sub(r"\s+", " ", output),
        (
            "Start here:",
            "loopora demo --open",
            "isolated completed Run",
            'loopora start --workdir "$PWD"',
            "read-only next step",
            "If fit is uncertain",
            'loopora fit --workdir "$PWD"',
            "Outside an Agent session",
            "continue in Web",
            "inside Codex, Claude Code, or OpenCode",
            'loopora init current --workdir "$PWD"',
            "Run only after READY review",
            "--details",
            "Existing work:",
            'loopora status --workdir "$PWD"',
            "Readiness:",
            'loopora doctor --workdir "$PWD"',
            "Support:",
            'loopora support --workdir "$PWD"',
            "Chinese output:",
            "--language zh",
            "Contributor checks:",
            "loopora dev check",
        ),
    )
    normalized = re.sub(r"\s+", " ", output)
    for detail in (
        "<project-dir>",
        "preview shape `loopora serve",
        "Plan-file/expert path",
        "Other advanced commands are still available",
        "loopora orchestrations",
    ):
        assert detail not in normalized


def assert_init_help_scannable_first_use_path(output: str) -> None:
    assert_ordered_fragments(
        re.sub(r"\s+", " ", output),
        (
            "First-use path:",
            "If you are not sure this task needs a Loop",
            "When fit is strong:",
            "Targetless setup commands below are preview-only",
            'loopora init --workdir "$PWD"',
            "Same-Agent setup:",
            "loopora init current --workdir '<project-dir>'",
            "if detection is unavailable or ambiguous",
            "loopora init <agent> --workdir '<project-dir>'",
            "Explicit-adapter readiness",
            "loopora doctor --workdir '<project-dir>'",
            "3. After readiness passes",
            "choose one path:",
            "Same-Agent path:",
            "Fit Guide/Web choices: use `loopora serve",
            "Fit Guide first, then creation choices",
            "Web conversation outside an Agent session",
            "Plan File import",
            "Plan-file/expert path:",
            "Existing work path:",
            "Usage/setup help:",
            "loopora support --workdir '<project-dir>'",
            "4. After the READY preview",
            "Fit Guide/Web choices: create or run from Web",
            "Same-Agent path: return to the same Agent session",
        ),
    )


def assert_fit_unreviewed_plain_hides_routes(output: str) -> None:
    assert all(
        fragment in output
        for fragment in (
            "Next before setup:",
            "Complete review inputs:",
            "--fit-reason '<which strong-fit signal applies and why Loopora is needed>'",
            "Route choices stay hidden until the fit review is complete.",
        )
    )
    assert all(fragment not in output for fragment in ("Choose the route that matches", "Fit Guide/Web choices", "loopora init", "<project-dir>"))


def assert_before_install_doctor_plain_output(plain) -> None:
    assert plain.exit_code == 1, plain.stdout
    assert "Loopora doctor: not_ready" in plain.stdout
    assert all(term in plain.stdout for term in ("same-Agent project entry ready: no", "package: loopora", "source "))
    assert "readiness summary: blocked until same-Agent project entry is ready." in plain.stdout
    assert "primary next action: If you are not sure this task needs a Loop" in plain.stdout
    assert all(term in plain.stdout for term in ("same-Agent project entries:", "setup options: Codex, Claude Code, OpenCode"))
    assert "recommended install:" not in plain.stdout
    assert "loopora init codex" in plain.stdout
    assert "loopora init claude" in plain.stdout
    assert "loopora init opencode" in plain.stdout
    assert "If you are not sure this task needs a Loop, run this before installing same-Agent project entries:" in plain.stdout
    assert "Choose the same-Agent project entry that matches your current host." in plain.stdout
    assert plain.stdout.index("primary next action:") < plain.stdout.index("next:")
    assert plain.stdout.index("loopora fit") < plain.stdout.index("Choose the same-Agent project entry that matches your current host")
    handoff_terms = (
        "/loopora-plan handoff is not ready yet",
        "After installing the matching same-Agent project entry, confirm readiness before returning to Agent:",
        "After same-Agent project entry is ready, run /loopora-plan to prepare the Loop preview.",
    )
    assert all(fragment in plain.stdout for fragment in handoff_terms)
    assert "After installing the matching same-Agent project entry, return to that Agent" not in plain.stdout
    assert "refresh or restart that Agent" not in plain.stdout
    assert "loopora doctor --workdir" in plain.stdout
    assert "After same-Agent project entry is ready, run /loopora-plan to prepare the Loop preview." in plain.stdout
    assert "first task message handoff:" in plain.stdout
    assert "completed fit review:" in plain.stdout
    assert "generic orientation example (not a completed review):" in plain.stdout
    assert "/loopora-plan\n\nLoopora fit:" in plain.stdout


def assert_start_and_fit_app_state_reset_recovery(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        web_bind_preflight,
        "probe_web_bind",
        lambda *_args: (_ for _ in ()).throw(OSError(errno.EADDRINUSE, "busy")),
    )
    monkeypatch.setattr(web_bind_preflight, "next_available_web_port", lambda **_kwargs: None)
    monkeypatch.setattr(
        "loopora.first_use_route_readiness.app_state_report",
        lambda *_args, **_kwargs: {
            "web_ready": False,
            "status": "development_reset_required",
            "next_action": "preview_dev_reset_before_web",
        },
    )
    start_payload = start_guidance_payload(COMPLETE_FIT_REVIEW, workdir=tmp_path, preflight_web_route=True)
    fit_payload = complete_fit_guidance_payload(workdir=tmp_path, preflight_web_route=True)
    for payload in (start_payload, fit_payload):
        web_action = _web_route_action(payload)
        archive_action, recovery_action = web_action["recovery_actions"]
        assert [action["kind"] for action in web_action["recovery_actions"]] == ["create_recovery_archive", "preview_app_database_reset"]
        assert (web_action["command_ready"], web_action["command_blockers"]) == (
            False,
            ["web_port_unavailable", "app_state_not_ready"],
        )
        assert (recovery_action["kind"], recovery_action["command_ready"], recovery_action["scope"]) == (
            "preview_app_database_reset",
            True,
            "app",
        )
        assert "dev reset --scope app" in recovery_action["command"]
        assert "recovery create --workdir" in archive_action["command"]
    fit_plain = CliRunner().invoke(cli.app, ["fit", "--workdir", str(tmp_path), *complete_fit_review_cli_args(), "--details"])
    fit_json = CliRunner().invoke(cli.app, ["fit", "--workdir", str(tmp_path), *complete_fit_review_cli_args(), "--json"])
    start_text = "\n".join(start_guidance_lines(start_payload))
    assert "Recovery: Create private recovery archive" in start_text
    assert "Recovery: Preview App database reset" in start_text
    assert "- Ready now: same-Agent setup choice; support route." in start_text
    assert "Fit Guide/Web choices (usable local Web port, App/Web readiness)" in start_text
    fit_stdout = fit_plain.stdout
    assert all(
        fragment in fit_stdout
        for fragment in (
            "Create private recovery archive",
            "Preview App database reset",
            "Requested Web command, currently unavailable:",
            "- Ready now: same-Agent setup choice; support route.",
            "Fit Guide/Web choices (usable local Web port, App/Web readiness)",
            "/loopora-plan",
            "/loopora-run",
            "READY preview review",
        )
    )
    assert _web_route_action(json.loads(fit_json.stdout))["recovery_actions"][1]["local_only"] is True
    monkeypatch.setattr(web_bind_preflight, "probe_web_bind", lambda *_args: None)
    start_payload = start_guidance_payload(COMPLETE_FIT_REVIEW, workdir=tmp_path, preflight_web_route=True)
    fit_payload = complete_fit_guidance_payload(workdir=tmp_path, preflight_web_route=True)
    for payload in (start_payload, fit_payload):
        recovery_actions = _web_route_action(payload)["recovery_actions"]
        archive_action, reset_action, temporary_action = recovery_actions
        assert [action["kind"] for action in recovery_actions] == ["create_recovery_archive", "preview_app_database_reset", "use_temporary_app_home"]
        assert archive_action["command"].endswith(f"recovery create --workdir {tmp_path}")
        assert reset_action["command"].endswith(f"dev reset --scope app --workdir {tmp_path}")
        assert temporary_action["command"].startswith('LOOPORA_HOME="$(mktemp -d)" loopora serve --open --workdir')
        assert "does not delete, migrate, or repair" in temporary_action["note"]
    fit_plain = CliRunner().invoke(cli.app, ["fit", "--workdir", str(tmp_path), *complete_fit_review_cli_args(), "--details"])
    assert "temporary-home recovery" not in "\n".join(start_guidance_lines(start_payload))
    assert "Recovery: Temporary Web preview" in "\n".join(start_guidance_lines(start_payload))
    assert "Temporary Web preview" in fit_plain.stdout
    assert "Fit Guide/Web choices: blocked until App/Web readiness is resolved." in fit_plain.stdout


def _web_route_action(payload: dict[str, object]) -> dict[str, object]:
    return next(
        action for action in payload["route_actions_after_strong_fit"] if isinstance(action, dict) and action.get("kind") == "open_web_creation_choices"
    )


def assert_readme_entry_points(readmes: list[str], documented_adapters: list[set[str]]) -> None:
    assert documented_adapters == [{"codex", "claude", "opencode"}, {"codex", "claude", "opencode"}]
    assert all("loopora serve " in readme for readme in readmes)
    assert all('loopora init current --workdir "$PWD"' in readme for readme in readmes)
    assert all("loopora support" in readme for readme in readmes)
    assert all('loopora init codex --workdir "$PWD"' in readme for readme in readmes)
    assert all('loopora init claude --workdir "$PWD"' in readme for readme in readmes)
    assert all('loopora init opencode --workdir "$PWD"' in readme for readme in readmes)
    assert all('loopora init <agent> --workdir "$PWD" --check' in readme for readme in readmes)
    assert all('loopora agent <agent> check --workdir "$PWD"' in readme for readme in readmes)
    assert all('loopora uninstall <agent> --workdir "$PWD" --dry-run' in readme for readme in readmes)
    assert all('loopora doctor --workdir "$PWD"' in readme for readme in readmes)
    assert all("uv run python -m loopora --help" in readme for readme in readmes)
    assert all("--public-json" in readme for readme in readmes)
    assert all("--strict" in readme for readme in readmes)
    assert all("apply_command" in readme for readme in readmes)
    assert all("--yes" in readme for readme in readmes)
    assert all("loopora diagnose doctor" in readme for readme in readmes)
    assert "After the preview looks right, run `/loopora-run`" in readmes[0]
    assert "预览看起来正确后，运行 `/loopora-run`" in readmes[1]
    assert all("loopora init codex\n" not in readme for readme in readmes)
    assert all("loopora init claude\n" not in readme for readme in readmes)
    assert all("loopora init opencode\n" not in readme for readme in readmes)
    assert all("loopora init codex --check" not in readme for readme in readmes)
    assert all('loopora init codex --workdir "$PWD" --check' not in readme for readme in readmes)
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
    assert "Web composer and Agent Native are peer entry surfaces" in contracts
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
        assert "Fit Guide/Web choices create or run from Web" in re.sub(r"\s+", " ", result.stdout)
        assert "After the READY Loop preview matches the task judgment, run /loopora-run in the same Agent session" not in re.sub(r"\s+", " ", result.stdout)
        assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in re.sub(r"\s+", " ", result.stdout)
        assert "After readiness passes" in result.stdout
        assert "choose one path" in re.sub(r"\s+", " ", result.stdout)
        normalized = re.sub(r"\s+", " ", result.stdout)
        assert all(term in normalized for term in WEB_CREATION_CHOICE_TERMS)

    serve_result = runner.invoke(cli.app, ["serve", "--help"])
    assert serve_result.exit_code == 0, result_error_text(serve_result)

    root_no_args = runner.invoke(cli.app, [])
    assert root_no_args.exit_code == 0, result_error_text(root_no_args)
    assert "Start here:" in root_no_args.stdout
    assert "Missing command" not in result_error_text(root_no_args)

    help_result = runner.invoke(cli.app, ["--help"])
    assert help_result.exit_code == 0, result_error_text(help_result)
    assert root_no_args.stdout == help_result.stdout
    normalized_help = re.sub(r"\s+", " ", help_result.stdout)
    _assert_root_help_public_entry_points(help_result, normalized_help=normalized_help)
    for args, expected in (
        (["run", "--help"], "Expert direct-run path"),
        (["dev"], "Contributor flow"),
        (["agent"], "Internal runtime used by /loopora-plan and /loopora-run project entries"),
    ):
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 0, result_error_text(result)
        assert expected in result.stdout


def _assert_root_help_public_entry_points(help_result, *, normalized_help: str) -> None:
    assert_root_help_scannable_first_use_path(help_result.stdout)
    assert 'loopora start --workdir "$PWD"' in normalized_help
    assert 'loopora fit --workdir "$PWD"' in normalized_help
    assert "loopora demo --open" in normalized_help
    assert "Set up same-Agent project entries" in normalized_help
    assert 'loopora doctor --workdir "$PWD"' in normalized_help
    assert 'loopora support --workdir "$PWD"' in normalized_help
    assert "Outside an Agent session continue in Web" in normalized_help
    assert 'loopora init current --workdir "$PWD"' in normalized_help
    assert "Run only after READY review" in normalized_help
    assert "Add `--details` to start or fit" in normalized_help
    assert "Existing work" in normalized_help
    assert "Contributor checks: run local checks with `loopora dev check`" in normalized_help
    assert "Expert: create and run a Loop from an existing spec file." not in help_result.stdout
    assert "Expert: create and inspect reusable run flows" not in help_result.stdout
    assert "Developer: run local checks and reset incompatible development state" not in help_result.stdout
    assert "Internal runtime used by /loopora-plan and /loopora-run project entries" not in help_result.stdout
    assert help_result.stdout.index("│ demo") < help_result.stdout.index("│ serve") < help_result.stdout.index("│ init") < help_result.stdout.index("│ doctor")
    assert help_result.stdout.index("│ doctor") < help_result.stdout.index("│ support")
    assert help_result.stdout.index("│ support") < help_result.stdout.index("│ uninstall")
    assert help_result.stdout.index("│ uninstall") < help_result.stdout.index("│ loops") < help_result.stdout.index("│ bundles")
    assert help_result.stdout.index("│ bundles") < help_result.stdout.index("│ diagnose")


def assert_ready_doctor_plain_output(plain, *, web_port: int = 8742) -> None:
    assert plain.exit_code == 0, plain.stdout
    for fragment in (
        "Loopora doctor: ready",
        "same-Agent project entry ready: yes",
        "readiness summary: same-Agent project entry, App state, and Web start are ready.",
        "primary next action: Return to Codex",
        "App state: not_initialized (Web ready: yes)",
        "ready: Codex (codex); adapter check passes; next: return to Agent",
        "setup options: Claude Code, OpenCode",
        "Return to Codex with the Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context.",
        "If /loopora-plan or /loopora-run is not visible in Codex, refresh or restart Codex.",
        "/loopora-plan",
        "Review whether the READY Loop preview matches the task judgment.",
        "After the READY preview matches the task judgment, run /loopora-run in the same Agent session.",
        f"loopora serve --open --host 127.0.0.1 --port {web_port}",
        "first task message handoff:",
        "completed fit review:",
        "generic orientation example (not a completed review):",
        "/loopora-plan\n\nLoopora fit:",
    ):
        assert fragment in plain.stdout
    for fragment in DOCTOR_READY_WEB_TERMS:
        assert fragment in plain.stdout
    assert "loopora init claude" not in plain.stdout
    assert "loopora init opencode" not in plain.stdout


def _assert_init_group_help(init_group_help) -> None:
    normalized_init_group_help = re.sub(r"\s+", " ", init_group_help.stdout)
    assert init_group_help.exit_code == 0, result_error_text(init_group_help)
    assert (
        "Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context" in normalized_init_group_help
    )
    assert "Targetless setup commands below are preview-only" in normalized_init_group_help
    assert 'loopora init --workdir "$PWD"' in normalized_init_group_help
    assert "loopora init <agent> --workdir '<project-dir>'" in normalized_init_group_help
    assert "loopora doctor --workdir '<project-dir>'" in normalized_init_group_help
    assert "If you are not sure this task needs a Loop" in normalized_init_group_help
    assert "When fit is strong" in normalized_init_group_help
    assert "/loopora-plan" in normalized_init_group_help
    assert "/loopora-run" in normalized_init_group_help
    assert "loopora serve --open --workdir '<project-dir>' --host 127.0.0.1 --port 8742" in normalized_init_group_help
    assert "After readiness passes" in normalized_init_group_help
    assert "Plan-file/expert path" in normalized_init_group_help
    assert "Existing work path" in normalized_init_group_help
    assert "Fit Guide/Web choices" in normalized_init_group_help
    assert "create or run from Web" in normalized_init_group_help
    assert "After the READY preview matches the task judgment, run `/loopora-run` in the same Agent session" not in normalized_init_group_help
    assert all(term in normalized_init_group_help for term in WEB_CREATION_CHOICE_TERMS)


def _assert_codex_init_help(init_help) -> None:
    normalized_init_help = re.sub(r"\s+", " ", init_help.stdout)
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
    assert "First-use path:" in init_help.stdout
    assert "If you are not sure this task needs a Loop" in normalized_init_help
    assert "loopora fit" in normalized_init_help
    assert 'loopora init codex --workdir "$PWD"' in normalized_init_help
    assert 'loopora doctor --workdir "$PWD"' in normalized_init_help
    assert "Fit Guide/Web choices create or run from Web" in normalized_init_help
    assert "After the READY Loop preview matches the task judgment, run /loopora-run in the same Agent session" not in normalized_init_help
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in normalized_init_help
    assert normalized_init_help.index("loopora fit") < normalized_init_help.index('loopora init codex --workdir "$PWD"')
    assert normalized_init_help.index('loopora init codex --workdir "$PWD"') < normalized_init_help.index('loopora doctor --workdir "$PWD"')
    assert normalized_init_help.index('loopora doctor --workdir "$PWD"') < normalized_init_help.index("After readiness passes")
    assert "After readiness passes" in normalized_init_help
    assert "choose one path" in normalized_init_help
    assert "Plan-file/expert path" in normalized_init_help
    assert "Existing work path" in normalized_init_help
    assert all(term in normalized_init_help for term in WEB_CREATION_CHOICE_TERMS)
    assert "Project directory where the Coding Agent will" in init_help.stdout
    assert "work." in init_help.stdout
    assert "adapter" not in init_help.stdout.lower()


def assert_cli_agent_entry_help(runner: CliRunner) -> None:
    _assert_init_group_help(runner.invoke(cli.app, ["init", "--help"]))
    _assert_codex_init_help(runner.invoke(cli.app, ["init", "codex", "--help"]))

    uninstall_help = runner.invoke(cli.app, ["uninstall", "codex", "--help"])
    normalized_uninstall_help = re.sub(r"\s+", " ", uninstall_help.stdout)
    assert uninstall_help.exit_code == 0, result_error_text(uninstall_help)
    assert "Remove the Loopora-managed Codex project entry." in uninstall_help.stdout
    assert "Project directory where the Coding Agent" in normalized_uninstall_help
    assert "will work." in normalized_uninstall_help
    for term in (
        "only files proven Loopora-managed",
        "User-owned host configuration",
        "kept files",
        "--dry-run",
        "loopora init codex",
    ):
        assert term in normalized_uninstall_help
    assert "adapter" not in uninstall_help.stdout.lower()

    agent_check_help = runner.invoke(cli.app, ["agent", "codex", "check", "--help"])
    normalized_agent_check_help = re.sub(r"\s+", " ", agent_check_help.stdout)
    assert agent_check_help.exit_code == 0, result_error_text(agent_check_help)
    for term in (
        "Check is read-only",
        "does not install, repair, overwrite",
        'loopora doctor --workdir "$PWD"',
        "loopora init codex",
    ):
        assert term in normalized_agent_check_help

    agent_help = runner.invoke(cli.app, ["agent", "codex", "plan", "--help"])
    normalized_agent_help = re.sub(r"\s+", " ", agent_help.stdout)
    assert agent_help.exit_code == 0, result_error_text(agent_help)
    assert "Validate a confirmed candidate plan or open non-interactive Web alignment." in agent_help.stdout
    assert "Candidate Loop plan file" in agent_help.stdout
    assert "produced by" in normalized_agent_help
    assert "the Coding Agent." in normalized_agent_help
    assert "--plan-file" in agent_help.stdout
    assert "Candidate Loopora bundle YAML" not in agent_help.stdout
    for term in ("runtime command behind `/loopora-plan`", "--message", "READY preview"):
        assert term in normalized_agent_help

    runtime_help_terms = {
        ("run",): ("runtime command behind `/loopora-run`", "READY preview", "skipping review"),
        ("next",): ("current step contract", "native execution", "result template"),
        ("submit",): ("claimed step", "result template", "do not submit ad hoc observations"),
    }
    for args, expected_terms in runtime_help_terms.items():
        runtime_help = runner.invoke(cli.app, ["agent", "codex", *args, "--help"])
        normalized_runtime_help = re.sub(r"\s+", " ", runtime_help.stdout)
        assert runtime_help.exit_code == 0, result_error_text(runtime_help)
        for term in expected_terms:
            assert term in normalized_runtime_help

    _assert_agent_runtime_group_help(runner.invoke(cli.app, ["agent", "codex", "--help"]))
    _assert_top_level_agent_runtime_help(runner.invoke(cli.app, ["agent", "--help"]))


def _assert_agent_runtime_group_help(agent_group_help) -> None:
    normalized = re.sub(r"\s+", " ", agent_group_help.stdout)
    assert agent_group_help.exit_code == 0, result_error_text(agent_group_help)
    assert "Internal Codex runtime used by Loopora project entries" in agent_group_help.stdout
    assert " plan" in agent_group_help.stdout
    assert " run" in agent_group_help.stdout
    assert "adapter runtime" in normalized.lower()
    for term in (
        "not by first-use shell workflows",
        "loopora fit",
        'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742',
        "loopora init codex",
        'loopora doctor --workdir "$PWD"',
        "loopora agent codex check",
    ):
        assert term in normalized
    assert normalized.index("loopora fit") < normalized.index("loopora init codex")


def _assert_top_level_agent_runtime_help(top_level_agent_help) -> None:
    normalized = re.sub(r"\s+", " ", top_level_agent_help.stdout)
    assert top_level_agent_help.exit_code == 0, result_error_text(top_level_agent_help)
    for term in (
        "Internal runtime used by /loopora-plan and /loopora-run",
        "not by first-use shell workflows",
        "loopora start",
        'loopora start --workdir "$PWD"',
        "target project before copying Web/init/doctor route commands",
        "loopora fit",
        "Fit Guide/Web choices printed by the target-project start guide",
        'loopora init --workdir "$PWD"',
        'loopora doctor --workdir "$PWD"',
        "loopora agent <agent> check",
    ):
        assert term in normalized
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' not in normalized
    assert normalized.index("loopora start") < normalized.index("loopora fit") < normalized.index("loopora init --workdir")


def assert_cli_bundle_import_help(runner: CliRunner) -> None:
    import_help = runner.invoke(cli.app, ["bundles", "import", "--help"])
    normalized = re.sub(r"\s+", " ", import_help.stdout)
    assert import_help.exit_code == 0, result_error_text(import_help)
    assert "Import one Loop plan file and materialize its run-ready assets." in import_help.stdout
    assert "Path to a Loop plan file" in import_help.stdout
    assert "For first use, leave this import command" in normalized
    assert "loopora start" in normalized
    assert "loopora fit" in normalized
    assert "Fit Guide/Web choices path" in normalized
    assert 'loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742' in normalized
    assert "same-Agent path" in normalized
    assert 'loopora init <agent> --workdir "$PWD"' in normalized
    assert 'loopora doctor --workdir "$PWD"' in normalized
    assert normalized.index("Fit Guide/Web choices path") < normalized.index("same-Agent path")
    assert normalized.index("same-Agent path") < normalized.index("/loopora-plan") < normalized.index("/loopora-run")
    assert "YAML bundle" not in import_help.stdout


def _entry(payload: dict, adapter: str) -> dict:
    for item in payload["agent_entries"]:
        if item["adapter"] == adapter:
            return item
    raise AssertionError(f"missing adapter entry: {adapter}")


def free_local_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def assert_before_install_doctor_payload(payload: dict, *, workdir: Path, web_port: int) -> None:
    assert next(iter(payload)) == "diagnose_doctor_summary"
    assert payload["schema_version"] == 2
    assert payload["status"] == "not_ready"
    assert payload["ready"] is False
    assert payload["agent_entry_ready"] is False
    assert payload["strict_ready"] is False
    assert payload["diagnose_doctor_summary"]["agent_entry_ready"] is False
    assert payload["diagnose_doctor_summary"]["strict_ready"] is False
    assert payload["workdir"] == str(workdir.resolve())
    assert payload["diagnose_doctor_summary"]["app_state_status"] == "not_initialized"
    assert payload["diagnose_doctor_summary"]["app_state_web_ready"] is True
    assert payload["app_state"]["status"] == "not_initialized"
    assert payload["app_state"]["web_ready"] is True
    assert payload["app_state"]["needs_attention"] is False
    assert payload["web"]["origin"] == f"http://127.0.0.1:{web_port}"
    assert payload["web"]["requested_port"] == web_port
    assert payload["web"]["start_available"] is True
    assert payload["web"]["loopback"] is True
    assert payload["web"]["requires_token_when_non_loopback"] is True
    assert payload["diagnose_doctor_summary"]["first_task_guidance_available"] is True
    assert payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert payload["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert (
        payload["diagnose_doctor_summary"]["first_task_handoff_policy"],
        payload["first_task_handoff_executable"],
        payload["diagnose_doctor_summary"]["first_task_handoff_executable"],
        payload["first_task_handoff_blockers"],
    ) == (payload["first_task_handoff_policy"], False, False, ["same_agent_entry_required"])
    _assert_before_install_doctor_entries(payload)
    _assert_before_install_doctor_actions(payload, web_port=web_port)


def _assert_before_install_doctor_entries(payload: dict) -> None:
    codex = _entry(payload, "codex")
    assert codex["ready"] is False
    assert codex["install_state"] == "not_installed"
    assert codex["details_are_expected"] is True
    assert codex["next_action"] == "install_agent_entry"
    assert "loopora init codex" in codex["commands"]["install"]
    assert "failed_checks" not in codex
    claude = _entry(payload, "claude")
    opencode = _entry(payload, "opencode")
    assert "loopora init claude" in claude["commands"]["install"]
    assert "loopora init opencode" in opencode["commands"]["install"]
    assert payload["recommended_adapter"] == ""


def _assert_before_install_doctor_actions(payload: dict, *, web_port: int) -> None:
    assert any("Choose the same-Agent project entry that matches your current host" in step for step in payload["next_steps"])
    assert payload["next_actions"] == payload["next_action_items"]
    action_kinds = [item["kind"] for item in payload["next_action_items"]]
    assert action_kinds == [
        "check_fit_first",
        "install_agent_entry",
        "confirm_readiness",
        "run_loopora_plan",
        "support",
    ]
    assert payload["primary_next_action_kind"] == payload["diagnose_doctor_summary"]["primary_next_action_kind"] == "check_fit_first"
    assert (
        payload["next_action_kinds"],
        payload["diagnose_doctor_summary"]["next_action_kinds"],
        payload["next_action_ready_now_kinds"],
        payload["diagnose_doctor_summary"]["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["diagnose_doctor_summary"]["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["diagnose_doctor_summary"]["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
        payload["diagnose_doctor_summary"]["next_action_command_blockers"],
    ) == (
        action_kinds,
        action_kinds,
        ["check_fit_first", "install_agent_entry", "support"],
        ["check_fit_first", "install_agent_entry", "support"],
        {"confirm_readiness": "install_agent_entry"},
        {"confirm_readiness": "install_agent_entry"},
        ["run_loopora_plan"],
        ["run_loopora_plan"],
        {"run_loopora_plan": ["same_agent_entry_required"]},
        {"run_loopora_plan": ["same_agent_entry_required"]},
    )
    assert [(item["kind"], item.get("command_ready"), item.get("command_blockers")) for item in payload["next_action_items"] if item.get("command")] == [
        ("check_fit_first", True, []),
        ("confirm_readiness", True, []),
        ("run_loopora_plan", False, ["same_agent_entry_required"]),
        ("support", True, []),
    ]
    assert command_tokens(payload["next_action_items"][0]["command"])[-4:] == [
        "loopora",
        "fit",
        "--workdir",
        payload["workdir"],
    ]
    assert (payload["next_action_items"][1]["selection_required"], payload["next_action_items"][2]["after_action"]) == (
        True,
        "install_agent_entry",
    )
    assert [choice["adapter"] for choice in payload["next_action_items"][1]["adapter_choices"]] == [
        "codex",
        "claude",
        "opencode",
    ]
    assert all(choice["command_ready"] is True and choice["command_blockers"] == [] for choice in payload["next_action_items"][1]["adapter_choices"])
    assert all(key not in payload["next_action_items"][1] for key in ("adapter", "command"))
    assert (
        "loopora doctor --workdir" in payload["next_action_items"][2]["command"],
        f"--web-port {web_port}" in payload["next_action_items"][2]["command"],
        "loopora support --workdir" in payload["next_action_items"][-1]["command"],
        f"--web-port {web_port}" in payload["next_action_items"][-1]["command"],
    ) == (True, True, True, True)
    assert payload["next_steps"][0].startswith("If you are not sure this task needs a Loop")
    assert any(f"--web-port {web_port}" in step for step in payload["next_steps"])


def assert_public_action_summaries(payload: dict, *, expected_terms: tuple[str, ...] = ()) -> None:
    assert [item["kind"] for item in payload["next_action_summaries"]] == payload["next_actions"]
    assert (
        payload["diagnose_doctor_public_summary"]["next_action_summaries"],
        payload["diagnose_doctor_public_summary"]["next_action_ready_now_kinds"],
        payload["diagnose_doctor_public_summary"]["next_action_ready_after_actions"],
        payload["diagnose_doctor_public_summary"]["next_action_blocked_kinds"],
        payload["diagnose_doctor_public_summary"]["next_action_command_blockers"],
    ) == (
        payload["next_action_summaries"],
        payload["next_action_ready_now_kinds"],
        payload["next_action_ready_after_actions"],
        payload["next_action_blocked_kinds"],
        payload["next_action_command_blockers"],
    )
    encoded = json.dumps(payload["next_action_summaries"], ensure_ascii=False)
    assert all(term in encoded for term in expected_terms)


def command_tokens(command: str) -> list[str]:
    return shlex.split(command)


def assert_command_uses_home_and_workdir(command: str, *, loopora_home: Path | str, workdir: Path) -> None:
    tokens = command_tokens(command)
    assert tokens[0] == f"LOOPORA_HOME={loopora_home!s}"
    assert "--workdir" in tokens
    assert tokens[tokens.index("--workdir") + 1] == str(workdir)


def assert_init_next_order(normalized_output: str) -> None:
    next_section = normalized_output.split("If you are not sure this task needs a Loop", 1)[1]
    assert "When fit is strong" in next_section
    assert all(
        term in next_section
        for term in (
            "Fit Guide/Web choices",
            "Fit Guide first, then creation choices",
            "Web conversation outside an Agent session",
            "Plan File import",
            "manual expert paths",
            "Plan-file/expert path",
            "Existing work path",
            "loopora init current",
            "Fit Guide/Web choices",
            "create or run from Web",
            "Same-Agent path: return to the same Agent session",
        )
    )
    web_command_index = next_section.index("loopora serve --open --workdir '<project-dir>' --host 127.0.0.1 --port 8742")
    assert next_section.index("loopora fit") < next_section.index("loopora init <agent> --workdir '<project-dir>'")
    assert next_section.index("loopora doctor --workdir '<project-dir>'") < next_section.index("choose one path")
    assert next_section.index("choose one path") < next_section.index("/loopora-plan")
    assert next_section.index("choose one path") < web_command_index
    ready_preview_index = next_section.index("READY preview")
    web_continue_index = next_section.index("Fit Guide/Web choices", ready_preview_index)
    assert next_section.index("/loopora-plan") < ready_preview_index
    assert ready_preview_index < web_continue_index < next_section.index("/loopora-run", ready_preview_index)
