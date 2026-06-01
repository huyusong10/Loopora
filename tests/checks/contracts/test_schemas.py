from __future__ import annotations

from pathlib import Path

from loopora.context_flow import (
    EVIDENCE_ITEM_SCHEMA,
    ITERATION_SUMMARY_SCHEMA,
    LATEST_STATE_SCHEMA,
    STEP_HANDOFF_SCHEMA,
    STEP_INSTRUCTION_CONTEXT_SCHEMA,
    output_contract_prompt,
)
from loopora.service import (
    CHALLENGER_SCHEMA,
    CHECK_PLANNER_SCHEMA,
    GENERATOR_SCHEMA,
    TESTER_SCHEMA,
    VERIFIER_SCHEMA,
)
from loopora.service_prompts import CUSTOM_SCHEMA, ServiceRunPromptMixin
import loopora.context_schema_evidence as context_schema_evidence
import loopora.context_schema_shared as context_schema_shared
import loopora.context_schemas as context_schemas
import loopora.service_prompt_checks as service_prompt_checks
import loopora.service_prompt_builder_schemas as service_prompt_builder_schemas
import loopora.service_prompt_guidance_schemas as service_prompt_guidance_schemas
import loopora.service_prompt_requests as service_prompt_requests
import loopora.service_prompt_review_schemas as service_prompt_review_schemas
import loopora.service_prompt_schemas as service_prompt_schemas
import loopora.service_prompts as service_prompts


class PromptHarness(ServiceRunPromptMixin):
    def _is_bootstrap_workspace(self, _workdir: Path) -> bool:
        return False


def test_object_schemas_with_properties_are_strict_and_exhaustive() -> None:
    schemas = {
        "GENERATOR_SCHEMA": GENERATOR_SCHEMA,
        "CHECK_PLANNER_SCHEMA": CHECK_PLANNER_SCHEMA,
        "TESTER_SCHEMA": TESTER_SCHEMA,
        "VERIFIER_SCHEMA": VERIFIER_SCHEMA,
        "CHALLENGER_SCHEMA": CHALLENGER_SCHEMA,
        "CUSTOM_SCHEMA": CUSTOM_SCHEMA,
        "EVIDENCE_ITEM_SCHEMA": EVIDENCE_ITEM_SCHEMA,
        "STEP_INSTRUCTION_CONTEXT_SCHEMA": STEP_INSTRUCTION_CONTEXT_SCHEMA,
        "STEP_HANDOFF_SCHEMA": STEP_HANDOFF_SCHEMA,
        "ITERATION_SUMMARY_SCHEMA": ITERATION_SUMMARY_SCHEMA,
        "LATEST_STATE_SCHEMA": LATEST_STATE_SCHEMA,
    }

    for schema_name, schema in schemas.items():
        for path, issue in _find_schema_issues(schema):
            raise AssertionError(f"{schema_name} at {path}: {issue}")


def test_service_prompts_keep_role_output_schemas_in_dedicated_module() -> None:
    schema_sources = {
        "GENERATOR_SCHEMA": service_prompt_builder_schemas,
        "CHECK_PLANNER_SCHEMA": service_prompt_builder_schemas,
        "TESTER_SCHEMA": service_prompt_review_schemas,
        "VERIFIER_SCHEMA": service_prompt_review_schemas,
        "CHALLENGER_SCHEMA": service_prompt_guidance_schemas,
        "CUSTOM_SCHEMA": service_prompt_guidance_schemas,
        "BUILDER_SCHEMA": service_prompt_builder_schemas,
        "INSPECTOR_SCHEMA": service_prompt_review_schemas,
        "GATEKEEPER_SCHEMA": service_prompt_review_schemas,
        "GUIDE_SCHEMA": service_prompt_guidance_schemas,
    }
    for schema_name in (
        "GENERATOR_SCHEMA",
        "CHECK_PLANNER_SCHEMA",
        "TESTER_SCHEMA",
        "VERIFIER_SCHEMA",
        "CHALLENGER_SCHEMA",
        "CUSTOM_SCHEMA",
        "BUILDER_SCHEMA",
        "INSPECTOR_SCHEMA",
        "GATEKEEPER_SCHEMA",
        "GUIDE_SCHEMA",
    ):
        assert getattr(service_prompts, schema_name) is getattr(service_prompt_schemas, schema_name)
        assert getattr(service_prompt_schemas, schema_name) is getattr(schema_sources[schema_name], schema_name)
    assert service_prompts.GeneratorPromptRequest is service_prompt_requests.GeneratorPromptRequest
    assert service_prompt_checks.normalize_generated_checks("not a list") == []


def test_service_prompt_helpers_stay_out_of_prompt_mixin_source() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    prompts_source = (repo_root / "src" / "loopora" / "service_prompts.py").read_text(encoding="utf-8")
    schemas_source = (repo_root / "src" / "loopora" / "service_prompt_schemas.py").read_text(encoding="utf-8")
    builder_schemas_source = (repo_root / "src" / "loopora" / "service_prompt_builder_schemas.py").read_text(
        encoding="utf-8"
    )
    review_schemas_source = (repo_root / "src" / "loopora" / "service_prompt_review_schemas.py").read_text(
        encoding="utf-8"
    )
    guidance_schemas_source = (repo_root / "src" / "loopora" / "service_prompt_guidance_schemas.py").read_text(
        encoding="utf-8"
    )
    request_source = (repo_root / "src" / "loopora" / "service_prompt_requests.py").read_text(encoding="utf-8")
    checks_source = (repo_root / "src" / "loopora" / "service_prompt_checks.py").read_text(encoding="utf-8")
    contracts_source = (repo_root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_prompt_builder_schemas import" in schemas_source
    assert "from loopora.service_prompt_review_schemas import" in schemas_source
    assert "from loopora.service_prompt_guidance_schemas import" in schemas_source
    assert "GENERATOR_SCHEMA = {" in builder_schemas_source
    assert "TESTER_SCHEMA = {" in review_schemas_source
    assert "CHALLENGER_SCHEMA = {" in guidance_schemas_source
    assert "GENERATOR_SCHEMA = {" not in schemas_source
    assert "TESTER_SCHEMA = {" not in schemas_source
    assert "CHALLENGER_SCHEMA = {" not in schemas_source
    assert "class GeneratorPromptRequest" in request_source
    assert "def generator_prompt_request_from_args" in request_source
    assert "def normalize_generated_checks" in checks_source
    assert "class GeneratorPromptRequest" not in prompts_source
    assert "def generator_prompt_request_from_args" not in prompts_source
    assert "def normalize_generated_checks" not in prompts_source
    assert "service_prompt_requests.py" in contracts_source
    assert "service_prompt_checks.py" in contracts_source
    assert "service_prompt_builder_schemas.py" in contracts_source
    assert "service_prompt_review_schemas.py" in contracts_source
    assert "service_prompt_guidance_schemas.py" in contracts_source


def test_context_evidence_schemas_have_dedicated_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    evidence_source = (repo_root / "src" / "loopora" / "context_schema_evidence.py").read_text(encoding="utf-8")
    shared_source = (repo_root / "src" / "loopora" / "context_schema_shared.py").read_text(encoding="utf-8")
    step_source = (repo_root / "src" / "loopora" / "context_schema_step_instruction.py").read_text(encoding="utf-8")
    iteration_source = (repo_root / "src" / "loopora" / "context_schema_iteration_state.py").read_text(encoding="utf-8")
    schemas_source = (repo_root / "src" / "loopora" / "context_schemas.py").read_text(encoding="utf-8")
    contracts_source = (repo_root / "design" / "contracts.md").read_text(encoding="utf-8")

    for marker in (
        "ARTIFACT_REF_SCHEMA = {",
        "EVIDENCE_ITEM_SCHEMA = {",
        "EVIDENCE_MANIFEST_CLAIM_SCHEMA = {",
    ):
        assert marker in evidence_source
        assert marker not in shared_source
    assert "from loopora.context_schema_evidence import" in shared_source
    assert "from loopora.context_schema_evidence import" in step_source
    assert "from loopora.context_schema_evidence import" in iteration_source
    assert "from loopora.context_schema_evidence import" in schemas_source
    assert context_schema_shared.EVIDENCE_ITEM_SCHEMA is context_schema_evidence.EVIDENCE_ITEM_SCHEMA
    assert context_schemas.EVIDENCE_MANIFEST_CLAIM_SCHEMA is context_schema_evidence.EVIDENCE_MANIFEST_CLAIM_SCHEMA
    assert "context_schema_evidence.py" in contracts_source


def test_builder_schema_and_prompt_expose_proof_artifact_fields() -> None:
    proof_fields = {"proof_files", "proof_artifacts", "artifact_paths"}

    assert proof_fields <= set(GENERATOR_SCHEMA["required"])
    assert proof_fields <= set(GENERATOR_SCHEMA["properties"])
    assert all(field in output_contract_prompt("builder") for field in proof_fields)


def test_runtime_output_contracts_name_top_level_schema_required_fields() -> None:
    contracts_and_schemas = [
        (output_contract_prompt("builder"), GENERATOR_SCHEMA),
        (output_contract_prompt("inspector"), TESTER_SCHEMA),
        (output_contract_prompt("gatekeeper"), VERIFIER_SCHEMA),
        (output_contract_prompt("guide"), CHALLENGER_SCHEMA),
        (output_contract_prompt("custom"), CUSTOM_SCHEMA),
    ]

    for prompt, schema in contracts_and_schemas:
        missing = [field for field in schema["required"] if field not in prompt]
        assert not missing


def test_runtime_output_contracts_explain_empty_required_arrays() -> None:
    contracts_and_schemas = [
        (output_contract_prompt("builder"), GENERATOR_SCHEMA),
        (output_contract_prompt("inspector"), TESTER_SCHEMA),
        (output_contract_prompt("gatekeeper"), VERIFIER_SCHEMA),
        (output_contract_prompt("custom"), CUSTOM_SCHEMA),
    ]

    for prompt, schema in contracts_and_schemas:
        array_fields = _required_array_fields(schema)
        assert array_fields
        assert "empty" in prompt.lower()
        for field in array_fields:
            assert field in prompt


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


def _find_schema_issues(schema: object, path: str = "root") -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object" and "properties" in schema:
            if schema.get("additionalProperties") is not False:
                failures.append((path, "objects with properties must declare additionalProperties: false"))
            property_names = list(schema["properties"].keys())
            required = schema.get("required", [])
            missing = [key for key in property_names if key not in required]
            if missing:
                failures.append((path, f"missing required keys: {missing}"))
        for key, value in schema.items():
            failures.extend(_find_schema_issues(value, f"{path}.{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            failures.extend(_find_schema_issues(item, f"{path}[{index}]"))
    return failures
