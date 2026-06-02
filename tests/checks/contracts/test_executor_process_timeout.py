from __future__ import annotations

import os
from pathlib import Path

import pytest

from loopora.executor import ExecutorError, RealCodexExecutor, RoleRequest


def test_real_executor_times_out_after_idle_period(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex_path = fake_bin / "codex"
    codex_path.write_text("#!/bin/sh\nsleep 5\n", encoding="utf-8")
    codex_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="generator",
        prompt="test prompt",
        workdir=tmp_path,
        model="gpt-5.4",
        reasoning_effort="low",
        output_schema={"type": "object", "properties": {}, "additionalProperties": True},
        output_path=run_dir / "generator_output.json",
        run_dir=run_dir,
        idle_timeout_seconds=0.3,
    )

    executor = RealCodexExecutor()
    with pytest.raises(ExecutorError, match="produced no output"):
        executor.execute(
            request,
            lambda _event_type, _payload: None,
            lambda: False,
            lambda _pid: None,
        )
