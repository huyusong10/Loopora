from __future__ import annotations

import json
from pathlib import Path

from runner_helpers import _create_loop


MIN_AUTO_GENERATED_CHECK_COUNT = 3


def test_exploratory_run_generates_and_freezes_checks(
    service_factory,
    exploratory_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, exploratory_spec_file, sample_workdir, name="Exploratory Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    compiled_spec = json.loads((run_dir / "contract" / "compiled_spec.json").read_text(encoding="utf-8"))
    run_contract = json.loads((run_dir / "contract" / "run_contract.json").read_text(encoding="utf-8"))
    auto_checks = json.loads((run_dir / "contract" / "auto_checks.json").read_text(encoding="utf-8"))
    step_contexts = sorted(run_dir.glob("iterations/iter_000/steps/*/step_instruction_context.json"))
    first_step_context = json.loads(step_contexts[0].read_text(encoding="utf-8"))
    tester_output = json.loads((run_dir / "tester_output.json").read_text(encoding="utf-8"))
    snapshot_contract = service.run_observation_snapshot(run["id"])["key_takeaways"]["judgment_contract"]

    assert compiled_spec["check_mode"] == "auto_generated"
    assert len(compiled_spec["checks"]) >= MIN_AUTO_GENERATED_CHECK_COUNT
    assert any(target["id"] == "done_when.check_001" for target in compiled_spec["coverage_targets"])
    assert run_contract["compiled_spec"]["check_mode"] == "auto_generated"
    assert run_contract["compiled_spec"]["checks"] == compiled_spec["checks"]
    assert run_contract["compiled_spec"]["coverage_targets"] == compiled_spec["coverage_targets"]
    assert snapshot_contract["check_mode"] == "auto_generated"
    assert snapshot_contract["check_count"] == len(compiled_spec["checks"])
    assert any(target["id"] == "done_when.check_001" for target in snapshot_contract["coverage_targets"])
    assert auto_checks["count"] == len(compiled_spec["checks"])
    assert first_step_context["contract"]["check_mode"] == "auto_generated"
    assert first_step_context["contract"]["check_count"] == len(compiled_spec["checks"])
    assert any(target["id"] == "done_when.check_001" for target in first_step_context["contract"]["coverage_targets"])
    assert tester_output["execution_summary"]["total_checks"] == len(compiled_spec["checks"])
    assert tester_output["check_results"]


def test_generated_check_normalization_requires_object_items(service_factory) -> None:
    service = service_factory(scenario="success")

    assert service._normalize_generated_checks("not a list") == []

    checks = service._normalize_generated_checks(
        [
            "not an object",
            {
                "title": "Primary outcome",
                "details": "The run has a concrete proof path.",
                "when": "After Builder finishes.",
                "expect": "Proof is present.",
                "fail_if": "Proof is missing.",
            },
        ]
    )

    assert checks == [
        {
            "id": "check_001",
            "title": "Primary outcome",
            "details": "The run has a concrete proof path.",
            "when": "After Builder finishes.",
            "expect": "Proof is present.",
            "fail_if": "Proof is missing.",
            "source": "auto_generated",
        }
    ]
