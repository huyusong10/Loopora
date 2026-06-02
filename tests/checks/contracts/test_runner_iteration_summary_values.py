from __future__ import annotations

from pathlib import Path

from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary
from loopora.run_artifacts import RunArtifactLayout
from loopora.runner_support_requests import RunnerSummaryRequest
from loopora.service_runner_support import ServiceRunnerSupportMixin
from loopora.stagnation import StagnationUpdateRequest, update_stagnation


def test_workflow_summary_requires_literal_gatekeeper_passed_boolean(tmp_path: Path) -> None:
    class RunnerSupportHarness(ServiceRunnerSupportMixin):
        @staticmethod
        def _truncate_text(value: str | None, max_length: int = 220) -> str:
            return str(value or "")[:max_length]

    service = RunnerSupportHarness()
    gatekeeper_step_result = {
        "step": {"id": "gatekeeper_step"},
        "step_order": 0,
        "role": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        "runtime_role": "verifier",
        "output": {
            "passed": "true",
            "decision_summary": "String pass must remain blocked in summary projections.",
            "composite_score": 1.0,
            "evidence_refs": [],
        },
    }

    entry = service._build_runner_iteration_entry(
        0,
        [gatekeeper_step_result],
        {"stagnation_mode": "none"},
        previous_composite=None,
    )
    summary = service._build_runner_summary(
        RunnerSummaryRequest(
            run={"workdir": str(tmp_path), "completion_mode": "gatekeeper", "iteration_interval_seconds": 0.0},
            strategy_source={"preset": "custom"},
            compiled_spec={"checks": [], "check_mode": "specified"},
            iter_id=0,
            step_results=[gatekeeper_step_result],
            stagnation={"stagnation_mode": "none"},
            exhausted=False,
            previous_composite=None,
        )
    )

    assert entry["score"]["passed"] is False
    assert "- Passed: `False`" in summary
    assert "- Strategy preset: `custom`" in summary
    assert "Still iterating." in summary
    assert "All checks passed in this iteration." not in summary
    assert "- Workflow preset:" not in summary


def test_iteration_summaries_require_literal_score_numbers(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    gatekeeper_step_result = {
        "step": {"id": "gatekeeper_step"},
        "step_order": 0,
        "role": {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper"},
        "runtime_role": "verifier",
        "output": {
            "passed": False,
            "decision_summary": "String scores should not enter iteration context.",
            "composite_score": "0.95",
            "evidence_refs": [],
        },
        "handoff": {"status": "failed", "source": {"step_order": 0, "step_id": "gatekeeper_step"}},
    }
    stagnation = {
        "stagnation_mode": "plateau",
        "recent_composites": ["0.7", 0.8, True],
        "recent_deltas": ["0.1", 0.2, False],
        "consecutive_low_delta": "2",
    }
    service = ServiceRunnerSupportMixin()

    legacy_entry = service._build_runner_iteration_entry(
        0,
        [gatekeeper_step_result],
        stagnation,
        previous_composite=0.4,
    )
    summary = build_iteration_summary(
        IterationSummaryContext(
            layout=layout,
            iter_id=0,
            step_results=[gatekeeper_step_result],
            stagnation=stagnation,
            previous_composite=0.4,
            timestamp="2026-01-01T00:00:00Z",
        )
    )

    assert legacy_entry["score"]["composite"] is None
    assert legacy_entry["score"]["delta"] is None
    assert legacy_entry["stagnation"]["recent_composites"] == [0.8]
    assert legacy_entry["stagnation"]["recent_deltas"] == [0.2]
    assert legacy_entry["stagnation"]["consecutive_low_delta"] == 0
    assert summary["score"]["composite"] is None
    assert summary["score"]["delta"] is None
    assert summary["stagnation"]["recent_composites"] == [0.8]
    assert summary["stagnation"]["recent_deltas"] == [0.2]
    assert summary["stagnation"]["consecutive_low_delta"] == 0


def test_stagnation_update_requires_literal_score_history() -> None:
    stagnation = update_stagnation(
        StagnationUpdateRequest(
            stagnation={
                "recent_composites": ["0.7", 0.8, True],
                "recent_deltas": ["0.1", 0.2, False],
            },
            composite=0.81,
            current_iter=1,
            delta_threshold=0.05,
            trigger_window=2,
            regression_window=2,
        )
    )

    assert stagnation["recent_composites"] == [0.8, 0.81]
    assert stagnation["recent_deltas"] == [0.2, 0.01]
    assert stagnation["consecutive_low_delta"] == 1
    assert stagnation["stagnation_mode"] == "none"
