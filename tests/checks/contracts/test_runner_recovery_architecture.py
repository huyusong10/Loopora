from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_recovery_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    recovery_source = (REPO_ROOT / "src" / "loopora" / "service_run_recovery.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_run_recovery import ServiceRunRecoveryMixin" in lifecycle_source
    assert "def _recover_local_orphaned_run" not in lifecycle_source
    assert "def _reconcile_stale_runs" in recovery_source
    assert "def _try_mark_run_active" in recovery_source
    assert "service_run_recovery.py" in design_source
