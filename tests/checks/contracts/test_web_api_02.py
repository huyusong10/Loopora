from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from loopora.run_observation_events import PROGRESS_EVENT_TYPES, TIMELINE_EVENT_TYPES
from loopora.run_artifacts import RunArtifactLayout
from loopora.run_takeaways import (
    build_evidence_manifest,
    build_legacy_iteration_takeaway,
    build_role_takeaway_from_handoff,
    display_iter,
    normalize_run_takeaway_projection_shape,
)
from loopora.web import build_app


def test_takeaway_evidence_manifest_does_not_promote_boolean_manifest_counts(tmp_path: Path) -> None:
    runs_dir = tmp_path / "run"
    layout = RunArtifactLayout(runs_dir)
    layout.initialize()
    layout.evidence_manifest_path.write_text(
        json.dumps(
            {
                "manifest_path": True,
                "claim_count": True,
                "artifact_backed_claim_count": "1",
                "direct_proof_claim_count": 2,
                "problems": [
                    {"code": True, "claim_id": 7, "severity": False, "message": 3},
                    {"code": "missing_artifact", "claim_id": "ev_001", "severity": "warning", "message": "Proof file is missing."},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = build_evidence_manifest({"runs_dir": str(runs_dir)})

    assert manifest["claim_count"] == 0
    assert manifest["artifact_backed_claim_count"] == 0
    assert manifest["direct_proof_claim_count"] == 2
    assert manifest["manifest_path"] == "evidence/manifest.json"
    assert manifest["problem_count"] == 2
    assert manifest["problems"][0] == {"code": "", "claim_id": "", "severity": "", "message": ""}
    assert manifest["problems"][1] == {
        "code": "missing_artifact",
        "claim_id": "ev_001",
        "severity": "warning",
        "message": "Proof file is missing.",
    }

def test_takeaway_projection_normalization_does_not_promote_boolean_counts() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_projection_counts", "status": "succeeded", "run_status": "succeeded"},
        {
            "source_event_id": True,
            "evidence_count": True,
            "evidence_coverage": {
                "ledger_path": True,
                "coverage_path": True,
                "status": True,
                "evidence_count": True,
                "covered_check_count": "1",
                "missing_check_count": 2,
                "covered_check_ids": "check_001",
                "missing_check_ids": ["check_002", True],
                "risk_signals": [False, "manual review"],
            },
            "evidence_manifest": {
                "claim_count": True,
                "artifact_backed_claim_count": "1",
                "direct_proof_claim_count": 2,
                "problem_count": True,
            },
            "judgment_contract": {
                "contract_path": True,
                "source_bundle": {
                    "id": "bundle_projection",
                    "name": "Projection Bundle",
                    "bundle_sha256": "abc123",
                    "bundle_bytes": 42,
                    "bundle_yaml_path": "/tmp/loopora/bundle_projection.yml",
                },
                "collaboration_summary": True,
                "loop_fit_reasons": [False, "Future rounds keep proof alive."],
                "goal": "  Keep the frozen task visible.  ",
                "workflow_collaboration_intent": 8,
                "execution_strategy": [False, "Prove the focused path first."],
                "local_governance": [False, "GateKeeper treats skipped AGENTS.md evidence as Blocking."],
                "role_postures": [
                    {
                        "role_name": "Builder",
                        "archetype": "builder",
                        "posture_notes": "Keep the change narrow and verifiable.",
                    },
                    False,
                ],
                "judgment_tradeoffs": [False, "Prefer proof before polish."],
                "success_surface": ["Stable surface", True],
                "fake_done_states": [False, "Only the happy path"],
                "evidence_preferences": ["Proof artifact", 3],
                "residual_risk": "  Minor copy polish.  ",
            },
            "iteration_count": True,
            "role_conclusion_count": "1",
            "latest_display_iter": True,
        },
    )

    assert projection["source_event_id"] == 0
    assert projection["evidence_count"] == 0
    assert projection["evidence_coverage"]["ledger_path"] == ""
    assert projection["evidence_coverage"]["coverage_path"] == ""
    assert projection["evidence_coverage"]["status"] == "pending"
    assert projection["evidence_coverage"]["evidence_count"] == 0
    assert projection["evidence_coverage"]["covered_check_count"] == 0
    assert projection["evidence_coverage"]["missing_check_count"] == 2
    assert projection["evidence_coverage"]["covered_check_ids"] == []
    assert projection["evidence_coverage"]["missing_check_ids"] == ["check_002"]
    assert projection["evidence_coverage"]["risk_signals"] == ["manual review"]
    assert projection["evidence_manifest"]["claim_count"] == 0
    assert projection["evidence_manifest"]["artifact_backed_claim_count"] == 0
    assert projection["evidence_manifest"]["direct_proof_claim_count"] == 2
    assert projection["evidence_manifest"]["problem_count"] == 0
    assert projection["judgment_contract"]["contract_path"] == ""
    assert projection["judgment_contract"]["source_bundle"]["id"] == "bundle_projection"
    assert projection["judgment_contract"]["source_bundle"]["bundle_sha256"] == "abc123"
    assert projection["judgment_contract"]["source_bundle"]["bundle_bytes"] == 42
    assert projection["judgment_contract"]["source_bundle"]["bundle_yaml_path"] == "/tmp/loopora/bundle_projection.yml"
    assert projection["judgment_contract"]["collaboration_summary"] == ""
    assert projection["judgment_contract"]["loop_fit_reasons"] == ["Future rounds keep proof alive."]
    assert projection["judgment_contract"]["goal"] == "Keep the frozen task visible."
    assert projection["judgment_contract"]["check_mode"] == ""
    assert projection["judgment_contract"]["check_count"] == 0
    assert projection["judgment_contract"]["completion_mode"] == ""
    assert projection["judgment_contract"]["strategy_preset"] == ""
    assert projection["judgment_contract"]["strategy_collaboration_intent"] == ""
    assert projection["judgment_contract"]["workflow_preset"] == ""
    assert projection["judgment_contract"]["workflow_collaboration_intent"] == ""
    assert projection["judgment_contract"]["execution_strategy"] == ["Prove the focused path first."]
    assert projection["judgment_contract"]["local_governance"] == ["GateKeeper treats skipped AGENTS.md evidence as Blocking."]
    assert projection["judgment_contract"]["role_postures"] == ["Builder: Keep the change narrow and verifiable."]
    assert projection["judgment_contract"]["judgment_tradeoffs"] == ["Prefer proof before polish."]
    assert projection["judgment_contract"]["coverage_targets"] == []
    assert projection["judgment_contract"]["success_surface"] == ["Stable surface"]
    assert projection["judgment_contract"]["fake_done_states"] == ["Only the happy path"]
    assert projection["judgment_contract"]["evidence_preferences"] == ["Proof artifact"]
    assert projection["judgment_contract"]["residual_risk"] == "Minor copy polish."
    assert projection["iteration_count"] == 0
    assert projection["role_conclusion_count"] == 0
    assert projection["latest_display_iter"] is None

def test_takeaway_projection_normalizes_task_verdict_bucket_shapes() -> None:
    projection = normalize_run_takeaway_projection_shape(
        {"id": "run_projection_buckets", "status": "failed", "run_status": "failed"},
        {
            "task_verdict": {
                "status": "failed",
                "source": "gatekeeper",
                "summary": "Stored projection should keep stable bucket entries.",
                "buckets": {
                    "blocking": [True, "real blocker", {"label": "structured blocker"}],
                    "residual_risk": [False],
                },
            },
            "evidence_buckets": {
                "residual_risk": [False, "manual risk"],
                "unknown": ["not a stable bucket"],
            },
        },
    )

    assert projection["task_verdict"]["buckets"]["blocking"] == [
        {"label": "real blocker"},
        {"label": "structured blocker"},
    ]
    assert projection["task_verdict"]["buckets"]["residual_risk"] == []
    assert projection["evidence_buckets"] == {"residual_risk": [{"label": "manual risk"}]}

@pytest.mark.parametrize("iter_value", [True, "2", 1.5])
def test_takeaway_display_iter_requires_integer_sequence(iter_value) -> None:
    assert display_iter(iter_value) is None

    iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_run",
            "status": "succeeded",
            "current_iter": iter_value,
            "summary_md": "# Loopora Run Summary\n\nLegacy run completed.",
        }
    )

    assert iteration is not None
    assert iteration["iter"] == 0
    assert iteration["display_iter"] == 1

def test_takeaway_role_source_and_legacy_failure_fields_require_literal_values() -> None:
    role = build_role_takeaway_from_handoff(
        {
            "source": {
                "iter": "4",
                "step_order": "8",
                "step_id": "builder_step",
                "runtime_role": "generator",
            },
            "status": "passed",
            "summary": "done",
            "blocking_items": ["real blocker", True],
            "evidence_refs": ["ev_001", False],
        }
    )

    assert role["id"].startswith("iter-0-")
    assert role["step_order"] == 0
    assert role["blocking_item"] == "real blocker"
    assert role["evidence_refs"] == ["ev_001"]

    malformed_role = build_role_takeaway_from_handoff(
        {
            "source": {"iter": 0, "step_order": 1, "step_id": "bad_shape"},
            "status": "blocked",
            "summary": True,
            "recommended_next_action": 7,
            "blocking_items": "string blocker",
            "evidence_refs": "ev_bad",
        }
    )

    assert malformed_role["summary"] == ""
    assert malformed_role["next_action"] == ""
    assert malformed_role["blocking_item"] == ""
    assert malformed_role["evidence_refs"] == []

    malformed_identity_role = build_role_takeaway_from_handoff(
        {
            "source": {
                "iter": 0,
                "step_order": 0,
                "step_id": True,
                "role_name": True,
                "runtime_role": True,
                "archetype": True,
            },
            "status": "passed",
            "summary": "done",
        }
    )

    assert malformed_identity_role["role_name"] == "-"
    assert malformed_identity_role["step_id"] == ""
    assert malformed_identity_role["archetype"] == ""
    assert "True" not in malformed_identity_role["id"]

    legacy_gatekeeper_iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_blocker",
            "status": "failed",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {
                "passed": False,
                "blocking_issues": "full blocker",
                "hard_constraint_violations": [True, "hard blocker"],
            },
        }
    )

    assert legacy_gatekeeper_iteration is not None
    assert legacy_gatekeeper_iteration["roles"][0]["blocking_item"] == "full blocker"

    iteration = build_legacy_iteration_takeaway(
        {
            "id": "legacy_run",
            "status": "failed",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {
                "passed": False,
                "priority_failures": [
                    {
                        "role": "generator",
                        "error_code": "provider_failed",
                        "attempts": "2",
                        "degraded": "false",
                    }
                ],
            },
        }
    )

    assert iteration is not None
    blocking_item = iteration["roles"][0]["blocking_item"]
    assert "provider_failed" in blocking_item
    assert "attempts=2" not in blocking_item
    assert "degraded" not in blocking_item

def test_api_run_observation_snapshot_is_bounded_and_redacted(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Snapshot Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])

    for index in range(45):
        service.repository.append_event(
            run["id"],
            "run_finished",
            {"status": "succeeded", "reason": f"snapshot timeline {index}", "iter": index},
        )
    for index in range(2050):
        service.repository.append_event(
            run["id"],
            "role_started",
            {"role": "generator", "step_id": "builder_step", "iter": index},
            role="generator",
        )
    marker = "UNIQUE-SNAPSHOT-SECRET-MARKER"
    redacted_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {
            "type": "command",
            "message": "uv run pytest -q",
            "prompt": marker,
            "json_schema": {"marker": marker},
        },
        role="generator",
    )

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["run"]["id"] == run["id"]
    assert payload["latest_event_id"] == redacted_event["id"]
    assert len(payload["timeline_events"]) == 40
    assert len(payload["console_events"]) == 160
    assert len(payload["progress_events"]) == 2000
    assert payload["key_takeaways"]["run_status"] == "succeeded"
    assert 0 < payload["key_takeaways"]["source_event_id"] <= payload["latest_event_id"]
    assert marker not in json.dumps(payload, ensure_ascii=False)

    html_response = client.get(f"/runs/{run['id']}")
    assert html_response.status_code == 200
    assert marker not in html_response.text
    timeline_text = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    assert marker not in timeline_text
    assert "uv run pytest -q" in json.dumps(payload["console_events"], ensure_ascii=False)

def test_api_run_observation_snapshot_projects_stable_timeline_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Parallel Snapshot Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    service.repository.append_event(
        run["id"],
        "role_request_prepared",
        {"role_name": "Builder", "role": "builder", "step_id": "build", "iter": 0},
        role="builder",
    )
    payload = {
        "iter": 0,
        "parallel_group": "inspection_pack",
        "step_orders": [1, 2],
        "step_ids": ["inspect_a", "inspect_b"],
    }
    service.repository.append_event(run["id"], "parallel_group_started", payload)
    service.repository.append_event(run["id"], "parallel_group_finished", payload)
    service.repository.append_event(
        run["id"],
        "control_triggered",
        {"signal": "gatekeeper_rejected", "role_id": "guide", "reason": "needs repair"},
    )
    service.repository.append_event(
        run["id"],
        "run_finished",
        {"status": "succeeded", "reason": "legacy_terminal_event_without_verdict"},
    )

    assert "role_request_prepared" in TIMELINE_EVENT_TYPES
    assert "control_triggered" in TIMELINE_EVENT_TYPES
    assert "parallel_group_started" in TIMELINE_EVENT_TYPES
    assert "run_finished" in TIMELINE_EVENT_TYPES
    assert "parallel_group_started" in PROGRESS_EVENT_TYPES
    assert "run_finished" in PROGRESS_EVENT_TYPES
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == 200
    snapshot = response.json()
    timeline_events = [event for event in snapshot["timeline_events"] if event["event_type"].startswith("parallel_group_")]
    timeline_event_by_type = {event["event_type"]: event for event in snapshot["timeline_events"]}
    progress_types = [event["event_type"] for event in snapshot["progress_events"]]
    assert timeline_event_by_type["role_request_prepared"]["title"] == "Role request prepared"
    assert timeline_event_by_type["control_triggered"]["title"] == "Control triggered"
    assert [event["event_type"] for event in timeline_events] == ["parallel_group_started", "parallel_group_finished"]
    assert timeline_events[0]["title"] == "Parallel review started"
    assert timeline_events[0]["detail"] == "inspection_pack, steps=2"
    assert timeline_event_by_type["run_finished"]["detail"] == (
        "legacy_terminal_event_without_verdict, task_verdict_status=not_evaluated"
    )
    assert "parallel_group_started" in progress_types
    assert "parallel_group_finished" in progress_types
    assert "run_finished" in progress_types

def test_api_run_observation_snapshot_uses_persisted_takeaway_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Snapshot Projection Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    marker = "LIVE-ARTIFACT-UPDATE-AFTER-PROJECTION"
    handoff_path = next(Path(run["runs_dir"]).glob("iterations/iter_*/steps/*/handoff.json"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["summary"] = marker
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
    late_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "late non-projection event"},
        role="generator",
    )

    client = TestClient(build_app(service=service))
    snapshot_response = client.get(f"/api/runs/{run['id']}/observation-snapshot")
    live_response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["latest_event_id"] == late_event["id"]
    assert snapshot_payload["key_takeaways"]["source_event_id"] < snapshot_payload["latest_event_id"]
    assert marker not in json.dumps(snapshot_payload["key_takeaways"], ensure_ascii=False)
    assert live_response.status_code == 200
    assert marker in json.dumps(live_response.json(), ensure_ascii=False)

def test_api_run_observation_snapshot_normalizes_legacy_takeaway_projection_shape(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Legacy Snapshot Projection Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    legacy_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "legacy projection cutoff"},
        role="generator",
    )
    service.repository.record_run_takeaway_projection(
        run["id"],
        legacy_event["id"],
        {
            "run_status": "succeeded",
            "task_verdict": {"status": "passed", "source": "gatekeeper", "summary": "legacy shape", "buckets": {}},
            "iterations": [],
        },
    )

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == 200
    key_takeaways = response.json()["key_takeaways"]
    assert key_takeaways["source_event_id"] == legacy_event["id"]
    assert key_takeaways["task_verdict_path"] == ""
    assert key_takeaways["evidence_buckets"] == {}
    assert key_takeaways["evidence_coverage"]["status"] == "pending"
    assert key_takeaways["evidence_coverage"]["coverage_path"] == ""
    assert key_takeaways["evidence_manifest"]["manifest_path"] == ""
    assert key_takeaways["evidence_manifest"]["claim_count"] == 0
    assert key_takeaways["evidence_count"] == 0

@pytest.mark.parametrize("event_type", ("control_completed", "control_failed"))
def test_control_events_refresh_persisted_takeaway_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    event_type: str,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Control Projection Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    handoff_path = next(Path(run["runs_dir"]).glob("iterations/iter_*/steps/*/handoff.json"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    control_marker = f"{event_type}-snapshot-marker"
    later_marker = f"{event_type}-later-marker"
    handoff["summary"] = control_marker
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
    control_event = service.append_run_event(
        run["id"],
        event_type,
        {"control_id": "audit_control", "signal": "no_evidence_progress", "evidence_refs": []},
    )
    handoff["summary"] = later_marker
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False), encoding="utf-8")
    late_event = service.repository.append_event(
        run["id"],
        "codex_event",
        {"type": "stdout", "message": "late non-projection event"},
        role="generator",
    )

    client = TestClient(build_app(service=service))
    response = client.get(f"/api/runs/{run['id']}/observation-snapshot")

    assert response.status_code == 200
    payload = response.json()
    key_takeaways_text = json.dumps(payload["key_takeaways"], ensure_ascii=False)
    assert payload["latest_event_id"] == late_event["id"]
    assert payload["key_takeaways"]["source_event_id"] == control_event["id"]
    assert control_marker in key_takeaways_text
    assert later_marker not in key_takeaways_text

def test_run_takeaway_projection_backfills_existing_terminal_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Snapshot Backfill Loop",
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
    with service.repository.transaction() as connection:
        connection.execute("DELETE FROM run_takeaway_projections WHERE run_id = ?", (run["id"],))

    restarted = service.__class__(
        repository=service.repository,
        settings=service.settings,
        executor_factory=service.executor_factory,
    )
    snapshot = restarted.run_observation_snapshot(run["id"])

    assert 0 < snapshot["key_takeaways"]["source_event_id"] <= snapshot["latest_event_id"]
    assert snapshot["key_takeaways"]["iteration_count"] >= 1

def test_run_takeaway_projection_backfills_terminal_runs_with_only_generic_events(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Minimal Snapshot Backfill Loop",
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
    latest_event_id = service.repository.latest_event_id(run["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nLifecycle closed before any role takeaway event was written.\n",
    )
    with service.repository.transaction() as connection:
        connection.execute("DELETE FROM workdir_locks WHERE run_id = ?", (run["id"],))
        connection.execute("DELETE FROM run_takeaway_projections WHERE run_id = ?", (run["id"],))

    restarted = service.__class__(
        repository=service.repository,
        settings=service.settings,
        executor_factory=service.executor_factory,
    )
    snapshot = restarted.run_observation_snapshot(run["id"])

    assert snapshot["latest_event_id"] == latest_event_id
    assert snapshot["key_takeaways"]["source_event_id"] == latest_event_id
    assert snapshot["key_takeaways"]["run_status"] == "succeeded"
    assert snapshot["key_takeaways"]["iteration_count"] == 0
    assert "Lifecycle closed before any role takeaway event" in snapshot["key_takeaways"]["latest_summary"]
