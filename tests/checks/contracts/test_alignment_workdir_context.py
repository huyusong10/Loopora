from pathlib import Path

import pytest

from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolutionRequest,
    AlignmentLooporaContextResolverContext,
    AlignmentWorkdirContextResolverContext,
    alignment_workdir_context_payload,
    get_alignment_workdir_context,
    resolve_plan_context_from_workdir_context,
    resolve_loopora_context,
)
from loopora.service_types import LooporaError


class FakeAlignmentWorkdirContextRepository:
    def __init__(self, sessions: list[dict]) -> None:
        self.sessions = sessions
        self.list_limits: list[int] = []

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_limits.append(limit)
        return self.sessions[:limit]


def test_alignment_workdir_context_payload_collects_sessions_loops_files_and_fresh_choice(tmp_path: Path) -> None:
    state_dir = tmp_path / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_text("# Task\n\nImprove the Loop.", encoding="utf-8")
    repo = FakeAlignmentWorkdirContextRepository(
        [
            {
                "id": "align_1",
                "status": "idle",
                "workdir": str(tmp_path),
                "transcript": [{"role": "user", "content": "Existing alignment"}],
                "bundle_path": str(state_dir / "alignment_sessions" / "align_1" / "artifacts" / "bundle.yml"),
            }
        ]
    )
    run = {
        "id": "run_1",
        "loop_id": "loop_1",
        "status": "awaiting_agent",
        "runs_dir": str(state_dir / "runs" / "run_1"),
    }
    context = AlignmentWorkdirContextResolverContext(
        repository=repo,
        list_loops=lambda: [
            {
                "id": "loop_1",
                "name": "Evidence Loop",
                "workdir": str(tmp_path),
                "latest_run_id": "run_1",
                "spec_path": str(spec_path),
                "bundle": {"id": "bundle_1", "name": "Bundle Loop"},
            }
        ],
        get_run=lambda _run_id: run,
    )

    payload = alignment_workdir_context_payload(context, tmp_path)
    option_types = [option["source_type"] for option in payload["options"]]

    assert payload["workdir"] == str(tmp_path)
    assert payload["state_dir"] == str(state_dir)
    assert payload["has_loopora_state"] is True
    assert payload["requires_choice"] is True
    assert payload["recommended_option_id"] == ""
    assert repo.list_limits == [100]
    assert "alignment_session" in option_types
    assert "run" in option_types
    assert "bundle" in option_types
    assert "spec_file" not in option_types
    assert payload["options"][-1]["option_id"] == "regenerate"


def test_alignment_workdir_context_payload_uses_fresh_choice_when_no_sources(tmp_path: Path) -> None:
    repo = FakeAlignmentWorkdirContextRepository([])
    context = AlignmentWorkdirContextResolverContext(
        repository=repo,
        list_loops=list,
        get_run=lambda _run_id: {},
    )

    payload = alignment_workdir_context_payload(context, tmp_path)
    resolution = resolve_plan_context_from_workdir_context(payload)

    assert payload["has_loopora_state"] is False
    assert payload["requires_choice"] is False
    assert payload["recommended_option_id"] == "regenerate"
    assert [option["option_id"] for option in payload["options"]] == ["regenerate"]
    assert resolution["action"] == "create_new"
    assert resolution["confidence"] == "no_existing_context"
    assert resolution["fresh"] is True


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


def test_alignment_workdir_context_payload_keeps_loop_option_when_latest_run_is_missing(tmp_path: Path) -> None:
    repo = FakeAlignmentWorkdirContextRepository([])

    def missing_run(run_id: str) -> dict:
        raise LooporaError(f"unknown run: {run_id}")

    context = AlignmentWorkdirContextResolverContext(
        repository=repo,
        list_loops=lambda: [
            {
                "id": "loop_1",
                "name": "Loop without run",
                "workdir": str(tmp_path),
                "latest_run_id": "run_missing",
            }
        ],
        get_run=missing_run,
    )

    payload = alignment_workdir_context_payload(context, tmp_path)

    assert [option["source_type"] for option in payload["options"]] == ["loop", "none"]


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
