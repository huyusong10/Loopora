from __future__ import annotations

from service_architecture_test_support import loopora_source


def test_run_lifecycle_delegates_agent_current_step_projection() -> None:
    lifecycle_source = loopora_source("service_run_lifecycle.py")
    projection_source = loopora_source("service_run_current_step_projection.py")
    acceptance_source = loopora_source("service_run_acceptance.py") + loopora_source("service_run_acceptance_evidence.py")

    assert (
        "from loopora.service_run_current_step_projection import current_agent_step_projection"
        in loopora_source("service_run_observation.py")
    )
    assert "from loopora.service_run_acceptance import ServiceRunAcceptanceMixin" in lifecycle_source
    assert "agent_native_active_step_view" not in lifecycle_source
    assert "def current_agent_step_projection" in projection_source
    assert "agent_native_active_step_view" in projection_source
    assert "def run_acceptance_evidence_payload_from_takeaways" in acceptance_source
    assert "def _acceptance_judgment_summary" not in lifecycle_source
