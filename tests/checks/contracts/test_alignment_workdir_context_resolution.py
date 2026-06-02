from __future__ import annotations

from pathlib import Path

import pytest

from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolutionRequest,
    AlignmentLooporaContextResolverContext,
    get_alignment_workdir_context,
    resolve_loopora_context,
    resolve_plan_context_from_workdir_context,
)
from loopora.service_types import LooporaError


def test_get_alignment_workdir_context_attaches_default_plan_resolution(tmp_path: Path) -> None:
    plan_calls: list[dict] = []

    def workdir_context_payload(root: Path) -> dict:
        assert root == tmp_path.resolve()
        return {
            "workdir": str(root),
            "state_dir": str(root / ".loopora"),
            "has_loopora_state": False,
            "recommended_option_id": "regenerate",
            "options": [{"option_id": "regenerate", "action": "regenerate"}],
        }

    def resolve_plan_context(payload: dict, *, source_option_id: str = "") -> dict:
        plan_calls.append({"workdir": payload["workdir"], "source_option_id": source_option_id})
        return {"action": "create_new", "source_option_id": source_option_id}

    result = get_alignment_workdir_context(
        AlignmentLooporaContextResolverContext(
            workdir_context_payload=workdir_context_payload,
            resolve_plan_context=resolve_plan_context,
            resolve_run_context=lambda _root, **_kwargs: {},
        ),
        tmp_path,
    )

    assert result["resolution"] == {"action": "create_new", "source_option_id": ""}
    assert plan_calls == [{"workdir": str(tmp_path.resolve()), "source_option_id": ""}]


def test_resolve_loopora_context_routes_plan_and_run_from_one_command_boundary(tmp_path: Path) -> None:
    run_calls: list[dict] = []

    def workdir_context_payload(root: Path) -> dict:
        return {
            "workdir": str(root),
            "state_dir": str(root / ".loopora"),
            "has_loopora_state": True,
            "options": [{"option_id": "bundle:one", "action": "improve"}],
        }

    def resolve_plan_context(payload: dict, *, source_option_id: str = "") -> dict:
        return {"intent": "plan", "workdir": payload["workdir"], "selected_option_id": source_option_id}

    def resolve_run_context(root: Path, *, adapter: str = "", context_id: str = "") -> dict:
        run_calls.append({"root": str(root), "adapter": adapter, "context_id": context_id})
        return {"intent": "run", "adapter": adapter, "context_id": context_id}

    context = AlignmentLooporaContextResolverContext(
        workdir_context_payload=workdir_context_payload,
        resolve_plan_context=resolve_plan_context,
        resolve_run_context=resolve_run_context,
    )

    plan = resolve_loopora_context(
        context,
        tmp_path,
        AlignmentLooporaContextResolutionRequest(intent="plan", source_option_id="bundle:one"),
    )
    run = resolve_loopora_context(
        context,
        tmp_path,
        AlignmentLooporaContextResolutionRequest(intent="run", adapter="codex", context_id="thread-1"),
    )

    assert plan == {"intent": "plan", "workdir": str(tmp_path.resolve()), "selected_option_id": "bundle:one"}
    assert run == {"intent": "run", "adapter": "codex", "context_id": "thread-1"}
    assert run_calls == [{"root": str(tmp_path.resolve()), "adapter": "codex", "context_id": "thread-1"}]

    with pytest.raises(LooporaError, match="workdir does not exist"):
        resolve_loopora_context(
            context,
            tmp_path / "missing",
            AlignmentLooporaContextResolutionRequest(intent="run"),
        )


def test_resolve_plan_context_from_workdir_context_preserves_selection_semantics() -> None:
    context = {
        "workdir": "/workspace",
        "state_dir": "/workspace/.loopora",
        "has_loopora_state": True,
        "requires_choice": True,
        "options": [
            {"option_id": "continue_session:align_1", "action": "continue_session"},
            {"option_id": "bundle:bundle_1", "action": "improve"},
            {"option_id": "regenerate", "action": "regenerate"},
        ],
    }

    choose = resolve_plan_context_from_workdir_context(context)
    continue_session = resolve_plan_context_from_workdir_context(context, source_option_id="continue_session:align_1")
    improve = resolve_plan_context_from_workdir_context(context, source_option_id="bundle:bundle_1")
    fresh = resolve_plan_context_from_workdir_context(context, source_option_id="regenerate")

    assert choose["action"] == "choose_source"
    assert choose["requires_user_choice"] is True
    assert continue_session["action"] == "continue_session"
    assert continue_session["fresh"] is False
    assert improve["action"] == "improve_existing"
    assert improve["fresh"] is False
    assert fresh["action"] == "create_new"
    assert fresh["confidence"] == "explicit_fresh"
