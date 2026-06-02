from __future__ import annotations

from pathlib import Path

from compacted_contract_support import FakeAlignmentWorkdirContextRepository
from loopora.service_alignment_workdir_context import (
    AlignmentWorkdirContextResolverContext,
    alignment_workdir_context_payload,
    resolve_plan_context_from_workdir_context,
)
from loopora.service_types import LooporaError


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
