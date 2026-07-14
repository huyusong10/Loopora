from __future__ import annotations

import json
from pathlib import Path

from loopora.service_types import LooporaError

RESULT_FILE_MISSING_ERROR = "result file is missing"
RESULT_FILE_UNREADABLE_ERROR = "result file could not be read"
RESULT_FILE_INVALID_JSON_ERROR = "result file must contain valid JSON"
RESULT_FILE_OBJECT_ERROR = "result file must contain one JSON object"


def read_result_file_object(path: Path) -> dict:
    try:
        if path.is_dir():
            raise IsADirectoryError
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LooporaError(RESULT_FILE_MISSING_ERROR) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise LooporaError(RESULT_FILE_UNREADABLE_ERROR) from exc
    except json.JSONDecodeError as exc:
        raise LooporaError(RESULT_FILE_INVALID_JSON_ERROR) from exc
    if not isinstance(payload, dict):
        raise LooporaError(RESULT_FILE_OBJECT_ERROR)
    return payload
