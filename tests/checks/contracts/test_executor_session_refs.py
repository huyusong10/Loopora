from __future__ import annotations

from pathlib import Path

from loopora.executor_session_refs import extract_session_ref, infer_codex_session_ref_from_rollouts


def test_executor_session_ref_extracts_nested_session_payload() -> None:
    payload = {
        "type": "event",
        "data": {
            "sessionId": {"uuid": "11111111-2222-4333-8444-555555555555"},
            "rolloutPath": "/tmp/rollout-11111111-2222-4333-8444-555555555555.jsonl",
        },
    }

    assert extract_session_ref(payload) == {
        "session_id": "11111111-2222-4333-8444-555555555555",
        "rollout_path": "/tmp/rollout-11111111-2222-4333-8444-555555555555.jsonl",
    }


def test_executor_session_ref_infers_codex_rollout_and_skips_invalid_candidates(tmp_path: Path) -> None:
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    sessions_dir = tmp_path / "codex-home" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "rollout-invalid.jsonl").mkdir()
    session_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    rollout_path = sessions_dir / f"rollout-{session_id}.jsonl"
    rollout_path.write_text(f'{{"cwd": "{workdir}", "type": "session_meta"}}\n', encoding="utf-8")

    assert infer_codex_session_ref_from_rollouts(
        workdir=workdir,
        current_ref={},
        codex_home=tmp_path / "codex-home",
    ) == {
        "session_id": session_id,
        "rollout_path": str(rollout_path),
    }
