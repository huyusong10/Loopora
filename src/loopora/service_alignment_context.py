from __future__ import annotations

import re
from hashlib import sha256


def alignment_source_option_id(source_type: str, identifier: object) -> str:
    normalized_identifier = str(identifier or "").strip()
    if source_type == "spec_file":
        digest = sha256(normalized_identifier.encode("utf-8")).hexdigest()[:16]
        return f"spec_file:{digest}"
    safe_identifier = re.sub(r"[^A-Za-z0-9_.:-]+", "-", normalized_identifier).strip("-")
    return f"{source_type}:{safe_identifier}"


def alignment_context_title_preview(content: str, *, limit: int = 80) -> str:
    text = " ".join(str(content or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
