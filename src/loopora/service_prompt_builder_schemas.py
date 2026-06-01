from __future__ import annotations


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
