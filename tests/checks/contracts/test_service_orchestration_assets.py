from __future__ import annotations


def test_service_accepts_strategy_source_for_orchestration_mutations(service_factory) -> None:
    service = service_factory(scenario="success")

    created = service.create_orchestration(
        name="Strategy Source Inspect First",
        description="Creates through the legacy Loopfile-compatible source field.",
        workflow={"preset": "inspect_first"},
    )
    updated = service.update_orchestration(
        created["id"],
        name="Strategy Source Build First",
        description="Updates through the Strategy Source service boundary.",
        strategy_source={"preset": "build_first"},
    )

    assert created["workflow_json"]["preset"] == "inspect_first"
    assert updated["workflow_json"]["preset"] == "build_first"
