from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from loopora.branding import state_dir_for_workdir
from loopora.service_alignment_context import (
    add_alignment_context_option,
    alignment_bundle_file_has_ready_validation,
    alignment_bundle_context_option,
    alignment_file_bundle_context_option,
    alignment_loop_context_option,
    alignment_run_context_option,
    alignment_same_workdir,
    alignment_session_context_options,
    alignment_spec_file_context_option,
    alignment_workdir_spec_candidates,
    bounded_alignment_context_options,
)
from loopora.service_types import LooporaError


@dataclass(frozen=True)
class AlignmentWorkdirContextResolverContext:
    repository: object
    list_loops: Callable[[], list[dict]]
    get_run: Callable[[str], dict]
    state_dir_for_workdir: Callable[[Path], Path] = state_dir_for_workdir


@dataclass(frozen=True)
class AlignmentLooporaContextResolverContext:
    workdir_context_payload: Callable[[Path], dict]
    resolve_plan_context: Callable[..., dict]
    resolve_run_context: Callable[..., dict]


@dataclass(frozen=True)
class AlignmentLooporaContextResolutionRequest:
    intent: str = "plan"
    adapter: str = ""
    context_id: str = ""
    source_option_id: str = ""


def get_alignment_workdir_context(context: AlignmentLooporaContextResolverContext, workdir: Path) -> dict:
    root = workdir.expanduser().resolve()
    payload = context.workdir_context_payload(root)
    payload["resolution"] = context.resolve_plan_context(payload)
    return payload


def resolve_loopora_context(
    context: AlignmentLooporaContextResolverContext,
    workdir: Path,
    request: AlignmentLooporaContextResolutionRequest | None = None,
) -> dict:
    request = request or AlignmentLooporaContextResolutionRequest()
    root = workdir.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise LooporaError(f"workdir does not exist: {root}")
    normalized_intent = str(request.intent or "plan").strip().lower()
    if normalized_intent == "run":
        return context.resolve_run_context(root, adapter=request.adapter, context_id=request.context_id)
    payload = context.workdir_context_payload(root)
    return context.resolve_plan_context(payload, source_option_id=request.source_option_id)


def alignment_workdir_context_payload(context: AlignmentWorkdirContextResolverContext, root: Path) -> dict:
    if not root.exists() or not root.is_dir():
        raise LooporaError(f"workdir does not exist: {root}")
    options: list[dict] = []
    seen_option_ids: set[str] = set()
    seen_bundle_paths = collect_alignment_session_context_options(context.repository, root, options, seen_option_ids)
    seen_spec_paths = collect_alignment_loop_context_options(context, root, options, seen_option_ids)
    state_dir = context.state_dir_for_workdir(root)
    collect_alignment_filesystem_context_options(
        state_dir,
        options,
        seen_option_ids,
        seen_bundle_paths=seen_bundle_paths,
        seen_spec_paths=seen_spec_paths,
    )
    add_alignment_context_option(
        {
            "option_id": "regenerate",
            "action": "regenerate",
            "source_type": "none",
            "label_zh": "重新生成",
            "label_en": "Start fresh",
            "description_zh": "忽略这个目录里已有的 Loopora 产物，从当前消息重新编排。",
            "description_en": "Ignore existing Loopora artifacts in this workdir and compose from the new message.",
        },
        options,
        seen_option_ids,
    )
    has_sources = any(str(option.get("action") or "") != "regenerate" for option in options)
    return {
        "workdir": str(root),
        "state_dir": str(state_dir),
        "has_loopora_state": state_dir.exists(),
        "requires_choice": has_sources,
        "recommended_option_id": "" if has_sources else "regenerate",
        "options": bounded_alignment_context_options(options),
    }


def resolve_plan_context_from_workdir_context(context: dict, *, source_option_id: str = "") -> dict:
    option_id = str(source_option_id or context.get("recommended_option_id") or "").strip()
    options = [option for option in context.get("options") or [] if isinstance(option, dict)]
    selected = next((option for option in options if option.get("option_id") == option_id), None)
    base = {
        "schema_version": 1,
        "intent": "plan",
        "workdir": str(context.get("workdir") or ""),
        "state_dir": str(context.get("state_dir") or ""),
        "has_loopora_state": bool(context.get("has_loopora_state")),
        "selected_option_id": option_id,
        "requires_user_choice": False,
        "choices": [],
    }
    if selected and selected.get("action") == "regenerate":
        return {
            **base,
            "action": "create_new",
            "confidence": "explicit_fresh" if source_option_id else "no_existing_context",
            "fresh": True,
        }
    if selected and selected.get("action") == "continue_session":
        return {
            **base,
            "action": "continue_session",
            "confidence": "selected_context",
            "fresh": False,
            "selected": selected,
        }
    if selected:
        return {
            **base,
            "action": "improve_existing",
            "confidence": "selected_context",
            "fresh": False,
            "selected": selected,
        }
    if context.get("requires_choice"):
        return {
            **base,
            "action": "choose_source",
            "confidence": "ambiguous",
            "fresh": False,
            "requires_user_choice": True,
            "choices": options,
        }
    return {
        **base,
        "action": "create_new",
        "confidence": "no_existing_context",
        "fresh": True,
    }


def collect_alignment_session_context_options(
    repository: object,
    root: Path,
    options: list[dict],
    seen_option_ids: set[str],
) -> set[str]:
    seen_bundle_paths: set[str] = set()
    for session in repository.list_alignment_sessions(limit=100):
        if not alignment_same_workdir(session.get("workdir"), root):
            continue
        for option in alignment_session_context_options(session):
            add_alignment_context_option(option, options, seen_option_ids)
            bundle_path = str(option.get("bundle_path") or "").strip()
            if bundle_path:
                seen_bundle_paths.add(str(Path(bundle_path).expanduser().resolve()))
    return seen_bundle_paths


def collect_alignment_loop_context_options(
    context: AlignmentWorkdirContextResolverContext,
    root: Path,
    options: list[dict],
    seen_option_ids: set[str],
) -> set[str]:
    seen_spec_paths: set[str] = set()
    for loop in context.list_loops():
        if not alignment_same_workdir(loop.get("workdir"), root):
            continue
        spec_path = str(loop.get("spec_path") or "").strip()
        if spec_path:
            seen_spec_paths.add(str(Path(spec_path).expanduser().resolve()))
        latest_run_id = str(loop.get("latest_run_id") or "").strip()
        if latest_run_id:
            with suppress(LooporaError):
                add_alignment_context_option(
                    alignment_run_context_option(context.get_run(latest_run_id), loop=loop),
                    options,
                    seen_option_ids,
                )
        bundle = loop.get("bundle") if isinstance(loop.get("bundle"), dict) else {}
        bundle_id = str(bundle.get("id") or "").strip()
        option = (
            alignment_bundle_context_option(bundle_id, loop=loop, bundle=bundle)
            if bundle_id
            else alignment_loop_context_option(loop)
        )
        add_alignment_context_option(option, options, seen_option_ids)
    return seen_spec_paths


def collect_alignment_filesystem_context_options(
    state_dir: Path,
    options: list[dict],
    seen_option_ids: set[str],
    *,
    seen_bundle_paths: set[str],
    seen_spec_paths: set[str],
) -> None:
    if not state_dir.exists():
        return
    expected_workdir = state_dir.parent
    for bundle_path in sorted((state_dir / "alignment_sessions").glob("*/artifacts/bundle.yml"))[:20]:
        resolved_bundle_path = str(bundle_path.expanduser().resolve())
        if resolved_bundle_path in seen_bundle_paths:
            continue
        seen_bundle_paths.add(resolved_bundle_path)
        if not alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=expected_workdir):
            continue
        add_alignment_context_option(
            alignment_file_bundle_context_option(
                source_session_id=bundle_path.parent.parent.name,
                bundle_path=bundle_path,
            ),
            options,
            seen_option_ids,
        )
    for spec_path in alignment_workdir_spec_candidates(state_dir):
        resolved_spec = str(spec_path.expanduser().resolve())
        if resolved_spec in seen_spec_paths:
            continue
        seen_spec_paths.add(resolved_spec)
        add_alignment_context_option(alignment_spec_file_context_option(spec_path), options, seen_option_ids)
