from __future__ import annotations

from pathlib import Path

from bundle_derive_test_support import create_manual_loop


def test_derive_bundle_keeps_role_definition_keys_consistent(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_manual_loop(
        service,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        name="Parallel Review Loop",
        orchestration_id="builtin:build_then_parallel_review",
    )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived Parallel Review")

    role_definition_keys = {role["key"] for role in derived["role_definitions"]}
    workflow_keys = {role["role_definition_key"] for role in derived["workflow"]["roles"]}
    assert workflow_keys <= role_definition_keys
    assert "contract-inspector" in role_definition_keys
    assert "evidence-inspector" in role_definition_keys
