from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEV_CHECK_SCHEMA_VERSION = 3
DEFAULT_FAST_PROFILE = "default-fast"
FOCUSED_PROFILE = "focused"


@dataclass(frozen=True)
class ChangedFileDetection:
    files: list[str]
    source: str
    status: str
    ignored_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class DevCheckCommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class DevCheckReportContext:
    workdir: Path
    profile: str
    status: str
    changed_file_detection: ChangedFileDetection
    focused_selection: str = ""
    selected_focused_guides: tuple[dict[str, Any], ...] = ()
    focused_ran_tokens: tuple[str, ...] = ()
