from __future__ import annotations

from pathlib import Path

from loopora.context_flow import output_contract_prompt
from loopora.service import (
    CHALLENGER_SCHEMA,
    CHECK_PLANNER_SCHEMA,
    GENERATOR_SCHEMA,
    TESTER_SCHEMA,
    VERIFIER_SCHEMA,
)
from loopora.service_prompts import ServiceRunPromptMixin


class PromptHarness(ServiceRunPromptMixin):
    def _is_bootstrap_workspace(self, _workdir: Path) -> bool:
        return False


def test_tester_prompts_name_execution_summary_shape() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    prompts = [
        mixin._tester_prompt(compiled_spec, 0, "default"),
        output_contract_prompt("inspector"),
    ]

    for prompt in prompts:
        for field in ("total_checks", "passed", "failed", "errored", "total_duration_ms"):
            assert field in prompt


def test_gatekeeper_prompts_name_metric_and_priority_failure_shapes() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    tester_output = _prompt_contract_tester_output()
    prompts = [
        mixin._verifier_prompt(compiled_spec, tester_output, 0, "default"),
        output_contract_prompt("gatekeeper"),
    ]

    for prompt in prompts:
        for field in (
            "metrics",
            "name",
            "value",
            "threshold",
            "passed",
            "metric_scores",
            "check_pass_rate",
            "quality_score",
            "priority_failures",
            "error_code",
            "summary",
            "coverage_results",
            "target_id",
            "status",
            "evidence_refs",
            "note",
        ):
            assert field in prompt


def test_legacy_role_prompts_name_top_level_schema_required_fields(tmp_path) -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    tester_output = _prompt_contract_tester_output()

    prompts_and_schemas = [
        (mixin._check_planner_prompt(compiled_spec), CHECK_PLANNER_SCHEMA),
        (mixin._generator_prompt(compiled_spec, tmp_path, 0, "default"), GENERATOR_SCHEMA),
        (mixin._tester_prompt(compiled_spec, 0, "default"), TESTER_SCHEMA),
        (mixin._verifier_prompt(compiled_spec, tester_output, 0, "default"), VERIFIER_SCHEMA),
        (mixin._challenger_prompt(compiled_spec, {"stagnation_mode": "plateau"}, 1), CHALLENGER_SCHEMA),
    ]

    for prompt, schema in prompts_and_schemas:
        missing = [field for field in schema["required"] if field not in prompt]
        assert not missing


def test_legacy_role_prompts_explain_empty_required_arrays(tmp_path) -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    tester_output = _prompt_contract_tester_output()
    prompts_and_schemas = [
        (mixin._generator_prompt(compiled_spec, tmp_path, 0, "default"), GENERATOR_SCHEMA),
        (mixin._tester_prompt(compiled_spec, 0, "default"), TESTER_SCHEMA),
        (mixin._verifier_prompt(compiled_spec, tester_output, 0, "default"), VERIFIER_SCHEMA),
    ]

    for prompt, schema in prompts_and_schemas:
        array_fields = _required_array_fields(schema)
        assert array_fields
        assert "empty" in prompt.lower()
        for field in array_fields:
            assert field in prompt


def _prompt_contract_spec() -> dict:
    return {
        "goal": "Verify the main flow.",
        "checks": [
            {
                "id": "check_001",
                "title": "Main flow works",
                "details": "The main flow is usable.",
                "when": "When the user follows the main path.",
                "expect": "The main path succeeds.",
                "fail_if": "The path breaks.",
            }
        ],
        "constraints": "- Keep changes focused.",
    }


def _prompt_contract_tester_output() -> dict:
    return {
        "execution_summary": {
            "total_checks": 1,
            "passed": 0,
            "failed": 1,
            "errored": 0,
            "total_duration_ms": 10,
        },
        "check_results": [],
        "dynamic_checks": [],
        "tester_observations": "No passing proof.",
        "coverage_results": [],
    }


def _required_array_fields(schema: dict) -> list[str]:
    properties = schema.get("properties") or {}
    return [
        field
        for field in schema.get("required", [])
        if isinstance(properties.get(field), dict) and properties[field].get("type") == "array"
    ]
