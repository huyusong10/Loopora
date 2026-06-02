from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopora.executor import EXECUTOR_OUTPUT_MAX_BYTES, ExecutorError, RealCodexExecutor, RoleRequest


def test_opencode_stream_text_is_bounded_before_event_emit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="generator",
        prompt="Return JSON only.",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={"type": "object", "properties": {}, "additionalProperties": True},
        output_path=run_dir / "generator_output.json",
        run_dir=run_dir,
        executor_kind="opencode",
    )
    emitted: list[tuple[str, dict]] = []
    state = {"latest_text": "", "text_parts": [], "text_size_bytes": 0}
    oversized_line = json.dumps({"type": "text", "part": {"text": "x" * (EXECUTOR_OUTPUT_MAX_BYTES + 1)}})

    with pytest.raises(ExecutorError, match="opencode output is too large"):
        RealCodexExecutor()._handle_opencode_line(
            oversized_line,
            state,
            lambda event_type, payload: emitted.append((event_type, payload)),
            request,
        )

    assert emitted == []
    assert state == {"latest_text": "", "text_parts": [], "text_size_bytes": 0}
