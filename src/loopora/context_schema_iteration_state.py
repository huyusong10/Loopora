from __future__ import annotations

from loopora.context_schema_evidence import (
    EVIDENCE_COVERAGE_GAP_SCHEMA,
    EVIDENCE_COVERAGE_RESULT_SCHEMA,
)
from loopora.context_schema_shared import (
    STEP_HANDOFF_SCHEMA,
)

ITERATION_SUMMARY_SCHEMA = {
    "type": "object",
    "required": ["phase", "iter", "timestamp", "workflow", "step_handoffs", "score", "gatekeeper_verdict", "stagnation", "latest_refs"],
    "properties": {
        "phase": {"type": "string"},
        "iter": {"type": "integer"},
        "timestamp": {"type": "string"},
        "workflow": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "step_id",
                    "role_id",
                    "role_name",
                    "runtime_role",
                    "archetype",
                    "model",
                    "status",
                    "parallel_group",
                ],
                "properties": {
                    "step_id": {"type": "string"},
                    "role_id": {"type": "string"},
                    "role_name": {"type": "string"},
                    "runtime_role": {"type": "string"},
                    "archetype": {"type": "string"},
                    "model": {"type": "string"},
                    "status": {"type": "string"},
                    "parallel_group": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "step_handoffs": {"type": "array", "items": STEP_HANDOFF_SCHEMA},
        "score": {
            "type": "object",
            "required": ["composite", "delta", "passed"],
            "properties": {
                "composite": {"type": ["number", "null"]},
                "delta": {"type": ["number", "null"]},
                "passed": {"type": ["boolean", "null"]},
            },
            "additionalProperties": False,
        },
        "gatekeeper_verdict": {
            "type": "object",
            "required": [
                "passed",
                "decision_summary",
                "blocking_issues",
                "feedback_to_builder",
                "evidence_refs",
                "evidence_claims",
                "residual_risks",
                "coverage_results",
            ],
            "properties": {
                "passed": {"type": ["boolean", "null"]},
                "decision_summary": {"type": "string"},
                "blocking_issues": {"type": "array", "items": {"type": "string"}},
                "feedback_to_builder": {"type": "string"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "evidence_claims": {"type": "array", "items": {"type": "string"}},
                "residual_risks": {"type": "array", "items": {"type": "string"}},
                "coverage_results": {"type": "array", "items": EVIDENCE_COVERAGE_RESULT_SCHEMA},
            },
            "additionalProperties": False,
        },
        "stagnation": {
            "type": "object",
            "required": [
                "mode",
                "evidence_progress_mode",
                "recent_composites",
                "recent_deltas",
                "consecutive_low_delta",
                "coverage_status",
                "covered_check_count",
                "missing_check_count",
                "covered_check_ids",
                "missing_check_ids",
                "coverage_top_gaps",
                "consecutive_no_required_coverage_delta",
            ],
            "properties": {
                "mode": {"type": "string"},
                "evidence_progress_mode": {"type": "string"},
                "recent_composites": {"type": "array", "items": {"type": "number"}},
                "recent_deltas": {"type": "array", "items": {"type": "number"}},
                "consecutive_low_delta": {"type": "integer"},
                "coverage_status": {"type": "string"},
                "covered_check_count": {"type": "integer"},
                "missing_check_count": {"type": "integer"},
                "covered_check_ids": {"type": "array", "items": {"type": "string"}},
                "missing_check_ids": {"type": "array", "items": {"type": "string"}},
                "coverage_top_gaps": {"type": "array", "items": EVIDENCE_COVERAGE_GAP_SCHEMA},
                "consecutive_no_required_coverage_delta": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "latest_refs": {
            "type": "object",
            "required": ["summary_path", "latest_gatekeeper", "latest_by_step", "latest_by_role", "latest_by_archetype"],
            "properties": {
                "summary_path": {"type": "string"},
                "latest_gatekeeper": {"type": ["string", "null"]},
                "latest_by_step": {"type": "object"},
                "latest_by_role": {"type": "object"},
                "latest_by_archetype": {"type": "object"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

LATEST_STATE_SCHEMA = {
    "type": "object",
    "required": [
        "latest_iteration",
        "latest_by_step",
        "latest_by_role",
        "latest_by_archetype",
        "latest_gatekeeper",
        "latest_summary_path",
    ],
    "properties": {
        "latest_iteration": {"type": ["integer", "null"]},
        "latest_by_step": {"type": "object"},
        "latest_by_role": {"type": "object"},
        "latest_by_archetype": {"type": "object"},
        "latest_gatekeeper": {"type": ["string", "null"]},
        "latest_summary_path": {"type": "string"},
    },
    "additionalProperties": False,
}
