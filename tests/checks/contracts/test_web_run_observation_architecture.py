from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_observation_has_dedicated_service_boundary() -> None:
    lifecycle_source = (REPO_ROOT / "src" / "loopora" / "service_run_lifecycle.py").read_text(encoding="utf-8")
    observation_source = (REPO_ROOT / "src" / "loopora" / "service_run_observation.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_run_observation import ServiceRunObservationMixin" in lifecycle_source
    assert "def run_observation_snapshot" not in lifecycle_source
    assert "def run_observation_snapshot" in observation_source
    assert "def get_runtime_activity" in observation_source
    assert "service_run_observation.py" in design_source
