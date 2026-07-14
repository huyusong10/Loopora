from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_result_acceptance_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    acceptance_source = (REPO_ROOT / "src" / "loopora" / "service_run_acceptance.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.service_run_acceptance import ServiceRunAcceptanceMixin" in lifecycle_source
    assert "ServiceRunAcceptanceMixin" in lifecycle_source
    assert "def accept_run_result" not in lifecycle_source
    assert "def reopen_run_result_acceptance" in acceptance_source
    assert "def run_result_acceptance_state" in acceptance_source
    assert "def _latest_run_result_acceptance_state_event_for_source" in acceptance_source
    assert "RUN_RESULT_ACCEPTANCE_EVENT_TYPES" in acceptance_source
    assert "service_run_acceptance.py" in design_source
