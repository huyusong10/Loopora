from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_incident_root_cause_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    repro_verifies = _dedupe_values(
        [
            "root-cause-repro",
            "negative_evidence",
            "task_anchor",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    monitoring_verifies = _dedupe_values(
        [
            "root-cause-repro",
            "monitoring",
            "negative_evidence",
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
            "root-cause-repro",
            "monitoring",
            "negative_evidence",
            "local-governance",
            *projection.evidence_verifies,
        ]
    )
    workflow = bundle["workflow"]
    workflow["preset"] = "incident-root-cause-repro"
    workflow_intents._replace_incident_root_cause_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "repro_inspector", "role_definition_key": "repro-inspector"},
        {"id": "incident_builder", "role_definition_key": "incident-root-cause-builder"},
        {"id": "monitoring_inspector", "role_definition_key": "monitoring-evidence-inspector"},
        {"id": "incident_gatekeeper", "role_definition_key": "incident-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "repro_inspection_step", "role_id": "repro_inspector", "on_pass": "continue"},
        {
            "id": "incident_builder_step",
            "role_id": "incident_builder",
            "inputs": {
                "handoffs_from": ["repro_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": repro_verifies,
                    "limit": 20,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "monitoring_inspection_step",
            "role_id": "monitoring_inspector",
            "inputs": {
                "handoffs_from": ["repro_inspection_step", "incident_builder_step"],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": monitoring_verifies,
                    "limit": 32,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "incident_gatekeeper_step",
            "role_id": "incident_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "repro_inspection_step",
                    "incident_builder_step",
                    "monitoring_inspection_step",
                ],
                "evidence_query": {
                    "archetypes": ["inspector", "builder"],
                    "verifies": gatekeeper_verifies,
                    "limit": 40,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
