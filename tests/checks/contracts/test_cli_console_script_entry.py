from __future__ import annotations

import subprocess
import sys
from importlib.metadata import distribution

MODULE_HELP_TIMEOUT_SECONDS = 10
CLI_SUCCESS = 0


def test_cli_package_exposes_loopora_console_script() -> None:
    console_scripts = {
        entry_point.name: entry_point.value
        for entry_point in distribution("loopora").entry_points
        if entry_point.group == "console_scripts"
    }

    assert console_scripts["loopora"] == "loopora.cli:app"


def test_cli_package_exposes_python_module_entry_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "loopora", "--help"],
        capture_output=True,
        check=False,
        text=True,
        timeout=MODULE_HELP_TIMEOUT_SECONDS,
    )

    assert result.returncode == CLI_SUCCESS
    assert "Loopora CLI" in result.stdout
    assert "init" in result.stdout


def test_cli_package_exposes_python_module_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "loopora", "--version"],
        capture_output=True,
        check=False,
        text=True,
        timeout=MODULE_HELP_TIMEOUT_SECONDS,
    )

    assert result.returncode == CLI_SUCCESS
    assert result.stdout.strip() == f"loopora {distribution('loopora').version}"
