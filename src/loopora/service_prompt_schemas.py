from __future__ import annotations

COVERAGE_RESULT_ARRAY_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["target_id", "status", "evidence_refs", "note"],
        "properties": {
            "target_id": {"type": "string"},
            "status": {"type": "string", "enum": ["covered", "weak", "blocked", "missing"]},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "note": {"type": "string"},
        },
        "additionalProperties": False,
    },
}

TESTER_SCHEMA = {
    "type": "object",
    "required": ["execution_summary", "check_results", "dynamic_checks", "tester_observations", "coverage_results"],
    "properties": {
        "execution_summary": {
            "type": "object",
            "required": ["total_checks", "passed", "failed", "errored", "total_duration_ms"],
            "properties": {
                "total_checks": {"type": "integer"},
                "passed": {"type": "integer"},
                "failed": {"type": "integer"},
                "errored": {"type": "integer"},
                "total_duration_ms": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "check_results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "status", "notes"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {"type": "string", "enum": ["passed", "failed", "errored", "skipped"]},
                    "notes": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "dynamic_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "status", "notes"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {"type": "string", "enum": ["passed", "failed", "errored", "skipped"]},
                    "notes": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "tester_observations": {"type": "string"},
        "coverage_results": COVERAGE_RESULT_ARRAY_SCHEMA,
    },
    "additionalProperties": False,
}

VERIFIER_SCHEMA = {
    "type": "object",
    "required": [
        "passed",
        "decision_summary",
        "composite_score",
        "metrics",
        "metric_scores",
        "blocking_issues",
        "hard_constraint_violations",
        "failed_check_ids",
        "priority_failures",
        "feedback_to_builder",
        "feedback_to_generator",
        "evidence_refs",
        "evidence_claims",
        "residual_risks",
        "coverage_results",
    ],
    "properties": {
        "passed": {"type": "boolean"},
        "decision_summary": {"type": "string"},
        "composite_score": {"type": "number"},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "value", "threshold", "passed"],
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "number"},
                    "threshold": {"type": "number"},
                    "passed": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        "metric_scores": {
            "type": "object",
            "required": ["check_pass_rate", "quality_score"],
            "properties": {
                "check_pass_rate": {
                    "type": "object",
                    "required": ["value", "threshold", "passed"],
                    "properties": {
                        "value": {"type": "number"},
                        "threshold": {"type": "number"},
                        "passed": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
                "quality_score": {
                    "type": "object",
                    "required": ["value", "threshold", "passed"],
                    "properties": {
                        "value": {"type": "number"},
                        "threshold": {"type": "number"},
                        "passed": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
        "blocking_issues": {"type": "array", "items": {"type": "string"}},
        "hard_constraint_violations": {"type": "array", "items": {"type": "string"}},
        "failed_check_ids": {"type": "array", "items": {"type": "string"}},
        "priority_failures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["error_code", "summary"],
                "properties": {
                    "error_code": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "feedback_to_builder": {"type": "string"},
        "feedback_to_generator": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "evidence_claims": {"type": "array", "items": {"type": "string"}},
        "residual_risks": {"type": "array", "items": {"type": "string"}},
        "coverage_results": COVERAGE_RESULT_ARRAY_SCHEMA,
    },
    "additionalProperties": False,
}

INSPECTOR_SCHEMA = TESTER_SCHEMA

GATEKEEPER_SCHEMA = VERIFIER_SCHEMA


CHALLENGER_SCHEMA = {
    "type": "object",
    "required": ["created_at_iter", "mode", "consumed", "analysis", "seed_question", "meta_note"],
    "properties": {
        "created_at_iter": {"type": "integer"},
        "mode": {"type": "string"},
        "consumed": {"type": "boolean"},
        "analysis": {
            "type": "object",
            "required": ["stagnation_pattern", "recommended_shift", "risk_note"],
            "properties": {
                "stagnation_pattern": {"type": "string"},
                "recommended_shift": {"type": "string"},
                "risk_note": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "seed_question": {"type": "string"},
        "meta_note": {"type": "string"},
    },
    "additionalProperties": False,
}

CUSTOM_SCHEMA = {
    "type": "object",
    "required": [
        "status",
        "summary",
        "blocking_items",
        "recommended_next_action",
        "observations",
        "recommendations",
        "risks",
        "handoff_note",
    ],
    "properties": {
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "blocking_items": {"type": "array", "items": {"type": "string"}},
        "recommended_next_action": {"type": "string"},
        "observations": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "handoff_note": {"type": "string"},
    },
    "additionalProperties": False,
}

GUIDE_SCHEMA = CHALLENGER_SCHEMA

GENERATOR_SCHEMA = {
    "type": "object",
    "required": [
        "attempted",
        "abandoned",
        "assumption",
        "summary",
        "changed_files",
        "proof_files",
        "proof_artifacts",
        "artifact_paths",
    ],
    "properties": {
        "attempted": {"type": "string", "description": "What the Builder changed or tried to change in this pass."},
        "abandoned": {
            "type": "string",
            "description": "Only unfinished work or real downstream risk; use an empty string for deliberate scope limits.",
        },
        "assumption": {
            "type": "string",
            "description": "The assumption or validation step downstream roles should check next.",
        },
        "summary": {"type": "string", "description": "Short user-facing handoff summary of the completed Builder pass."},
        "changed_files": {"type": "array", "items": {"type": "string"}, "description": "Workspace files changed by this pass."},
        "proof_files": {"type": "array", "items": {"type": "string"}, "description": "Files containing reproducible proof or checks."},
        "proof_artifacts": {"type": "array", "items": {"type": "string"}, "description": "Small inline proof snippets or artifact labels."},
        "artifact_paths": {"type": "array", "items": {"type": "string"}, "description": "Additional workspace artifact paths."},
    },
    "additionalProperties": False,
}

CHECK_PLANNER_SCHEMA = {
    "type": "object",
    "required": ["checks", "generation_notes"],
    "properties": {
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "details", "when", "expect", "fail_if"],
                "properties": {
                    "title": {"type": "string"},
                    "details": {"type": "string"},
                    "when": {"type": "string"},
                    "expect": {"type": "string"},
                    "fail_if": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "generation_notes": {"type": "string"},
    },
    "additionalProperties": False,
}

BUILDER_SCHEMA = GENERATOR_SCHEMA
