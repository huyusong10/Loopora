from __future__ import annotations

from collections.abc import Mapping

from loopora.run_projection_fields import task_verdict_from_run
from loopora.run_takeaway_common import (
    clean_takeaway_text,
    display_iter as _display_iter,
    summary_excerpt as _summary_excerpt,
)


def task_verdict_status(verdict: object) -> str:
    if not isinstance(verdict, Mapping):
        return "not_evaluated"
    return str(verdict.get("status") or "not_evaluated").strip() or "not_evaluated"


def task_verdict_label(status: object) -> tuple[str, str]:
    labels = {
        "not_evaluated": ("Loop 裁决：未评估", "Task verdict: not evaluated"),
        "passed": ("Loop 裁决：已通过", "Task verdict: passed"),
        "failed": ("Loop 裁决：未通过", "Task verdict: failed"),
        "insufficient_evidence": ("Loop 裁决：证据不足", "Task verdict: insufficient evidence"),
        "passed_with_residual_risk": ("Loop 裁决：有残余风险地通过", "Task verdict: passed with residual risk"),
    }
    normalized = str(status or "not_evaluated").strip() or "not_evaluated"
    return labels.get(normalized, (f"Loop 裁决：{normalized}", f"Task verdict: {normalized.replace('_', ' ')}"))


def task_verdict_status_from_run(run: Mapping[str, object]) -> str:
    return task_verdict_status(task_verdict_from_run(run))


def build_run_summary_snapshot(run: dict) -> dict:
    task_verdict = task_verdict_from_run(run)
    raw_verdict = run.get("last_verdict_json") or {}
    buckets = task_verdict.get("buckets") if isinstance(task_verdict.get("buckets"), Mapping) else {}
    failed_count = len(buckets.get("blocking") or raw_verdict.get("failed_check_ids") or [])
    composite_score = raw_verdict.get("composite_score")
    task_status = str(task_verdict.get("status") or "not_evaluated")
    if task_status == "passed":
        verdict_title = ("Loop 裁决：已通过", "Task verdict: passed")
        verdict_note = (
            task_verdict.get("summary") or _first_task_bucket_text(buckets, "proven") or "证据支持本次 Loop 结论。",
            task_verdict.get("summary") or _first_task_bucket_text(buckets, "proven") or "Evidence supports the task conclusion.",
        )
    elif task_status == "passed_with_residual_risk":
        verdict_title = ("Loop 裁决：有残余风险地通过", "Task verdict: passed with residual risk")
        verdict_note = (
            task_verdict.get("summary") or _first_task_bucket_text(buckets, "residual_risk") or "证据支持本次 Loop 结论，但仍保留了已接受的可见残余风险。",
            task_verdict.get("summary")
            or _first_task_bucket_text(buckets, "residual_risk")
            or "Evidence supports the task conclusion, with accepted residual risk still visible.",
        )
    elif task_status == "failed":
        verdict_title = ("Loop 裁决：未通过", "Task verdict: failed")
        verdict_note = (
            task_verdict.get("summary") or _first_task_bucket_text(buckets, "blocking") or f"还有 {failed_count} 个阻断项，优先看证据桶。",
            task_verdict.get("summary")
            or _first_task_bucket_text(buckets, "blocking")
            or f"{failed_count} blocker(s) remain. Start with the evidence buckets.",
        )
    elif task_status == "insufficient_evidence":
        verdict_title = ("Loop 裁决：证据不足", "Task verdict: insufficient evidence")
        verdict_note = (
            task_verdict.get("summary") or _first_task_bucket_text(buckets, "unproven", "weak") or "运行已到边界，但证据还不足以证明 Loop 通过。",
            task_verdict.get("summary")
            or _first_task_bucket_text(buckets, "unproven", "weak")
            or "The run reached its boundary, but evidence is not strong enough for a task pass.",
        )
    else:
        verdict_title = ("Loop 裁决：未评估", "Task verdict: not evaluated")
        verdict_note = (
            task_verdict.get("summary") or "还没有可用的证据裁决。",
            task_verdict.get("summary") or "No evidence-based task verdict is available yet.",
        )

    status_notes = {
        "queued": ("运行已创建，正在等待执行。", "The run is created and waiting to start."),
        "running": ("当前运行正在推进，下面的摘要会持续更新。", "This run is in progress and the summary will keep updating."),
        "awaiting_agent": ("当前运行正在等待宿主 Agent 提交下一步结果。", "This run is waiting for the host Agent to submit the next step result."),
        "succeeded": ("这次运行已正常结束；任务是否通过仍看 Loop 裁决。", "This run finished normally; task pass or fail still comes from the Loop verdict."),
        "failed": ("这次运行已失败结束。", "This run finished with a failure."),
        "stopped": ("这次运行已被手动停止。", "This run was stopped manually."),
        "draft": ("运行还没有真正开始。", "The run has not started yet."),
    }
    status = run.get("status") or "draft"
    status_note = status_notes.get(status, status_notes["draft"])
    raw_summary_excerpt = _summary_excerpt(run.get("summary_md"))
    summary_excerpt_zh, summary_excerpt_en = verdict_safe_summary_pair(
        task_status=task_status,
        run_status=str(status),
        verdict_note_zh=str(verdict_note[0] or ""),
        verdict_note_en=str(verdict_note[1] or ""),
        raw_excerpt=raw_summary_excerpt,
    )

    return {
        "display_iter": _display_iter(run.get("current_iter")),
        "summary_excerpt": summary_excerpt_en or raw_summary_excerpt,
        "summary_excerpt_zh": summary_excerpt_zh,
        "summary_excerpt_en": summary_excerpt_en,
        "summary_empty_zh": "还没有稳定输出。",
        "summary_empty_en": "No substantial output yet.",
        "status_note_zh": status_note[0],
        "status_note_en": status_note[1],
        "verdict_title_zh": verdict_title[0],
        "verdict_title_en": verdict_title[1],
        "verdict_note_zh": verdict_note[0],
        "verdict_note_en": verdict_note[1],
        "failed_count": failed_count,
        "composite_score": composite_score,
    }


def verdict_safe_excerpt_pair(task_verdict: Mapping[str, object], *, run_status: object, raw_excerpt: str) -> tuple[str, str]:
    verdict = task_verdict if isinstance(task_verdict, Mapping) else {}
    status = task_verdict_status(verdict)
    buckets = verdict.get("buckets") if isinstance(verdict.get("buckets"), Mapping) else {}
    note = clean_takeaway_text(verdict.get("summary"), max_length=170) or _first_task_bucket_text(
        buckets,
        *_status_bucket_preference(status),
    )
    return verdict_safe_summary_pair(
        task_status=status,
        run_status=str(run_status or ""),
        verdict_note_zh=note,
        verdict_note_en=note,
        raw_excerpt=raw_excerpt,
    )


def verdict_safe_summary_pair(
    *,
    task_status: str,
    run_status: str,
    verdict_note_zh: str,
    verdict_note_en: str,
    raw_excerpt: str,
) -> tuple[str, str]:
    normalized_status = str(task_status or "not_evaluated").strip() or "not_evaluated"
    normalized_run_status = str(run_status or "").strip().lower()
    if normalized_run_status not in {"succeeded", "failed", "stopped"}:
        return raw_excerpt, raw_excerpt
    if normalized_status == "passed":
        return (
            f"Loop 裁决已通过：{verdict_note_zh or raw_excerpt or '证据支持本次 Loop 结论。'}",
            f"Task verdict passed: {verdict_note_en or raw_excerpt or 'Evidence supports the task conclusion.'}",
        )
    if normalized_status == "passed_with_residual_risk":
        return (
            f"Loop 裁决带残余风险通过：{verdict_note_zh or '仍有已接受的可见残余风险。'}",
            f"Task verdict passed with residual risk: {verdict_note_en or 'Accepted residual risk remains visible.'}",
        )
    if normalized_status == "failed":
        return (
            f"Loop 裁决未通过：{verdict_note_zh or '阻断项仍然存在。'}",
            f"Task verdict failed: {verdict_note_en or 'Blockers remain.'}",
        )
    if normalized_status == "insufficient_evidence":
        return (
            f"Loop 裁决证据不足：{verdict_note_zh or '必需证据仍未证明。'}",
            f"Task verdict still insufficient: {verdict_note_en or 'Required evidence is still unproven.'}",
        )
    return (
        f"Loop 裁决未评估：{verdict_note_zh or '没有可用的证据裁决。'}",
        f"Task verdict not evaluated: {verdict_note_en or 'No evidence-based verdict is available.'}",
    )


def _status_bucket_preference(status: str) -> tuple[str, ...]:
    normalized = str(status or "").strip()
    if normalized == "passed":
        return ("proven",)
    if normalized == "passed_with_residual_risk":
        return ("residual_risk", "proven")
    if normalized == "failed":
        return ("blocking", "unproven", "weak")
    if normalized == "insufficient_evidence":
        return ("unproven", "weak", "blocking")
    return ("unproven", "weak", "blocking", "residual_risk")


def _first_task_bucket_text(buckets: Mapping[str, object], *bucket_names: str) -> str:
    for bucket_name in bucket_names:
        items = buckets.get(bucket_name)
        if not isinstance(items, list) or not items:
            continue
        item = items[0]
        if not isinstance(item, Mapping):
            if str(item).strip():
                return str(item).strip()
            continue
        for key in ("text", "label", "reason"):
            text = str(item.get(key) or "").strip()
            if text:
                return text
    return ""
