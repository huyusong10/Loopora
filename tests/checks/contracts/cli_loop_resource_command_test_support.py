from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import shlex
from typing import Any

from typer.testing import Result

from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR


DELETED_RUN_COUNT = 2
RETRY_CLI_RUN_START_KINDS = ["retry_cli_run_start"]
RETRY_RUN_START_STATUS = ("failed", "run_start_failed", "retry_run_start")
SPEC_TEXT = "# Task\n\nKeep going.\n"


def write_spec(root: Path, name: str = "spec.md", text: str = SPEC_TEXT) -> Path:
    spec_path = root / name
    spec_path.write_text(text, encoding="utf-8")
    return spec_path


def make_workdir(root: Path, name: str = "workdir") -> Path:
    workdir = root / name
    workdir.mkdir()
    return workdir


def payload_from(result: Result) -> dict[str, Any]:
    return json.loads(result.stdout)


def payload_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def fail_create_loop_service(message: str) -> type[object]:
    class FailService:
        def create_loop(self, **_kwargs: object) -> None:
            raise AssertionError(message)

    return FailService


def run_start_failed_run(loop_id: str, run_id: str = "run_failed_start") -> dict[str, Any]:
    return {
        "id": run_id,
        "loop_id": loop_id,
        "status": "failed",
        "error_message": BACKGROUND_WORKER_START_ERROR,
        "task_verdict": {"status": "not_evaluated", "source": "run_status"},
    }


def assert_recovery_summary_actions(payload: dict[str, Any], summary_key: str, state_key: str, state: str, expected: list[str]) -> None:
    actions = payload["next_actions"]
    action_kinds = [item["kind"] for item in actions]
    ready_now = [item["kind"] for item in actions if not item.get("after_action")]
    ready_after = {item["kind"]: item["after_action"] for item in actions if item.get("after_action")}
    assert (payload[summary_key]["next_action_kinds"], action_kinds, payload[summary_key][state_key]) == (expected, expected, state)
    assert (payload["next_action_ready_now_kinds"], payload[summary_key]["next_action_ready_after_actions"]) == (ready_now, ready_after)


def assert_retry_cli_run_start_ready(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["next_actions"][0]
    assert action["kind"] == RETRY_CLI_RUN_START_KINDS[0]
    assert payload["next_action_kinds"] == payload["next_action_ready_now_kinds"] == RETRY_CLI_RUN_START_KINDS
    assert payload["next_action_ready_after_actions"] == {}
    return action


def assert_command_options(tokens: list[str], expected: Mapping[str, str]) -> None:
    assert {option: option_value(tokens, option) for option in expected} == expected


def option_value(tokens: list[str], option: str) -> str:
    return tokens[tokens.index(option) + 1]


def loopora_command_tokens(command: str) -> list[str]:
    tokens = shlex.split(command)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("--"):
        tokens = tokens[1:]
    return tokens
