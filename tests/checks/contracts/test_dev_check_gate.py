from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora.cli import app
from loopora.dev_check import DevCheckCommandResult, run_dev_check


def test_dev_check_list_exposes_complexity_and_distribution_gates() -> None:
    result = CliRunner().invoke(app, ["dev", "check", "--list", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    steps = {step["id"]: step for step in payload["steps"]}
    assert steps["complexity_budget"]["command"] == "uv run python scripts/complexity_budget.py --enforce"
    assert steps["package_build"]["command"] == "uv build --out-dir tmp/package-check"
    assert steps["contract_checks"]["command"] == "uv run pytest -q tests/checks/contracts"


def test_failed_package_build_cleans_generated_output(tmp_path: Path) -> None:
    package_output = tmp_path / "tmp" / "package-check"
    package_output.mkdir(parents=True)
    (package_output / "stale.whl").write_text("stale", encoding="utf-8")
    metadata = tmp_path / "src" / "loopora.egg-info"
    metadata.mkdir(parents=True)
    (metadata / "PKG-INFO").write_text("stale", encoding="utf-8")

    def runner(command: tuple[str, ...], _cwd: Path) -> DevCheckCommandResult:
        if command[:2] == ("uv", "build"):
            return DevCheckCommandResult(returncode=1, stderr="build failed")
        return DevCheckCommandResult(returncode=0)

    result = run_dev_check(workdir=tmp_path, command_runner=runner)

    assert result["status"] == "fail"
    assert result["dev_check_summary"]["failed_step_id"] == "package_build"
    assert not package_output.exists()
    assert not metadata.exists()
