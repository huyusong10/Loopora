from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from web_loop_creation_api_test_support import loop_creation_client, loop_creation_step, loop_creation_workflow, post_loop_creation


ROUND_MODE_INTERVAL_SECONDS = 0.1


def test_api_can_create_round_based_loop_without_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Round Builder Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="rounds",
        iteration_interval_seconds=ROUND_MODE_INTERVAL_SECONDS,
        strategy_source=loop_creation_workflow(steps=[loop_creation_step("builder_step", "builder")]),
    )

    assert response.status_code == HTTPStatus.CREATED
    loop = response.json()["loop"]
    assert loop["completion_mode"] == "rounds"
    assert loop["iteration_interval_seconds"] == ROUND_MODE_INTERVAL_SECONDS
    assert loop["workflow_json"]["steps"][0]["role_id"] == "builder"
