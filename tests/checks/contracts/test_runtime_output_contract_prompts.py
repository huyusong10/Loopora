from __future__ import annotations

from loopora.context_flow import output_contract_prompt
from loopora.service import CHALLENGER_SCHEMA, GENERATOR_SCHEMA, TESTER_SCHEMA, VERIFIER_SCHEMA
from loopora.service_prompts import CUSTOM_SCHEMA


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


def _required_array_fields(schema: dict) -> list[str]:
    properties = schema.get("properties") or {}
    return [
        field
        for field in schema.get("required", [])
        if isinstance(properties.get(field), dict) and properties[field].get("type") == "array"
    ]
