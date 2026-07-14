from __future__ import annotations

"""Fake Builder, Check Planner, and Inspector role payloads."""

from loopora.runtime_task_language import runtime_task_text


def fake_builder_payload(iter_id: int, *, display_language: str = "en") -> dict:
    return {
        "attempted": runtime_task_text(
            display_language,
            f"Iter {iter_id}: refine workdir against the frozen task contract",
            f"第 {iter_id + 1} 轮：依据冻结的任务契约收紧工作区结果",
        ),
        "abandoned": runtime_task_text(
            display_language,
            "Did not widen scope or lower Done When to make the iteration look complete.",
            "没有为了让本轮看起来完成而扩大范围或降低 Done When。",
        ),
        "assumption": runtime_task_text(
            display_language,
            "The highest-impact gain is still the primary path with evidence Inspector can verify.",
            "当前最高价值方向仍是推进主路径，并留下 Inspector 可验证的证据。",
        ),
        "summary": runtime_task_text(
            display_language,
            "Applied a focused change strategy and left the proof surface for Inspector and GateKeeper.",
            "采用了聚焦的改动策略，并为 Inspector 与 GateKeeper 留下可审查证明面。",
        ),
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }


def fake_check_planner_payload(compiled_spec: dict, *, display_language: str = "en") -> dict:
    goal = (compiled_spec.get("goal") or "the prototype").strip()
    if display_language == "zh" and goal == "the prototype":
        goal = "当前原型"
    return {
        "checks": [
            {
                "title": runtime_task_text(display_language, "Goal alignment", "目标对齐"),
                "details": runtime_task_text(
                    display_language,
                    f"When: someone reviews the current prototype against the goal.\n"
                    f"Expect: the main flow clearly moves toward {goal}.\n"
                    "Fail if: the prototype feels unrelated, confusing, or incomplete in its primary direction.",
                    f"当：有人依据目标审查当前原型。\n预期：主流程明确朝 {goal} 推进。\n失败条件：原型与目标脱节、令人困惑，或主方向仍不完整。",
                ),
                "when": runtime_task_text(display_language, "Someone evaluates the prototype as-is.", "有人按当前状态审查原型。"),
                "expect": runtime_task_text(display_language, f"The main flow visibly supports {goal}.", f"主流程明显支持 {goal}。"),
                "fail_if": runtime_task_text(
                    display_language,
                    "The current direction is confusing or disconnected from the goal.",
                    "当前方向令人困惑或与目标脱节。",
                ),
            },
            {
                "title": runtime_task_text(display_language, "Primary interaction holds together", "主交互路径完整"),
                "details": runtime_task_text(
                    display_language,
                    "When: a user follows the most obvious interaction path.\n"
                    "Expect: the path remains understandable from start to finish.\n"
                    "Fail if: the experience breaks, stalls, or loses its state.",
                    "当：用户沿最明显的交互路径操作。\n预期：从开始到结束都能理解这条路径。\n失败条件：体验中断、停滞或丢失状态。",
                ),
                "when": runtime_task_text(display_language, "A user follows the most obvious path.", "用户沿最明显的路径操作。"),
                "expect": runtime_task_text(display_language, "The path stays understandable and coherent.", "这条路径始终清楚且连贯。"),
                "fail_if": runtime_task_text(
                    display_language,
                    "The experience breaks, stalls, or loses its state.",
                    "体验中断、停滞或丢失状态。",
                ),
            },
            {
                "title": runtime_task_text(display_language, "Prototype safety", "原型安全性"),
                "details": runtime_task_text(
                    display_language,
                    "When: the user hits an incomplete or awkward edge in the prototype.\n"
                    "Expect: the interface still communicates what is happening.\n"
                    "Fail if: the prototype crashes, misleads the user, or becomes unusable.",
                    "当：用户遇到原型中尚未完成或不够自然的边界。\n预期：界面仍能说明正在发生什么。\n失败条件：原型崩溃、误导用户或变得不可用。",
                ),
                "when": runtime_task_text(display_language, "An incomplete or awkward edge appears.", "出现尚未完成或不够自然的边界。"),
                "expect": runtime_task_text(display_language, "The interface still communicates clearly.", "界面仍能清楚说明当前状态。"),
                "fail_if": runtime_task_text(
                    display_language,
                    "The prototype crashes, misleads the user, or becomes unusable.",
                    "原型崩溃、误导用户或变得不可用。",
                ),
            },
        ],
        "generation_notes": runtime_task_text(
            display_language,
            "Generated a compact exploratory check set because the spec did not provide explicit checks.",
            "由于 spec 没有提供明确检查项，已生成一组紧凑的探索性检查。",
        ),
    }


def fake_tester_payload(
    iter_id: int,
    checks: list[dict],
    check_count: int,
    *,
    display_language: str = "en",
) -> dict:
    passed_checks = min(check_count, 1 + iter_id)
    total_checks = check_count
    results = []
    for index, check in enumerate(checks, start=1):
        status = "passed" if index <= passed_checks else "failed"
        results.append(
            {
                "id": check["id"],
                "title": check["title"],
                "status": status,
                "notes": _fake_check_notes(check, status, display_language=display_language),
            }
        )
    return {
        "execution_summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": max(total_checks - passed_checks, 0),
            "errored": 0,
            "total_duration_ms": 500 + iter_id * 25,
        },
        "check_results": results,
        "dynamic_checks": [],
        "tester_observations": runtime_task_text(
            display_language,
            "Fake executor evaluated the compiled Markdown checks against the frozen run contract; "
            "passed checks move toward Proven only through traceable evidence, while failed checks stay "
            "Blocking or Unproven for GateKeeper.",
            "模拟 executor 依据冻结的 Run 契约执行了已编译的 Markdown 检查；通过的检查只有在具备可追溯证据时才会进入 Proven，"
            "失败的检查则对 GateKeeper 保持 Blocking 或 Unproven。",
        ),
        "coverage_results": [],
    }


def _fake_check_notes(check: dict, status: str, *, display_language: str) -> str:
    base = str(check.get("expect") or check.get("details") or "").strip()
    if status == "passed":
        suffix = runtime_task_text(
            display_language,
            "Fake evidence treats this as Proven only through the inspector evidence ledger.",
            "模拟证据只有通过 Inspector 证据账本，才会把这一项视为 Proven。",
        )
    else:
        suffix = runtime_task_text(
            display_language,
            "This remains Blocking or Unproven until a later Builder repair produces new proof.",
            "在后续 Builder 修复产生新证明前，这一项保持 Blocking 或 Unproven。",
        )
    return f"{base} {suffix}".strip()
