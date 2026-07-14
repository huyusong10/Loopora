from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REVIEW_RUNNER_PATH = ROOT / "tests" / "reviews" / "run.py"


def _load_review_runner() -> Any:
    spec = importlib.util.spec_from_file_location("loopora_review_runner", REVIEW_RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


review_runner = _load_review_runner()


def case_targets(case_name: str) -> tuple[Any, dict[str, dict[str, Any]]]:
    case = review_runner._parse_case(ROOT / "tests" / "reviews" / "cases" / case_name)
    return case, {target["id"]: target for target in case.targets}


def target_terms(target: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for item in target["terms"]:
        terms.add(item["term"] if isinstance(item, dict) else item)
    return terms


def write_source_lines(root: Path, relative_path: str, lines: list[str]) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_term_hints_report(
    monkeypatch: Any,
    tmp_path: Path,
    *,
    globs: list[str],
    terms: list[str],
) -> str:
    monkeypatch.setattr(review_runner, "ROOT", tmp_path)
    artifact = review_runner._write_term_hints(
        {
            "id": "expert-language-hints",
            "type": "term_hints",
            "globs": globs,
            "terms": terms,
        },
        tmp_path,
    )
    return artifact.path.read_text(encoding="utf-8")


def write_text_index_report(case_name: str, target_id: str, tmp_path: Path) -> str:
    _case, targets = case_targets(case_name)
    artifact = review_runner._write_text_index(targets[target_id], tmp_path)
    return artifact.path.read_text(encoding="utf-8")


def write_artifact_paths_report(case_name: str, target_id: str, tmp_path: Path) -> tuple[str, list[str]]:
    _case, targets = case_targets(case_name)
    artifact = review_runner._write_artifact_paths(targets[target_id], tmp_path, cli_artifacts=[])
    return artifact.path.read_text(encoding="utf-8"), artifact.hints
