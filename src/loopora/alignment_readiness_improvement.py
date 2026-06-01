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
