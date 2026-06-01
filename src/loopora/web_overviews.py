from __future__ import annotations

from collections.abc import Mapping

from fastapi import HTTPException

from loopora.providers import executor_profile
from loopora.run_artifact_catalog import list_run_artifacts
from loopora.run_takeaway_common import (
    LEGACY_RUNTIME_ROLE_TO_ARCHETYPE,
    display_iter as _display_iter,
    summary_excerpt as _summary_excerpt,
)
from loopora.run_takeaway_evidence import build_evidence_coverage as _build_evidence_coverage
from loopora.run_takeaways import build_run_key_takeaways as _build_run_key_takeaways
from loopora.strategy_source import strategy_source_from_record
from loopora.web_task_verdict_overviews import build_run_summary_snapshot as _build_run_summary_snapshot
from loopora.web_task_verdict_overviews import task_verdict_label as _task_verdict_label
from loopora.web_task_verdict_overviews import task_verdict_status as _task_verdict_status
from loopora.web_task_verdict_overviews import task_verdict_status_from_run as _task_verdict_status_from_run
from loopora.web_task_verdict_overviews import verdict_safe_excerpt_pair as _verdict_safe_excerpt_pair
from loopora.web_timeline_overviews import format_timeline_event as _format_timeline_event


def _artifact_record_or_404(run: dict, artifact_id: str) -> dict:
    for artifact in list_run_artifacts(run):
        if artifact["id"] == artifact_id:
            return artifact
    raise HTTPException(status_code=404, detail="unknown artifact")


def _strategy_role_executor_summary(
    strategy_source: Mapping[str, object] | None,
    *,
    fallback_executor_kind: str = "codex",
) -> str:
    roles = strategy_source.get("roles", []) if isinstance(strategy_source, Mapping) else []
    if not isinstance(roles, list) or not roles:
        return "-"
    counts: dict[str, int] = {}
    for role in roles:
        if not isinstance(role, Mapping):
            continue
        raw_kind = str(role.get("executor_kind", "")).strip() or fallback_executor_kind
        try:
            label = executor_profile(raw_kind).label
        except ValueError:
            label = raw_kind or "-"
        counts[label] = counts.get(label, 0) + 1
    if not counts:
        return "-"
    return " · ".join(f"{label} x{count}" if count > 1 else label for label, count in counts.items())


def _overview_strategy_source(record: Mapping[str, object] | None) -> Mapping[str, object]:
    return strategy_source_from_record(record) or {}


def _decorate_loop_overview(loop: dict) -> dict:
    latest_run_id = loop.get("latest_run_id")
    latest_status = loop.get("latest_status") or "draft"
    summary_excerpt = _summary_excerpt(loop.get("latest_summary_md"))
    strategy_source = _overview_strategy_source(loop)
    task_verdict = loop.get("latest_task_verdict_json") if isinstance(loop.get("latest_task_verdict_json"), Mapping) else {}
    task_status = _task_verdict_status(task_verdict)
    task_label_zh, task_label_en = _task_verdict_label(task_status)
    card_excerpt_zh, card_excerpt_en = _verdict_safe_excerpt_pair(task_verdict, run_status=latest_status, raw_excerpt=summary_excerpt)
    hints = {
        "draft": ("还没有运行，先检查 Loop 契约和工作目录。", "No run yet. Start by checking the spec and workdir."),
        "queued": ("已经进入队列，点进去看最新状态。", "Queued up. Open it to see the current state."),
        "running": ("正在推进中，点进去看实时进展。", "Actively progressing. Open it for live updates."),
        "succeeded": ("最近一次运行已结束，点进去看 Loop 裁决。", "The latest run finished. Open it for the task verdict."),
        "failed": ("最近一次运行失败，建议先看运行状态和 Loop 裁决。", "The latest run failed. Start with run status and task verdict."),
        "stopped": ("最近一次运行已停止。", "The latest run was stopped."),
    }
    hint_zh, hint_en = hints.get(latest_status, hints["draft"])
    if latest_status == "succeeded" and task_status == "passed_with_residual_risk":
        hint_zh, hint_en = ("最近一次 Loop 裁决带残余风险通过。", "The latest task verdict passed with residual risk.")
    elif latest_status == "succeeded" and task_status == "passed":
        hint_zh, hint_en = ("最近一次 Loop 裁决已通过。", "The latest task verdict passed.")
    elif task_status == "failed":
        hint_zh, hint_en = ("最近一次 Loop 裁决未通过。", "The latest task verdict failed.")
    elif task_status == "insufficient_evidence":
        hint_zh, hint_en = ("最近一次 Loop 裁决证据不足。", "The latest task verdict has insufficient evidence.")
    bundle = loop.get("bundle") if isinstance(loop.get("bundle"), Mapping) else None
    managed_by_bundle = bool(bundle and bundle.get("id"))
    return {
        **loop,
        "role_executor_summary": _strategy_role_executor_summary(
            strategy_source,
            fallback_executor_kind=loop.get("executor_kind", "codex"),
        ),
        "role_count": len(strategy_source.get("roles", []) if isinstance(strategy_source, Mapping) else []),
        "step_count": len(strategy_source.get("steps", []) if isinstance(strategy_source, Mapping) else []),
        "display_iter": _display_iter(loop.get("latest_current_iter")),
        "card_href": f"/runs/{latest_run_id}" if latest_run_id else f"/loops/{loop['id']}",
        "card_hint_zh": hint_zh,
        "card_hint_en": hint_en,
        "card_excerpt": card_excerpt_en or summary_excerpt,
        "card_excerpt_zh": card_excerpt_zh,
        "card_excerpt_en": card_excerpt_en,
        "latest_task_verdict_status": task_status,
        "latest_task_verdict_label_zh": task_label_zh,
        "latest_task_verdict_label_en": task_label_en,
        "managed_by_bundle": managed_by_bundle,
        "bundle_id": str((bundle or {}).get("id", "") or "").strip(),
        "bundle_name": str((bundle or {}).get("name", "") or "").strip(),
    }


def _decorate_run_overview(run: dict) -> dict:
    strategy_source = _overview_strategy_source(run)
    summary = _build_run_summary_snapshot(run)
    task_status = _task_verdict_status_from_run(run)
    return {
        **run,
        "role_executor_summary": _strategy_role_executor_summary(
            strategy_source,
            fallback_executor_kind=run.get("executor_kind", "codex"),
        ),
        "display_iter": _display_iter(run.get("current_iter")),
        "summary_excerpt": _summary_excerpt(run.get("summary_md")),
        "task_verdict_status": task_status,
        "task_verdict_title_zh": summary["verdict_title_zh"],
        "task_verdict_title_en": summary["verdict_title_en"],
        "task_verdict_note_zh": summary["verdict_note_zh"],
        "task_verdict_note_en": summary["verdict_note_en"],
    }


__all__ = [
    "LEGACY_RUNTIME_ROLE_TO_ARCHETYPE",
    "_artifact_record_or_404",
    "_build_evidence_coverage",
    "_build_run_key_takeaways",
    "_build_run_summary_snapshot",
    "_decorate_loop_overview",
    "_decorate_run_overview",
    "_display_iter",
    "_format_timeline_event",
    "_overview_strategy_source",
]
