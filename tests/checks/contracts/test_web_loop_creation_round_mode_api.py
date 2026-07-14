from __future__ import annotations

from http import HTTPStatus
import json
import re
from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient
from runner_helpers import _create_loop

from loopora.web import build_app
from web_api_test_support import _assert_recovery_summary_actions
from web_loop_creation_api_test_support import (
    loop_creation_client,
    loop_creation_payload,
    loop_creation_step,
    loop_creation_workflow,
    post_loop_creation,
)


ROUND_MODE_INTERVAL_SECONDS = 0.1
ROOT = Path(__file__).resolve().parents[3]


def _input_tag(html: str, testid: str) -> str:
    match = re.search(rf'<input\b(?=[^>]*data-testid="{re.escape(testid)}")[^>]*>', html)
    assert match is not None
    return match.group(0)


def _pristine_loop_form(html: str) -> dict[str, object]:
    match = re.search(r'<script id="pristine-loop-form-json" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert match is not None
    return json.loads(match.group(1))


def test_manual_create_and_plan_file_import_default_to_saved_loop_without_start(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    response = TestClient(build_app(service=service)).get("/loops/new/manual", params={"workdir": str(sample_workdir)})

    assert response.status_code == HTTPStatus.OK
    assert "checked" not in _input_tag(response.text, "manual-loop-start-immediately")
    assert "checked" not in _input_tag(response.text, "bundle-import-start-immediately")
    assert _pristine_loop_form(response.text)["start_immediately"] is False


def test_create_choice_existing_work_is_scoped_to_target_workdir(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    current_workdir.mkdir()
    other_workdir.mkdir()
    _create_loop(service, sample_spec_file, other_workdir, name="Other Project Loop")
    client = TestClient(build_app(service=service))

    encoded_current = quote(str(current_workdir.resolve()), safe="")
    foreign_choice = client.get(f"/loops/new?workdir={encoded_current}")
    foreign_home = client.get(f"/?workdir={encoded_current}")
    current_loop = _create_loop(service, sample_spec_file, current_workdir, name="Current Project Loop")
    current_choice = client.get(f"/loops/new?workdir={encoded_current}")
    current_home = client.get(f"/?workdir={encoded_current}")

    assert foreign_choice.status_code == HTTPStatus.OK
    assert foreign_home.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="empty"' in foreign_choice.text
    assert 'data-testid="loop-create-existing-show-all-link"' in foreign_choice.text
    assert (
        'href="/" data-existing-action-kind="view_all_work" '
        'data-testid="loop-create-existing-show-all-link"'
    ) in foreign_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in foreign_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' not in foreign_choice.text
    assert 'data-testid="home-returning-actions"' in foreign_home.text
    assert 'data-testid="home-empty-show-all-link"' in foreign_home.text
    assert "Other Project Loop" not in foreign_home.text
    assert current_choice.status_code == HTTPStatus.OK
    assert current_home.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' not in current_choice.text
    assert 'data-testid="loop-create-existing-saved-link"' in current_choice.text
    assert f'class="secondary-button" href="/loops/{current_loop["id"]}?workdir={encoded_current}"' in current_choice.text
    assert 'data-existing-action-kind="open_saved_loop"' in current_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in current_choice.text
    assert (
        f'class="primary-button" href="/loops/{current_loop["id"]}?workdir={encoded_current}" '
        'data-testid="home-returning-saved-link"'
    ) in current_home.text
    assert 'data-home-saved-action-kind="open_saved_loop"' in current_home.text
    assert 'data-testid="home-returning-attention-link"' not in current_home.text
    assert 'data-testid="home-returning-recent-link"' not in current_home.text
    assert "Open saved Loop" in current_choice.text
    assert "Open saved Loop" in current_home.text
    assert "Current Project Loop" in current_home.text


def test_create_choice_saved_only_multiple_loops_reviews_saved_loop_library(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    _create_loop(service, sample_spec_file, current_workdir, name="First Saved Loop")
    _create_loop(service, sample_spec_file, current_workdir, name="Second Saved Loop")
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_choice = client.get(f"/loops/new?workdir={encoded_current}")
    current_home = client.get(f"/?workdir={encoded_current}")

    assert current_choice.status_code == HTTPStatus.OK
    assert current_home.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' not in current_choice.text
    assert 'data-testid="loop-create-existing-saved-link"' in current_choice.text
    assert f'class="secondary-button" href="/?workdir={encoded_current}#saved-loops"' in current_choice.text
    assert 'data-existing-action-kind="review_saved_loops"' in current_choice.text
    assert "Review Saved Loops" in current_choice.text
    assert "Open saved Loop" not in current_choice.text
    assert 'class="primary-button" href="#saved-loops" data-testid="home-returning-saved-link"' in current_home.text
    assert 'data-home-saved-action-kind="review_saved_loops"' in current_home.text
    assert "Review Saved Loops" in current_home.text
    assert "Open saved Loop" not in current_home.text


def test_create_choice_single_saved_global_link_preserves_loop_workdir_context(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    loop = _create_loop(service, sample_spec_file, current_workdir, name="Global Saved Loop")
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    global_choice = client.get("/loops/new")
    global_home = client.get("/")

    assert global_choice.status_code == HTTPStatus.OK
    assert global_home.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in global_choice.text
    assert f'class="secondary-button" href="/loops/{loop["id"]}?workdir={encoded_current}"' in global_choice.text
    assert 'data-existing-action-kind="open_saved_loop"' in global_choice.text
    assert f'href="/loops/{loop["id"]}?workdir={encoded_current}" data-testid="home-returning-saved-link"' in global_home.text
    assert 'data-home-saved-action-kind="open_saved_loop"' in global_home.text


def test_create_choice_existing_work_includes_same_target_active_alignment_session(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    current_workdir.mkdir()
    other_workdir.mkdir()
    other_session = service.create_alignment_session(
        workdir=other_workdir,
        message="Other project compose should not count.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(other_session["id"], status="running")
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    foreign_choice = client.get(f"/loops/new?workdir={encoded_current}")
    current_session = service.create_alignment_session(
        workdir=current_workdir,
        message="Current project compose should count as existing work.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(current_session["id"], status="running")
    current_choice = client.get(f"/loops/new?workdir={encoded_current}")

    assert foreign_choice.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="empty"' in foreign_choice.text
    assert 'data-testid="loop-create-existing-show-all-link"' in foreign_choice.text
    assert (
        'href="/" data-existing-action-kind="view_all_work" '
        'data-testid="loop-create-existing-show-all-link"'
    ) in foreign_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in foreign_choice.text
    assert current_choice.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' in current_choice.text
    assert (
        f'href="/loops/new/bundle?alignment_session_id={current_session["id"]}&amp;workdir={encoded_current}"'
        in current_choice.text
    )
    assert 'data-existing-action-kind="resume_alignment_session"' in current_choice.text
    assert "Resume chat" in current_choice.text
    assert 'data-testid="loop-create-existing-saved-link"' not in current_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in current_choice.text


def test_create_choice_existing_work_links_directly_to_primary_active_loop(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    loop = _create_loop(service, sample_spec_file, current_workdir, name="Evidence Gap Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nCoverage still needs direct evidence.",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Coverage still needs direct evidence.",
        },
    )
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_choice = client.get(f"/loops/new?workdir={encoded_current}")

    assert current_choice.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' in current_choice.text
    assert f'href="/runs/{run["id"]}?workdir={encoded_current}"' in current_choice.text
    assert 'href="/#activity' not in current_choice.text
    assert 'data-existing-action-kind="continue_evidence"' in current_choice.text
    assert "Continue evidence" in current_choice.text
    assert f'class="ghost-button" href="/loops/{loop["id"]}?workdir={encoded_current}"' in current_choice.text
    assert 'data-testid="loop-create-existing-saved-link"' in current_choice.text
    assert 'data-existing-action-kind="open_saved_loop"' in current_choice.text
    assert "Open saved Loop" in current_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in current_choice.text


def test_create_choice_existing_work_surfaces_ready_alignment_candidate(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    imported_session = service.create_alignment_session(
        workdir=current_workdir,
        message="Imported READY candidate should no longer need attention.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        imported_session["id"],
        status="ready",
        linked_bundle_id="bundle_imported",
    )
    ready_session = service.create_alignment_session(
        workdir=current_workdir,
        message="READY candidate should remain reviewable.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(ready_session["id"], status="ready")
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_choice = client.get(f"/loops/new?workdir={encoded_current}")

    assert current_choice.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' in current_choice.text
    assert (
        f'href="/loops/new/bundle?alignment_session_id={ready_session["id"]}&amp;workdir={encoded_current}"'
        in current_choice.text
    )
    assert 'data-existing-action-kind="review_alignment_bundle"' in current_choice.text
    assert "Review and create Loop" in current_choice.text
    assert "Continue Web Conversation" not in current_choice.text
    assert imported_session["id"] not in current_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in current_choice.text


def test_create_choice_existing_work_labels_recent_terminal_runs_without_attention(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    loop = _create_loop(service, sample_spec_file, current_workdir, name="Completed Evidence Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nEvidence passed.",
        task_verdict={"status": "passed", "source": "gatekeeper", "summary": "Evidence passed."},
    )
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_choice = client.get(f"/loops/new?workdir={encoded_current}")

    assert current_choice.status_code == HTTPStatus.OK
    assert 'data-existing-work-state="available"' in current_choice.text
    assert 'data-testid="loop-create-existing-attention-link"' in current_choice.text
    assert 'data-testid="loop-create-existing-saved-link"' in current_choice.text
    assert f'href="/runs/{run["id"]}?workdir={encoded_current}"' in current_choice.text
    assert f'class="ghost-button" href="/loops/{loop["id"]}?workdir={encoded_current}"' in current_choice.text
    assert 'href="/#activity' not in current_choice.text
    assert 'data-existing-action-kind="review_recent_activity"' in current_choice.text
    assert 'data-existing-action-kind="open_saved_loop"' in current_choice.text
    assert "Recent Activity" in current_choice.text
    assert "Open saved Loop" in current_choice.text
    assert "Needs Attention" not in current_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in current_choice.text


def test_manual_loop_form_submits_custom_command_execution_settings(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/loops/new/manual",
        data={
            "name": "Manual Custom Command Loop",
            "spec_path": str(sample_spec_file),
            "workdir": str(sample_workdir),
            "orchestration_id": "builtin:build_first",
            "completion_mode": "rounds",
            "executor_kind": "custom",
            "executor_mode": "command",
            "command_cli": "local-wrapper",
            "command_args_text": "--output\n{output_path}\n{prompt}\n",
            "model": "",
            "reasoning_effort": "",
            "iteration_interval_seconds": "0",
            "max_iters": "3",
            "max_role_retries": "1",
            "delta_threshold": "0.005",
            "trigger_window": "2",
            "regression_window": "2",
        },
        follow_redirects=False,
    )

    assert response.status_code == HTTPStatus.SEE_OTHER
    created = [item for item in service.list_loops() if item["name"] == "Manual Custom Command Loop"]
    assert len(created) == 1
    assert created[0]["executor_kind"] == "custom"
    assert created[0]["executor_mode"] == "command"
    assert created[0]["command_cli"] == "local-wrapper"
    assert "{output_path}" in created[0]["command_args_text"]


def test_loop_create_executor_modes_use_real_browser_form_fields() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js").read_text(encoding="utf-8")
    alignment_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(fragment in template for fragment in (
        'data-testid="manual-execution-settings-panel"',
        'name="executor_kind"',
        'name="executor_mode"',
        'type="radio"',
        'data-testid="manual-mode-preset-input"',
        'data-testid="manual-mode-command-input"',
        'name="command_cli"',
        'name="command_args_text"',
        'name="model"',
        'name="reasoning_effort"',
    ))
    assert all(fragment in page_script for fragment in (
        "executor_kind: String(formData.get(\"executor_kind\")",
        "executor_mode: executionCommandMode ? \"command\" : \"preset\"",
        "command_cli: executionCommandMode ? String(formData.get(\"command_cli\")",
        "command_args_text: executionCommandMode ? String(formData.get(\"command_args_text\")",
        "draft.executor_mode = manualCommandMode() ? \"command\" : \"preset\"",
        "element.type === \"radio\"",
        "syncManualExecutionControls({preserveUserModel: true, preserveUserReasoning: true})",
    ))
    assert all(fragment in template for fragment in (
        'name="alignment_executor_mode"',
        'form="alignment-start-form"',
        'data-testid="alignment-mode-preset-input"',
        'data-testid="alignment-mode-command-input"',
    ))
    assert 'id="alignment-executor-mode" name="alignment_executor_mode"' not in template
    assert all(fragment in alignment_script for fragment in (
        "panel.querySelectorAll(\"input[name='alignment_executor_mode']\")",
        "function selectedExecutorMode()",
        "function setExecutorMode(nextMode)",
        "input.focus({preventScroll: true})",
        'setAlignmentMode(input.value || chip.dataset.alignmentModeChoice || "preset")',
        "setExecutorMode(profile.command_only ? \"command\" : nextMode)",
    ))


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


def test_api_round_loop_explicit_strategy_source_owns_orchestration_identity(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    client = loop_creation_client(service_factory)

    preset_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Explicit Preset API Loop",
            orchestration_id="builtin:build_first",
            strategy_source={"preset": "inspect_first"},
            completion_mode="rounds",
        ),
    )

    assert preset_response.status_code == HTTPStatus.CREATED
    preset_loop = preset_response.json()["loop"]
    assert preset_loop["workflow_json"]["preset"] == "inspect_first"
    assert preset_loop["orchestration_id"] == "builtin:inspect_first"

    custom_workflow = loop_creation_workflow(steps=[loop_creation_step("custom_builder_step", "builder")])
    custom_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            sample_spec_file,
            sample_workdir,
            name="Explicit Custom API Loop",
            orchestration_id="builtin:inspect_first",
            workflow=custom_workflow,
            completion_mode="rounds",
        ),
    )

    assert custom_response.status_code == HTTPStatus.CREATED
    custom_loop = custom_response.json()["loop"]
    assert custom_loop["workflow_json"]["steps"][0]["id"] == "custom_builder_step"
    assert custom_loop["orchestration_id"] == ""

    preset_recovery_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            tmp_path / "missing-inline-preset-spec.md",
            sample_workdir,
            name="Inline Preset Missing Spec Loop",
            orchestration_id="builtin:build_first",
            strategy_source={"preset": "inspect_first"},
            completion_mode="rounds",
        ),
    )
    assert preset_recovery_response.status_code == HTTPStatus.BAD_REQUEST
    preset_command = preset_recovery_response.json()["next_actions"][0]["command"]
    assert "--strategy-preset inspect_first" in preset_command
    assert "--orchestration-id" not in preset_command

    custom_recovery_response = client.post(
        "/api/loops",
        json=loop_creation_payload(
            tmp_path / "missing-inline-custom-spec.md",
            sample_workdir,
            name="Inline Custom Missing Spec Loop",
            orchestration_id="builtin:inspect_first",
            workflow=custom_workflow,
            completion_mode="rounds",
        ),
    )
    assert custom_recovery_response.status_code == HTTPStatus.BAD_REQUEST
    assert [item["kind"] for item in custom_recovery_response.json()["next_actions"]] == [
        "choose_spec",
        "retry_web_compose",
    ]
    assert "loopora spec init" not in custom_recovery_response.text


def test_manual_round_loop_spec_recovery_uses_effective_strategy_source(
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    client = TestClient(build_app(service=service_factory(scenario="success")))

    preset_response = client.post(
        "/loops/new/manual",
        data={
            "name": "Manual Inline Preset Loop",
            "workdir": str(sample_workdir),
            "spec_path": str(tmp_path / "missing-manual-preset-spec.md"),
            "orchestration_id": "builtin:build_first",
            "strategy_json": json.dumps({"preset": "inspect_first"}),
            "completion_mode": "rounds",
        },
    )

    assert preset_response.status_code == HTTPStatus.OK
    assert "--strategy-preset inspect_first" in preset_response.text
    assert "--orchestration-id" not in preset_response.text

    custom_workflow = loop_creation_workflow(steps=[loop_creation_step("custom_builder_step", "builder")])
    custom_response = client.post(
        "/loops/new/manual",
        data={
            "name": "Manual Inline Custom Loop",
            "workdir": str(sample_workdir),
            "spec_path": str(tmp_path / "missing-manual-custom-spec.md"),
            "orchestration_id": "builtin:inspect_first",
            "workflow_json": json.dumps(custom_workflow),
            "completion_mode": "rounds",
        },
    )

    assert custom_response.status_code == HTTPStatus.OK
    assert 'data-recovery-action-kind="choose_spec"' in custom_response.text
    assert 'data-recovery-action-kind="retry_web_compose"' in custom_response.text
    assert "loopora spec init" not in custom_response.text


def test_api_loop_creation_projects_path_normalization_failures_as_compose_recovery(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    workdir = tmp_path / "project"
    workdir.mkdir()
    cases = [
        (
            loop_creation_payload(
                sample_spec_file,
                workdir,
                name="Bad Workdir API Loop",
                workdir="bad\0workdir",
            ),
            "target_workdir_unavailable",
            "blocked_by_workdir",
            "workdir_state",
            "workdir",
            ["choose_workdir", "retry_web_compose", "confirm_readiness"],
        ),
        (
            loop_creation_payload(
                sample_spec_file,
                workdir,
                name="Bad Spec API Loop",
                spec_path="bad\0spec.md",
            ),
            "target_spec_unavailable",
            "blocked_by_spec",
            "spec_state",
            "spec_path",
            ["choose_spec", "retry_web_compose"],
        ),
    ]

    for request_payload, recovery_kind, status, state_key, path_key, action_kinds in cases:
        response = client.post("/api/loops", json=request_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert payload["loop_recovery"] == recovery_kind
        assert payload["status"] == status
        assert payload[path_key] == ""
        assert payload[state_key]["status"] == "unavailable"
        assert payload[state_key]["error"].endswith("could not be inspected")
        summary_key = "web_workdir_recovery_summary" if state_key == "workdir_state" else "web_spec_recovery_summary"
        status_key = "workdir_state_status" if state_key == "workdir_state" else "spec_state_status"
        _assert_recovery_summary_actions(
            payload,
            summary_key=summary_key,
            state_key=status_key,
            state="unavailable",
            expected=action_kinds,
        )
        assert all("command" not in item for item in payload["next_actions"])
        encoded = json.dumps(payload, ensure_ascii=False)
        assert "embedded null" not in encoded
        assert str(Path.cwd()) not in encoded

    assert service.list_loops() == []


def test_manual_loop_form_projects_path_normalization_failures_as_recovery(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    cases = [
        (
            {
                "name": "Bad Workdir Manual Loop",
                "spec_path": str(sample_spec_file),
                "workdir": "bad\0workdir",
            },
            ["choose_workdir", "confirm_readiness", "retry_web_compose"],
            "Target project directory cannot be inspected",
        ),
        (
            {
                "name": "Bad Spec Manual Loop",
                "spec_path": "bad\0spec.md",
                "workdir": str(sample_workdir),
            },
            ["choose_spec", "retry_web_compose"],
            "Spec path cannot be inspected",
        ),
    ]

    for data, action_kinds, summary in cases:
        response = client.post("/loops/new/manual", data=data)

        assert response.status_code == HTTPStatus.OK
        assert summary in response.text
        for kind in action_kinds:
            assert f'data-recovery-action-kind="{kind}"' in response.text
        assert "data-recovery-command-copy" not in response.text
        assert "embedded null" not in response.text
        assert str(Path.cwd()) not in response.text

    assert service.list_loops() == []
