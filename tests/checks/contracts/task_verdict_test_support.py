from __future__ import annotations

import json
from pathlib import Path


def write_task_verdict_coverage(run_dir: Path, payload: dict) -> None:
    coverage_path = run_dir / "evidence" / "coverage.json"
    coverage_path.parent.mkdir(parents=True)
    coverage_payload = {"schema_version": 1, **payload}
    coverage_path.write_text(json.dumps(coverage_payload, ensure_ascii=False), encoding="utf-8")
