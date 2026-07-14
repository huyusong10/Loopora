from __future__ import annotations

# Merged from test_web_loop_creation_command_mode_api.py
from http import HTTPStatus
import json
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient

from loopora.service_types import LooporaWorkdirUnavailableError
from loopora.web import build_app
from loopora.web_workdir_recovery import (
    web_alignment_workdir_recovery_payload,
    web_loop_create_spec_recovery_payload,
)
from web_loop_creation_api_test_support import loop_creation_client, loop_creation_payload


def _assert_action_readiness(payload: dict, expected: list[str], ready_now: list[str], ready_after: dict[str, str]) -> None:
    assert ([item["kind"] for item in payload["next_actions"]], payload["next_action_ready_now_kinds"], payload["next_action_ready_after_actions"]) == (
        expected,
        ready_now,
        ready_after,
    )


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
    payload = response.json()
    loop = payload["loop"]
    assert loop["executor_mode"] == "command"
    assert loop["command_cli"] == "codex"
    assert "{schema_path}" in loop["command_args_text"]
    redirect_parts = urlsplit(payload["redirect_url"])
    assert redirect_parts.path == f"/loops/{loop['id']}"
    assert parse_qs(redirect_parts.query).get("workdir") == [str(sample_workdir.resolve())]


def test_api_loop_creation_uses_strategy_preset_aliases_for_creation_and_spec_recovery(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    client = loop_creation_client(service_factory)
    response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Preset API Loop",
            strategy_preset="inspect_first",
            completion_mode="rounds",
        ),
    )

    assert response.status_code == HTTPStatus.CREATED
    loop = response.json()["loop"]
    assert loop["workflow_json"]["preset"] == "inspect_first"
    assert loop["orchestration_id"] == "builtin:inspect_first"

    missing_spec = tmp_path / "missing-preset-spec.md"
    recovery_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            missing_spec,
            sample_workdir,
            name="Preset Missing Spec API Loop",
            workflow_preset="inspect_first",
        ),
    )
    assert recovery_response.status_code == HTTPStatus.BAD_REQUEST
    command = recovery_response.json()["next_actions"][0]["command"]
    assert "--strategy-preset inspect_first" in command


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
        workflow=loop_creation_workflow(steps=[loop_creation_step("builder_step", "builder", on_pass="finish_run")]),
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
    assert response.json()["error"] == "invalid max_iters: must be an integer"

    bool_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", max_iters=False),
    )

    assert bool_response.status_code == HTTPStatus.BAD_REQUEST
    assert bool_response.json()["error"] == "invalid max_iters: must be a finite number"

    fractional_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", max_iters=1.5),
    )

    assert fractional_response.status_code == HTTPStatus.BAD_REQUEST
    assert fractional_response.json()["error"] == "invalid max_iters: must be an integer"

    non_finite_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="Broken Loop", delta_threshold="nan"),
    )

    assert non_finite_response.status_code == HTTPStatus.BAD_REQUEST
    assert non_finite_response.json()["error"] == "invalid delta_threshold: must be a finite number"


def test_api_loop_creation_rejects_invalid_compose_options_before_resource_recovery(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing-project"
    workdir = tmp_path / "workdir"
    missing_spec = tmp_path / "missing-spec.md"
    workdir.mkdir()
    cases = [
        (
            loop_creation_payload(
                sample_spec_file,
                missing_workdir,
                name="Bad Executor Before Workdir",
                executor_kind="bogus",
            ),
            "invalid executor_kind: unsupported executor kind: 'bogus'. Expected one of: codex, claude, opencode, custom",
        ),
        (
            loop_creation_payload(
                missing_spec,
                workdir,
                name="Bad Completion Before Spec",
                completion_mode="banana",
            ),
            "invalid completion_mode: unsupported completion mode: banana",
        ),
        (
            loop_creation_payload(
                missing_spec,
                workdir,
                name="Bad Command Template Before Spec",
                executor_mode="command",
                command_args_text="{schema_path}",
            ),
            "invalid command_args_text: custom command is missing required placeholders: {prompt}, {output_path}",
        ),
        (
            loop_creation_payload(
                missing_spec,
                workdir,
                name="Bad Role Model Before Spec",
                role_models={"builder": ""},
            ),
            "invalid role_models: invalid role model override: builder=",
        ),
        (
            loop_creation_payload(
                missing_spec,
                workdir,
                name="Bad Numeric Before Spec",
                trigger_window=0,
            ),
            "invalid trigger_window: must be >= 1",
        ),
    ]

    for payload, expected_error in cases:
        response = client.post("/api/loops", json=payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        body = response.json()
        assert body == {"error": expected_error}

    assert not missing_workdir.exists()
    assert not missing_spec.exists()
    assert service.list_loops() == []


def test_api_loop_creation_reports_required_name_as_json_error(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    client = loop_creation_client(service_factory)

    response = client.post("/api/loops", json=loop_creation_payload(sample_spec_file, sample_workdir, name=""))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"error": "name is required"}


def test_api_loop_creation_redacts_low_level_storage_errors(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    local_path = tmp_path / "private" / "loopora.db"

    def fail_create_loop(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(service, "create_loop", fail_create_loop)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, sample_workdir, name="API Storage Error Loop"),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"] == "Loop could not be created"
    assert "permission denied" not in response.text
    assert str(local_path) not in response.text
    assert service.list_loops() == []


def test_api_loop_creation_projects_service_workdir_race_as_compose_recovery(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    racing_workdir = tmp_path / "racing-workdir"
    racing_workdir.mkdir()

    def fail_create_loop(*_args, **_kwargs):
        racing_workdir.rmdir()
        raise LooporaWorkdirUnavailableError(workdir=str(racing_workdir), workdir_state="missing", action="compose")

    monkeypatch.setattr(service, "create_loop", fail_create_loop)
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, racing_workdir, name="API Workdir Race Loop"),
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["surface"] == "web_loop_create"
    assert payload["workdir_state"]["status"] == "missing"
    _assert_action_readiness(
        payload,
        ["create_workdir", "retry_web_compose", "confirm_readiness"],
        ["create_workdir"],
        {"retry_web_compose": "create_workdir", "confirm_readiness": "retry_web_compose"},
    )
    assert service.list_loops() == []


def test_manual_loop_form_rejects_invalid_compose_options_before_workdir_recovery(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing-project"

    response = client.post(
        "/loops/new/manual",
        data={
            "name": "Bad Manual Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(missing_workdir),
            "executor_kind": "custom",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert "invalid executor_mode: Custom Command only supports command mode" in response.text
    assert "Target project directory does not exist yet" not in response.text
    assert not missing_workdir.exists()
    assert service.list_loops() == []


def test_api_loop_creation_explains_unusable_compose_inputs(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing-project"

    workdir_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, missing_workdir, name="Missing Workdir API Loop"),
    )

    assert workdir_response.status_code == HTTPStatus.BAD_REQUEST
    workdir_payload = workdir_response.json()
    assert workdir_payload["loop_recovery"] == "target_workdir_unavailable"
    assert workdir_payload["status"] == "blocked_by_workdir"
    assert "workdir does not exist:" not in workdir_payload["error"]
    _assert_action_readiness(
        workdir_payload,
        ["create_workdir", "retry_web_compose", "confirm_readiness"],
        ["create_workdir"],
        {"retry_web_compose": "create_workdir", "confirm_readiness": "retry_web_compose"},
    )
    assert "mkdir -p" in workdir_payload["next_actions"][0]["command"]
    assert workdir_payload["next_actions"][1]["target"] == "web_loop_create"
    assert workdir_payload["next_actions"][2]["after_action"] == "retry_web_compose"
    assert not missing_workdir.exists()
    assert service.list_loops() == []

    required_workdir_response = client.post(
        "/api/loops",
        json=loop_creation_payload(sample_spec_file, missing_workdir, name="Blank Workdir API Loop", workdir=""),
    )

    assert required_workdir_response.status_code == HTTPStatus.BAD_REQUEST
    required_workdir_payload = required_workdir_response.json()
    assert required_workdir_payload["loop_recovery"] == "target_workdir_unavailable"
    assert required_workdir_payload["status"] == "blocked_by_workdir"
    assert required_workdir_payload["workdir"] == ""
    assert required_workdir_payload["workdir_state"]["status"] == "required"
    _assert_action_readiness(
        required_workdir_payload,
        ["choose_workdir", "retry_web_compose", "confirm_readiness"],
        ["choose_workdir"],
        {"retry_web_compose": "choose_workdir", "confirm_readiness": "retry_web_compose"},
    )
    assert "command" not in required_workdir_payload["next_actions"][1]
    assert "command" not in required_workdir_payload["next_actions"][2]

    workdir = tmp_path / "workdir"
    missing_spec = tmp_path / "missing-spec.md"
    workdir.mkdir()
    spec_response = client.post(
        "/api/loops",
        json=loop_creation_payload(missing_spec, workdir, name="Missing Spec API Loop"),
    )

    assert spec_response.status_code == HTTPStatus.BAD_REQUEST
    spec_payload = spec_response.json()
    assert spec_payload["loop_recovery"] == "target_spec_unavailable"
    assert spec_payload["status"] == "blocked_by_spec"
    assert "spec does not exist:" not in spec_payload["error"]
    _assert_action_readiness(spec_payload, ["create_spec", "retry_web_compose", "choose_spec"], ["create_spec", "choose_spec"], {"retry_web_compose": "create_spec"})
    assert "loopora spec init" in spec_payload["next_actions"][0]["command"]
    assert "--strategy-preset quality_gate" in spec_payload["next_actions"][0]["command"]
    assert spec_payload["next_actions"][1]["target"] == "web_loop_create"
    assert "command" not in spec_payload["next_actions"][2]
    assert not missing_spec.exists()
    assert service.list_loops() == []

    required_spec_response = client.post(
        "/api/loops",
        json=loop_creation_payload(missing_spec, workdir, name="Blank Spec API Loop", spec_path=""),
    )

    assert required_spec_response.status_code == HTTPStatus.BAD_REQUEST
    required_spec_payload = required_spec_response.json()
    assert required_spec_payload["loop_recovery"] == "target_spec_unavailable"
    assert required_spec_payload["status"] == "blocked_by_spec"
    assert required_spec_payload["spec_path"] == ""
    assert required_spec_payload["spec_state"]["status"] == "required"
    _assert_action_readiness(required_spec_payload, ["choose_spec", "retry_web_compose"], ["choose_spec"], {"retry_web_compose": "choose_spec"})
    assert "command" not in required_spec_payload["next_actions"][1]


def test_web_compose_workdir_recovery_redacts_uninspectable_workdir(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "blocked-project"
    local_path = tmp_path / "private" / "blocked-project"
    blocked_resolved = workdir.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {local_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    payload = web_alignment_workdir_recovery_payload(workdir, action="create_alignment_session")

    assert payload["loop_recovery"] == "target_workdir_unavailable"
    assert payload["status"] == "blocked_by_workdir"
    assert payload["workdir"] == str(blocked_resolved)
    assert payload["workdir_state"]["status"] == "unavailable"
    assert payload["workdir_state"]["error"] == "workdir could not be inspected"
    assert payload["workdir_state"]["usable_for_web_alignment"] is False
    _assert_action_readiness(
        payload,
        ["choose_workdir", "confirm_readiness", "retry_web_compose"],
        ["choose_workdir"],
        {"confirm_readiness": "choose_workdir", "retry_web_compose": "confirm_readiness"},
    )
    assert "command" not in payload["next_actions"][1]
    assert "command" not in payload["next_actions"][2]
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "permission denied" not in encoded
    assert str(local_path) not in encoded


def test_web_compose_spec_recovery_redacts_uninspectable_spec(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "blocked-spec.md"
    local_path = tmp_path / "private" / "blocked-spec.md"
    blocked_resolved = spec_path.resolve(strict=False)
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == blocked_resolved:
            raise OSError(f"permission denied: {local_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    payload = web_loop_create_spec_recovery_payload(spec_path, action="create_loop")

    assert payload["loop_recovery"] == "target_spec_unavailable"
    assert payload["status"] == "blocked_by_spec"
    assert payload["spec_path"] == str(blocked_resolved)
    assert payload["spec_state"]["status"] == "unavailable"
    assert payload["spec_state"]["error"] == "spec path could not be inspected"
    _assert_action_readiness(payload, ["choose_spec", "retry_web_compose"], ["choose_spec"], {"retry_web_compose": "choose_spec"})
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "permission denied" not in encoded
    assert str(local_path) not in encoded


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


def test_api_loop_creation_uses_shared_execution_normalization_for_aliases(
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
            name="Alias Loop",
            executor_kind="claude-code",
            executor_mode=" PRESET ",
            model="",
            reasoning_effort="xhigh",
            command_cli="ignored-in-preset",
        ),
    )

    assert response.status_code == HTTPStatus.CREATED
    loop = response.json()["loop"]
    assert loop["executor_kind"] == "claude"
    assert loop["executor_mode"] == "preset"
    assert loop["command_cli"] == ""
    assert loop["model"] == CLAUDE_DEFAULT_MODEL
    assert loop["reasoning_effort"] == "max"


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
        workflow=loop_creation_workflow(steps=[loop_creation_step("builder_step", "builder", inherit_session="sometimes")]),
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


def test_alignment_composer_starts_from_task_and_keeps_optional_judgment_context(service_factory, tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    template = (root / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    page_script = (root / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    styles = (root / "src" / "loopora" / "static" / "pages" / "alignment.css").read_text(encoding="utf-8")
    tutorial_template = (root / "src" / "loopora" / "templates" / "tutorial.html").read_text(encoding="utf-8")
    tutorial_script = (root / "src" / "loopora" / "static" / "pages" / "tutorial.js").read_text(encoding="utf-8")
    choice_script = (root / "src" / "loopora" / "static" / "pages" / "create_choice.js").read_text(encoding="utf-8")
    ordinary_client = loop_creation_client(service_factory)
    ordinary_tutorial = ordinary_client.get("/fit-guide").text
    playground = tmp_path / "demo-playground"
    playground.mkdir()
    demo_tutorial = TestClient(build_app(service=ordinary_client.app.state.service, demo_mode=True, demo_playground_workdir=str(playground))).get("/fit-guide").text
    assert all(fragment in template for fragment in ('data-testid="alignment-direct-path-check-input"', 'data-testid="alignment-judgment-tradeoffs-input"', 'data-testid="alignment-judgment-details"', 'aria-required="true"', 'aria-describedby="alignment-error"'))
    assert all(fragment in template for fragment in ("One sentence is enough; the conversation fills the remaining judgment.", "data-tradeoffs-en=", 'data-testid="loop-create-fit-review" data-create-choice-fit-prompt'))
    assert all(fragment in template for fragment in ('data-alignment-entry-phase="task"', 'data-alignment-entry-copy="reviewed"', 'data-alignment-entry-copy="partial"', 'data-alignment-entry-task-only', 'data-testid="alignment-entry-handoff-summary"'))
    assert 'href="{{ nav_tutorial_fit_href }}" data-testid="loop-create-fit-guide-link"' in template
    assert all(fragment in page_script for fragment in ('document.getElementById("alignment-direct-path-check")', 'document.getElementById("alignment-judgment-tradeoffs")', 'return [taskGoalInput].filter(Boolean)', 'input.setAttribute("aria-invalid", "true")'))
    assert all(fragment in page_script for fragment in ('judgmentTradeoffs: judgmentTradeoffsInput?.value.trim() || ""', "const populatedFields = fields.filter", "button.dataset.tradeoffsEn", "Describe the task first; the conversation can clarify the remaining judgment."))
    assert ".alignment-judgment-grid {\n  display: grid;\n  grid-template-columns: repeat(2, minmax(0, 1fr));" in styles
    assert all(fragment in styles for fragment in (".create-choice-fit-review", ".create-choice-fit-review[hidden]", ".create-choice-tutorial-handoff-review"))
    assert 'data-testid="loop-create-tutorial-handoff"' in template
    assert all(fragment in template for fragment in ('data-create-choice-handoff-web', 'data-create-choice-web-start', 'data-create-choice-setup-start', 'data-create-choice-expert-start', 'data-create-choice-handoff-copy-direct', 'data-create-choice-handoff-finish'))
    assert all(fragment in template for fragment in ('data-testid="loop-create-tutorial-handoff-meta"', 'data-testid="loop-create-tutorial-handoff-review"', 'data-testid="loop-create-tutorial-handoff-review-count"'))
    assert all(fragment in template for fragment in ("pages/create_choice.js", 'data-tutorial-fit-href="{{ nav_tutorial_fit_href }}"'))
    assert 'href="/loops/new/bundle"\n                data-testid="tutorial-fit-task-use-web"' in ordinary_tutorial
    assert f'href="/loops/new/bundle?alignment_workdir={quote(str(playground), safe="")}"' in demo_tutorial
    assert 'data-testid="tutorial-fit-task-use-web"' in tutorial_template
    assert all(fragment in tutorial_template for fragment in ('data-tutorial-fit-route="choice"', 'data-tutorial-fit-route="setup"', 'data-tutorial-fit-route="web"', 'data-tutorial-fit-route="expert"'))
    assert all(fragment in tutorial_script for fragment in ('document.querySelectorAll("[data-tutorial-fit-route]")', 'function setHandoffLinksEnabled(enabled)', 'setHandoffLinksEnabled(false)', 'setHandoffLinksEnabled(true)', 'function directDecisionHandoffPayload(inputs, sourceWorkdir)', 'writeFitHandoff(directDecisionHandoffPayload(inputs, tutorialWorkdirContext()))'))
    assert "targetIsWebCreationPath && missingInputIds.length > 0" not in tutorial_script
    assert all(fragment in tutorial_script for fragment in ('reviewShell?.classList.toggle("has-task", hasTask)', 'fieldShell.hidden = inputId === "task"', 'draftPane.hidden = !hasTask && !preferDirect'))
    assert 'const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1"' in page_script
    assert 'const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1"' in choice_script
    assert all(fragment in choice_script for fragment in ('missingInputIds.length === 0 && setupAllowed', 'window.LooporaUI.tutorialFitSetupCommandState', 'setupGateReady', 'setupGateBlockers', 'Choose a target project before copying same-Agent setup commands'))
    assert "reviewCompletionCommand: String(payload?.review_completion_command" in choice_script
    assert 'renderMetaLine(localeText("缺少", "Missing"), missing)' in choice_script
    assert all(fragment in choice_script for fragment in ("function handoffMatchesTarget(handoff)", "const targetWorkdir = currentWorkdirContext()", "allowEmptyLeft: !targetWorkdir", "rawHandoff.readyForWeb && !hasWorkdirMismatch", 'document.querySelectorAll("[data-create-choice-web-start]")', "const hasWorkdirMismatch = Boolean(rawHandoff && !handoffMatchesTarget(rawHandoff));", "const directPathBlocksCurrentTarget = Boolean(rawHandoff?.prefersDirect && !hasWorkdirMismatch);", 'bridge.classList.toggle("is-warning", hasWorkdirMismatch)', 'finishLink?.classList.remove("is-primary-recovery")', "toolsLink.hidden = handoff.directPathBlocksCurrentTarget", "function setSetupLinkEnabled(enabled)", "function setExpertLinkEnabled(enabled)", "setSetupLinkEnabled(!handoff.directPathBlocksCurrentTarget)", "setExpertLinkEnabled(!handoff.directPathBlocksCurrentTarget)", "currentHandoff?.directPathBlocksCurrentTarget", "directCopyButton.hidden = !directCommand", "window.LooporaUI.writeTextToClipboard(command)", 'sourceWorkdirScopedHref(baseHref, workdir, {urlParam: "alignment_workdir"})', 'setWebStartHrefs(handoff.sourceWorkdir && !currentWorkdirContext() ? handoff.sourceWorkdir : "")', 'useSourceLink.classList.toggle("is-primary-recovery", rawHandoff.readyForWeb && hasWorkdirMismatch)', "currentHandoff?.webStartBlocked", "setWebLinkEnabled(true)", "fitPrompt.hidden = !hasWorkdirMismatch", "reviewDisclosure.open = true", "const projectLines = hasWorkdirMismatch"))
    assert all(fragment in page_script for fragment in ("function setAlignmentEntryPhase", "panel.dataset.alignmentEntryPhase = phase", "alignmentEntryHandoffSummary.dataset.knownCount", 'setAlignmentEntryPhase("task")'))
    assert all(fragment in styles for fragment in ('font-size: 2.25rem', '[data-alignment-entry-task-only][hidden]', '.alignment-entry-handoff-summary', '.bundle-chat-shell:not(.has-session):has(.bundle-chat-main[data-alignment-entry-phase="reviewed"]) .bundle-chat-sidebar', '.bundle-chat-main[data-alignment-entry-phase="reviewed"] .bundle-chat-empty'))
    assert "sessionStorage?.removeItem(FIT_HANDOFF_STORAGE_KEY)" in choice_script
    assert "function applyTutorialFitHandoff()" in page_script
    assert 'data-testid="alignment-tutorial-handoff-bridge"' in template
    assert "function renderTutorialFitHandoffBridge()" in page_script
    assert all(fragment in page_script for fragment in ("const canPrefill = !handoff.blocksWebConversation && fieldsAreEmpty && !hasWorkdirMismatch", "blocksWebConversation", "function tutorialFitHandoffBlocksCurrentWebConversation(handoff)", "const directPathBlocksWebConversation = tutorialFitHandoffBlocksCurrentWebConversation(handoff)", "tutorialFitHandoffBlocksWebConversation", "Direct path selected", "Copy direct-path command", "alignment-tutorial-handoff-manual-copy", "function renderTutorialHandoffManualCopy", "window.LooporaUI?.renderManualCopy?.(container, value", "alignment-tutorial-handoff-manual-copy-textarea", "The browser blocked automatic copy; copy the command below manually.", "The browser blocked automatic copy; copy the Fit Guide draft below manually.", "sendButton.disabled = submitPending", "(!active && tutorialFitHandoffBlocksWebConversation)", "(!active && executorReadinessState.blocking === true)", "Web conversation cannot start"))
    assert all(fragment in page_script for fragment in ("function setDraftWorkdirContext", "syncAlignmentWorkdirContext({syncUrl})", 'function tutorialFitReviewHref(workdir = "")', 'url.searchParams.set("workdir", targetWorkdir)', 'data-tutorial-handoff-finish data-testid="alignment-tutorial-handoff-finish-link"', "const targetWorkdir = workdirInput.value.trim()", "allowEmptyLeft: !targetWorkdir", "allowEmptyLeft: !currentWorkdir"))
    assert "alignment-tutorial-handoff-prefill" in page_script
    assert "Switch and prefill" not in page_script
    assert "alignment-tutorial-handoff-copy-draft" in page_script
    assert all(fragment in styles for fragment in ("alignment-tutorial-handoff-summary", ".alignment-agent-review-actions a"))
