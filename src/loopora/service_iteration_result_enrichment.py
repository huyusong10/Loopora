from __future__ import annotations

"""Tester and verifier result enrichment for iteration reporting."""

from collections.abc import Callable

from loopora.runtime_task_language import runtime_task_language, runtime_task_text
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_finite_number


def verifier_passed(verifier_result: dict) -> bool:
    return structured_bool_is_true(verifier_result.get("passed"))


def empty_status_counts() -> dict[str, int]:
    return {"passed": 0, "failed": 0, "errored": 0, "skipped": 0}


def count_statuses(items: list[dict]) -> dict[str, int]:
    counts = empty_status_counts()
    for item in items:
        status = str(item.get("status", "")).strip().lower()
        if status in counts:
            counts[status] += 1
    return counts


def collect_non_passing_items(items: list[dict], *, source: str, truncate_text: Callable[..., str]) -> list[dict]:
    failures = []
    for item in items:
        status = str(item.get("status", "")).strip().lower()
        if status == "passed":
            continue
        failures.append(
            {
                "id": str(item.get("id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "status": status or "unknown",
                "source": source,
                "notes": truncate_text(str(item.get("notes", "")).strip(), max_length=280),
            }
        )
    return failures


def enrich_tester_result(tester_result: dict, *, truncate_text: Callable[..., str]) -> dict:
    result = dict(tester_result)
    check_results = list(result.get("check_results", []))
    dynamic_checks = list(result.get("dynamic_checks", []))
    check_counts = count_statuses(check_results)
    dynamic_counts = count_statuses(dynamic_checks)
    overall_counts = {key: check_counts.get(key, 0) + dynamic_counts.get(key, 0) for key in empty_status_counts()}
    failed_items = collect_non_passing_items(check_results, source="specified", truncate_text=truncate_text)
    failed_items.extend(collect_non_passing_items(dynamic_checks, source="dynamic", truncate_text=truncate_text))
    result["status_counts"] = {
        "check_results": check_counts,
        "dynamic_checks": dynamic_counts,
        "overall": overall_counts,
    }
    result["failed_items"] = failed_items
    result["specified_check_failures"] = [item["id"] for item in failed_items if item["source"] == "specified"]
    result["dynamic_check_failures"] = [item["id"] for item in failed_items if item["source"] == "dynamic"]
    return result


def build_decision_summary(
    verifier_result: dict,
    tester_result: dict,
    *,
    truncate_text: Callable[..., str],
    language: str = "en",
) -> str:
    reasons: list[str] = []
    failed_check_titles = list(verifier_result.get("failed_check_titles", []))
    dynamic_failures = list(tester_result.get("dynamic_check_failures", []))
    hard_constraint_violations = list(verifier_result.get("hard_constraint_violations", []))
    failing_metrics = list(verifier_result.get("failing_metrics", []))
    priority_failures = list(verifier_result.get("priority_failures", []))
    if failed_check_titles:
        reasons.append(
            runtime_task_text(language, "specified checks still failing: ", "指定检查仍未通过：")
            + ", ".join(failed_check_titles[:3])
            + ("..." if len(failed_check_titles) > 3 else "")
        )
    if dynamic_failures:
        failure_count = len(dynamic_failures)
        reasons.append(
            runtime_task_text(
                language, f"{failure_count} dynamic check failure" + ("s remain" if failure_count != 1 else " remains"), f"仍有 {failure_count} 项动态检查失败"
            )
        )
    if hard_constraint_violations:
        violation_count = len(hard_constraint_violations)
        reasons.append(
            runtime_task_text(
                language, f"{violation_count} hard constraint violation" + ("s" if violation_count != 1 else ""), f"存在 {violation_count} 项硬约束违规"
            )
        )
    if failing_metrics:
        metric_names = [str(item.get("name", "")).strip() for item in failing_metrics if item.get("name")]
        if metric_names:
            reasons.append(runtime_task_text(language, "failing metrics: ", "未达标指标：") + ", ".join(metric_names))
    if priority_failures and not reasons:
        reasons.append(
            runtime_task_text(language, "priority failures reported: ", "已报告优先失败项：")
            + ", ".join(truncate_text(item.get("summary"), 120) for item in priority_failures[:2])
        )
    if verifier_passed(verifier_result):
        return runtime_task_text(
            language,
            "GateKeeper accepted this iteration's supplied checks and evidence; "
            "Loopora Core still derives the task verdict from coverage targets and run artifacts.",
            "GateKeeper 接受了本轮提交的检查与证据；Loopora Core 仍依据覆盖目标和 Run 产物推导任务裁决。",
        )
    if not reasons:
        return runtime_task_text(
            language,
            "Task verdict is not ready: GateKeeper did not accept this iteration because Weak or Unproven evidence remains below threshold; "
            "do not lower the frozen run contract.",
            "任务裁决尚未就绪：GateKeeper 未接受本轮结果，因为仍有 Weak 或 Unproven 证据低于阈值；不得降低冻结的 Run 契约。",
        )
    return runtime_task_text(
        language,
        "Task verdict is not ready: GateKeeper did not accept this iteration because "
        + "; ".join(reasons)
        + ". Treat these as Blocking or Unproven evidence until repaired.",
        "任务裁决尚未就绪：GateKeeper 未接受本轮结果，原因是" + "；".join(reasons) + "。在修复前，应将这些问题视为 Blocking 或 Unproven 证据。",
    )


def split_action_hints(feedback: str | None) -> list[str]:
    text = str(feedback or "").strip()
    if not text:
        return []
    hints = []
    for raw_line in text.splitlines():
        cleaned = raw_line.strip().lstrip("-*").strip()
        if cleaned:
            hints.append(cleaned)
    return hints[:5] if hints else [text]


def enrich_verifier_result(
    verifier_result: dict,
    compiled_spec: dict,
    tester_result: dict,
    *,
    truncate_text: Callable[..., str],
) -> dict:
    result = dict(verifier_result)
    result["passed"] = verifier_passed(result)
    result["composite_score"] = structured_finite_number(
        result.get("composite_score"),
        default=1.0 if result["passed"] else 0.0,
    )
    check_title_map = {str(check.get("id", "")).strip(): str(check.get("title", "")).strip() for check in compiled_spec.get("checks", [])}
    failed_check_titles = [check_title_map.get(check_id, check_id) for check_id in result.get("failed_check_ids", [])]
    failing_metrics = []
    for name, metric in (result.get("metric_scores") or {}).items():
        if not isinstance(metric, dict):
            failing_metrics.append({"name": str(name), "value": None, "threshold": None})
            continue
        if structured_bool_is_true(metric.get("passed")):
            continue
        failing_metrics.append(
            {
                "name": name,
                "value": metric.get("value"),
                "threshold": metric.get("threshold"),
            }
        )
    result["failed_check_titles"] = failed_check_titles
    result["failing_metrics"] = failing_metrics
    result["hard_constraint_violation_count"] = len(result.get("hard_constraint_violations", []))
    result["priority_failure_count"] = len(result.get("priority_failures", []))
    result["decision_summary"] = build_decision_summary(
        result,
        tester_result,
        truncate_text=truncate_text,
        language=runtime_task_language(compiled_spec),
    )
    result["next_actions"] = split_action_hints(result.get("feedback_to_generator"))
    return result
