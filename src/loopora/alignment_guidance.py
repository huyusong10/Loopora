from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import yaml

from loopora.system_prompt_assets import load_system_prompt_asset


@dataclass(frozen=True)
class AlignmentGuidanceAssets:
    source_dir: Path
    system_prompt_template: str
    compiler_gates: str
    compiler_policy: str
    product_primer: str
    alignment_playbook: str
    quality_rubric: str
    bundle_contract: str
    examples: str
    example_selection: dict
    bundle_scenario_fixtures: dict
    improvement_bundle_fixtures: dict
    localized_base_bundle_overrides: dict
    refund_bundle_fixtures: dict
    task_domain_projection: dict
    task_role_fixtures: dict
    task_role_governance: dict
    task_spec_scaffold_templates: dict
    task_spec_workflow_notes: dict
    task_visible_scaffolds: dict
    task_workflow_intents: dict
    preconfirmation_fixtures: dict
    readiness_issue_fixtures: dict
    specialized_workflow_display_names: dict
    feedback_improvement: str
    repair_input_template: str
    current_bundle_template: str
    selected_source_context_template: str
    selected_spec_markdown_template: str
    bundle_improvement_context_template: str


def alignment_guidance_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / "alignment"


def alignment_system_prompt_asset_ref() -> str:
    return "alignment/web-alignment-agent.md"


def _read_guidance_asset(source_dir: Path, name: str) -> str:
    return (source_dir / name).read_text(encoding="utf-8")


def _read_guidance_json_asset(source_dir: Path, name: str) -> dict:
    try:
        value = json.loads(_read_guidance_asset(source_dir, name))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid alignment guidance JSON asset: {name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"alignment guidance JSON asset must decode to an object: {name}")
    return value


def _read_guidance_yaml_asset(source_dir: Path, name: str) -> dict:
    try:
        value = yaml.safe_load(_read_guidance_asset(source_dir, name)) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid alignment guidance YAML asset: {name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"alignment guidance YAML asset must decode to an object: {name}")
    return value


def load_alignment_guidance_assets() -> AlignmentGuidanceAssets:
    source_dir = alignment_guidance_dir()
    return AlignmentGuidanceAssets(
        source_dir=source_dir,
        system_prompt_template=load_system_prompt_asset(alignment_system_prompt_asset_ref()),
        compiler_gates=_read_guidance_asset(source_dir, "compiler-gates.md"),
        compiler_policy=_read_guidance_asset(source_dir, "compiler-policy.md"),
        product_primer=_read_guidance_asset(source_dir, "product-primer.md"),
        alignment_playbook=_read_guidance_asset(source_dir, "alignment-playbook.md"),
        quality_rubric=_read_guidance_asset(source_dir, "quality-rubric.md"),
        bundle_contract=_read_guidance_asset(source_dir, "bundle-contract.md"),
        examples=_read_guidance_asset(source_dir, "examples.md"),
        example_selection=_read_guidance_json_asset(source_dir, "example-selection.json"),
        bundle_scenario_fixtures=_read_guidance_json_asset(source_dir, "bundle-scenario-fixtures.json"),
        improvement_bundle_fixtures=_read_guidance_yaml_asset(source_dir, "improvement-bundle-fixtures.yml"),
        localized_base_bundle_overrides=_read_guidance_yaml_asset(source_dir, "localized-base-bundle-overrides.yml"),
        refund_bundle_fixtures=_read_guidance_yaml_asset(source_dir, "refund-bundle-fixtures.yml"),
        task_domain_projection=_read_guidance_json_asset(source_dir, "task-domain-projection.json"),
        task_role_fixtures=_read_guidance_json_asset(source_dir, "task-role-fixtures.json"),
        task_role_governance=_read_guidance_json_asset(source_dir, "task-role-governance.json"),
        task_spec_scaffold_templates=_read_guidance_json_asset(source_dir, "task-spec-scaffold-templates.json"),
        task_spec_workflow_notes=_read_guidance_json_asset(source_dir, "task-spec-workflow-notes.json"),
        task_visible_scaffolds=_read_guidance_json_asset(source_dir, "task-visible-scaffolds.json"),
        task_workflow_intents=_read_guidance_json_asset(source_dir, "task-workflow-intents.json"),
        preconfirmation_fixtures=_read_guidance_json_asset(source_dir, "preconfirmation-scenario-fixtures.json"),
        readiness_issue_fixtures=_read_guidance_json_asset(source_dir, "readiness-issue-fixtures.json"),
        specialized_workflow_display_names=_read_guidance_json_asset(source_dir, "specialized-workflow-display-names.json"),
        feedback_improvement=_read_guidance_asset(source_dir, "feedback-improvement.md"),
        repair_input_template=_read_guidance_asset(source_dir, "repair-input.md"),
        current_bundle_template=_read_guidance_asset(source_dir, "current-bundle.md"),
        selected_source_context_template=_read_guidance_asset(source_dir, "selected-source-context.md"),
        selected_spec_markdown_template=_read_guidance_asset(source_dir, "selected-spec-markdown.md"),
        bundle_improvement_context_template=_read_guidance_asset(source_dir, "bundle-improvement-context.md"),
    )
