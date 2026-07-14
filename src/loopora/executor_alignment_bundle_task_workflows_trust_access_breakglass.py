from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection
from loopora.executor_alignment_bundle_task_visible_scaffolds_trust import (
    _replace_support_impersonation_visible_scaffold,
)


def _replace_support_impersonation_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    projection_verifies = [
        verify for verify in projection.evidence_verifies if verify not in {"deletion-retention", "experiment-assignment", "message-delivery"}
    ]
    policy_verifies = _dedupe_values(
        [
            "support-impersonation",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "audit-integrity",
            "session-lifecycle",
            "monitoring",
            "data-export",
            "eval-set",
            "task_anchor",
            "local-governance",
            *projection_verifies,
        ]
    )
    evidence_verifies = _dedupe_values(
        [
            "support-impersonation",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "audit-integrity",
            "session-lifecycle",
            "monitoring",
            "data-export",
            "eval-set",
            "negative_evidence",
            "local-governance",
            *projection_verifies,
        ]
    )
    gatekeeper_verifies = _dedupe_values(
        [
            "done_when",
            "fake_done",
            "evidence_buckets",
            "residual_risk",
            "support-impersonation",
            "permission-auth",
            "tenant-isolation",
            "privacy-redaction",
            "audit-integrity",
            "session-lifecycle",
            "monitoring",
            "data-export",
            "eval-set",
            "local-governance",
            *projection_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "support-impersonation-policy-first"
    _replace_support_impersonation_visible_scaffold(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow_intents._replace_support_impersonation_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "breakglass_policy_inspector", "role_definition_key": "breakglass-policy-inspector"},
        {"id": "breakglass_builder", "role_definition_key": "breakglass-builder"},
        {"id": "access_evidence_inspector", "role_definition_key": "access-evidence-inspector"},
        {"id": "breakglass_gatekeeper", "role_definition_key": "breakglass-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "breakglass_policy_inspection_step", "role_id": "breakglass_policy_inspector", "on_pass": "continue"},
        {
            "id": "breakglass_builder_step",
            "role_id": "breakglass_builder",
            "inputs": {
                "handoffs_from": ["breakglass_policy_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": policy_verifies,
                    "limit": 32,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "access_evidence_inspection_step",
            "role_id": "access_evidence_inspector",
            "inputs": {
                "handoffs_from": ["breakglass_policy_inspection_step", "breakglass_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": evidence_verifies,
                    "limit": 40,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "breakglass_gatekeeper_step",
            "role_id": "breakglass_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "breakglass_policy_inspection_step",
                    "breakglass_builder_step",
                    "access_evidence_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 48,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]


__all__ = ("_replace_support_impersonation_task_workflow",)
