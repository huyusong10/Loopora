from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import _traceability_projection, build_bundle_control_summary
from loopora.service_bundle_control_trace_mining import build_execution_strategy_trace


MAX_PROJECTED_JUDGMENT_TRADEOFFS = 4


def test_execution_strategy_trace_accepts_priority_language() -> None:
    traces = build_execution_strategy_trace(
        collaboration_summary=(
            "Execution priorities: focused implementation, permission proof, audit repair, "
            "and only later UI polish."
        )
    )

    assert any("Execution priorities" in item for item in traces)


def test_bundle_control_summary_projects_strict_vs_pragmatic_tradeoff() -> None:
    traceability = _traceability_projection(
        {
            "bundle": {
                "collaboration_summary": "Strict blocking beats pragmatic progress when evidence is weak.",
            },
            "raw_sections": {"Task": "Do the work.", "Evidence Preferences": "Collect evidence."},
            "roles": [{"name": "Builder", "archetype": "builder", "posture_notes": "Build the slice."}],
            "strategy_source": {"collaboration_intent": "Builder then GateKeeper."},
            "strategy_flow_projection": {"summary": "Builder -> GateKeeper"},
            "gatekeeper": {"enabled": True, "roles": ["GateKeeper"], "finish_steps": ["gatekeeper_step"]},
            "controls": [],
        }
    )

    tradeoff_item = next(item for item in traceability["items"] if item["key"] == "judgment_tradeoffs")
    assert tradeoff_item["mapped"] is True
    assert tradeoff_item["evidence"] == ["Strict blocking beats pragmatic progress when evidence is weak."]
    assert "judgment_tradeoffs" not in traceability["missing"]


def test_bundle_control_summary_prioritizes_task_specific_tradeoffs(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] += "\n\nTradeoff: strict blocking beats pragmatic progress when evidence is weak."

    summary = build_bundle_control_summary(bundle)

    assert any("strict blocking beats pragmatic progress" in item for item in summary["judgment_tradeoffs"])
    assert len(summary["judgment_tradeoffs"]) <= MAX_PROJECTED_JUDGMENT_TRADEOFFS


def test_bundle_control_summary_does_not_invent_tradeoff_projection() -> None:
    traceability = _traceability_projection(
        {
            "bundle": {"collaboration_summary": "Use the available plan surfaces."},
            "raw_sections": {"Task": "Do the work.", "Evidence Preferences": "Collect evidence."},
            "roles": [{"name": "Builder", "archetype": "builder", "posture_notes": "Build the slice."}],
            "strategy_source": {"collaboration_intent": "Builder then GateKeeper."},
            "strategy_flow_projection": {"summary": "Builder -> GateKeeper"},
            "gatekeeper": {"enabled": True, "roles": ["GateKeeper"], "finish_steps": ["gatekeeper_step"]},
            "controls": [],
        }
    )

    tradeoff_item = next(item for item in traceability["items"] if item["key"] == "judgment_tradeoffs")
    assert tradeoff_item["mapped"] is False
    assert "judgment_tradeoffs" in traceability["missing"]
