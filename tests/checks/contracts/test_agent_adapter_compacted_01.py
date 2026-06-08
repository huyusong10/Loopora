from __future__ import annotations

# Merged from test_agent_adapter_check_claude_role_configs.py
from agent_adapter_check_test_support import assert_agent_check_payload
from agent_adapter_test_support import CliRunner, Path, cli, json


def test_cli_agent_adapter_check_validates_claude_role_frontmatter_and_tools(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "claude", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    inspector_agent = workdir / ".claude" / "agents" / "loopora-inspector.md"
    orchestrator_agent = workdir / ".claude" / "agents" / "loopora-orchestrator.md"
    inspector_agent.write_text(
        inspector_agent.read_text(encoding="utf-8").replace(
            "tools: Read, Glob, Grep, Bash",
            "tools: Read, Glob, Grep, Bash, Write",
        ),
        encoding="utf-8",
    )
    orchestrator_agent.write_text(
        orchestrator_agent.read_text(encoding="utf-8").replace(
            "name: loopora-orchestrator",
            "name: loopora-coordinator",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.claude/agents/loopora-inspector.md)" in text_result.stdout
    assert "fail: role_permissions (.claude/agents/loopora-orchestrator.md)" in text_result.stdout
    assert "discoverable frontmatter and role tool allowlist" in text_result.stdout
    assert "tools=Bash,Glob,Grep,Read" in text_result.stdout
    assert "name=loopora-orchestrator" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "claude", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert "tools=Bash,Glob,Grep,Read" in failed_permissions[".claude/agents/loopora-inspector.md"]["message"]
    assert "name=loopora-orchestrator" in failed_permissions[".claude/agents/loopora-orchestrator.md"]["message"]

# Merged from test_agent_adapter_check_cli_recovery.py


def test_cli_adapter_check_before_install_reports_install_state_not_internal_missing_files(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    text_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check"])

    assert text_result.exit_code == 1
    assert "Codex Loopora entry check: fail" in text_result.stdout
    assert "install_state: not_installed" in text_result.stdout
    assert "missing managed files are expected before install" in text_result.stdout
    assert "Run:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "Then verify:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()} --check" in text_result.stdout
    assert "supporting_file" not in text_result.stdout
    assert "role_agent" not in text_result.stdout
    assert "If a file is unmanaged" not in text_result.stdout

    json_result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert json_result.exit_code == 1
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_check_payload(payload, status="fail")
    assert summary["check_status"] == "fail"
    assert summary["check_recovery"]["state"] == "not_installed"
    assert summary["check_recovery"]["details_are_expected"] is True
    assert summary["check_recovery"]["install_command"].endswith(f"--workdir {workdir.resolve()}")


def test_cli_agent_adapter_check_alias_reports_actionable_install_state(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])

    assert text_result.exit_code == 1
    assert "Codex Loopora entry check: fail" in text_result.stdout
    assert "install_state: not_installed" in text_result.stdout
    assert "Run:" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "No such command" not in text_result.output

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    summary, _legacy = assert_agent_check_payload(payload, status="pass")
    assert summary["check_status"] == "pass"
    assert summary["check_recovery"]["check_command"].endswith(f"--workdir {workdir.resolve()} --check")
    assert summary["agent_surface"]["entry_kind"] == "project_skill"
    assert summary["agent_surface"]["role_agents"]["builder"]["path"] == ".codex/agents/loopora-builder.toml"
    assert summary["agent_surface"]["native_dispatch"]["accepted_native_tools"] == ["spawn_agent"]
    assert "CODEX_SESSION_ID" in summary["agent_surface"]["context_identity_env"]

# Merged from test_agent_adapter_check_codex_role_configs.py


def test_cli_agent_adapter_check_validates_codex_role_toml_and_contract(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    builder_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    guide_agent = workdir / ".codex" / "agents" / "loopora-guide.toml"
    builder_agent.write_text(
        builder_agent.read_text(encoding="utf-8").replace(
            'name = "loopora-builder"',
            'name = "loopora-maker"',
        ),
        encoding="utf-8",
    )
    guide_agent.write_text(
        guide_agent.read_text(encoding="utf-8").replace(
            "Do not launch codex, claude, or opencode from inside this role.",
            "Nested provider CLIs may be launched from inside this role.",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.codex/agents/loopora-builder.toml)" in text_result.stdout
    assert "fail: role_permissions (.codex/agents/loopora-guide.toml)" in text_result.stdout
    assert "discoverable TOML metadata and the Loopora role contract" in text_result.stdout
    assert "name=loopora-builder" in text_result.stdout
    assert "Do not launch codex, claude, or opencode" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert "name=loopora-builder" in failed_permissions[".codex/agents/loopora-builder.toml"]["message"]
    assert "Do not launch codex, claude, or opencode" in failed_permissions[".codex/agents/loopora-guide.toml"]["message"]

# Merged from test_agent_adapter_check_missing_role_config.py


def test_cli_agent_adapter_check_explains_missing_role_agent_config(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    role_agent = workdir / ".codex" / "agents" / "loopora-builder.toml"
    role_agent.unlink()

    text_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir)])

    assert text_result.exit_code == 1
    assert "fail: role_agent (.codex/agents/loopora-builder.toml)" in text_result.stdout
    assert "managed role agent config for loopora-builder is missing" in text_result.stdout
    assert f"loopora init codex --workdir {workdir.resolve()}" in text_result.stdout
    assert "before /loopora-run dispatch" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "codex", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(json_result.stdout), status="fail")
    failed_role = next(
        item
        for item in payload["checks"]
        if item["name"] == "role_agent" and item["path"] == ".codex/agents/loopora-builder.toml"
    )
    assert failed_role["status"] == "fail"
    assert "managed role agent config for loopora-builder is missing" in failed_role["message"]
    assert "before /loopora-run dispatch" in failed_role["message"]

# Merged from test_agent_adapter_check_opencode_role_configs.py


def test_cli_agent_adapter_check_validates_opencode_role_permission_boundary(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "opencode", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout

    orchestrator_agent = workdir / ".opencode" / "agents" / "loopora-orchestrator.md"
    builder_agent = workdir / ".opencode" / "agents" / "loopora-builder.md"
    orchestrator_agent.write_text(
        orchestrator_agent.read_text(encoding="utf-8").replace(
            "    loopora-inspector: allow",
            "    loopora-inspector: deny",
        ),
        encoding="utf-8",
    )
    builder_agent.write_text(
        builder_agent.read_text(encoding="utf-8").replace(
            "  task: deny",
            "  task:\n    external-reviewer: allow",
        ),
        encoding="utf-8",
    )

    text_result = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir)])
    assert text_result.exit_code == 1
    assert "fail: role_permissions (.opencode/agents/loopora-orchestrator.md)" in text_result.stdout
    assert "allow only Loopora role agents" in text_result.stdout
    assert "permission.task.loopora-inspector=allow" in text_result.stdout
    assert "permission.task deny" in text_result.stdout

    json_result = runner.invoke(cli.app, ["agent", "opencode", "check", "--workdir", str(workdir), "--json"])
    assert json_result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(json_result.stdout), status="fail")
    assert payload["check_status"] == "fail"
    failed_permissions = {
        item["path"]: item
        for item in payload["checks"]
        if item["name"] == "role_permissions" and item["status"] == "fail"
    }
    assert ".opencode/agents/loopora-orchestrator.md" in failed_permissions
    assert ".opencode/agents/loopora-builder.md" in failed_permissions
    assert "permission.task.loopora-inspector=allow" in failed_permissions[".opencode/agents/loopora-orchestrator.md"][
        "message"
    ]
    assert "nested subagents/provider flows" in failed_permissions[".opencode/agents/loopora-builder.md"]["message"]

# Merged from test_agent_adapter_entry_template_architecture.py
from agent_adapter_architecture_test_support import (
    REPO_ROOT,
    assert_design_mentions,
    assert_markers_absent,
    assert_markers_present,
    loopora_source,
)


def test_agent_adapter_templates_delegate_shared_entry_contracts() -> None:
    templates_source = loopora_source("agent_adapter_templates")
    contracts_source = loopora_source("agent_adapter_entry_contracts")
    run_contract_source = loopora_source("agent_adapter_run_contract")
    entry_templates_source = loopora_source("agent_adapter_entry_templates")
    plan_contract_asset = (
        REPO_ROOT / "src" / "loopora" / "assets" / "system_prompts" / "agent_native" / "plan-contract.md"
    ).read_text(encoding="utf-8")
    run_contract_asset = (
        REPO_ROOT / "src" / "loopora" / "assets" / "system_prompts" / "agent_native" / "run-contract.md"
    ).read_text(encoding="utf-8")
    contract_markers = (
        "def agent_plan_contract",
        "def agent_recovery_matrix",
        "def agent_result_template_guide",
        "def agent_role_dispatch_guide",
    )
    run_contract_markers = (
        "def agent_native_run_entry_contract",
        "def agent_native_loop_body",
        "def agent_run_section_overview",
    )
    entry_template_markers = (
        "def codex_loopora_gen_skill",
        "def codex_loopora_loop_skill",
        "def claude_loopora_loop_skill",
        "def opencode_loopora_loop_command",
    )

    assert "from loopora.agent_adapter_entry_contracts import" in templates_source
    assert "from loopora.agent_adapter_run_contract import agent_native_loop_body" in templates_source
    assert "from loopora.agent_adapter_entry_templates import" in templates_source
    assert "from loopora.system_prompt_assets import" in contracts_source
    assert "from loopora.system_prompt_assets import" in run_contract_source
    assert "from loopora.system_prompt_assets import" in entry_templates_source
    assert "def managed_templates" in templates_source
    assert_markers_present(contracts_source, contract_markers)
    assert_markers_absent(templates_source, contract_markers)
    assert_markers_present(run_contract_source, run_contract_markers)
    assert_markers_absent(contracts_source, run_contract_markers)
    assert_markers_absent(templates_source, run_contract_markers)
    assert_markers_present(entry_templates_source, entry_template_markers)
    assert_markers_absent(templates_source, entry_template_markers)
    assert "Enter Loopora's planning stage" not in contracts_source
    assert "Enter Loopora's run stage" not in run_contract_source
    assert "Enter Loopora's planning stage" in plan_contract_asset
    assert "Enter Loopora's run stage" in run_contract_asset
    assert "## Detailed Contract" not in entry_templates_source
    assert "## Detailed Contract" not in templates_source
    assert_design_mentions(
        "system_prompt_assets.py",
        "agent_adapter_entry_contracts.py",
        "agent_adapter_run_contract.py",
        "agent_adapter_entry_templates.py",
    )

# Merged from test_agent_adapter_generated_cli_home.py
from loopora.agent_native_submit_hints import agent_native_submit_command

from agent_adapter_test_support import (
    _assert_loopora_cli_command,
    agent_adapters,
    cli_agent_adapter_commands,
    shlex,
)


def test_agent_native_generated_cli_commands_preserve_loopora_home(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project with spaces"
    result_file = workdir / ".loopora" / "agent_outbox" / "codex" / "run_agent__iter000__step00__builder_step.result.json"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    expected_prefix = f"LOOPORA_HOME={shlex.quote(str(home))} LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill "

    run_command = agent_adapters.agent_loop_json_command("codex", workdir, entry_source="codex_project_skill")
    submit_command = agent_native_submit_command(
        adapter="codex",
        run_id="run_agent",
        step_id="builder_step",
        entry_source="codex_project_skill",
        result_file=str(result_file),
    )
    next_command = cli_agent_adapter_commands._agent_next_command_hint(
        adapter="codex",
        workdir=workdir,
        context_id="",
        run_id="run_agent",
        entry_source="codex_project_skill",
    )
    repair_command = cli_agent_adapter_commands._agent_plan_cli_command(
        adapter="codex",
        workdir=str(workdir),
        message="Repair the focused deletion-flow Loop.",
        entry_source="codex_project_skill",
        bundle_file=str(workdir / "candidate.yml"),
    )
    next_commands = agent_adapters._adapter_install_next_commands("codex", workdir)
    check_recovery = agent_adapters._adapter_check_recovery(
        "codex",
        workdir,
        status={"status": "not_installed"},
        check_status="fail",
    )

    assert run_command.startswith(expected_prefix)
    assert submit_command.startswith(expected_prefix)
    assert next_command.startswith(expected_prefix)
    assert repair_command.startswith(expected_prefix)
    assert f"--workdir {shlex.quote(str(workdir))}" in run_command
    assert f"--result-file {shlex.quote(str(result_file))}" in submit_command
    assert f"--workdir {shlex.quote(str(workdir))}" in next_command
    assert f"--bundle-file {shlex.quote(str(workdir / 'candidate.yml'))}" in repair_command
    _assert_loopora_cli_command(
        next_commands["check"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        next_commands["agent_check"],
        f"loopora agent codex check --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["install_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["check_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )

# Merged from test_agent_adapter_hook_architecture.py


def test_claude_hook_assets_have_dedicated_boundary() -> None:
    host_config_source = loopora_source("agent_adapter_host_config")
    hook_source = loopora_source("agent_adapter_claude_hook")
    hook_markers = (
        "CLAUDE_SESSION_HOOK_COMMAND",
        "CLAUDE_SESSION_HOOK_GROUP",
        "def claude_session_hook_script",
    )

    assert "from loopora.agent_adapter_claude_hook import" in host_config_source
    assert_markers_present(hook_source, hook_markers)
    assert "def claude_session_hook_script" not in host_config_source
    assert "def install_host_config" in host_config_source
    assert "def install_host_config" not in hook_source
    assert_design_mentions("agent_adapter_claude_hook.py")

# Merged from test_agent_adapter_identity_architecture.py
import pytest

from loopora.agent_adapters import normalize_agent_adapter_kind as legacy_normalize_agent_adapter_kind
from loopora.agent_native_adapter_contracts import normalize_agent_adapter_kind
from loopora.service_types import LooporaError


def test_agent_native_adapter_contracts_normalize_host_aliases_without_installer_state() -> None:
    assert normalize_agent_adapter_kind("openai-codex") == "codex"
    assert normalize_agent_adapter_kind("claude-code") == "claude"
    assert normalize_agent_adapter_kind("open-code") == "opencode"
    assert legacy_normalize_agent_adapter_kind("claudecode") == "claude"

    with pytest.raises(LooporaError, match="unsupported agent adapter"):
        normalize_agent_adapter_kind("unknown-agent")

# Merged from test_agent_adapter_lifecycle_architecture.py


def test_agent_adapter_lifecycle_has_dedicated_boundary() -> None:
    facade_source = loopora_source("agent_adapters")
    lifecycle_source = loopora_source("agent_adapter_lifecycle")
    status_source = loopora_source("agent_adapter_status")
    check_recovery_source = loopora_source("agent_adapter_check_recovery")
    lifecycle_markers = (
        "def list_agent_adapter_statuses",
        "def agent_adapter_status",
        "def check_agent_adapter",
        "def install_agent_adapter",
        "def uninstall_agent_adapter",
    )
    facade_markers = (
        "def write_agent_binding",
        "def agent_loop_command",
        "def agent_loop_json_command",
    )

    assert "from loopora.agent_adapter_lifecycle import" in facade_source
    assert "from loopora.agent_adapter_check_recovery import adapter_check_recovery as _adapter_check_recovery" in (
        lifecycle_source
    )
    assert_markers_present(lifecycle_source, lifecycle_markers)
    assert_markers_absent(facade_source, lifecycle_markers)
    assert "from loopora.agent_adapter_status import" in lifecycle_source
    assert "def managed_adapter_status" in status_source
    assert "def not_implemented_adapter_status" in status_source
    assert "def managed_adapter_status" not in lifecycle_source
    assert "def _managed_adapter_status" not in lifecycle_source
    assert "def adapter_check_recovery" in check_recovery_source
    assert "def adapter_check_recovery" not in lifecycle_source
    assert_markers_present(facade_source, facade_markers)
    assert_markers_absent(lifecycle_source, facade_markers)
    assert_design_mentions(
        "agent_adapter_lifecycle.py",
        "agent_adapter_status.py",
        "agent_adapter_check_recovery.py",
    )

# Merged from test_agent_adapter_manifest_architecture.py


def test_agent_adapter_manifest_has_dedicated_boundary() -> None:
    managed_source = loopora_source("agent_adapter_managed_files")
    manifest_source = loopora_source("agent_adapter_manifest")
    lifecycle_source = loopora_source("agent_adapter_lifecycle")
    status_source = loopora_source("agent_adapter_status")
    dev_reset_source = loopora_source("dev_reset")
    manifest_markers = (
        "def manifest_payload",
        "def read_manifest",
        "def manifest_paths",
        "def manifest_hash_for_path",
        "def obsolete_managed_paths",
        "def managed_marker",
        "def manifest_relative_path",
        "OBSOLETE_MANAGED_PATHS = {",
    )
    managed_file_markers = (
        "def managed_file_status",
        "def managed_status_paths",
        "def remove_obsolete_managed_files",
        "def assert_targets_are_replaceable",
    )

    assert "from loopora.agent_adapter_manifest import" in managed_source
    assert "from loopora.agent_adapter_manifest import" in lifecycle_source
    assert "from loopora.agent_adapter_manifest import" in status_source
    assert "from loopora.agent_adapter_manifest import" in dev_reset_source
    assert_markers_present(manifest_source, manifest_markers)
    assert_markers_absent(managed_source, manifest_markers)
    assert_markers_present(managed_source, managed_file_markers)
    assert_markers_absent(manifest_source, managed_file_markers)
    assert_design_mentions("agent_adapter_manifest.py", "agent_adapter_managed_files.py")

# Merged from test_agent_adapter_recovery_context_title.py
from loopora.service_alignment_context import (
    ALIGNMENT_CONTEXT_TITLE_PREVIEW_LIMIT,
    alignment_context_title_from_session,
)


def test_agent_run_recovery_context_title_truncates_with_ellipsis() -> None:
    title = alignment_context_title_from_session(
        {
            "transcript": [
                {
                    "role": "user",
                    "content": (
                        "Build a refund-admin safety audit flow that prevents unauthorized refunds, "
                        "records provider failures, and preserves audit evidence."
                    ),
                }
            ]
        }
    )

    assert title.endswith("...")
    assert len(title) == ALIGNMENT_CONTEXT_TITLE_PREVIEW_LIMIT

# Merged from test_agent_adapter_recovery_failed_preview_choice.py
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    _assert_non_runnable_recovery_choice_routes_to_plan,
)


def test_agent_run_recovery_failed_preview_choice_points_to_repair(
    service_factory, tmp_path: Path, sample_workdir: Path
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bad-bundle.yml"
    bundle_file.write_text("version: 1\nspec:\n  name: Refund admin\n", encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a refund admin workflow with audit and provider-failure evidence.",
            bundle_file=bundle_file,
            context_id="thread-failed",
        )
    )
    resolution = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    choice = resolution["choices"][0]

    assert generated["requires_candidate_repair"] is True
    assert resolution["action"] == "choose_recoverable_context"
    assert choice["alignment_session_id"] == generated["session"]["id"]
    assert choice["action"] == "repair_failed_preview"
    assert "repair" in choice["choice_hint_en"]
    assert choice["preview_path"] == f"/loops/new/bundle?alignment_session_id={generated['session']['id']}"
    assert choice["validation_error"]
    assert "metadata.name is required" in choice["validation_error"]
    assert choice["plan_file_to_repair"] == str(bundle_file)
    assert choice["preview_plan_copy"].endswith("/artifacts/bundle.yml")
    assert choice["next_repair_step"].startswith("repair the candidate plan file")
    _assert_non_runnable_recovery_choice_routes_to_plan(choice, expected_status="needs_repair")

# Merged from test_agent_adapter_static_check_architecture.py


def test_agent_adapter_static_entry_checks_have_dedicated_boundary() -> None:
    static_source = loopora_source("agent_adapter_static_checks")
    entry_checks_source = loopora_source("agent_adapter_entry_static_checks")
    entry_check_markers = (
        "def adapter_entry_reference_map",
        "def adapter_supporting_files_checks",
        "def adapter_entry_shape_checks",
        "def entry_has_native_run_contract",
    )

    assert "from loopora.agent_adapter_entry_static_checks import" in static_source
    assert_markers_present(entry_checks_source, entry_check_markers)
    assert_markers_absent(static_source, entry_check_markers)
    assert "def adapter_static_checks" in static_source
    assert "def adapter_static_checks" not in entry_checks_source
    assert_design_mentions("agent_adapter_entry_static_checks.py")
