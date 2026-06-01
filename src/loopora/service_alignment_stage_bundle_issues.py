from __future__ import annotations

"""Generated-bundle issue selection for alignment output staging."""

from loopora.alignment_readiness_rules import (
    has_any_marker,
    workdir_facts_claims_unsupported_observed_stack,
)
from loopora.service_alignment_traceability_projection import alignment_bundle_visible_text


def alignment_bundle_workdir_fact_issues(bundle: dict, *, workdir_snapshot: str) -> list[str]:
    fields: dict[str, object] = {
        "collaboration_summary": bundle.get("collaboration_summary"),
        "spec.markdown": (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        "workflow.collaboration_intent": (
            (bundle.get("workflow") or {}).get("collaboration_intent")
            if isinstance(bundle.get("workflow"), dict)
            else ""
        ),
    }
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        for field_name in ("description", "prompt_markdown", "posture_notes"):
            fields[f"role_definition {key}.{field_name}"] = role.get(field_name)
    return [
        f"bundle field {field_name} must not claim an observed workdir stack unsupported by Workdir Snapshot"
        for field_name, value in fields.items()
        if workdir_facts_claims_unsupported_observed_stack(
            str(value or "").lower(),
            workdir_snapshot=workdir_snapshot,
        )
    ]


def alignment_improvement_bundle_issues(working_agreement: object, bundle: dict) -> list[str]:
    agreement = working_agreement if isinstance(working_agreement, dict) else {}
    if str(agreement.get("mode") or "") != "improvement":
        return []
    text = alignment_bundle_visible_text(bundle).lower()
    issues: list[str] = []
    if not has_any_marker(
        text,
        (
            "source intent",
            "source loop",
            "source bundle",
            "source workdir",
            "source defaults",
            "source posture",
            "stable intent",
            "stable task intent",
            "existing loop",
            "existing bundle",
            "base candidate",
            "既有意图",
            "来源 loop",
            "来源 bundle",
            "来源意图",
            "稳定意图",
            "原 bundle",
        ),
    ):
        issues.append("improvement bundle must state what source intent, workdir, defaults, or posture is preserved")
    if not has_any_marker(
        text,
        (
            "feedback-driven",
            "feedback",
            "run evidence",
            "evidence summary",
            "evidence gap",
            "gatekeeper verdict",
            "coverage",
            "delta",
            "反馈驱动",
            "反馈",
            "运行证据",
            "证据摘要",
            "证据缺口",
            "变化",
        ),
    ):
        issues.append("improvement bundle must state the feedback-driven governance delta")
    if not has_any_marker(
        text,
        (
            "spec",
            "role",
            "roles",
            "workflow",
            "evidence",
            "gatekeeper",
            "证据",
            "角色",
            "裁决",
            "治理面",
            "任务契约",
        ),
    ):
        issues.append("improvement bundle must map the delta to spec, roles, workflow, evidence, or GateKeeper")
    source = agreement.get("source") if isinstance(agreement.get("source"), dict) else {}
    source_bundle_id = str(source.get("source_bundle_id") or "").strip()
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    generated_bundle_id = str(metadata.get("bundle_id") or "").strip()
    if source_bundle_id and generated_bundle_id == source_bundle_id:
        issues.append(
            "improvement bundle must not reuse the source bundle id as metadata.bundle_id; "
            "leave bundle_id empty or choose a new standalone candidate id"
        )
    has_run_context = str(source.get("source_type") or "") == "run" and (
        source.get("coverage_summary")
        or source.get("evidence_summary")
        or source.get("task_verdict")
        or source.get("gatekeeper_verdict")
    )
    if has_run_context and not has_any_marker(
        text,
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
        issues.append("improvement bundle must translate run evidence, coverage, or GateKeeper verdict into bundle changes")
    source_completion_mode = str(source.get("source_completion_mode") or "").strip().lower()
    if source_completion_mode and source_completion_mode != "gatekeeper":
        has_source_completion_mode_delta = has_any_marker(
            text,
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
            text,
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
            issues.append("improvement bundle must state the source completion-mode governance delta")
    return issues
