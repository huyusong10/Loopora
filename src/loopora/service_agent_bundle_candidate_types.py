from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

AGENT_ALIGNMENT_CONTINUATION_ACTIVE_STATUSES = {"running", "validating", "repairing"}
AGENT_ALIGNMENT_CONTINUATION_TERMINAL_STATUSES = {"ready", "imported", "running_loop", "skipped"}
AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR = "candidate plan file could not be saved"


@dataclass(frozen=True)
class AgentBundleCandidateRequest:
    adapter: str
    workdir: Path | str
    message: str = ""
    bundle_yaml: str = ""
    bundle_file: Path | str | None = None
    context_id: str = ""
    entry_source: str = ""


@dataclass(frozen=True)
class AgentAlignmentContinuationRequest:
    adapter: str
    root: Path
    task_message: str
    entry_source: str
    host_context_id: str
    context_id: str
    existing_binding: dict[str, Any]
    candidate_provenance: dict[str, Any]
    loopora_fit_contradiction: bool
