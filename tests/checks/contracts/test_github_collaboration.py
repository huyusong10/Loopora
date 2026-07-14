from __future__ import annotations

import json
import shlex
import tomllib
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient
import yaml
from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix
from loopora import cli
from loopora.support_guidance import SUPPORT_HELP_EPILOG
from loopora.web import build_app

REPO_ROOT = Path(__file__).resolve().parents[3]
GITHUB_ROOT = REPO_ROOT / ".github"
CI_WORKFLOW = GITHUB_ROOT / "workflows" / "ci.yml"
CODEQL_WORKFLOW = GITHUB_ROOT / "workflows" / "codeql.yml"
DEPENDABOT_CONFIG = GITHUB_ROOT / "dependabot.yml"
UV_LOCK = REPO_ROOT / "uv.lock"
QUALITY_GATE_COMMAND = "uv run loopora dev check"
CODEQL_TIMEOUT_MINUTES = 20
DEPENDABOT_OPEN_PULL_REQUEST_LIMIT = 5
DEPENDABOT_SCHEMA_VERSION = 2
EXPECTED_UV_SYNC_STEP_COUNT = 2


def _assert_source_checkout_support_help_preserves_entry(monkeypatch) -> None:
    command_registration = (REPO_ROOT / "src" / "loopora" / "cli_root_commands.py").read_text(encoding="utf-8")
    assert "@app.command(epilog=rewrite_loopora_help_commands(SUPPORT_HELP_EPILOG))" in command_registration
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix.sys, "argv", ["/repo/src/loopora/__main__.py"])
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
    source_support_help = agent_adapter_command_prefix.rewrite_loopora_help_commands(SUPPORT_HELP_EPILOG)
    assert f"{source_entry} support" in source_support_help
    assert f'{source_entry} support --workdir "$PWD" --public-issue-bundle' in source_support_help
    assert f"{source_entry} doctor --public-json --workdir" in source_support_help
    assert f"{source_entry} --version" in source_support_help
    assert f"{source_entry} version --json" in source_support_help


def _github_workflow_triggers(config: dict[object, object]) -> object:
    return config.get("on", config.get(True))


def _locked_package_version(name: str) -> str:
    lock = tomllib.loads(UV_LOCK.read_text(encoding="utf-8"))
    versions = [package["version"] for package in lock["package"] if package["name"] == name]

    assert len(versions) == 1
    return versions[0]


def test_github_yaml_files_are_parseable() -> None:
    parsed = {
        path.relative_to(REPO_ROOT): yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(GITHUB_ROOT.rglob("*.yml"))
    }

    assert parsed
    assert all(document for document in parsed.values())


def test_dev_check_pr_evidence_block_maps_to_pr_template() -> None:
    result = CliRunner().invoke(
        cli.app,
        ["dev", "check", "--list", "--json", "--pr-evidence", "--changed-file", "README.md"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    block = payload["pr_evidence_summary"]["template_markdown"]
    for term in (
        "### Loopora PR Evidence",
        "- PR evidence stage: decision",
        "- Evidence command source: `loopora dev check`",
        "- Decision scope evidence: collected by this list-stage PR evidence command",
        "- Changed-file detection: provided/provided (1 file(s))",
        "- Recommended focused guide IDs: open_source_collaboration",
        "- Unmatched changed files: none",
        "- Ignored changed files: none",
        "- Final dev-check result: not run by this command",
        "- Package-build cleanup:",
        "- Public evidence reminder:",
        "<project-dir>",
        "<Loopora checkout>",
        "<redacted>",
    ):
        assert term in block


def test_dev_command_help_keeps_contributor_gate_and_reset_recovery_discoverable() -> None:
    runner = CliRunner()

    dev_help = runner.invoke(cli.app, ["dev", "--help"])
    check_help = runner.invoke(cli.app, ["dev", "check", "--help"])
    reset_help = runner.invoke(cli.app, ["dev", "reset", "--help"])

    assert dev_help.exit_code == 0, dev_help.stdout
    assert check_help.exit_code == 0, check_help.stdout
    assert reset_help.exit_code == 0, reset_help.stdout
    normalized_dev = " ".join(dev_help.stdout.split())
    normalized_check = " ".join(check_help.stdout.split())
    normalized_reset = " ".join(reset_help.stdout.split())
    for term in (
        "loopora dev check --list",
        "loopora dev check --focused recommended",
        "default-fast gate",
        "loopora dev reset",
    ):
        assert term in normalized_dev
    for term in ("focused guide IDs", "default-fast gate", "--changed-file", "--focused-ran", "--json", "--pr-evidence"):
        assert term in normalized_check
    for term in ("no-mutation preview", "--scope app", "--yes", "loopora doctor --workdir <project>"):
        assert term in normalized_reset


def test_cli_support_command_routes_public_reports_without_running_diagnostics(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()

    def fail_doctor(*_args, **_kwargs) -> None:
        raise AssertionError("support guidance must not run doctor diagnostics")

    monkeypatch.setattr("loopora.cli_root_commands.run_doctor_command", fail_doctor)
    private_home = tmp_path / "support-home"
    monkeypatch.setenv("LOOPORA_HOME", str(private_home))
    plain = runner.invoke(cli.app, ["support", "--workdir", str(tmp_path)])
    structured = runner.invoke(cli.app, ["support", "--workdir", str(tmp_path), "--json"])
    help_result = runner.invoke(cli.app, ["support", "--help"])

    assert plain.exit_code == 0, plain.stdout
    assert help_result.exit_code == 0, help_result.stdout
    normalized_plain = " ".join(plain.stdout.split())
    normalized_help = " ".join(help_result.stdout.split())
    for term in (
        "Loopora support",
        "best-effort",
        "fallback redacted readiness report command",
        "Run locally; paste generated outputs only",
        "preferred public issue support bundle command",
        "Run these commands locally",
        "support JSON is route metadata",
        "command fields are local-only",
        "paste the public issue support bundle first",
        "redacted report/version output only when requested",
        "not command lines that contain local paths",
        "Paste publicly only",
        "preferred first",
        "public issue support bundle output",
        "redacted doctor --public-json report output",
        "loopora --version output",
        "Keep local only",
        "printed command lines",
        "JSON command fields",
        "local Web Support URLs",
        "loopora doctor --public-json --workdir",
        "loopora --version",
        "GitHub Bug Report template",
        "https://github.com/huyusong10/Loopora/issues/new?template=bug_report.yml",
        "GitHub Feature Request template",
        "https://github.com/huyusong10/Loopora/issues/new?template=feature_request.yml",
        "SUPPORT.md",
        "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md",
        "SECURITY.md",
        "private reporting",
        "public issue may only ask for a private channel",
        "no details",
        "https://github.com/huyusong10/Loopora/security/advisories/new",
    ):
        assert term in normalized_plain
    for term in (
        "Paste publicly the public issue bundle first",
        "redacted doctor output",
        "only when requested",
        "loopora --version",
        "support JSON",
        "printed command lines",
        "JSON command fields",
        "local Web Support URLs",
        "local-only",
        "preview-only",
        "target project",
        "--web-host",
        "--web-port",
        "command execution blockers",
    ):
        assert term in normalized_help
    for term in ("credentials", "tokens", "private logs", "local paths", "local command lines", "sensitive workspace data"):
        assert term in plain.stdout
    assert str(private_home) not in plain.stdout
    _assert_source_checkout_support_help_preserves_entry(monkeypatch)
    _assert_cli_public_issue_bundle(runner, tmp_path, private_home)

    assert structured.exit_code == 0, structured.stdout
    payload = json.loads(structured.stdout)
    assert payload["schema_version"] == 1
    assert payload["language"] == "en"
    _assert_ready_support_summary(payload)
    _assert_support_command_state(payload, target_required=False, placeholders=False, executable=True, blockers=[])
    _assert_support_target_project_state(payload, status="ready", executable=True)
    _assert_support_next_actions(payload, target_required=False)
    assert payload["posting_guidance"] == {
        "run_commands_locally": True,
        "run_ready_commands_locally": True,
        "preview_command_fields_require_target_project": False,
        "paste_outputs_not_command_lines": True,
        "support_json_is_route_metadata": True,
        "command_fields_are_local_only": True,
        "preferred_public_output": "public_issue_bundle_output",
        "fallback_public_outputs": ["public_doctor_output"],
        "identity_public_outputs": ["version_output", "version_identity_json_output"],
        "pasteable_public_outputs": [
            "public_issue_bundle_output",
            "public_doctor_output",
            "version_output",
            "version_identity_json_output",
        ],
    }
    assert payload["public_issue_materials"] == {
        "preferred": ["public_issue_bundle_output"],
        "fallback": ["public_doctor_output"],
        "identity": ["version_output", "version_identity_json_output"],
        "pasteable": ["public_issue_bundle_output", "public_doctor_output", "version_output", "version_identity_json_output"],
        "local_only": ["support_json", "printed_command_lines", "command_fields", "local_web_support_urls"],
        "redact_or_remove": payload["redaction"],
    }
    _assert_support_public_doctor_command(payload, tmp_path, private_home)
    _assert_support_custom_web_target(runner, tmp_path)
    invalid = runner.invoke(cli.app, ["support", "--web-port", "bad", "--json"])
    assert invalid.exit_code == 1
    assert "invalid --web-port" in invalid.stdout
    assert "loopora --version" in payload["commands"]["version"]
    assert "loopora version --json" in payload["commands"]["version_json"]
    _assert_support_relative_workdir_resolves(monkeypatch, runner, tmp_path)
    bare_payload = json.loads(runner.invoke(cli.app, ["support", "--json"]).stdout)
    _assert_targetless_support_preview(runner.invoke(cli.app, ["support"]), bare_payload)
    assert bare_payload["commands"]["public_doctor"].endswith("--workdir '<project-dir>' || true")
    _assert_unusable_target_support_report_only(runner, tmp_path)
    _assert_support_issue_routes(payload)
    assert payload["docs"] == {
        "support": "SUPPORT.md",
        "security": "SECURITY.md",
        "contributing": "CONTRIBUTING.md",
    }
    assert payload["links"] == {
        "support": "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md",
        "security_policy": "https://github.com/huyusong10/Loopora/security/policy",
        "private_security_report": "https://github.com/huyusong10/Loopora/security/advisories/new",
    }
    assert payload["security_reporting"] == {
        "policy_url": "https://github.com/huyusong10/Loopora/security/policy",
        "private_report_url": "https://github.com/huyusong10/Loopora/security/advisories/new",
        "public_fallback": "private_channel_request_only",
        "public_fallback_no_sensitive_details": True,
    }
    _assert_zh_support_guidance(runner, payload)


def _assert_cli_public_issue_bundle(runner: CliRunner, workdir: Path, private_home: Path) -> None:
    bundle = runner.invoke(cli.app, ["support", "--workdir", str(workdir), "--public-issue-bundle"])
    assert bundle.exit_code == 0, bundle.stdout
    for term in (
        "Loopora public issue support bundle",
        "Paste publicly only; do not add local command lines, support JSON, or local Web URLs.",
        "Compact package/source identity:",
        "Public readiness summary:",
        "- Overall status:",
        "- Readiness axes:",
        "- Ready next action kinds:",
        "Redacted doctor --public-json report:",
        '"redacted": true',
        '"package":',
        '"project_directory_status": "ready"',
    ):
        assert term in bundle.stdout
    assert bundle.stdout.index("Compact package/source identity:") < bundle.stdout.index("Public readiness summary:")
    assert bundle.stdout.index("Public readiness summary:") < bundle.stdout.index("Redacted doctor --public-json report:")
    assert str(workdir) not in bundle.stdout
    assert str(private_home) not in bundle.stdout
    targetless_bundle = runner.invoke(cli.app, ["support", "--public-issue-bundle"])
    assert targetless_bundle.exit_code == 2
    assert "requires a target project" in targetless_bundle.output
    assert 'support --public-issue-bundle --workdir "$PWD"' in targetless_bundle.output
    assert "<project-dir>" not in targetless_bundle.output
    combined_bundle_json = runner.invoke(cli.app, ["support", "--workdir", str(workdir), "--public-issue-bundle", "--json"])
    assert combined_bundle_json.exit_code == 1
    assert "choose either --json or --public-issue-bundle" in combined_bundle_json.stdout


def test_web_public_issue_bundle_uses_server_side_public_bundle_text(service_factory, tmp_path: Path) -> None:
    client = TestClient(build_app(service=service_factory(scenario="success"), bind_host="127.0.0.1", bind_port=9123))
    support_page = client.get("/support", params={"workdir": str(tmp_path)}, headers={"Accept-Language": "zh-CN"})
    bundle = client.get("/api/diagnostics/public-issue-bundle", params={"workdir": str(tmp_path), "language": "zh"})
    targetless = client.get("/api/diagnostics/public-issue-bundle")
    targetless_doctor = client.get("/api/diagnostics/doctor")
    targetless_public_doctor = client.get("/api/diagnostics/doctor", params={"public": "true"})
    relative = client.get("/api/diagnostics/public-issue-bundle", params={"workdir": "."})
    relative_doctor = client.get("/api/diagnostics/doctor", params={"workdir": ".", "public": "true"})
    relative_support_page = client.get("/support", params={"workdir": "."})
    cleared_support_target = client.post("/support", params={"workdir": str(tmp_path)}, data={"workdir": ""}, follow_redirects=False)
    assert support_page.status_code == bundle.status_code == relative_support_page.status_code == HTTPStatus.OK
    assert targetless_doctor.status_code == targetless_public_doctor.status_code == HTTPStatus.OK
    assert (targetless.status_code, targetless.json()["error"], targetless.json()["target_project_required"], relative.status_code, relative.json()["error"], relative_doctor.status_code, relative_doctor.json()["error"], relative.json()["next_action_kind"]) == (
        HTTPStatus.BAD_REQUEST, "target_project_required", True, HTTPStatus.BAD_REQUEST, "target_project_absolute_path_required", HTTPStatus.BAD_REQUEST, "target_project_absolute_path_required", "choose_workdir_for_public_report",
    )
    doctor_payload = targetless_doctor.json()
    doctor_text = json.dumps(doctor_payload, ensure_ascii=False)
    public_doctor_payload = targetless_public_doctor.json()
    public_doctor_text = json.dumps(public_doctor_payload, ensure_ascii=False)
    assert (doctor_payload["status"], doctor_payload["target_project_required"], doctor_payload["workdir"], doctor_payload["workdir_state"]["status"], [item["kind"] for item in doctor_payload["next_action_items"]]) == ("target_required", True, "", "required", ["choose_workdir", "support"])
    assert (doctor_payload["next_action_items"][0]["command_ready"], doctor_payload["next_action_items"][0]["command_blockers"]) == (False, ["target_project_required"])
    assert not any(key.endswith("_command") or key == "start_command" for key in doctor_payload["web"])
    assert (public_doctor_payload["status"], public_doctor_payload["target_project_required"], public_doctor_payload["project_directory_status"], public_doctor_payload["next_actions"], public_doctor_payload["next_action_blocked_kinds"]) == ("target_required", True, "required", ["choose_project_directory", "support"], ["choose_project_directory"])
    assert public_doctor_payload["next_action_command_blockers"] == {"choose_project_directory": ["target_project_required"]}
    for command_term in ("loopora init", "loopora doctor --workdir", "loopora serve --open --host"):
        assert command_term not in doctor_text
        assert command_term not in public_doctor_text
    assert str(REPO_ROOT) not in public_doctor_text
    assert ("/api/diagnostics/public-issue-bundle?" in support_page.text, cleared_support_target.status_code, cleared_support_target.headers["location"]) == (True, HTTPStatus.SEE_OTHER, "/support?support_target_feedback=target_required#support-target-form")
    assert ("/api/diagnostics/public-issue-bundle?workdir=." not in relative_support_page.text, 'data-support-public-report-url=""' in relative_support_page.text) == (True, True)
    assert ('data-testid="global-workdir-context" hidden' in relative_support_page.text, 'value="."' not in relative_support_page.text) == (True, True)
    for term in (
        "Loopora 公开 issue 支持包",
        "紧凑版本/源码身份:",
        "公开就绪摘要:",
        "- 整体状态:",
        "- 就绪轴:",
        "脱敏 doctor --public-json 报告:",
        '"redacted": true',
        '"project_directory_status": "ready"',
    ):
        assert term in bundle.text
    assert bundle.text.index("公开就绪摘要:") < bundle.text.index("脱敏 doctor --public-json 报告:")
    assert str(tmp_path) not in bundle.text


def _assert_support_custom_web_target(runner: CliRunner, workdir: Path) -> None:
    custom = runner.invoke(cli.app, ["support", "--workdir", str(workdir), "--web-host", "0.0.0.0", "--web-port", "9000", "--json"])
    assert custom.exit_code == 0, custom.stdout
    custom_payload = json.loads(custom.stdout)
    expected_url = f"http://127.0.0.1:9000/support?{urlencode({'workdir': str(workdir)})}"
    assert custom_payload["commands"]["public_doctor"].endswith(f"--web-host 0.0.0.0 --web-port 9000 --workdir {shlex.quote(str(workdir))} || true")
    assert custom_payload["local_links"]["web_support"] == expected_url
    custom_plain = runner.invoke(cli.app, ["support", "--workdir", str(workdir), "--web-host", "0.0.0.0", "--web-port", "9000"])
    assert f"Local Web Support page for this Web target: {expected_url}" in custom_plain.stdout
    targetless_custom = json.loads(runner.invoke(cli.app, ["support", "--web-port", "9000", "--json"]).stdout)
    assert targetless_custom["commands"]["public_doctor"].endswith("--web-host 127.0.0.1 --web-port 9000 --workdir '<project-dir>' || true")
    assert targetless_custom["next_actions"][0]["command"].endswith('loopora support --web-host 127.0.0.1 --web-port 9000 --workdir "$PWD"')
    assert targetless_custom["local_links"]["web_support"] == "http://127.0.0.1:9000/support"


def _assert_support_relative_workdir_resolves(monkeypatch, runner: CliRunner, workdir: Path) -> None:
    monkeypatch.chdir(workdir)
    relative_payload = json.loads(runner.invoke(cli.app, ["support", "--workdir", ".", "--json"]).stdout)
    assert relative_payload["workdir_arg"] == str(workdir)
    assert relative_payload["commands"]["public_doctor"].endswith(f"--workdir {shlex.quote(str(workdir))} || true")


def _assert_ready_support_summary(payload: dict) -> None:
    action_kinds = [
        "run_public_issue_bundle", "run_public_doctor_report", "run_version_identity", "open_bug_report",
        "open_feature_request", "read_support_policy", "use_private_security_reporting",
    ]
    assert payload["support_summary"] == {
        "scope": "best_effort",
        "response_time": "no_guarantee",
        "local_first": True,
        "public_report_redacted": True,
        "target_project_required": False,
        "target_project_status": "ready",
        "target_project_setup_ready": True,
        "target_project_report_only": False,
        "command_fields_are_placeholders": False,
        "command_fields_executable": True,
        "command_field_blockers": [],
        "command_fields_are_local_only": True,
        "command_fields_public_pasteable": False,
        "issue_route_kinds": ["bug_report", "feature_request", "usage_or_setup", "security"],
        "next_action_kinds": action_kinds,
        "ready_next_action_kinds": action_kinds,
        "blocked_next_action_kinds": [],
        "next_action_ready_kinds": action_kinds,
        "next_action_ready_now_kinds": action_kinds,
        "next_action_ready_after_actions": {},
        "next_action_blocked_kinds": [],
        "next_action_command_blockers": {},
    }


def _assert_zh_support_guidance(runner: CliRunner, payload: dict) -> None:
    zh_plain = runner.invoke(cli.app, ["support", "--language", "zh-CN"])
    zh_json = runner.invoke(cli.app, ["support", "--language", "zh", "--json"])
    assert zh_plain.exit_code == 0, zh_plain.stdout
    for term in (
        "Loopora 支持", "仅预览", "已就绪的命令", "命令形状预览", "兜底脱敏就绪报告命令",
        "在本地运行；只粘贴生成的输出", "support JSON 是路由元数据", "公开 issue 中优先粘贴公开 issue 支持包",
        "仅在被要求时再提供脱敏报告/版本输出",
        "公开 issue 只粘贴", "公开 issue 支持包输出", "doctor --public-json 的脱敏报告输出", "loopora version --json 的结构化版本/源码身份输出",
        "仅限本地使用", "本页打印的命令行", "本地 Web 支持页 URL", "公开发布前请移除", "凭据", "公开 issue 只能请求私密渠道",
    ):
        assert term in zh_plain.stdout
    assert zh_json.exit_code == 0, zh_json.stdout
    zh_payload = json.loads(zh_json.stdout)
    assert zh_payload["language"] == "zh"
    assert zh_payload["target_project_status"] == "required"
    assert zh_payload["target_project_setup_ready"] is False
    assert zh_payload["target_project_report_only"] is False
    assert zh_payload["support_summary"]["issue_route_kinds"] == payload["support_summary"]["issue_route_kinds"]
    assert zh_payload["support_summary"]["next_action_kinds"] == [
        "choose_workdir_for_public_report", *payload["support_summary"]["next_action_kinds"],
    ]
    assert zh_payload["support_summary"]["ready_next_action_kinds"] == [
        "choose_workdir_for_public_report", "run_version_identity", "open_bug_report",
        "open_feature_request", "read_support_policy", "use_private_security_reporting",
    ]
    assert zh_payload["support_summary"]["blocked_next_action_kinds"] == ["run_public_issue_bundle", "run_public_doctor_report"]
    assert zh_payload["next_actions"][0]["command"].endswith('loopora support --language zh --workdir "$PWD"')
    assert [route["kind"] for route in zh_payload["issue_routes"]] == [route["kind"] for route in payload["issue_routes"]]
    assert [route["when_zh"] for route in zh_payload["issue_routes"]] == [route["when_zh"] for route in payload["issue_routes"]]


def _assert_support_public_doctor_command(payload: dict, workdir: Path, private_home: Path) -> None:
    public_issue_bundle = payload["commands"]["public_issue_bundle"]
    assert "loopora support --public-issue-bundle" in public_issue_bundle
    assert public_issue_bundle.endswith(f"--workdir {shlex.quote(str(workdir))}")
    assert str(private_home) not in public_issue_bundle
    public_doctor = payload["commands"]["public_doctor"]
    assert "loopora doctor --public-json --workdir" in public_doctor
    assert public_doctor.endswith(f"--workdir {shlex.quote(str(workdir))} || true")
    assert str(private_home) not in public_doctor


def _assert_support_command_state(
    payload: dict,
    *,
    target_required: bool,
    placeholders: bool,
    executable: bool,
    blockers: list[str],
) -> None:
    assert (
        payload["target_project_required"],
        payload["command_fields_are_placeholders"],
        payload["command_fields_executable"],
        payload["command_field_blockers"],
        payload["command_fields_are_local_only"],
        payload["command_fields_public_pasteable"],
    ) == (target_required, placeholders, executable, blockers, True, False)
    assert payload["support_summary"]["command_fields_executable"] is executable
    assert payload["support_summary"]["command_field_blockers"] == blockers
    assert (payload["support_summary"]["command_fields_are_local_only"], payload["support_summary"]["command_fields_public_pasteable"]) == (True, False)


def _assert_support_target_project_state(payload: dict, *, status: str, executable: bool) -> None:
    target_setup_ready = status == "ready"
    target_report_only = executable and status != "ready"
    assert (
        payload["target_project_status"],
        payload["target_project_setup_ready"],
        payload["target_project_report_only"],
    ) == (status, target_setup_ready, target_report_only)
    assert payload["support_summary"]["target_project_status"] == status
    assert payload["support_summary"]["target_project_setup_ready"] is target_setup_ready
    assert payload["support_summary"]["target_project_report_only"] is target_report_only


def _assert_targetless_support_preview(plain, payload: dict) -> None:
    assert plain.exit_code == 0, plain.stdout
    for term in ("Run only ready commands locally", "preview only", "Preview command shape", "public issue support bundle command shape", "redacted readiness report command shape", "Target-project support command", "support --workdir \"$PWD\"", "target project", "<project-dir>"):
        assert term in plain.stdout
    assert "redacted readiness report command: " not in plain.stdout
    assert plain.stdout.index("compact version/source identity command") < plain.stdout.index("Preview command shape")
    assert payload["posting_guidance"]["preview_command_fields_require_target_project"] is True
    assert payload["posting_guidance"]["run_ready_commands_locally"] is True
    _assert_support_command_state(
        payload,
        target_required=True,
        placeholders=True,
        executable=False,
        blockers=["target_project_required"],
    )
    _assert_support_target_project_state(payload, status="required", executable=False)
    assert payload["workdir_arg"] == "'<project-dir>'"
    _assert_support_next_actions(payload, target_required=True)


def _assert_unusable_target_support_report_only(runner: CliRunner, tmp_path: Path) -> None:
    file_target = tmp_path / "not-a-project.txt"
    file_target.write_text("not a project directory", encoding="utf-8")
    samples = [
        (tmp_path / "missing-project", "missing", "missing"),
        (file_target, "not_directory", "not a directory"),
    ]
    for target, status, status_label in samples:
        plain = runner.invoke(cli.app, ["support", "--workdir", str(target)])
        structured = runner.invoke(cli.app, ["support", "--workdir", str(target), "--json"])
        assert plain.exit_code == 0, plain.stdout
        assert structured.exit_code == 0, structured.stdout
        payload = json.loads(structured.stdout)
        normalized_plain = " ".join(plain.stdout.split())
        assert "Run ready preferred-bundle/fallback-report/identity commands locally" in normalized_plain
        assert f"Target project state: {status_label}" in normalized_plain
        assert "preferred bundle/fallback report commands are ready" in normalized_plain
        assert "setup still needs a usable target project" in normalized_plain
        _assert_support_command_state(
            payload,
            target_required=False,
            placeholders=False,
            executable=True,
            blockers=[],
        )
        _assert_support_target_project_state(payload, status=status, executable=True)
        _assert_support_next_actions(payload, target_required=False)


def _assert_support_next_actions(payload: dict, *, target_required: bool) -> None:
    actions = payload["next_actions"]
    kinds = [action["kind"] for action in actions]
    expected = [
        "run_public_issue_bundle", "run_public_doctor_report", "run_version_identity", "open_bug_report",
        "open_feature_request", "read_support_policy", "use_private_security_reporting",
    ]
    if target_required:
        expected.insert(0, "choose_workdir_for_public_report")
    assert payload["support_summary"]["next_action_kinds"] == kinds == expected
    assert payload["next_action_kinds"] == expected
    expected_ready = [
        kind
        for kind in expected
        if kind not in {"run_public_issue_bundle", "run_public_doctor_report"} or not target_required
    ]
    assert payload["support_summary"]["ready_next_action_kinds"] == expected_ready
    assert payload["support_summary"]["blocked_next_action_kinds"] == (
        ["run_public_issue_bundle", "run_public_doctor_report"] if target_required else []
    )
    expected_blockers = {"run_public_issue_bundle": ["target_project_required"], "run_public_doctor_report": ["target_project_required"]} if target_required else {}
    assert (payload["next_action_ready_kinds"], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"], payload["next_action_blocked_kinds"], payload["next_action_command_blockers"]) == (
        expected_ready, expected_ready, {}, ["run_public_issue_bundle", "run_public_doctor_report"] if target_required else [], expected_blockers
    )
    assert (payload["support_summary"]["next_action_ready_kinds"], payload["support_summary"]["next_action_ready_now_kinds"], payload["support_summary"]["next_action_ready_after_actions"], payload["support_summary"]["next_action_blocked_kinds"], payload["support_summary"]["next_action_command_blockers"]) == (
        expected_ready, expected_ready, {}, ["run_public_issue_bundle", "run_public_doctor_report"] if target_required else [], expected_blockers
    )
    if target_required:
        choose = actions[0]
        assert (choose["command_ready"], choose["command_blockers"], choose["local_only"]) == (True, [], True)
        assert choose["command"].endswith('loopora support --workdir "$PWD"')
        assert "<project-dir>" not in choose["command"]
    bundle = actions[1 if target_required else 0]
    assert (bundle["kind"], bundle["command_ready"], bundle["command_blockers"], bundle["local_only"], bundle["public_output"]) == (
        "run_public_issue_bundle", not target_required, ["target_project_required"] if target_required else [], True, "public_issue_bundle_output",
    )
    doctor = actions[2 if target_required else 1]
    assert (doctor["kind"], doctor["command_ready"], doctor["command_blockers"], doctor["allows_nonzero_exit"], doctor["local_only"], doctor["public_output"]) == (
        "run_public_doctor_report", not target_required, ["target_project_required"] if target_required else [], True, True, "public_doctor_output",
    )
    version = actions[3 if target_required else 2]
    assert (
        version["kind"],
        version["command_ready"],
        version["command_blockers"],
        version["local_only"],
        version["public_output"],
        version["public_outputs"],
        version["structured_public_output"],
    ) == (
        "run_version_identity",
        True,
        [],
        True,
        "version_output",
        ["version_output", "version_identity_json_output"],
        "version_identity_json_output",
    )
    assert "loopora --version" in version["command"]
    assert "loopora version --json" in version["structured_command"]
    assert (actions[-1]["kind"], actions[-1]["route_kind"], actions[-1]["private_report_url"], actions[-1]["public_fallback"]) == (
        "use_private_security_reporting", "security", "https://github.com/huyusong10/Loopora/security/advisories/new", "private_channel_request_only",
    )


def _assert_support_issue_routes(payload: dict) -> None:
    routes = payload["issue_routes"]
    assert [route["kind"] for route in routes] == ["bug_report", "feature_request", "usage_or_setup", "security"]
    assert [route["url"] for route in routes] == [
        "https://github.com/huyusong10/Loopora/issues/new?template=bug_report.yml",
        "https://github.com/huyusong10/Loopora/issues/new?template=feature_request.yml",
        "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md",
        "https://github.com/huyusong10/Loopora/security/advisories/new",
    ]
    assert [route["when"] for route in routes] == [route["when_en"] for route in routes]
    assert routes[0]["destination_zh"] == "GitHub Bug Report 模板"
    assert routes[0]["when_zh"].startswith("可复现的 Loopora 缺陷")
    assert routes[2]["destination_zh"].startswith("先阅读 SUPPORT.md")
    assert "Web 访问令牌暴露" in routes[3]["when_zh"]
    assert routes[3]["policy_url"] == "https://github.com/huyusong10/Loopora/security/policy"
    assert routes[3]["private_report_url"] == "https://github.com/huyusong10/Loopora/security/advisories/new"
    assert routes[3]["public_fallback_en"] == routes[3]["public_fallback"]
    assert "private reporting channel" in routes[3]["public_fallback"]
    assert "漏洞细节或敏感数据" in routes[3]["public_fallback_zh"]


def test_github_ci_workflow_keeps_default_quality_gate_contract() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    for term in (
        "name: CI",
        "pull_request:",
        "permissions:\n  contents: read",
        "group: ${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress: true",
        'python-version: ["3.11", "3.12"]',
        "Run default-fast verification gate",
        QUALITY_GATE_COMMAND,
        "uv run pytest tests/checks/journeys -q",
    ):
        assert term in workflow
    assert workflow.count("uv sync --locked") == EXPECTED_UV_SYNC_STEP_COUNT


def test_github_browser_journey_container_matches_locked_playwright_version() -> None:
    config = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    container = config["jobs"]["browser-journey"]["container"]

    assert container["image"] == f"mcr.microsoft.com/playwright/python:v{_locked_package_version('playwright')}-noble"


def test_github_codeql_workflow_keeps_security_scan_scope_and_permissions_explicit() -> None:
    config = yaml.safe_load(CODEQL_WORKFLOW.read_text(encoding="utf-8"))

    assert config["name"] == "CodeQL"
    assert _github_workflow_triggers(config) == {
        "push": {"branches": ["dev"]},
        "pull_request": {"branches": ["dev"]},
        "schedule": [{"cron": "37 3 * * 1"}],
        "workflow_dispatch": None,
    }
    assert config["permissions"] == {"contents": "read", "security-events": "write"}
    assert config["concurrency"] == {"group": "${{ github.workflow }}-${{ github.ref }}", "cancel-in-progress": True}

    job = config["jobs"]["analyze"]
    assert job["timeout-minutes"] == CODEQL_TIMEOUT_MINUTES
    assert job["strategy"]["fail-fast"] is False
    assert job["strategy"]["matrix"]["include"] == [
        {"language": "javascript-typescript", "build-mode": "none"},
        {"language": "python", "build-mode": "none"},
    ]

    steps = job["steps"]
    assert steps[0] == {"name": "Checkout", "uses": "actions/checkout@v6"}
    assert steps[1] == {
        "name": "Initialize CodeQL",
        "uses": "github/codeql-action/init@v4",
        "with": {"languages": "${{ matrix.language }}", "build-mode": "${{ matrix.build-mode }}"},
    }
    assert steps[2] == {"name": "Perform CodeQL analysis", "uses": "github/codeql-action/analyze@v4"}


def test_github_dependabot_keeps_dependency_update_prs_scoped_and_scheduled() -> None:
    config = yaml.safe_load(DEPENDABOT_CONFIG.read_text(encoding="utf-8"))

    assert config["version"] == DEPENDABOT_SCHEMA_VERSION
    updates = config["updates"]
    update_by_ecosystem = {entry["package-ecosystem"]: entry for entry in updates}

    assert set(update_by_ecosystem) == {"uv", "github-actions"}
    for entry in update_by_ecosystem.values():
        assert entry["directory"] == "/"
        assert entry["schedule"] == {"interval": "weekly", "day": "monday", "time": "09:00", "timezone": "Etc/UTC"}
        assert entry["open-pull-requests-limit"] == DEPENDABOT_OPEN_PULL_REQUEST_LIMIT
