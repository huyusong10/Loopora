from __future__ import annotations

import pytest
from typer.testing import CliRunner

from loopora import cli


@pytest.mark.parametrize("old_action", ["gen", "loop"])
def test_agent_runtime_does_not_keep_old_plan_run_aliases(old_action: str) -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "codex", old_action, "--help"])

    assert result.exit_code != 0
