from __future__ import annotations


def test_service_accepts_strategy_source_for_orchestration_mutations(service_factory) -> None:
    service = service_factory(scenario="success")

    created = service.create_orchestration(
        name="Strategy Source Inspect First",
        description="Creates through the Strategy Source service boundary.",
        strategy_source={"preset": "inspect_first"},
    )
    updated = service.update_orchestration(
        created["id"],
        name="Strategy Source Build First",
        description="Updates through the Strategy Source service boundary.",
        strategy_source={"preset": "build_first"},
    )

    assert created["workflow_json"]["preset"] == "inspect_first"
    assert updated["workflow_json"]["preset"] == "build_first"


def test_service_rejects_conflicting_strategy_source_aliases_for_orchestration_create(service_factory) -> None:
    service = service_factory(scenario="success")

    try:
        service.create_orchestration(
            name="Conflicting Strategy Source",
            strategy_source={"preset": "inspect_first"},
            workflow={"preset": "build_first"},
        )
    except TypeError as exc:
        assert "strategy_source and workflow cannot both be provided" in str(exc)
    else:
        raise AssertionError("conflicting strategy source aliases should be rejected")
