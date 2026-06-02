from __future__ import annotations

from context_architecture_test_support import design_contracts_source, loopora_source


def test_context_flow_delegates_schemas_and_prompt_contracts() -> None:
    from loopora import context_flow
    from loopora import context_prompt_contracts
    from loopora import context_schemas

    context_flow_source = loopora_source("context_flow.py")
    context_prompt_contracts_source = loopora_source("context_prompt_contracts.py")
    context_schemas_source = loopora_source("context_schemas.py")
    context_schema_boundary_source = loopora_source("context_schema_shared.py") + loopora_source(
        "context_schema_step_instruction.py"
    )
    context_schema_boundary_source += loopora_source("context_schema_iteration_state.py") + loopora_source(
        "context_schema_runtime.py"
    )
    headless_prompt_source = loopora_source("headless_prompt.py")

    assert context_flow.STEP_INSTRUCTION_CONTEXT_SCHEMA is context_schemas.STEP_INSTRUCTION_CONTEXT_SCHEMA
    assert context_flow.ITERATION_SUMMARY_SCHEMA is context_schemas.ITERATION_SUMMARY_SCHEMA
    assert context_flow.output_contract_prompt is context_prompt_contracts.output_contract_prompt
    assert context_flow.system_prompt_prefix is context_prompt_contracts.system_prompt_prefix
    assert "STEP_INSTRUCTION_CONTEXT_SCHEMA = {" not in context_flow_source
    assert "ITERATION_SUMMARY_SCHEMA = {" not in context_flow_source
    assert all(
        marker in context_schema_boundary_source
        for marker in ("STEP_INSTRUCTION_CONTEXT_SCHEMA = {", "ITERATION_SUMMARY_SCHEMA = {")
    )
    assert all(
        marker in context_schemas_source
        for marker in ("from loopora.context_schema_runtime import", "from loopora.context_schema_shared import")
    )
    assert "def output_contract_prompt" not in context_flow_source
    assert "def system_prompt_prefix" not in context_flow_source
    assert "def output_contract_prompt" in context_prompt_contracts_source
    assert "def system_prompt_prefix" in context_prompt_contracts_source
    assert "from loopora.context_prompt_contracts import" in headless_prompt_source
    assert "def build_step_instruction_context" in context_flow_source
    assert "def build_step_instruction_context" not in context_schemas_source


def test_context_flow_delegates_prompt_sections() -> None:
    from loopora import context_flow
    from loopora import context_prompt_sections

    context_flow_source = loopora_source("context_flow.py")
    context_prompt_sections_source = loopora_source("context_prompt_sections.py")
    headless_prompt_source = loopora_source("headless_prompt.py")

    assert context_flow.render_iteration_section is context_prompt_sections.render_iteration_section
    assert context_flow.render_evidence_section is context_prompt_sections.render_evidence_section
    assert context_flow.render_artifact_refs is context_prompt_sections.render_artifact_refs
    assert "def render_iteration_section" not in context_flow_source
    assert "def render_evidence_section" not in context_flow_source
    assert "def render_artifact_refs" not in context_flow_source
    assert "def render_iteration_section" in context_prompt_sections_source
    assert "def render_evidence_section" in context_prompt_sections_source
    assert "def render_artifact_refs" in context_prompt_sections_source
    assert "from loopora.context_value_helpers import clean_text as _clean_text" in context_prompt_sections_source
    assert "from loopora.context_prompt_sections import" in headless_prompt_source


def test_context_prompt_evidence_sections_have_dedicated_boundary() -> None:
    prompt_sections_source = loopora_source("context_prompt_sections.py")
    evidence_sections_source = loopora_source("context_prompt_evidence_sections.py")
    design_source = design_contracts_source()

    assert "from loopora.context_prompt_evidence_sections import" in prompt_sections_source
    assert "def render_evidence_section" in prompt_sections_source
    assert "return _render_evidence_section(evidence)" in prompt_sections_source
    assert "def render_artifact_refs" in prompt_sections_source
    assert "return _render_artifact_refs(refs)" in prompt_sections_source
    for marker in (
        "def _evidence_item_prompt_lines",
        "def _gatekeeper_support_prompt_value",
        "def _manifest_claims_by_id",
        "def _manifest_summary_prompt_line",
        "def _manifest_claim_prompt_lines",
        "def _prompt_bool",
        "def _artifact_ref_prompt_paths",
        "def _int_value",
    ):
        assert marker in evidence_sections_source
        assert marker not in prompt_sections_source
    for import_marker in (
        "from loopora.evidence_support import evidence_item_is_supporting_gatekeeper_ref",
        "from loopora.residual_risk_support import residual_risk_is_meaningful",
        "from loopora.structured_booleans import structured_bool_is_true",
        "from loopora.structured_numbers import structured_non_negative_int",
    ):
        assert import_marker in evidence_sections_source
        assert import_marker not in prompt_sections_source
    assert "context_prompt_evidence_sections.py" in design_source
