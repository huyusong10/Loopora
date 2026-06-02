from __future__ import annotations

from agent_adapter_check_test_support import assert_agent_check_payload
from agent_adapter_test_support import CliRunner, Path, agent_adapters, cli, json, pytest


def test_cli_adapter_check_validates_managed_supporting_files(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout

    healthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert healthy.exit_code == 0, healthy.stdout
    _healthy_summary, healthy_payload = assert_agent_check_payload(json.loads(healthy.stdout), status="pass")
    assert healthy_payload["check_status"] == "pass"
    assert any(item["name"] == "supporting_file" and item["status"] == "pass" for item in healthy_payload["checks"])

    reference = workdir / ".agents" / "skills" / "loopora-run" / "references" / "loopora-recovery-matrix.md"
    reference.unlink()

    unhealthy = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])
    assert unhealthy.exit_code == 1
    _unhealthy_summary, unhealthy_payload = assert_agent_check_payload(json.loads(unhealthy.stdout), status="fail")
    assert unhealthy_payload["check_status"] == "fail"
    assert any(item["name"] == "supporting_file" and item["status"] == "fail" for item in unhealthy_payload["checks"])
    assert not reference.exists()


def test_cli_adapter_check_validates_native_run_entry_contract(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    run_entry = workdir / ".agents" / "skills" / "loopora-run" / "SKILL.md"
    contract_block = (
        f"## {agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_TITLE}\n\n"
        + "\n".join(f"- {item}" for item in agent_adapters.NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
        + "\n\n"
    )
    run_entry_text = run_entry.read_text(encoding="utf-8")
    assert contract_block in run_entry_text
    run_entry.write_text(
        run_entry_text.replace(contract_block, ""),
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--check", "--json"])

    assert result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(result.stdout), status="fail")
    failed_contract = next(item for item in payload["checks"] if item["name"] == "entry_native_run_contract")
    assert failed_contract["status"] == "fail"
    assert failed_contract["path"] == ".agents/skills/loopora-run/SKILL.md"
    assert "native-run contract" in failed_contract["message"]


@pytest.mark.parametrize(
    "case",
    [
        {
            "adapter": "codex",
            "entry_path": ".agents/skills/loopora-run/SKILL.md",
            "old": "name: loopora-run",
            "new": "name: loopora-start",
            "expected_message": "name=loopora-run",
        },
        {
            "adapter": "claude",
            "entry_path": ".claude/skills/loopora-plan/SKILL.md",
            "old": "disable-model-invocation: true",
            "new": "disable-model-invocation: false",
            "expected_message": "disable-model-invocation=true",
        },
        {
            "adapter": "opencode",
            "entry_path": ".opencode/commands/loopora-run.md",
            "old": "agent: loopora-orchestrator",
            "new": "agent: build",
            "expected_message": "agent=loopora-orchestrator",
        },
    ],
)
def test_cli_adapter_check_validates_entry_frontmatter_contract(
    tmp_path: Path,
    case: dict[str, str],
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()
    adapter = case["adapter"]
    entry_path = case["entry_path"]

    install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout
    healthy = runner.invoke(cli.app, ["agent", adapter, "check", "--workdir", str(workdir), "--json"])
    assert healthy.exit_code == 0, healthy.stdout
    entry = workdir / entry_path
    entry.write_text(entry.read_text(encoding="utf-8").replace(case["old"], case["new"]), encoding="utf-8")

    result = runner.invoke(cli.app, ["agent", adapter, "check", "--workdir", str(workdir), "--json"])

    assert result.exit_code == 1
    _summary, payload = assert_agent_check_payload(json.loads(result.stdout), status="fail")
    failed_entry = next(
        item
        for item in payload["checks"]
        if item["name"] == "entry_frontmatter_contract" and item["path"] == entry_path
    )
    assert failed_entry["status"] == "fail"
    assert case["expected_message"] in failed_entry["message"]
    assert "discoverable frontmatter" in failed_entry["message"]
