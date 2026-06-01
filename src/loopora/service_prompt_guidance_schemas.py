from __future__ import annotations


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
