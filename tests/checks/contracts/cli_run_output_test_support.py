from __future__ import annotations

from loopora.cli_run_output import print_run_result


def assert_cli_list(output: str, key: str, *items: str) -> None:
    assert f"{key}:\n" in output
    assert f"{key}: [" not in output
    for item in items:
        assert f"- {item}" in output


def print_run_result_output(capsys, run: dict) -> str:
    print_run_result(run)
    return capsys.readouterr().out
