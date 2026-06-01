from __future__ import annotations

import json
from pathlib import Path

from loopora.run_artifacts import RunArtifactLayout


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_ledger(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8")


def _coverage_layout(tmp_path: Path) -> RunArtifactLayout:
    layout = RunArtifactLayout(tmp_path / "run_coverage")
    layout.initialize()
    _write_json(
        layout.contract_compiled_spec_path,
        {
            "checks": [
                {
                    "id": "check_001",
                    "title": "Required proof",
                    "details": "The required proof is verified.",
                }
            ]
        },
    )
    _write_json(layout.run_contract_path, {"completion_mode": "gatekeeper"})
    return layout
