from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_PROBE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "real-provider-probe.yml"
REAL_AGENT_PROBE = REPO_ROOT / "tests" / "probes" / "real_environment" / "test_real_agent_adapter_probe.py"


def test_github_real_probe_workflow_uses_handbook_runner_for_all_release_suites() -> None:
    workflow = REAL_PROBE_WORKFLOW.read_text(encoding="utf-8")

    assert "name: Real Probe" in workflow
    assert "on:\n  workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow
    assert "\n  pull_request:" not in workflow
    assert "\n  schedule:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "uv sync --locked" in workflow
    assert "uv pip check" in workflow
    assert "tests/probes/real_environment/run_real_probes.py" in workflow
    assert "suites:" in workflow
    assert 'default: "release"' in workflow
    assert "agent_targets:" in workflow
    assert "cli_targets:" in workflow
    assert "real-agent" in workflow
    assert "real-cli" in workflow
    assert "release-web" in workflow
    assert "LOOPORA_REAL_AGENT_COMMAND_TEMPLATE" in workflow
    assert "LOOPORA_REAL_CLAUDE_AGENT_COMMAND_TEMPLATE" in workflow
    assert "LOOPORA_REAL_OPENCODE_AGENT_COMMAND_TEMPLATE" in workflow
    assert "LOOPORA_REAL_PROBE_ALLOW_MODEL_OVERRIDE" in workflow
    assert "playwright install --with-deps chromium" in workflow
    assert "Upload real probe reports" in workflow
    assert "if: always()" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "loopora-real-probe-reports" in workflow
    assert "path: .loopora/real-probes/**" in workflow
    assert "if-no-files-found: ignore" in workflow


def test_github_real_probe_workflow_does_not_mix_experiments_into_release_probe() -> None:
    workflow = REAL_PROBE_WORKFLOW.read_text(encoding="utf-8")

    assert "tests/experiments/real_workflows" not in workflow
    assert "LOOPORA_ENABLE_REAL_CLI_PROBE: \"1\"" not in workflow


def test_real_agent_probe_uses_current_agent_step_view_contract() -> None:
    source = REAL_AGENT_PROBE.read_text(encoding="utf-8")

    assert "Agent Step View" in source
    assert "agent_step_view.json" in source
    assert "active.get(\"agent_step_view\")" in source
    assert "active.get(\"capsule\")" not in source
    assert "capsule.json" not in source
    assert "step capsule" not in source
    assert "execution capsule" not in source
