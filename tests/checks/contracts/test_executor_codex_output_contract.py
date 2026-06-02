from __future__ import annotations

import os
from pathlib import Path

import pytest

from loopora.executor import ExecutorError, RealCodexExecutor, RoleRequest


def test_real_codex_executor_can_parse_resume_output_without_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex_path = fake_bin / "codex"
    codex_path.write_text(
        "#!/bin/sh\n"
        "output=''\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--output-last-message\" ]; then\n"
        "    output=\"$2\"\n"
        "    shift 2\n"
        "    continue\n"
        "  fi\n"
        "  shift\n"
        "done\n"
        "printf '```json\\n{\"ok\": true, \"mode\": \"resume\"}\\n```\\n' > \"$output\"\n"
        "printf '{\"type\":\"stdout\",\"message\":\"resume ok\"}\\n'\n",
        encoding="utf-8",
    )
    codex_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="generator",
        prompt="Return JSON only.",
        workdir=tmp_path,
        model="gpt-5.4",
        reasoning_effort="medium",
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        output_path=run_dir / "generator_output.json",
        run_dir=run_dir,
        inherit_session=True,
        resume_session_id="session-123",
    )

    emitted: list[tuple[str, dict]] = []
    executor = RealCodexExecutor()
    payload = executor.execute(
        request,
        lambda event_type, payload: emitted.append((event_type, payload)),
        lambda: False,
        lambda _pid: None,
    )

    assert payload == {"ok": True, "mode": "resume"}
    assert ("codex_event", {"type": "stdout", "message": "resume ok"}) in emitted


def test_real_codex_executor_rejects_non_object_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    codex_path = fake_bin / "codex"
    codex_path.write_text(
        "#!/bin/sh\n"
        "output=''\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--output-last-message\" ]; then\n"
        "    output=\"$2\"\n"
        "    shift 2\n"
        "    continue\n"
        "  fi\n"
        "  shift\n"
        "done\n"
        "printf '[{\"ok\": true}]\\n' > \"$output\"\n",
        encoding="utf-8",
    )
    codex_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="generator",
        prompt="Return JSON only.",
        workdir=tmp_path,
        model="gpt-5.4",
        reasoning_effort="medium",
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        output_path=run_dir / "generator_output.json",
        run_dir=run_dir,
    )

    executor = RealCodexExecutor()
    with pytest.raises(ExecutorError, match="codex exec did not produce a JSON object"):
        executor.execute(
            request,
            lambda _event_type, _payload: None,
            lambda: False,
            lambda _pid: None,
        )
