from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_AGENT_TEST = REPO_ROOT / "tests" / "probes" / "real_environment" / "test_real_agent_adapter_probe.py"


def _load_real_agent_module():
    spec = importlib.util.spec_from_file_location("real_agent_probe", REAL_AGENT_TEST)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _write_phase_report_fixture(module, tmp_path: Path) -> tuple[dict, Path]:
    workdir = tmp_path / "work"
    workdir.mkdir()
    state_dir = workdir / ".loopora"
    run_id = "run_123"
    run_dir = state_dir / "runs" / run_id
    sentinel_log = tmp_path / "sentinel.log"
    candidate = state_dir / "agent_inbox" / "opencode" / "conversation-candidate.yml"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("version: 1\nmetadata:\n  name: phase report\n", encoding="utf-8")
    _write_json(
        state_dir / "alignment_sessions" / "align_ready" / "artifacts" / "validation.json",
        {"ok": True, "error": "", "semantic_lint": {"ok": True, "issues": []}},
    )
    _write_json(
        state_dir / "agent_adapters" / "opencode" / "bindings" / "ctx.json",
        {
            "adapter": "opencode",
            "alignment_status": "running_loop",
            "linked_bundle_id": "bundle_123",
            "linked_loop_id": "loop_123",
            "linked_run_id": run_id,
            "run_path": f"/runs/{run_id}",
            "execution_plane": "agent_native",
            "entry_invocations": [
                {"action": "plan", "entry_source": "opencode_project_command"},
                {"action": "run", "entry_source": "opencode_project_command"},
            ],
        },
    )
    _write_jsonl(
        run_dir / "events.jsonl",
        [
            {"id": 1, "event_type": "agent_native_step_claimed", "payload": {"step_id": "builder_step"}},
            {"id": 2, "event_type": "agent_native_step_submitted", "payload": {"step_id": "builder_step"}},
            {"id": 3, "event_type": "agent_native_step_claimed", "payload": {"step_id": "gatekeeper_step"}},
            {"id": 4, "event_type": "agent_native_step_submitted", "payload": {"step_id": "gatekeeper_step"}},
            {"id": 5, "event_type": "run_finished", "payload": {"status": "succeeded", "task_verdict_status": "passed"}},
        ],
    )
    _write_json(
        run_dir / "agent_native" / "state.json",
        {
            "status": "completed",
            "host_dispatches": [
                {
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_task",
                    "inline": False,
                    "native_trace": {"tool_call_id": "task_trace_123"},
                }
            ],
        },
    )
    _write_json(run_dir / "evidence" / "coverage.json", {"status": "covered", "covered_check_count": 3, "missing_check_ids": []})
    _write_json(run_dir / "evidence" / "task_verdict.json", {"status": "passed", "source": "gatekeeper", "summary": "passed"})
    _write_json(
        run_dir / "iterations" / "iter_000" / "steps" / "00__builder_step" / "agent_step_view.json",
        {
            "step_id": "builder_step",
            "role_dispatch": {"target_agent": "loopora-builder"},
            "native_todo": {
                "recommended": True,
                "not_evidence": True,
                "items": ["Read agent_work_panel.", "Submit and read agent_v3_envelope.summary."],
            },
        },
    )
    _write_json(
        run_dir / "iterations" / "iter_000" / "steps" / "01__gatekeeper_step" / "output.normalized.json",
        {"passed": True, "evidence_gate_status": "passed", "evidence_refs": ["ev_000_00_builder_step"]},
    )

    report, report_path = module._write_real_probe_phase_report(
        adapter="opencode",
        workdir=workdir,
        activity_snapshots=[
            {"running_count": 1, "queued_count": 0, "runs": [{"id": run_id, "status": "awaiting_agent"}]},
            {
                "runtime_visibility_source": "returned_run_url",
                "returned_run_url_phase": "during_process",
                "running_count": 0,
                "queued_count": 0,
                "runs": [{"id": run_id, "status": "succeeded", "run_path": f"/runs/{run_id}"}],
            },
        ],
        sentinel_log=sentinel_log,
        host_signals=module.PhaseReportHostSignals(
            command='opencode run --api-key AGENT_PHASE_SECRET_MARKER "...prompt..."',
            stdout=(
                "agent_work_panel:\n"
                "question_action: ask one Loop-shaping question in main_agent_session\n"
                "recommended_reply_shape: Goal: ...\n"
                "dispatch_next: invoke loopora-builder with role_dispatch.target_agent\n"
                "auto_repair: submitted result format repaired before submit; Core still blocked evidence_refs_unknown\n"
            ),
            stderr="native_todo not_evidence=true role_dispatch guidance observed\n",
        ),
    )

    return report, report_path


def test_real_agent_phase_report_summarizes_real_probe_milestones(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    report, report_path = _write_phase_report_fixture(module, tmp_path)

    assert report_path == tmp_path / "work" / ".loopora" / "real-probes" / "real-agent-phase-report.json"
    assert report_path.exists()
    phases = report["phase_statuses"]
    assert phases["candidate_file_created"]["ok"] is True
    assert phases["plan_invocation_observed"]["ok"] is True
    assert phases["gen_invocation_observed"]["ok"] is True
    assert phases["ready_validation_observed"]["ok"] is True
    assert phases["run_invocation_observed"]["ok"] is True
    assert phases["loop_invocation_observed"]["ok"] is True
    assert phases["runtime_activity_observed_run"]["ok"] is True
    assert phases["returned_run_url_observed"]["ok"] is True
    assert phases["returned_run_url_observed"]["phase"] == "during_process"
    assert phases["returned_run_url_observed"]["diagnostic_only"] is False
    assert phases["builder_submitted"]["ok"] is True
    assert phases["gatekeeper_submitted"]["ok"] is True
    assert phases["task_verdict_passed"]["ok"] is True
    assert report["diagnostics"]["runtime_visibility_sources"] == [
        {
            "source": "runtime_activity",
            "phase": "",
            "status": "awaiting_agent",
            "active_runtime_activity": True,
        },
        {
            "source": "returned_run_url",
            "phase": "during_process",
            "status": "succeeded",
            "active_runtime_activity": False,
        },
    ]
    assert report["diagnostics"]["task_verdict"]["status"] == "passed"
    assert "--model" not in report["command_preview"]
    assert "--effort" not in report["command_preview"]
    assert "--variant" not in report["command_preview"]
    assert "model_reasoning_effort" not in report["command_preview"]
    assert "AGENT_PHASE_SECRET_MARKER" not in json.dumps(report, ensure_ascii=False)
    assert "--api-key <secret omitted>" in report["command_preview"]
    assert report["model_policy"]["delegates_to_host_default"] is True
    health = report["diagnostics"]["experience_health"]
    assert health["agent_work_panel_seen"] is True
    assert health["agent_work_panel_sources"] == ["host_stdout_tail"]
    assert health["agent_work_panel_artifact_exposed"] is False
    assert health["agent_work_panel_artifact_sources"] == []
    assert health["todo_guidance_seen"] is True
    assert health["todo_not_evidence_confirmed"] is True
    assert health["user_question_guidance_available"] is True
    assert health["role_dispatch_guidance_seen"] is True
    assert health["native_trace_observed"] is True
    assert health["auto_repair_events"] == [
        {
            "source": "host_stdout_tail",
            "line": "auto_repair: submitted result format repaired before submit; Core still blocked evidence_refs_unknown",
        }
    ]
    assert "experience_health_is_review_signal_not_task_proof" in health["experience_notes"]
    assert module._compact_phase_report(report)["experience_health"] == health


def test_real_agent_returned_url_after_exit_is_diagnostic_not_runtime_activity(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    phases = module._phase_statuses(
        module.PhaseStatusInput(
            adapter="opencode",
            workdir=tmp_path,
            binding={"linked_run_id": "run_123", "entry_invocations": []},
            activity_snapshots=[
                {
                    "runtime_visibility_source": "returned_run_url",
                    "returned_run_url_phase": "post_exit_diagnostic_only",
                    "runs": [{"id": "run_123", "status": "succeeded", "run_path": "/runs/run_123"}],
                }
            ],
            events=[],
            validation_summaries=[],
        )
    )

    assert phases["runtime_activity_observed_run"]["ok"] is False
    assert phases["returned_run_url_observed"]["ok"] is True
    assert phases["returned_run_url_observed"]["phase"] == "post_exit_diagnostic_only"
    assert phases["returned_run_url_observed"]["diagnostic_only"] is True


def test_real_agent_terminal_probe_completion_requires_active_runtime_activity() -> None:
    module = _load_real_agent_module()
    report = {
        "phase_statuses": {
            "task_verdict_passed": {"ok": True},
            "runtime_activity_observed_run": {"ok": False},
        },
        "diagnostics": {"experience_health": {"agent_work_panel_seen": True}},
    }
    assert module._phase_report_has_terminal_proof_and_work_panel(report) is False

    report["phase_statuses"]["runtime_activity_observed_run"]["ok"] = True
    assert module._phase_report_has_terminal_proof_and_work_panel(report) is True


def test_real_agent_experience_health_scans_full_output_without_storing_transcript(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    health = module._experience_health_summary(
        workdir=tmp_path,
        run_path=Path(),
        host_stdout="agent_work_panel\n" + ("quiet completion line\n" * 500),
        host_stderr="",
    )

    assert health["agent_work_panel_seen"] is True
    assert health["agent_work_panel_sources"] == ["host_stdout"]
    assert health["agent_work_panel_artifact_exposed"] is False
    assert "quiet completion line" not in json.dumps(health, ensure_ascii=False)


def test_real_agent_experience_health_separates_host_visible_and_artifact_work_panel(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    workdir = tmp_path / "work"
    run_path = workdir / ".loopora" / "runs" / "run_artifact_panel"
    _write_json(
        run_path / "agent_native" / "state.json",
        {
            "last_agent_v3_envelope": {
                "summary": {
                    "agent_work_panel": {
                        "state": "awaiting_agent",
                        "next_action": "Dispatch loopora-builder.",
                    }
                }
            }
        },
    )

    health = module._experience_health_summary(
        workdir=workdir,
        run_path=run_path,
        host_stdout="",
        host_stderr="",
    )

    assert health["agent_work_panel_seen"] is False
    assert health["agent_work_panel_sources"] == []
    assert health["agent_work_panel_artifact_exposed"] is True
    assert health["agent_work_panel_artifact_sources"] == ["run_agent_native_artifact"]
    assert "agent_work_panel_exposed_in_loopora_artifact" in health["experience_notes"]


def test_real_agent_experience_health_reports_missing_work_panel_sources(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    health = module._experience_health_summary(
        workdir=tmp_path / "work",
        run_path=Path(),
        host_stdout="quiet\n",
        host_stderr="",
    )

    assert health["agent_work_panel_seen"] is False
    assert health["agent_work_panel_artifact_exposed"] is False
    assert health["agent_work_panel_artifact_sources"] == []


def test_real_agent_phase_report_requires_plain_passed_task_verdict(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    phases = module._phase_statuses(
        module.PhaseStatusInput(
            adapter="opencode",
            workdir=tmp_path,
            binding={"linked_run_id": "run_123", "entry_invocations": []},
            activity_snapshots=[],
            events=[
                {
                    "event_type": "run_finished",
                    "payload": {"status": "succeeded", "task_verdict_status": "passed_with_residual_risk"},
                }
            ],
            validation_summaries=[],
        )
    )

    assert phases["terminal_run_finished"]["ok"] is True
    assert phases["task_verdict_passed"]["ok"] is False


def test_real_agent_phase_report_formats_compact_failure(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    report = {
        "adapter": "opencode",
        "workdir": str(tmp_path),
        "phase_statuses": {"candidate_file_created": {"ok": False}},
        "diagnostics": {"binding": {}, "alignment_validations": [], "coverage": {}, "task_verdict": {}, "events_tail": [], "sentinel_log": {}},
    }
    message = module._format_real_probe_diagnostic_failure("boom", report=report, report_path=tmp_path / "phase.json")

    assert "boom" in message
    assert "Real probe phase report:" in message
    assert "candidate_file_created" in message


def test_real_agent_host_command_failure_reports_stdout_and_stderr(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    request = module.HostCommandMonitorRequest(
        command="host command",
        adapter="claude",
        workdir=tmp_path,
        env={},
        timeout=1,
        agent_web_url="http://127.0.0.1:1",
        sentinel_log=tmp_path / "sentinel.log",
    )
    completed = module.subprocess.CompletedProcess("host command", 2, "host stdout", "host stderr")

    with pytest.raises(AssertionError) as excinfo:
        module._raise_host_command_failure(request, completed, [])

    message = str(excinfo.value)
    assert "real claude Agent host command exited 2" in message
    assert "host stdout" in message
    assert "host stderr" in message
    assert (tmp_path / ".loopora" / "real-probes" / "real-agent-phase-report.json").exists()


def test_real_agent_external_config_pin_requires_explicit_override(monkeypatch) -> None:
    module = _load_real_agent_module()
    monkeypatch.delenv(module.REAL_PROBE_MODEL_OVERRIDE_ENV, raising=False)

    with pytest.raises(AssertionError):
        module._assert_real_agent_command_model_policy("opencode", "opencode run --model other-model")
    with pytest.raises(AssertionError):
        module._assert_real_agent_command_model_policy("claude", "claude --effort high prompt")
    with pytest.raises(AssertionError):
        module._assert_real_agent_command_model_policy("codex", 'codex exec -c model_reasoning_effort="high" prompt')

    monkeypatch.setenv(module.REAL_PROBE_MODEL_OVERRIDE_ENV, "1")
    module._assert_real_agent_command_model_policy("opencode", "opencode run --model other-model")
    module._assert_real_agent_command_model_policy("claude", "claude --effort high prompt")
    module._assert_real_agent_command_model_policy("codex", 'codex exec -c model_reasoning_effort="high" prompt')


def test_real_agent_prompt_requires_authoring_without_embedded_candidate_yaml(tmp_path: Path) -> None:
    module = _load_real_agent_module()
    executor_script = tmp_path / "release_executor.py"
    executor_script.write_text("print('ok')\n", encoding="utf-8")
    prompt = module._release_probe_prompt("opencode", tmp_path / "candidate.yml", executor_script)

    assert "Use these requirements to author, not copy, the candidate" in prompt
    assert "does not pre-create, prewrite, or embed a complete candidate YAML" in prompt
    assert "execution task, not a planning task" in prompt
    assert "do not return a todo-only response" in prompt
    assert "do not end a response after preparatory commands" in prompt
    assert "a run binding exists" in prompt
    assert "final main-session answer visibly includes a literal `agent_work_panel:` block" in prompt
    assert "agent_work_panel:" in prompt
    assert "Final response format" in prompt
    assert "Your final stdout must include the literal line `agent_work_panel:`" in prompt
    assert "Do not omit the block even when the task verdict passed" in prompt
    assert "verify that" in prompt
    assert "Required bundle structure checklist" in prompt
    assert "`workflow` is the workflow object, not the `loop` object" in prompt
    assert "YAML front matter lines" in prompt
    assert "archetype: builder" in prompt
    assert "archetype: gatekeeper" in prompt
    assert "role_definition_key: release-proof-builder" in prompt
    assert "Do not claim an observed workdir stack" in prompt
    assert "`workflow.collaboration_intent` is required" in prompt
    assert "inputs.evidence_query.archetypes" in prompt
    assert "Do not use unsupported evidence query keys" in prompt
    assert "`# Task`" in prompt
    assert "exactly three top-level bullet items" in prompt
    assert "Extra Done When bullets create uncovered required targets" in prompt
    assert "must contain exactly two top-level bullet items" in prompt
    assert "role_id: builder" in prompt
    assert "Each step object must use an explicit `id`; do not use `key`" in prompt
    assert "BEGIN_LOOPORA_CANDIDATE_YAML" not in prompt
    assert "\nrole_definitions:" not in prompt
    assert "\nworkflow:" not in prompt
