from pathlib import Path

from loopora.alignment_readiness_rules import alignment_improvement_readiness_issues
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_stage import alignment_improvement_bundle_issues


def test_alignment_improvement_bundle_requires_completion_mode_delta_for_rounds_source(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] = (
        "Preserve the source Loop stable intent, source workdir, and useful source posture while applying "
        "a feedback-driven governance delta that maps to spec, roles, workflow, evidence expectations, "
        "and GateKeeper strictness."
    )
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert "improvement bundle must state the source completion-mode governance delta" in issues


def test_alignment_improvement_bundle_accepts_loop_verdict_marker_for_completion_mode_delta() -> None:
    bundle = {
        "metadata": {},
        "collaboration_summary": (
            "保留来源 Loop 的稳定意图；基于反馈变化，新的方案把 rounds completion mode 的"
            "运行生命周期与 Loop 裁决分开，并把证据放回治理面。"
        ),
        "loop": {},
        "spec": {},
        "workflow": {},
        "role_definitions": [],
    }
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert "improvement bundle must state the source completion-mode governance delta" not in issues


def test_alignment_improvement_readiness_accepts_loop_verdict_marker_for_completion_mode_delta() -> None:
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_completion_mode": "rounds",
            },
        },
    }
    output = {
        "agreement_summary": (
            "保留既有意图，基于反馈调整治理面；原完成模式是 rounds，新的运行生命周期"
            "与 Loop 裁决分开。"
        ),
        "readiness_evidence": {},
    }

    issues = alignment_improvement_readiness_issues(session, output)

    assert "improvement_completion_mode_delta" not in issues


def test_alignment_improvement_bundle_rejects_reusing_source_bundle_id(
    sample_workdir: Path,
) -> None:
    source_bundle_id = "bundle_source"
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["metadata"]["bundle_id"] = source_bundle_id
    bundle["collaboration_summary"] = (
        "Preserve the source Loop stable intent, source workdir, and useful source posture while applying "
        "a feedback-driven governance delta that maps to spec, roles, workflow, evidence expectations, "
        "and GateKeeper strictness."
    )
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_bundle_id": source_bundle_id,
                "source_completion_mode": "gatekeeper",
            },
        },
    }

    issues = alignment_improvement_bundle_issues(session["working_agreement"], bundle)

    assert (
        "improvement bundle must not reuse the source bundle id as metadata.bundle_id; leave bundle_id empty or choose a new standalone candidate id"
    ) in issues
