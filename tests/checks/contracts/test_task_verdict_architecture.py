from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_task_verdict_bucket_projection_has_dedicated_boundary() -> None:
    task_verdicts_source = (REPO_ROOT / "src" / "loopora" / "task_verdicts.py").read_text(encoding="utf-8")
    bucket_source = (REPO_ROOT / "src" / "loopora" / "task_verdict_buckets.py").read_text(encoding="utf-8")
    status_source = (REPO_ROOT / "src" / "loopora" / "task_verdict_status.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.task_verdict_buckets import" in task_verdicts_source
    assert "from loopora.task_verdict_status import" in task_verdicts_source
    assert "def build_task_verdict_buckets" in bucket_source
    assert "def status_from_gatekeeper" in status_source
    assert "def summary_for_task_verdict" in status_source
    assert "def _append_coverage_target_buckets" not in task_verdicts_source
    assert "def _dedupe_bucket_items" not in task_verdicts_source
    assert "def _passed_gatekeeper_status" not in task_verdicts_source
    assert "def _required_coverage_status" not in task_verdicts_source
    assert "task_verdict_buckets.py" in contracts_source
    assert "task_verdict_status.py" in contracts_source
