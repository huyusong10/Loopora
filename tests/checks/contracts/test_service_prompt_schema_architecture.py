from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source

from loopora import service_prompt_builder_schemas
from loopora import service_prompt_checks
from loopora import service_prompt_guidance_schemas
from loopora import service_prompt_requests
from loopora import service_prompt_review_schemas
from loopora import service_prompt_schemas
from loopora import service_prompts


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
    contracts_source = design_boundary_source()

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
