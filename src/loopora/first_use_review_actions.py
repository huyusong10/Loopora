from __future__ import annotations

from collections.abc import Mapping
import json
import shlex
from urllib.parse import quote, urlencode, urlsplit

from loopora.first_use_action_readiness import (
    first_use_action_readiness_summary,
    project_first_use_action_readiness_summary,
)
from loopora.first_use_web_recovery import first_use_web_creation_choice_blockers


def fit_review_web_actions(
    route_actions: list[dict[str, object]],
    *,
    context: Mapping[str, object],
) -> list[dict[str, object]]:
    review_pending = context.get("review_pending") is True
    target_ready = context.get("target_ready") is True
    if not review_pending or not target_ready:
        return []
    source = next(
        (
            action
            for action in route_actions
            if str(action.get("kind") or "") == "open_web_creation_choices"
        ),
        None,
    )
    if source is None:
        return []
    blockers = first_use_web_creation_choice_blockers(source)
    open_url = _fit_review_open_url(
        source,
        review_inputs=context.get("review_inputs") if isinstance(context.get("review_inputs"), Mapping) else {},
        workdir=str(context.get("workdir") or ""),
    )
    command = str(source.get("command") or "").strip()
    open_path = _relative_open_path(open_url)
    return [
        {
            **source,
            **({"command": f"{command} --open-path {shlex.quote(open_path)}"} if command else {}),
            "kind": "continue_fit_review_in_web",
            "route_contexts": ["fit_review"],
            "route_path": "/fit-guide",
            "setup_independent": True,
            "review_independent": True,
            "open_url": open_url,
            "open_url_local_only": True,
            "opens_browser": True,
            "review_context_transport": "url_fragment",
            "command_ready": not blockers,
            "command_blockers": blockers,
            "note": (
                "Open the local Fit Guide to complete judgment interactively; setup, creation, and run remain blocked."
                if str(context.get("language") or "en") != "zh"
                else "打开本地 Fit Guide 交互补齐判断；设置、创建和运行仍保持阻止。"
            ),
        }
    ]


def _relative_open_path(open_url: str) -> str:
    parsed = urlsplit(open_url)
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{parsed.path or '/'}{query}{fragment}"


def _fit_review_open_url(
    source: Mapping[str, object],
    *,
    review_inputs: Mapping[str, object] | None,
    workdir: str,
) -> str:
    host = str(source.get("host") or "127.0.0.1").strip()
    port = int(source.get("port") or 8742)
    query = urlencode({"workdir": workdir}) if workdir else ""
    path = f"/fit-guide?{query}" if query else "/fit-guide"
    supplied = {
        str(key): str(value).strip()
        for key, value in dict(review_inputs or {}).items()
        if str(key).strip() and str(value).strip()
    }
    fragment = ""
    if supplied:
        encoded = quote(json.dumps(supplied, ensure_ascii=False, separators=(",", ":")), safe="")
        fragment = f"#fit-review={encoded}"
    return f"http://{host}:{port}{path}{fragment}"


def project_fit_review_action_summary(payload: dict[str, object], *, summary_key: str) -> None:
    actions = [action for action in list(payload.get("review_actions") or []) if isinstance(action, dict)]
    kinds = [str(action.get("kind") or "") for action in actions if str(action.get("kind") or "")]
    payload["review_action_kinds"] = kinds
    readiness = first_use_action_readiness_summary(actions)
    project_first_use_action_readiness_summary(payload, prefix="review_action", readiness=readiness)
    summary = payload.get(summary_key)
    if isinstance(summary, dict):
        summary["review_action_kinds"] = list(kinds)
        project_first_use_action_readiness_summary(summary, prefix="review_action", readiness=readiness)


def fit_review_is_pending(task_review: Mapping[str, object]) -> bool:
    if not task_review:
        return True
    summary = task_review.get("task_fit_review_summary")
    if not isinstance(summary, Mapping):
        return True
    return not bool(summary.get("ready_for_loopora_plan_message")) and str(
        summary.get("setup_blocker") or ""
    ) not in {"prefer_direct_path", "missing_direct_decision_input"}
