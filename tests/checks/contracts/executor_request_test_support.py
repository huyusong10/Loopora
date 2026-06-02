from __future__ import annotations

from pathlib import Path

from loopora.executor import RoleRequest


def role_request(tmp_path: Path, *, executor_kind: str, model: str, reasoning_effort: str) -> RoleRequest:
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    return RoleRequest(
        run_id="run_test",
        role="tester",
        prompt="Return JSON only.",
        workdir=tmp_path,
        model=model,
        reasoning_effort=reasoning_effort,
        output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]},
        output_path=run_dir / "output.json",
        run_dir=run_dir,
        executor_kind=executor_kind,
    )
