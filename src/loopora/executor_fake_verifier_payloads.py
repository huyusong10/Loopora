from __future__ import annotations

"""Fake GateKeeper, Guide, and Custom role payloads."""

from loopora.runtime_task_language import runtime_task_text
from loopora.step_instruction_context import step_instruction_context_from_mapping


def fake_verifier_payload(
    scenario: str,
    iter_id: int,
    request,
    check_count: int,
    *,
    display_language: str = "en",
) -> dict:
    tester_output = (
        request.extra_context.get("inspector_output")
        or request.extra_context.get("tester_output")
        or {
            "execution_summary": {"total_checks": check_count, "passed": 0},
            "check_results": [],
        }
    )
    total_checks = max(tester_output["execution_summary"]["total_checks"], 1)
    passed_checks = tester_output["execution_summary"]["passed"]
    composite = 0.62 if scenario == "plateau" and iter_id < 2 else 0.621 if scenario == "plateau" else round(min(0.45 + iter_id * 0.25, 1.0), 3)
    failed_check_ids = [check["id"] for check in tester_output["check_results"] if check.get("status") != "passed"]
    check_pass_rate = round(passed_checks / total_checks, 3)
    passed = composite >= 0.9 and not failed_check_ids
    evidence_refs = _evidence_refs(request)
    evidence_claims = _fake_gatekeeper_evidence_claims(
        passed=passed,
        evidence_refs=evidence_refs,
        failed_check_ids=failed_check_ids,
        display_language=display_language,
    )
    return {
        "passed": passed,
        "decision_summary": runtime_task_text(
            display_language,
            (
                "Task verdict passes from upstream evidence refs; the run lifecycle alone is not proof."
                if passed
                else "Task verdict is not ready because Weak, Unproven, or Blocking evidence remains."
            ),
            ("任务裁决依据上游证据引用通过；仅有 Run 生命周期成功并不构成证明。" if passed else "任务裁决尚未就绪，因为仍有 Weak、Unproven 或 Blocking 证据。"),
        ),
        "composite_score": composite,
        "metrics": [
            {
                "name": "check_pass_rate",
                "value": check_pass_rate,
                "threshold": 0.9,
                "passed": check_pass_rate >= 0.9,
            },
            {
                "name": "quality_score",
                "value": composite,
                "threshold": 0.9,
                "passed": composite >= 0.9,
            },
        ],
        "metric_scores": {
            "check_pass_rate": {
                "value": check_pass_rate,
                "threshold": 0.9,
                "passed": check_pass_rate >= 0.9,
            },
            "quality_score": {
                "value": composite,
                "threshold": 0.9,
                "passed": composite >= 0.9,
            },
        },
        "blocking_issues": [],
        "hard_constraint_violations": [],
        "failed_check_ids": failed_check_ids,
        "priority_failures": [],
        "feedback_to_builder": runtime_task_text(
            display_language,
            "Repair the smallest Blocking or Unproven gap without lowering the frozen contract.",
            "在不降低冻结契约的前提下，修复最小的 Blocking 或 Unproven 缺口。",
        ),
        "feedback_to_generator": runtime_task_text(
            display_language,
            "Repair the smallest Blocking or Unproven gap without lowering the frozen contract.",
            "在不降低冻结契约的前提下，修复最小的 Blocking 或 Unproven 缺口。",
        ),
        "evidence_refs": evidence_refs if passed else [],
        "evidence_claims": evidence_claims,
        "residual_risks": [],
        "coverage_results": [],
    }


def fake_challenger_payload(iter_id: int, request, *, display_language: str = "en") -> dict:
    return {
        "created_at_iter": iter_id,
        "mode": request.extra_context.get("stagnation_mode", "plateau"),
        "consumed": False,
        "analysis": {
            "stagnation_pattern": runtime_task_text(
                display_language,
                "fake executor detected stalled gains with Weak or Unproven evidence.",
                "模拟 executor 检测到改进停滞，且证据仍处于 Weak 或 Unproven。",
            ),
            "recommended_shift": runtime_task_text(
                display_language,
                "Try the smallest repair or proof that turns one Blocking or Unproven gap into Proven evidence.",
                "尝试最小修复或证明，将一项 Blocking 或 Unproven 缺口转为 Proven 证据。",
            ),
            "risk_note": runtime_task_text(
                display_language,
                "Changing direction too broadly may hide Residual risk or silently lower the frozen contract.",
                "过度扩大方向调整可能掩盖 Residual risk，或无声降低冻结契约。",
            ),
        },
        "seed_question": runtime_task_text(
            display_language,
            "What is the smallest testable change that breaks the plateau?",
            "打破停滞所需的最小可测试改动是什么？",
        ),
        "meta_note": runtime_task_text(display_language, "This is a suggestion, not a command.", "这是一条建议，不是命令。"),
    }


def fake_custom_payload(*, display_language: str = "en") -> dict:
    return {
        "status": "advisory",
        "summary": runtime_task_text(
            display_language,
            "Collected read-only evidence against the frozen contract and prepared a scoped handoff.",
            "已依据冻结契约收集只读证据，并准备好范围明确的交接。",
        ),
        "blocking_items": [
            runtime_task_text(
                display_language,
                "A restricted role can guide the next move but cannot close the loop alone.",
                "受限角色可以指导下一步，但不能独自结束 Loop。",
            ),
        ],
        "recommended_next_action": runtime_task_text(
            display_language,
            "Use the strongest evidence path for the next change without lowering Done When.",
            "下一次改动应采用最强证据路径，且不得降低 Done When。",
        ),
        "observations": [
            runtime_task_text(
                display_language,
                "The custom role stayed inside the current workspace evidence.",
                "自定义角色始终限定在当前工作区证据内。",
            ),
            runtime_task_text(
                display_language,
                "No write action was claimed from this restricted role.",
                "该受限角色没有声称执行任何写入动作。",
            ),
        ],
        "recommendations": [
            runtime_task_text(
                display_language,
                "Use the strongest evidence path for the next change without lowering Done When.",
                "下一次改动应采用最强证据路径，且不得降低 Done When。",
            ),
        ],
        "risks": [
            runtime_task_text(
                display_language,
                "A restricted role can guide the next move but cannot close the loop alone.",
                "受限角色可以指导下一步，但不能独自结束 Loop。",
            ),
        ],
        "handoff_note": runtime_task_text(
            display_language,
            "Pass these observations to a Builder or Inspector step.",
            "将这些观察结果交给 Builder 或 Inspector 步骤。",
        ),
    }


def _fake_gatekeeper_evidence_claims(
    *,
    passed: bool,
    evidence_refs: list[str],
    failed_check_ids: list[str],
    display_language: str,
) -> list[str]:
    if passed:
        joined_refs = (
            ", ".join(evidence_refs)
            if evidence_refs
            else runtime_task_text(
                display_language,
                "measured gate metrics",
                "可度量的守门指标",
            )
        )
        return [
            runtime_task_text(
                display_language,
                f"Proven: GateKeeper cited upstream evidence refs ({joined_refs}) and kept run status separate from task verdict.",
                f"Proven：GateKeeper 引用了上游证据（{joined_refs}），并保持 Run 状态与任务裁决相互独立。",
            )
        ]
    if failed_check_ids:
        joined_checks = ", ".join(failed_check_ids[:4])
        return [
            runtime_task_text(
                display_language,
                f"Blocking: compiled checks remain unpassed ({joined_checks}), so the task contract cannot be lowered to close the run.",
                f"Blocking：已编译检查仍未通过（{joined_checks}），因此不能通过降低任务契约来结束 Run。",
            )
        ]
    return [
        runtime_task_text(
            display_language,
            "Unproven: quality evidence is still below the GateKeeper threshold.",
            "Unproven：质量证据仍低于 GateKeeper 阈值。",
        )
    ]


def _evidence_refs(request) -> list[str]:
    step_instruction_context = step_instruction_context_from_mapping(request.extra_context)
    evidence_items = []
    if isinstance(step_instruction_context, dict):
        evidence_items = list((step_instruction_context.get("evidence") or {}).get("items") or [])
    return [
        str(item.get("id"))
        for item in evidence_items
        if isinstance(item, dict) and str(item.get("id") or "").strip() and str(item.get("archetype") or "").strip().lower() != "gatekeeper"
    ][-3:]
