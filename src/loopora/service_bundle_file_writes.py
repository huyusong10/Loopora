from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from uuid import uuid4


def write_bundle_text_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{uuid4().hex}")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except Exception:
        with suppress(OSError):
            tmp.unlink()
        raise
