from __future__ import annotations

from pathlib import Path

from loopora.agent_adapter_role_contracts import role_agent_body
from loopora.context_flow import output_contract_prompt, system_prompt_prefix
from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
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


def test_inspector_prompts_keep_dynamic_checks_for_nonduplicated_extra_checks() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    prompts = [
        mixin._tester_prompt(compiled_spec, 0, "default"),
        output_contract_prompt("inspector"),
        role_agent_body("inspector"),
    ]

    for prompt in prompts:
        normalized = prompt.lower()
        assert "dynamic_checks" in prompt
        assert "unless you performed a new reproducible check" in normalized
        assert "not already represented by" in normalized
        assert "listed done when/check id" in normalized
        assert "scope, checksum, or coverage target" in normalized
        assert "checksum/scope, or command-success facts" in normalized
        assert "extra nonduplicated claim it proves" in normalized
    assert "unless you performed a new reproducible check" not in role_agent_body("builder").lower()
    assert "unless you performed a new reproducible check" not in role_agent_body("gatekeeper").lower()


def test_inspector_prompts_prefer_exact_primary_proof_before_extra_sanity_checks() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    prompts = [
        mixin._tester_prompt(compiled_spec, 0, "default"),
        system_prompt_prefix("inspector"),
        role_agent_body("inspector"),
    ]

    for prompt in prompts:
        normalized = prompt.lower()
        assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE in prompt
        assert "explicit done when/check commands" in normalized
        assert "run that exact command" in normalized
        assert "do not add broader discovery/sanity variants" in normalized
        assert "primary command fails, is ambiguous" in normalized
        assert "specific uncovered target" in normalized

    assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE not in role_agent_body("builder")
    assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE not in role_agent_body("gatekeeper")


def test_proof_command_output_guidance_rejects_truncated_fallbacks() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    tester_output = _prompt_contract_tester_output()
    prompts = [
        mixin._generator_prompt(compiled_spec, Path("/tmp/example"), 0, "default"),
        mixin._tester_prompt(compiled_spec, 0, "default"),
        mixin._verifier_prompt(compiled_spec, tester_output, 0, "default"),
        system_prompt_prefix("builder"),
        system_prompt_prefix("inspector"),
        system_prompt_prefix("gatekeeper"),
        role_agent_body("builder"),
        role_agent_body("inspector"),
        role_agent_body("gatekeeper"),
    ]

    for prompt in prompts:
        normalized = prompt.lower()
        assert PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE in prompt
        assert "proof, sanity, discovery, directory-listing, context-check, or evidence-producing commands" in normalized
        assert "`head`" in prompt
        assert "`head -c`" in prompt
        assert "`tail`" in prompt
        assert "`sed`" in prompt
        assert "`jq`" in prompt
        assert "`grep`" in prompt
        assert "`wc`" in prompt
        assert "do not run a truncated or filtered fallback" in normalized
        assert "preserve the complete listing" in normalized
        assert "do not replace it with `ls ... | head`" in normalized
        assert "explicit exit code" in normalized
        assert "write it directly to a task-owned path" in normalized
        assert "do not stage it in `/tmp`" in normalized
        assert ".loopora/agent_artifacts/<run_id>/<step_id>/" in prompt
        assert "count-only probes" in normalized


def test_inspector_prompts_reuse_upstream_proof_artifacts_before_reruns() -> None:
    mixin = PromptHarness()
    compiled_spec = _prompt_contract_spec()
    prompts = [
        mixin._tester_prompt(compiled_spec, 0, "default"),
        system_prompt_prefix("inspector"),
        role_agent_body("inspector"),
    ]

    for prompt in prompts:
        normalized = prompt.lower()
        assert INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE in prompt
        assert "fresh upstream task-owned proof artifacts" in normalized
        assert "inspect known upstream evidence refs" in normalized
        assert "without rerunning the identical command" in normalized
        assert "missing, stale, ambiguous" in normalized


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
