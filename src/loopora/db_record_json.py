from __future__ import annotations

import json


def json_dict(raw_value: object) -> dict:
    try:
        value = json.loads(str(raw_value or "{}"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
