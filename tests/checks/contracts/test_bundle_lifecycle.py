from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.run_takeaways import build_run_key_takeaways
from loopora.service import LooporaError


def _assert_imported_bundle_runtime_judgment_projection(run_contract: dict, prompt_text: str, imported: dict) -> None:
    source_bundle = run_contract["source_bundle"]
    assert source_bundle == _expected_imported_source_bundle(imported)
    assert run_contract["collaboration_summary"].startswith("Prefer evidence")
    assert any("Prefer evidence before rushing forward" in item for item in run_contract["judgment_tradeoffs"])
    assert any("Start with evidence, then commit to one repair slice." in item for item in run_contract["execution_strategy"])
    assert any(item["posture_notes"] == "Treat maintainability debt as first-class in this task." for item in run_contract["role_postures"])
    assert any(item["posture_notes"] == "Prefer project-owned commands and primary artifacts." for item in run_contract["role_postures"])
    assert any(item["posture_notes"] == "Do not pass brittle fixes just because the happy path moved." for item in run_contract["role_postures"])
    assert "Bundle collaboration summary: Prefer evidence before rushing forward." in prompt_text
    assert "Judgment tradeoffs:" in prompt_text
    assert "Execution strategy:" in prompt_text
    assert "Role postures:" in prompt_text
    assert "Prefer evidence before rushing forward" in prompt_text
    assert "Start with evidence, then commit to one repair slice." in prompt_text
    assert "Success surface:" in prompt_text
    assert "The implementation stays maintainable for the next round." in prompt_text
    assert "Fake done states:" in prompt_text
    assert "A patch that only fixes the happy path while leaving obvious duplication behind." in prompt_text
    assert "Evidence preferences:" in prompt_text
    assert "Prefer real project commands and reproducible tests over screenshots alone." in prompt_text
    assert "Residual risk:" in prompt_text
    assert "Minor copy polish can wait, but structural regressions should fail closed." in prompt_text
    assert "Role definition posture:" in prompt_text
    assert "Treat maintainability debt as first-class in this task." in prompt_text


def _assert_imported_bundle_takeaway_projection(takeaways: dict, imported: dict) -> None:
    judgment_contract = takeaways["judgment_contract"]
    assert judgment_contract["source_bundle"] == _expected_imported_source_bundle(imported)
    assert judgment_contract["collaboration_summary"].startswith("Prefer evidence")
    assert any("Prefer evidence before rushing forward" in item for item in judgment_contract["judgment_tradeoffs"])
    assert any("Treat maintainability debt as first-class in this task." in item for item in judgment_contract["role_postures"])
    assert any("Prefer project-owned commands and primary artifacts." in item for item in judgment_contract["role_postures"])
    assert judgment_contract["goal"] == "Ship the requested behavior without creating brittle structure."


def _assert_imported_bundle_acceptance_projection(accepted_payload: dict, imported: dict) -> None:
    expected_source_bundle = _expected_imported_source_bundle(imported)
    assert accepted_payload["source_bundle"] == expected_source_bundle
    assert accepted_payload["judgment_contract"]["source_bundle"] == expected_source_bundle
    assert accepted_payload["run_contract_path"] == "contract/run_contract.json"
    assert accepted_payload["judgment_contract_summary"].startswith("Prefer evidence")
    assert any("Prefer evidence before rushing forward" in item for item in accepted_payload["judgment_tradeoffs"])
    assert any("Treat maintainability debt as first-class" in item for item in accepted_payload["role_postures"])
    assert accepted_payload["success_surface"] == ["The implementation stays maintainable for the next round."]
    assert accepted_payload["fake_done_states"] == [
        "A patch that only fixes the happy path while leaving obvious duplication behind."
    ]
    assert accepted_payload["evidence_preferences"] == [
        "Prefer real project commands and reproducible tests over screenshots alone."
    ]
    assert accepted_payload["residual_risk"] == "Minor copy polish can wait, but structural regressions should fail closed."


def _expected_imported_source_bundle(imported: dict) -> dict:
    exported_bundle_data = Path(imported["bundle_yaml_path"]).read_bytes()
    return {
        "id": imported["id"],
        "name": imported["name"],
        "revision": imported["revision"],
        "source_bundle_id": imported["source_bundle_id"],
        "imported_from_path": imported["imported_from_path"],
        "bundle_sha256": hashlib.sha256(exported_bundle_data).hexdigest(),
        "bundle_bytes": len(exported_bundle_data),
        "bundle_yaml_path": imported["bundle_yaml_path"],
    }


def test_service_imports_and_exports_bundle_round_trip(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))

    assert imported["name"] == "Guided Inspect First"
    assert imported["loop"] is not None
    assert imported["orchestration"] is not None
    assert len(imported["role_definitions"]) == 3

    exported = service.export_bundle(imported["id"])

    assert exported["collaboration_summary"].startswith("Prefer evidence")
    assert exported["workflow"]["collaboration_intent"] == "Start with evidence, then commit to one repair slice."
    assert exported["spec"]["markdown"].startswith("# Task")
    assert exported["role_definitions"][0]["posture_notes"]

    rerun = service.rerun(imported["loop_id"])
    assert rerun["status"] == "succeeded"
    run_dir = Path(rerun["runs_dir"])
    run_contract = json.loads((run_dir / "contract" / "run_contract.json").read_text(encoding="utf-8"))
    prompt_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((run_dir / "context" / "role_requests").glob("*.prompt.txt"))
    )
    _assert_imported_bundle_runtime_judgment_projection(run_contract, prompt_text, imported)
    takeaways = build_run_key_takeaways(rerun)
    _assert_imported_bundle_takeaway_projection(takeaways, imported)
    service.accept_run_result(rerun["id"])
    accepted_payload = service.recent_run_events(rerun["id"], event_types={"run_result_accepted"})[-1]["payload"]
    _assert_imported_bundle_acceptance_projection(accepted_payload, imported)


@pytest.mark.parametrize(
    ("yaml_line", "error_text"),
    (
        ('  delta_threshold: "inf"', "bundle loop settings must use finite numbers"),
        ("  delta_threshold: -0.1", "bundle loop.delta_threshold must be >= 0"),
    ),
)
def test_bundle_import_rejects_invalid_loop_runtime_numbers(
    service_factory,
    sample_workdir: Path,
    yaml_line: str,
    error_text: str,
) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace("  delta_threshold: 0.005", yaml_line)

    with pytest.raises(LooporaError, match=error_text):
        service.import_bundle_text(yaml_text)


@pytest.mark.parametrize(
    ("yaml_line", "error_text"),
    (
        ("  max_iters: 4.5", "bundle loop.max_iters must be an integer"),
        ("  max_role_retries: 1.5", "bundle loop.max_role_retries must be an integer"),
        ("  trigger_window: 2.5", "bundle loop.trigger_window must be an integer"),
        ("  regression_window: 2.5", "bundle loop.regression_window must be an integer"),
    ),
)
def test_bundle_import_rejects_fractional_integer_runtime_numbers(
    service_factory,
    sample_workdir: Path,
    yaml_line: str,
    error_text: str,
) -> None:
    service = service_factory(scenario="success")
    original_key = yaml_line.split(":", 1)[0].strip()
    original_line = {
        "max_iters": "  max_iters: 4",
        "max_role_retries": "  max_role_retries: 1",
        "trigger_window": "  trigger_window: 2",
        "regression_window": "  regression_window: 2",
    }[original_key]
    yaml_text = _bundle_yaml(sample_workdir).replace(original_line, yaml_line)

    with pytest.raises(LooporaError, match=error_text):
        service.import_bundle_text(yaml_text)


def test_bundle_import_preserves_zero_loop_runtime_numbers(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace("  max_iters: 4", "  max_iters: 0")
        .replace("  max_role_retries: 1", "  max_role_retries: 0")
        .replace("  delta_threshold: 0.005", "  delta_threshold: 0")
    )

    imported = service.import_bundle_text(yaml_text)

    assert imported["loop"]["max_iters"] == 0
    assert imported["loop"]["max_role_retries"] == 0
    assert imported["loop"]["delta_threshold"] == 0.0
    exported = service.export_bundle(imported["id"])
    assert exported["loop"]["max_iters"] == 0
    assert exported["loop"]["max_role_retries"] == 0
    assert exported["loop"]["delta_threshold"] == 0.0


def test_bundle_import_accepts_lossless_float_encoded_integer_runtime_numbers(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace("  max_iters: 4", "  max_iters: 4.0")
        .replace("  max_role_retries: 1", "  max_role_retries: 1.0")
        .replace("  trigger_window: 2", "  trigger_window: 2.0")
        .replace("  regression_window: 2", "  regression_window: 2.0")
    )

    imported = service.import_bundle_text(yaml_text)

    assert imported["loop"]["max_iters"] == 4
    assert imported["loop"]["max_role_retries"] == 1
    assert imported["loop"]["trigger_window"] == 2
    assert imported["loop"]["regression_window"] == 2
