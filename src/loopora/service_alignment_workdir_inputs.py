from __future__ import annotations

from pathlib import Path

from loopora.workdir_inputs import normalize_recoverable_workdir


def normalize_alignment_workdir(workdir: Path) -> Path:
    return normalize_recoverable_workdir(workdir, action="alignment")
