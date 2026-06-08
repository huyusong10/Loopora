from __future__ import annotations

from loopora.alignment_readiness_shared import ALIGNMENT_READINESS_EVIDENCE_KEYS, has_any_marker


def alignment_improvement_readiness_issues(session: dict, output: dict) -> list[str]:
    previous_agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if str(previous_agreement.get("mode") or "") != "improvement":
        return []
    evidence = output.get("readiness_evidence") if isinstance(output.get("readiness_evidence"), dict) else {}
    combined = " ".join(
        [
            str(output.get("agreement_summary", "") or ""),
            *(str(evidence.get(key, "") or "") for key in ALIGNMENT_READINESS_EVIDENCE_KEYS),
        ]
    ).lower()
    issues: list[str] = []
    if not has_any_marker(
        combined,
        (
            "preserve",
            "keep",
            "stable",
            "unchanged",
            "existing intent",
            "保留",
            "保持",
            "稳定",
            "不变",
            "既有意图",
        ),
    ):
        issues.append("improvement_preservation")
    if not has_any_marker(
        combined,
        (
            "change",
            "revise",
            "improve",
            "adjust",
            "feedback-driven",
            "source feedback",
            "user feedback",
            "review feedback",
            "run feedback",
            "feedback shows",
            "feedback proves",
            "evidence gap",
            "改进",
            "修订",
            "调整",
            "反馈驱动",
            "来源反馈",
            "用户反馈",
            "评审反馈",
            "运行反馈",
            "反馈证明",
            "证据缺口",
        ),
    ):
        issues.append("improvement_delta")
    if not has_any_marker(
        combined,
        (
            "spec",
            "role",
            "workflow",
            "evidence",
            "gatekeeper",
            "surface",
            "roles",
            "证据",
            "角色",
            "裁决",
            "治理面",
        ),
    ):
        issues.append("improvement_surface")
    if improvement_refactor_delta_issue(session, combined):
        issues.append("improvement_refactor_delta")
    source = previous_agreement.get("source") if isinstance(previous_agreement.get("source"), dict) else {}
    has_run_context = str(source.get("source_type") or "") == "run" and (
        source.get("coverage_summary") or source.get("evidence_summary") or source.get("task_verdict") or source.get("gatekeeper_verdict")
    )
    if has_run_context and not has_any_marker(
        combined,
        (
            "run evidence",
            "coverage",
            "verdict",
            "gatekeeper verdict",
            "evidence summary",
            "运行证据",
            "覆盖",
            "裁决",
            "证据摘要",
        ),
    ):
        issues.append("run_evidence_translation")
    source_completion_mode = str(source.get("source_completion_mode") or "").strip().lower()
    if source_completion_mode and source_completion_mode != "gatekeeper":
        has_source_completion_mode_delta = has_any_marker(
            combined,
            (
                "completion mode",
                "completion_mode",
                "`rounds`",
                "rounds completion",
                "source uses rounds",
                "run lifecycle",
                "lifecycle completion",
                "source completion",
                "完成模式",
                "运行生命周期",
                "生命周期收束",
            ),
        ) and has_any_marker(
            combined,
            (
                "gatekeeper",
                "task verdict",
                "evidence-based verdict",
                "证据裁决",
                "loop 裁决",
                "任务裁决",
                "守门",
            ),
        )
        if not has_source_completion_mode_delta:
            issues.append("improvement_completion_mode_delta")
    return issues


def improvement_refactor_delta_issue(session: dict, combined_output_text: str) -> bool:
    feedback = _improvement_user_feedback_text(session).lower()
    if not has_any_marker(
        feedback,
        (
            "too conservative",
            "not enough refactor",
            "not refactor-heavy",
            "be more aggressive",
            "more aggressive",
            "aggressive refactor",
            "太保守",
            "不够重构",
            "更激进",
            "激进一点",
            "大刀阔斧",
        ),
    ):
        return False
    has_refactor_frame = has_any_marker(
        combined_output_text,
        (
            "task-scoped refactor",
            "refactor delta",
            "refactor risk",
            "refactor evidence",
            "重构 delta",
            "重构风险",
            "重构证据",
            "任务边界",
            "任务范围内的重构",
        ),
    )
    has_refactor_evidence_or_blocker = has_any_marker(
        combined_output_text,
        (
            "complexity only moved",
            "complexity moved elsewhere",
            "maintainability",
            "public behavior regressed",
            "behavior regressed",
            "evidence path",
            "regression",
            "complexity",
            "复杂度只是换地方",
            "复杂度",
            "可维护",
            "用户行为回归",
            "行为回归",
            "证据路径",
            "无法复验",
            "回归",
        ),
    )
    return not (has_refactor_frame and has_refactor_evidence_or_blocker)


def _improvement_user_feedback_text(session: dict) -> str:
    transcript = session.get("transcript") if isinstance(session.get("transcript"), list) else []
    return " ".join(
        str(item.get("content") or "")
        for item in transcript
        if isinstance(item, dict) and str(item.get("role") or "").strip() == "user"
    )
