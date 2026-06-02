from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from loopora.executor import (
    EXECUTOR_OUTPUT_MAX_BYTES,
    ExecutorError,
    RealCodexExecutor,
    RoleRequest,
)


def test_real_executor_supports_custom_command_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    custom_path = fake_bin / "custom-tool"
    custom_path.write_text(
        "#!/bin/sh\n"
        "output=''\n"
        "while [ \"$#\" -gt 0 ]; do\n"
        "  if [ \"$1\" = \"--output\" ]; then\n"
        "    output=\"$2\"\n"
        "    shift 2\n"
        "    continue\n"
        "  fi\n"
        "  shift\n"
        "done\n"
        "printf '{\"ok\": true, \"engine\": \"custom\"}\\n' > \"$output\"\n"
        "printf 'custom wrapper complete\\n'\n",
        encoding="utf-8",
    )
    custom_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="custom_helper",
        prompt="Emit JSON only.",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        output_path=run_dir / "custom_output.json",
        run_dir=run_dir,
        executor_kind="custom",
        executor_mode="command",
        command_cli="custom-tool",
        command_args_text="--output\n{output_path}\n{prompt}\n",
    )

    emitted: list[tuple[str, dict]] = []
    executor = RealCodexExecutor()
    payload = executor.execute(
        request,
        lambda event_type, payload: emitted.append((event_type, payload)),
        lambda: False,
        lambda _pid: None,
    )

    assert payload == {"ok": True, "engine": "custom"}
    assert request.output_path.exists()
    assert ("codex_event", {"type": "stdout", "message": "custom wrapper complete"}) in emitted


def test_real_executor_rejects_oversized_custom_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    script = (
        "import sys; "
        "from pathlib import Path; "
        f"Path(sys.argv[1]).write_text('{{\"blob\":\"' + ('x' * {EXECUTOR_OUTPUT_MAX_BYTES + 1}) + '\"}}', "
        "encoding='utf-8')"
    )
    request = RoleRequest(
        run_id="run_test",
        role="custom_helper",
        prompt="Emit JSON only.",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={"type": "object", "properties": {"blob": {"type": "string"}}, "required": ["blob"]},
        output_path=run_dir / "custom_output.json",
        run_dir=run_dir,
        executor_kind="custom",
        executor_mode="command",
        command_cli=sys.executable,
        command_args_text=f"-c\n{script}\n{{output_path}}\n{{prompt}}\n",
    )

    executor = RealCodexExecutor()
    with pytest.raises(ExecutorError, match="output file is too large"):
        executor.execute(
            request,
            lambda _event_type, _payload: None,
            lambda: False,
            lambda _pid: None,
        )


def test_real_executor_rejects_non_utf8_custom_output(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    script = "import sys; from pathlib import Path; Path(sys.argv[1]).write_bytes(b'\\xff')"
    request = RoleRequest(
        run_id="run_test",
        role="custom_helper",
        prompt="Emit JSON only.",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={"type": "object", "properties": {}, "additionalProperties": True},
        output_path=run_dir / "custom_output.json",
        run_dir=run_dir,
        executor_kind="custom",
        executor_mode="command",
        command_cli=sys.executable,
        command_args_text=f"-c\n{script}\n{{output_path}}\n{{prompt}}\n",
    )

    executor = RealCodexExecutor()
    with pytest.raises(ExecutorError, match="non-UTF-8 output"):
        executor.execute(
            request,
            lambda _event_type, _payload: None,
            lambda: False,
            lambda _pid: None,
        )
