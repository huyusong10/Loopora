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


def test_alignment_improvement_readiness_requires_task_scoped_refactor_delta_for_directional_critique() -> None:
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {"source_completion_mode": "gatekeeper"},
        },
        "transcript": [{"role": "user", "content": "这份 Loop 太保守，不够重构，帮我改激进一点。"}],
    }
    output = {
        "agreement_summary": "保留来源 Loop 的稳定意图，只基于用户反馈调整证据、角色和 workflow 治理面。",
        "readiness_evidence": {
            "task_scope": "保留来源 bundle 的用户目标、workdir 和 executor 默认值，只在反馈指向的治理面内调整。",
            "execution_strategy": "先保留稳定意图，再修复反馈证明薄弱的证据、角色、workflow 或 GateKeeper 面。",
            "role_posture": "保留 Builder 谨慎，调整 Inspector 责任，并让 GateKeeper 继续严格裁决。",
        },
    }

    issues = alignment_improvement_readiness_issues(session, output)

    assert "improvement_refactor_delta" in issues


def test_alignment_improvement_readiness_accepts_task_scoped_refactor_delta_for_directional_critique() -> None:
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {"source_completion_mode": "gatekeeper"},
        },
        "transcript": [{"role": "user", "content": "这份 Loop 太保守，不够重构，帮我改激进一点。"}],
    }
    output = {
        "agreement_summary": (
            "保留来源 Loop 的稳定用户行为和 workdir，只允许任务范围内的重构 delta；"
            "如果复杂度只是换地方、用户行为回归或证据路径仍无法复验，GateKeeper 必须阻断。"
        ),
        "readiness_evidence": {
            "task_scope": "保留来源 bundle 的用户目标、workdir 和 executor 默认值，只改变任务边界内的重构风险。",
            "execution_strategy": "先锁定可维护性证据，再调整 roles/workflow，让复杂度、行为回归和证据路径脆弱性提前暴露。",
            "role_posture": "Inspector 验证重构证据、复杂度没有只是换地方，并确认用户行为没有回归。",
        },
    }

    issues = alignment_improvement_readiness_issues(session, output)

    assert "improvement_refactor_delta" not in issues


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
