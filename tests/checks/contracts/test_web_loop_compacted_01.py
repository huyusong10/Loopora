from __future__ import annotations

# Merged from test_web_loop_creation_command_mode_api.py
from http import HTTPStatus
from pathlib import Path

from web_loop_creation_api_test_support import loop_creation_client, loop_creation_payload


def test_api_loop_creation_supports_command_mode(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Command Loop",
            executor_kind="codex",
            executor_mode="command",
            command_cli="codex",
            command_args_text="\n".join(
                [
                    "exec",
                    "--json",
                    "--cd",
                    "{workdir}",
                    "--sandbox",
                    "{sandbox}",
                    "--output-schema",
                    "{schema_path}",
                    "--output-last-message",
                    "{output_path}",
                    "{prompt}",
                ]
            ),
            model="",
            reasoning_effort="",
        ),
    )

    assert response.status_code == HTTPStatus.CREATED
    loop = response.json()["loop"]
    assert loop["executor_mode"] == "command"
    assert loop["command_cli"] == "codex"
    assert "{schema_path}" in loop["command_args_text"]

# Merged from test_web_loop_creation_gatekeeper_validation_api.py

from web_loop_creation_api_test_support import loop_creation_step, loop_creation_workflow, post_loop_creation


def test_api_rejects_gatekeeper_mode_without_finish_gatekeeper(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Invalid Gate Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="gatekeeper",
        workflow=loop_creation_workflow(steps=[loop_creation_step("builder_step", "builder")]),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "gatekeeper completion mode" in response.json()["error"]


def test_api_rejects_finish_run_for_non_gatekeeper_steps(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Invalid On Pass Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="rounds",
        workflow=loop_creation_workflow(
            steps=[loop_creation_step("builder_step", "builder", on_pass="finish_run")]
        ),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "non-gatekeeper steps only support on_pass=continue" in response.json()["error"]

# Merged from test_web_loop_creation_numeric_settings_api.py



def test_api_loop_creation_rejects_invalid_numeric_settings(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", max_iters="abc"),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "numeric loop settings" in response.json()["error"]

    bool_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", max_iters=False),
    )

    assert bool_response.status_code == HTTPStatus.BAD_REQUEST
    assert "numeric loop settings" in bool_response.json()["error"]

    fractional_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", max_iters=1.5),
    )

    assert fractional_response.status_code == HTTPStatus.BAD_REQUEST
    assert "numeric loop settings" in fractional_response.json()["error"]

    non_finite_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", delta_threshold="nan"),
    )

    assert non_finite_response.status_code == HTTPStatus.BAD_REQUEST
    assert "finite" in non_finite_response.json()["error"]

# Merged from test_web_loop_creation_provider_defaults_api.py

from loopora.providers import CLAUDE_DEFAULT_MODEL, OPENCODE_DEFAULT_MODEL



def test_api_loop_creation_supports_provider_specific_defaults(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    claude_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Claude Loop",
            executor_kind="claude",
            model="",
            reasoning_effort="xhigh",
        ),
    )
    assert claude_response.status_code == HTTPStatus.CREATED
    claude_loop = claude_response.json()["loop"]
    assert claude_loop["executor_kind"] == "claude"
    assert claude_loop["model"] == CLAUDE_DEFAULT_MODEL
    assert claude_loop["reasoning_effort"] == "max"

    codex_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Codex Loop",
            executor_kind="codex",
            reasoning_effort="",
        ),
    )
    assert codex_response.status_code == HTTPStatus.CREATED
    codex_loop = codex_response.json()["loop"]
    assert codex_loop["executor_kind"] == "codex"
    assert codex_loop["model"] == ""
    assert codex_loop["reasoning_effort"] == ""

    opencode_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="OpenCode Loop",
            executor_kind="opencode",
            model="",
            reasoning_effort="default",
        ),
    )
    assert opencode_response.status_code == HTTPStatus.CREATED
    opencode_loop = opencode_response.json()["loop"]
    assert opencode_loop["executor_kind"] == "opencode"
    assert opencode_loop["model"] == OPENCODE_DEFAULT_MODEL
    assert opencode_loop["reasoning_effort"] == ""

# Merged from test_web_loop_creation_role_models_api.py



def test_api_loop_creation_accepts_role_model_overrides(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Role Models Loop",
            executor_kind="codex",
            model="gpt-5.4",
            reasoning_effort="medium",
            role_models={
                "generator": "gpt-5.4-mini",
                "verifier": "gpt-5.4",
            },
        ),
    )

    assert response.status_code == HTTPStatus.CREATED
    loop = response.json()["loop"]
    assert loop["role_models_json"] == {
        "builder": "gpt-5.4-mini",
        "gatekeeper": "gpt-5.4",
    }

# Merged from test_web_loop_creation_workflow_session_flags_api.py

from web_loop_creation_api_test_support import (
    loop_creation_role,
)


def test_api_normalizes_boolean_like_workflow_step_session_flags(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Session Flag Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="rounds",
        workflow=loop_creation_workflow(
            roles=[
                loop_creation_role("builder", "Builder", "builder"),
                loop_creation_role("inspector", "Inspector", "inspector"),
            ],
            steps=[
                loop_creation_step("builder_step", "builder", inherit_session="false"),
                loop_creation_step("inspector_step", "inspector", inherit_session="true"),
            ],
        ),
    )

    assert response.status_code == HTTPStatus.CREATED
    steps = response.json()["loop"]["workflow_json"]["steps"]
    assert steps[0]["inherit_session"] is False
    assert steps[1]["inherit_session"] is True


def test_api_rejects_invalid_workflow_step_session_flag(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Invalid Session Flag Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="rounds",
        workflow=loop_creation_workflow(
            steps=[loop_creation_step("builder_step", "builder", inherit_session="sometimes")]
        ),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "inherit_session must be a boolean" in response.json()["error"]

# Merged from test_web_loop_creation_workflow_step_ids_api.py



def test_api_rejects_duplicate_workflow_step_ids(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    client = loop_creation_client(service_factory)

    response = post_loop_creation(
        client,
        sample_spec_file,
        sample_workdir,
        name="Duplicate Step Loop",
        executor_kind="codex",
        model="gpt-5.4",
        reasoning_effort="medium",
        completion_mode="rounds",
        workflow=loop_creation_workflow(
            roles=[
                loop_creation_role("builder", "Builder", "builder"),
                loop_creation_role("inspector", "Inspector", "inspector"),
            ],
            steps=[
                loop_creation_step("shared_step", "builder"),
                loop_creation_step("shared_step", "inspector"),
            ],
        ),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "duplicate workflow step id" in response.json()["error"]
