from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_prompt_asset_ownership_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    contract_verifies = _dedupe_values(
        [
            "prompt-asset-ownership",
            "system-prompt-loading",
            "locale-neutrality",
            "strategy-source-boundary",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    ownership_verifies = _dedupe_values(
        [
            "prompt-asset-ownership",
            "system-prompt-loading",
            "locale-neutrality",
            "static-asset-refs",
            "negative_evidence",
            "strategy-source-boundary",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    rendering_verifies = _dedupe_values(
        [
            "runtime-rendering",
            "placeholder-safety",
            "system-prompt-loading",
            "backward-compatibility",
            "strategy-source-boundary",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    gatekeeper_verifies = _dedupe_values(
        [
            "done_when",
            "fake_done",
            "evidence_buckets",
            "residual_risk",
            "prompt-asset-ownership",
            "system-prompt-loading",
            "locale-neutrality",
            "runtime-rendering",
            "placeholder-safety",
            "static-asset-refs",
            "strategy-source-boundary",
            "backward-compatibility",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "prompt-asset-ownership-contract-parallel-rendering"
    workflow_intents._replace_prompt_asset_ownership_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "prompt_surface_contract_inspector", "role_definition_key": "prompt-surface-contract-inspector"},
        {"id": "prompt_asset_builder", "role_definition_key": "prompt-asset-builder"},
        {"id": "prompt_asset_ownership_inspector", "role_definition_key": "prompt-asset-ownership-inspector"},
        {"id": "runtime_prompt_rendering_inspector", "role_definition_key": "runtime-prompt-rendering-inspector"},
        {"id": "prompt_asset_gatekeeper", "role_definition_key": "prompt-asset-gatekeeper"},
    ]
    workflow["steps"] = [
        {
            "id": "prompt_surface_contract_inspection_step",
            "role_id": "prompt_surface_contract_inspector",
            "on_pass": "continue",
        },
        {
            "id": "prompt_asset_builder_step",
            "role_id": "prompt_asset_builder",
            "inputs": {
                "handoffs_from": ["prompt_surface_contract_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": contract_verifies,
                    "limit": 36,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "prompt_asset_ownership_inspection_step",
            "role_id": "prompt_asset_ownership_inspector",
            "parallel_group": "prompt_asset_review_pack",
            "inputs": {
                "handoffs_from": ["prompt_surface_contract_inspection_step", "prompt_asset_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": ownership_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "runtime_prompt_rendering_inspection_step",
            "role_id": "runtime_prompt_rendering_inspector",
            "parallel_group": "prompt_asset_review_pack",
            "inputs": {
                "handoffs_from": ["prompt_surface_contract_inspection_step", "prompt_asset_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": rendering_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "prompt_asset_gatekeeper_step",
            "role_id": "prompt_asset_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "prompt_surface_contract_inspection_step",
                    "prompt_asset_builder_step",
                    "prompt_asset_ownership_inspection_step",
                    "runtime_prompt_rendering_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 60,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
