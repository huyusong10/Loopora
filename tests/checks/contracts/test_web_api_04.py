from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from loopora.run_takeaways import (
    empty_judgment_contract,
)
from loopora.providers import CLAUDE_DEFAULT_MODEL, OPENCODE_DEFAULT_MODEL
import loopora.service_run_lifecycle as service_run_lifecycle
from loopora.web import build_app

from web_api_test_support import (
    _start_agent_first_loop,
    _create_api_loop_run,
    _wait_for_run_success,
)

def test_run_detail_keeps_generic_rerun_for_passing_terminal_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Passing Detail Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    service.repository.update_run(
        run["id"],
        task_verdict={
            "status": "passed",
            "source": "gatekeeper",
            "summary": "Required proof is complete.",
            "buckets": {"proven": [{"label": "all required checks"}]},
        },
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/runs/{run['id']}")

    assert page_response.status_code == 200
    assert 'data-testid="run-rerun-button"' in page_response.text
    assert '<span data-lang="en">Rerun</span>' in page_response.text
    assert "Run next evidence pass" not in page_response.text
    assert "Record passing verdict" in page_response.text

def test_run_detail_rerun_routes_agent_first_terminal_run_back_to_slash_command(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    started = _start_agent_first_loop(service, tmp_path=tmp_path, workdir=sample_workdir)
    service.repository.update_run(
        started["run"]["id"],
        status="succeeded",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Required coverage still lacks direct evidence.",
            "buckets": {
                "proven": [],
                "weak": [],
                "unproven": [{"id": "coverage.required", "summary": "Required coverage is still missing."}],
                "blocking": [],
                "residual_risk": [],
            },
        },
        summary_md="# Loopora Run Summary\n\nLifecycle closed; task evidence still belongs to the Agent-first lane.\n",
    )
    client = TestClient(build_app(service=service))

    page_response = client.get(f"/runs/{started['run']['id']}")

    assert page_response.status_code == 200
    assert 'data-testid="run-agent-entry-start-guide"' in page_response.text
    assert 'data-testid="run-agent-entry-copy-command-hero"' in page_response.text
    assert 'data-testid="run-agent-entry-copy-command"' in page_response.text
    assert "/loopora-run" in page_response.text
    assert "loopora agent codex run" in page_response.text
    assert "--context-id web-api-agent-first" in page_response.text
    assert "开启下一轮" in page_response.text
    assert "复制续跑命令" in page_response.text
    assert 'data-agent-entry-command-copy' in page_response.text
    assert 'data-copy-value="' in page_response.text
    assert "LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill" in page_response.text
    assert "loopora agent codex run" in page_response.text
    assert 'data-testid="run-rerun-button"' not in page_response.text

    rerun_response = client.post(f"/runs/{started['run']['id']}/rerun")

    assert rerun_response.status_code == 409
    rerun_payload = rerun_response.json()
    assert "agent-first Loop runs" in rerun_payload["error"]
    assert rerun_payload["agent_entry_start"]["next_loop_action"] == "start_next_run_for_unproven_verdict"
    assert rerun_payload["agent_entry_start"]["linked_task_verdict_status"] == "insufficient_evidence"
    assert len(service.get_loop(started["run"]["loop_id"])["runs"]) == 1

def test_run_accept_result_rejects_active_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Active Accept Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    client = TestClient(build_app(service=service))

    response = client.post(f"/runs/{run['id']}/accept")

    assert response.status_code == 409
    assert "cannot accept run result in status" in response.json()["error"]

def test_run_accept_result_keeps_audit_shape_when_evidence_summary_is_unavailable(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    run_id = _create_api_loop_run(client, sample_spec_file, sample_workdir)
    _wait_for_run_success(client, run_id)

    def fail_takeaways(_run: dict) -> dict:
        raise RuntimeError("raw artifact read failed")

    monkeypatch.setattr(service_run_lifecycle, "build_run_key_takeaways", fail_takeaways)

    response = client.post(f"/runs/{run_id}/accept", follow_redirects=False)

    assert response.status_code == 303
    accepted_event = service.recent_run_events(run_id, event_types={"run_result_accepted"})[-1]
    payload = accepted_event["payload"]
    assert payload["evidence_source_event_id"] < accepted_event["id"]
    assert payload["evidence_available"] is False
    assert payload["evidence_error"] == "acceptance_evidence_unavailable"
    assert payload["judgment_contract"] == empty_judgment_contract()
    assert payload["run_contract_path"] == ""
    assert payload["judgment_contract_summary"] == ""
    assert payload["check_mode"] == ""
    assert payload["check_count"] == 0
    assert payload["completion_mode"] == ""
    assert payload["workflow_preset"] == ""
    assert payload["coverage_targets"] == []
    assert payload["loop_fit_reasons"] == []
    assert payload["execution_strategy"] == []
    assert payload["local_governance"] == []
    assert payload["role_postures"] == []
    assert payload["judgment_tradeoffs"] == []
    assert payload["success_surface"] == []
    assert payload["fake_done_states"] == []
    assert payload["evidence_preferences"] == []
    assert payload["residual_risk"] == ""
    assert payload["task_verdict_path"] == ""
    assert payload["coverage_path"] == ""
    assert payload["manifest_path"] == ""
    assert payload["evidence_count"] == 0
    assert payload["evidence_bucket_counts"] == {
        "proven": 0,
        "weak": 0,
        "unproven": 0,
        "blocking": 0,
        "residual_risk": 0,
    }

def test_api_loop_creation_supports_provider_specific_defaults(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    claude_response = client.post(
        "/api/loops",
        json={
            "name": "Claude Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "claude",
            "model": "",
            "reasoning_effort": "xhigh",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )
    assert claude_response.status_code == 201
    claude_loop = claude_response.json()["loop"]
    assert claude_loop["executor_kind"] == "claude"
    assert claude_loop["model"] == CLAUDE_DEFAULT_MODEL
    assert claude_loop["reasoning_effort"] == "max"

    codex_response = client.post(
        "/api/loops",
        json={
            "name": "Codex Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "reasoning_effort": "",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )
    assert codex_response.status_code == 201
    codex_loop = codex_response.json()["loop"]
    assert codex_loop["executor_kind"] == "codex"
    assert codex_loop["model"] == ""
    assert codex_loop["reasoning_effort"] == ""

    opencode_response = client.post(
        "/api/loops",
        json={
            "name": "OpenCode Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "opencode",
            "model": "",
            "reasoning_effort": "default",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )
    assert opencode_response.status_code == 201
    opencode_loop = opencode_response.json()["loop"]
    assert opencode_loop["executor_kind"] == "opencode"
    assert opencode_loop["model"] == OPENCODE_DEFAULT_MODEL
    assert opencode_loop["reasoning_effort"] == ""

def test_api_loop_creation_rejects_invalid_numeric_settings(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Broken Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "max_iters": "abc",
        },
    )

    assert response.status_code == 400
    assert "numeric loop settings" in response.json()["error"]

    bool_response = client.post(
        "/api/loops",
        json={
            "name": "Broken Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "max_iters": False,
        },
    )

    assert bool_response.status_code == 400
    assert "numeric loop settings" in bool_response.json()["error"]

    fractional_response = client.post(
        "/api/loops",
        json={
            "name": "Broken Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "max_iters": 1.5,
        },
    )

    assert fractional_response.status_code == 400
    assert "numeric loop settings" in fractional_response.json()["error"]

    non_finite_response = client.post(
        "/api/loops",
        json={
            "name": "Broken Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "delta_threshold": "nan",
        },
    )

    assert non_finite_response.status_code == 400
    assert "finite" in non_finite_response.json()["error"]

def test_api_loop_creation_supports_command_mode(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Command Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "executor_mode": "command",
            "command_cli": "codex",
            "command_args_text": "\n".join(
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
            "model": "",
            "reasoning_effort": "",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )

    assert response.status_code == 201
    loop = response.json()["loop"]
    assert loop["executor_mode"] == "command"
    assert loop["command_cli"] == "codex"
    assert "{schema_path}" in loop["command_args_text"]

def test_api_loop_creation_accepts_role_model_overrides(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/loops",
        json={
            "name": "Role Models Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "role_models": {
                "generator": "gpt-5.4-mini",
                "verifier": "gpt-5.4",
            },
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )

    assert response.status_code == 201
    loop = response.json()["loop"]
    assert loop["role_models_json"] == {
        "builder": "gpt-5.4-mini",
        "gatekeeper": "gpt-5.4",
    }

def test_prompt_template_download_and_validation_endpoints(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    template_response = client.get("/api/prompts/templates/builder.md")
    assert template_response.status_code == 200
    markdown_text = template_response.text
    assert "archetype: builder" in markdown_text

    localized_template_response = client.get("/api/prompts/templates/builder.md?locale=zh")
    assert localized_template_response.status_code == 200
    assert "# Builder Prompt" in localized_template_response.text
    assert "archetype: builder" in localized_template_response.text

    validation_response = client.post(
        "/api/prompts/validate",
        json={
            "markdown": markdown_text,
            "archetype": "builder",
        },
    )
    assert validation_response.status_code == 200
    assert validation_response.json()["ok"] is True

    mismatch_response = client.post(
        "/api/prompts/validate",
        json={
            "markdown": markdown_text,
            "archetype": "gatekeeper",
        },
    )
    assert mismatch_response.status_code == 200
    assert mismatch_response.json()["ok"] is False

def test_api_can_create_orchestration_and_use_it_for_loop(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    orchestration_response = client.post(
        "/api/orchestrations",
        json={
            "name": "Custom Inspect First",
            "description": "Inspector before Builder.",
            "workflow": {"preset": "inspect_first"},
        },
    )
    assert orchestration_response.status_code == 201
    orchestration = orchestration_response.json()["orchestration"]
    assert orchestration["name"] == "Custom Inspect First"
    assert orchestration["workflow_json"]["preset"] == "inspect_first"

    list_response = client.get("/api/orchestrations")
    assert list_response.status_code == 200
    assert any(item["id"] == orchestration["id"] for item in list_response.json())

    update_response = client.put(
        f"/api/orchestrations/{orchestration['id']}",
        json={
            "name": "Custom Build First",
            "description": "Updated description.",
            "workflow": {"preset": "build_first"},
        },
    )
    assert update_response.status_code == 200
    updated_orchestration = update_response.json()["orchestration"]
    assert updated_orchestration["name"] == "Custom Build First"
    assert updated_orchestration["workflow_json"]["preset"] == "build_first"

    loop_response = client.post(
        "/api/loops",
        json={
            "name": "Uses Custom Orchestration",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "orchestration_id": updated_orchestration["id"],
            "executor_kind": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
            "max_iters": 3,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
            "start_immediately": False,
        },
    )
    assert loop_response.status_code == 201
    loop = loop_response.json()["loop"]
    assert loop["orchestration"]["id"] == updated_orchestration["id"]
    assert loop["orchestration"]["name"] == "Custom Build First"
    assert loop["workflow_json"]["preset"] == "build_first"

def test_api_orchestration_hydrates_role_snapshots_from_role_definition_id(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = service.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown="""---
version: 1
archetype: builder
---

Focus on safe release work.
""",
        executor_kind="claude",
        executor_mode="preset",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Uses Role Definition Snapshot",
            "description": "Hydrates missing role fields from a role definition.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "role_definition_id": role_definition["id"]},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
        },
    )

    assert response.status_code == 201
    orchestration = response.json()["orchestration"]
    builder_role = orchestration["workflow_json"]["roles"][0]
    assert builder_role["name"] == "Release Builder"
    assert builder_role["prompt_ref"] == "release-builder.md"
    assert builder_role["executor_kind"] == "claude"
    assert builder_role["model"] == "gpt-5.4-mini"
    assert orchestration["prompt_files_json"]["release-builder.md"].startswith("---\nversion: 1")

def test_api_orchestration_rejects_unknown_role_definition_ids(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Broken Role Definition Reference",
            "description": "Should fail fast.",
            "workflow": {
                "version": 1,
                "roles": [
                    {"id": "builder", "role_definition_id": "role_missing"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
        },
    )

    assert response.status_code == 404
    assert "unknown role definition: role_missing" in response.json()["error"]

def test_api_orchestration_rejects_conflicting_role_definition_snapshot_fields(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = service.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown="""---
version: 1
archetype: builder
---

Focus on safe release work.
""",
        executor_kind="claude",
        executor_mode="preset",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Conflicting Role Snapshot",
            "description": "Should fail when snapshot fields conflict with the role definition.",
            "workflow": {
                "version": 1,
                "roles": [
                    {
                        "id": "builder",
                        "role_definition_id": role_definition["id"],
                        "model": "gpt-5.4",
                    },
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
        },
    )

    assert response.status_code == 400
    assert f"conflicts with role_definition_id {role_definition['id']} on model" in response.json()["error"]

def test_api_orchestration_rejects_conflicting_prompt_files_for_role_definition_id(service_factory) -> None:
    service = service_factory(scenario="success")
    role_definition = service.create_role_definition(
        name="Release Builder",
        description="Ships focused release work.",
        archetype="builder",
        prompt_ref="release-builder.md",
        prompt_markdown="""---
version: 1
archetype: builder
---

Focus on safe release work.
""",
        executor_kind="claude",
        executor_mode="preset",
        model="gpt-5.4-mini",
        reasoning_effort="high",
    )
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/orchestrations",
        json={
            "name": "Conflicting Role Prompt Snapshot",
            "description": "Should fail when prompt_files override a role definition prompt.",
            "workflow": {
                "version": 1,
                "roles": [
                    {
                        "id": "builder",
                        "role_definition_id": role_definition["id"],
                    },
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            },
            "prompt_files": {
                "release-builder.md": """---
version: 1
archetype: builder
---

Focus on risky release work.
""",
            },
        },
    )

    assert response.status_code == 400
    assert f"conflicts with role_definition_id {role_definition['id']} on prompt_markdown" in response.json()["error"]
