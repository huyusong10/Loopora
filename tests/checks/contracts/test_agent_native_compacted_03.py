from __future__ import annotations

# Merged from test_agent_native_step_view_paths.py
from loopora.agent_native_step_view_paths import (
    agent_native_step_contract_path_text,
    agent_native_step_view_artifact_path_texts,
    agent_native_step_view_path_text,
)


def test_agent_native_step_view_paths_prefer_split_contract_fields() -> None:
    step_view = {
        "agent_step_view_path": "steps/agent_step_view.json",
        "agent_step_view_absolute_path": "/runs/steps/agent_step_view.json",
        "step_contract_path": "steps/step_contract.json",
        "step_contract_absolute_path": "/runs/steps/step_contract.json",
    }

    assert agent_native_step_view_path_text(step_view) == "steps/agent_step_view.json"
    assert agent_native_step_view_path_text(step_view, absolute=True) == "/runs/steps/agent_step_view.json"
    assert agent_native_step_contract_path_text(step_view) == "steps/step_contract.json"
    assert agent_native_step_contract_path_text(step_view, absolute=True) == "/runs/steps/step_contract.json"


def test_agent_native_step_view_paths_do_not_fallback_to_legacy_capsule_fields() -> None:
    step_view = {"capsule_path": "steps/capsule.json", "capsule_absolute_path": "/runs/steps/capsule.json"}

    assert agent_native_step_view_path_text(step_view) == ""
    assert agent_native_step_contract_path_text(step_view) == ""
    assert agent_native_step_contract_path_text(step_view, absolute=True) == ""


def test_agent_native_step_view_artifact_paths_are_unique_and_write_split_paths_first() -> None:
    step_view = {
        "agent_step_view_absolute_path": "/runs/steps/agent_step_view.json",
        "agent_step_view_path": "steps/agent_step_view.json",
        "step_contract_absolute_path": "/runs/steps/step_contract.json",
    }

    assert agent_native_step_view_artifact_path_texts(step_view) == [
        "/runs/steps/agent_step_view.json",
        "/runs/steps/step_contract.json",
    ]

# Merged from test_agent_native_step_view_request.py
from loopora.agent_native_step_view import AgentNativeStepViewRequest, agent_native_step_view
from loopora.run_artifacts import RunArtifactLayout


def test_agent_native_step_view_request_consumes_step_instruction_context(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "workspace" / ".loopora" / "runs" / "run_agent_step_view")
    layout.initialize()
    step_context = {
        "iteration": {
            "coverage_status": "blocked",
            "evidence_progress_mode": "stalled",
            "target_count": 2,
            "covered_check_count": 1,
            "missing_check_count": 1,
            "missing_check_ids": ["check_002"],
            "coverage_top_gaps": [{"target_id": "done_when.check_002"}],
        },
        "evidence": {"known_ids": ["ev_000_00_builder_step"], "items": [{"id": "ev_000_00_builder_step"}]},
    }

    step_view = agent_native_step_view(
        AgentNativeStepViewRequest(
            adapter="codex",
            run={"id": "run_agent_step_view"},
            layout=layout,
            iter_id=0,
            step={"id": "builder_step", "action_policy": {}},
            step_order=0,
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
            runtime_role="builder",
            prompt="Build the smallest proof.",
            output_schema={"type": "object"},
            known_evidence_ids=["ev_000_00_builder_step"],
            step_instruction_context=step_context,
        )
    )

    assert step_view["required_coverage"]["status"] == "blocked"
    assert step_view["required_coverage"]["missing_check_ids"] == ["check_002"]
    assert step_view["known_evidence_refs"][0]["id"] == "ev_000_00_builder_step"

# Merged from test_agent_native_submit_boundaries.py
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    AgentNativeStepSubmitRequest,
    Path,
    RunArtifactLayout,  # noqa: F811 - compacted test keeps source-local import binding.
    _agent_native_host_dispatch,
    _agent_native_step_output,
    alignment_bundle_yaml,
    json,
)


def test_agent_native_submit_uses_active_step_order_zero_before_state_cursor(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Keep first-step submit artifacts anchored to the claimed active step.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["active_step"]["step_order"] == 0
    state["step_index"] = 7
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_step_output(step),
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    expected_output = layout.step_output_raw_path(0, 0, str(step["step_id"]))
    wrong_cursor_output = layout.step_output_raw_path(0, 7, str(step["step_id"]))
    assert result["submitted_step"]["iter"] == 0
    assert result["submitted_step"]["step_order"] == 0
    assert expected_output.exists()
    assert not wrong_cursor_output.exists()

# Merged from test_agent_native_submit_boundaries_architecture.py
from agent_native_contract_architecture_support import (
    assert_design_mentions,
    assert_markers_owned_by,
    design_contracts_source,
    loopora_source,
)


def test_agent_native_host_dispatch_validation_has_dedicated_boundary() -> None:
    submit_service_source = loopora_source("service_agent_native_submit.py")
    submit_validation_source = loopora_source("agent_native_submit_validation.py")
    host_dispatch_source = loopora_source("agent_native_host_dispatch_validation.py")

    assert "from loopora.agent_native_host_dispatch_validation import validate_agent_native_host_dispatch" in submit_service_source
    assert "from loopora.agent_native_host_dispatch_validation import" in submit_validation_source
    assert_markers_owned_by(
        host_dispatch_source,
        [submit_validation_source],
        "def validate_agent_native_host_dispatch",
        "def _agent_native_role_dispatch_for_submit",
        "def _agent_native_dispatch_trace",
        "def _agent_native_dispatch_position",
    )
    assert "agent_native_accepted_native_tools" in host_dispatch_source
    assert "agent_native_accepted_native_tools" not in submit_validation_source
    assert_design_mentions(design_contracts_source(), "agent_native_host_dispatch_validation.py")


def test_agent_native_submit_hints_have_dedicated_boundary() -> None:
    contracts_source = loopora_source("service_agent_native_contracts.py")
    hints_source = loopora_source("agent_native_submit_hints.py")
    step_view_source = loopora_source("agent_native_step_view.py")
    refresh_source = loopora_source("agent_native_step_view_refresh.py")

    assert "from loopora.agent_native_submit_hints import agent_native_result_artifact_stem" in step_view_source
    assert "from loopora.agent_native_submit_hints import" in refresh_source
    assert_markers_owned_by(
        hints_source,
        [contracts_source],
        "def agent_native_submit_command",
        "def agent_native_result_artifact_stem",
        "def agent_native_submit_hint_with_scoped_result_paths",
        "def _agent_native_command_workdir_arg",
    )
    assert_design_mentions(design_contracts_source(), "agent_native_submit_hints.py")

# Merged from test_agent_native_submit_contract.py
from compacted_agent_native_support import (
    assert_agent_native_submit_rejected,
    invalid_agent_native_submit_outputs,
    prepare_agent_native_submit_reject_context,
)


def test_agent_native_submit_rejects_read_only_workspace_claims_and_schema_mismatches(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    context = prepare_agent_native_submit_reject_context(service_factory, tmp_path, sample_workdir)

    for output, expected_error in invalid_agent_native_submit_outputs(context):
        assert_agent_native_submit_rejected(context, output, expected_error)

# Merged from test_agent_native_submitted_coverage_results.py
from agent_adapter_test_support import (
    _drive_agent_native_until_archetype,
)


def test_agent_native_submitted_step_exposes_coverage_results(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Ship the focused starter experience with explicit evidence classifications. "
                "Execution strategy: Inspector coverage_results must show exactly which target changed. "
                "Fake done risk: do not pass with only a handoff summary and no target evidence."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(
        service,
        result,
        adapter="codex",
        workdir=sample_workdir,
        archetype="inspector",
    )
    step = result["next_step"]

    inspector_output = _agent_native_step_output(step)
    inspector_output["coverage_results"] = [
        {
            "target_id": "done_when.check_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "Inspector verified the Builder proof against the first Done When target.",
        }
    ]

    submitted = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=inspector_output,
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert submitted["submitted_step"]["coverage_results"] == [
        {
            "target_id": "done_when.check_001",
            "status": "covered",
            "evidence_refs": ["ev_000_00_builder_step"],
            "note": "Inspector verified the Builder proof against the first Done When target.",
        }
    ]

# Merged from test_agent_native_terminal_unproven_continuation.py
from compacted_agent_native_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    assert_agent_entry_start_continuation,
    assert_continue_evidence_task_next_action,
    assert_continuation_step_artifacts,
    assert_continued_terminal_unproven_run,
    assert_observation_snapshot_continuation,
    assert_task_verdict_artifact_matches,
    assert_terminal_unproven_recovery_choice,
    complete_terminal_unproven_agent_run,
)


def test_agent_native_gatekeeper_pass_with_missing_required_coverage_keeps_task_verdict_insufficient(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    fixture = complete_terminal_unproven_agent_run(service_factory, tmp_path, sample_workdir)

    run = fixture.run
    task_verdict = run["task_verdict"]
    assert run["status"] == "succeeded"
    assert run["last_verdict_json"]["passed"] is True
    assert task_verdict["status"] == "insufficient_evidence"
    assert task_verdict["source"] == "gatekeeper"
    assert "Required coverage" in task_verdict["summary"]
    assert_continue_evidence_task_next_action(fixture.final)
    assert_agent_entry_start_continuation(fixture.service, run)
    assert_task_verdict_artifact_matches(run)


def test_agent_loop_restarts_after_terminal_insufficient_evidence(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    fixture = complete_terminal_unproven_agent_run(service_factory, tmp_path, sample_workdir)
    service = fixture.service
    previous_run = fixture.run

    recovery = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    choice = recovery["choices"][0]
    assert recovery["action"] == "choose_recoverable_context"
    assert_terminal_unproven_recovery_choice(choice, previous_run)

    continued = service.start_agent_loop(
        "codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False
    )

    assert_continued_terminal_unproven_run(service, fixture.started, continued, previous_run)
    assert_continuation_step_artifacts(continued, previous_run)
    assert_observation_snapshot_continuation(service, continued, previous_run)


def test_agent_continuation_focus_reads_bucket_labels_and_reasons(service_factory) -> None:
    service = service_factory(scenario="success")

    focus = service._agent_native_continuation_focus(
        {
            "buckets": {
                "blocking": [{"label": "Permission audit is missing."}],
                "weak": [{"reason": "Residual risk lacks an owner."}],
            }
        },
        {"top_gaps": [{"target_id": "done_when.audit", "text": "Audit command has no output."}]},
    )

    assert "Permission audit is missing." in focus
    assert "Residual risk lacks an owner." in focus
    assert "done_when.audit: Audit command has no output." in focus

# Merged from test_agent_native_web_import_headless_guard.py
from pathlib import Path  # noqa: F811 - compacted test keeps source-local import binding.

import pytest

from agent_adapter_test_support import LooporaConflictError


def test_web_import_cannot_headless_start_agent_first_preview(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    with pytest.raises(LooporaConflictError, match="agent-first Loop previews must be started from /loopora-run"):
        service.import_alignment_bundle(generated["session"]["id"], start_immediately=True, execute_async=True)

    blocked_session = service.get_alignment_session(generated["session"]["id"])
    assert blocked_session["status"] == "ready"
    assert not blocked_session.get("linked_run_id")
    assert service.list_bundles() == []

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        entry_source="codex_project_skill",
        execute_async=True,
    )

    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert started["next_step"]["execution_plane"] == "agent_native"
    assert (Path(started["run"]["runs_dir"]) / "agent_native" / "state.json").exists()

# Merged from test_agent_native_workflow_control_after_window.py
from agent_adapter_test_support import (
    Path,  # noqa: F811 - compacted test keeps source-local import binding.
    _agent_native_rejected_gatekeeper_output,
    _alignment_bundle_yaml_with_gatekeeper_control,
)


def test_agent_native_workflow_control_skip_records_after_not_elapsed_event(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_gatekeeper_control(sample_workdir, after="1h"), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Skip an agent-native GateKeeper rejection control before its after window elapses.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    result = _drive_agent_native_until_archetype(service, result, adapter="codex", workdir=sample_workdir, archetype="gatekeeper")
    step = result["next_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(step["run_id"]),
            step_id=str(step["step_id"]),
            output=_agent_native_rejected_gatekeeper_output(step),
            host_dispatch=_agent_native_host_dispatch("codex", step),
            entry_source="codex_project_skill",
        )
    )

    assert result["complete"] is False
    assert result["next_step"]["step_id"] == "builder_step"
    events = service.stream_events(str(result["run"]["id"]), limit=300)

    assert not any(event["event_type"] == "agent_native_controls_deferred" for event in events)
    assert not any(event["event_type"] == "control_triggered" for event in events)
    assert not any(event["event_type"] == "control_completed" for event in events)
    assert any(
        event["event_type"] == "control_skipped"
        and event["payload"]["signal"] == "gatekeeper_rejected"
        and event["payload"]["control_id"] == "gatekeeper_repair"
        and event["payload"]["skip_reason"] == "after_not_elapsed"
        for event in events
    )
