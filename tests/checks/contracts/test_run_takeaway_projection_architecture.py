from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_takeaway_projection_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    projection_source = (REPO_ROOT / "src" / "loopora" / "service_run_takeaway_projection.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_run_takeaway_projection import ServiceRunTakeawayProjectionMixin" in lifecycle_source
    assert "ServiceRunTakeawayProjectionMixin" in lifecycle_source
    assert "def _backfill_missing_run_takeaway_projections" not in lifecycle_source
    assert "def _record_run_takeaway_projection_for_event" in projection_source
    assert "def _backfill_missing_run_takeaway_projections" in projection_source
    assert "service_run_takeaway_projection.py" in design_source
