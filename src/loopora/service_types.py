from __future__ import annotations

from loopora.recovery import RecoveryResult

COMPLETION_MODES = ("gatekeeper", "rounds")
TERMINAL_RUN_STATUSES = frozenset({"succeeded", "failed", "stopped"})
ACTIVE_RUN_STATUSES = frozenset({"queued", "running", "awaiting_agent"})
ACTIVE_WORKDIR_CONFLICT_PREFIX = "another active run is already using"
ACTIVE_WORKDIR_CONFLICT_MESSAGE = f"{ACTIVE_WORKDIR_CONFLICT_PREFIX} the target workdir"


class LooporaError(RuntimeError):
    """Domain error surfaced to CLI and API consumers."""

    status_code = 400


class LooporaNotFoundError(LooporaError):
    """Raised when a stable domain resource cannot be found."""

    status_code = 404


class LooporaConflictError(LooporaError):
    """Raised when a request conflicts with active lifecycle state."""

    status_code = 409


class LooporaWorkdirUnavailableError(LooporaError):
    """Raised when a recoverable target project path is not usable."""

    def __init__(self, *, workdir: str, workdir_state: str, action: str = "run") -> None:
        self.workdir = workdir
        self.workdir_state = workdir_state
        self.action = action
        self.summary = _workdir_unavailable_summary(workdir_state, action=action)
        super().__init__(_workdir_unavailable_message(action, self.summary))


def _workdir_unavailable_message(action: str, summary: str) -> str:
    if action == "run":
        return f"target project is not ready for a run: {summary}"
    if action == "compose":
        return f"target project is not ready for Loop compose: {summary}"
    if action == "alignment":
        return f"target project is not ready for Alignment: {summary}"
    if action == "agent":
        return f"target project is not ready for same-Agent project entries: {summary}"
    return f"target project is not ready: {summary}"


def _workdir_unavailable_summary(workdir_state: str, *, action: str) -> str:
    action_summaries = {
        "compose": _compose_workdir_unavailable_summary,
        "alignment": _alignment_workdir_unavailable_summary,
        "agent": _agent_workdir_unavailable_summary,
    }
    summary = action_summaries.get(action)
    if summary:
        return summary(workdir_state)
    run_summaries = {
        "required": "Target project directory is missing from this saved Loop; choose a project directory before starting it.",
        "missing": "Target project directory does not exist yet; recreate it before starting this saved Loop.",
        "not_directory": "Target project path exists but is not a directory; choose a project directory before starting this saved Loop.",
        "unavailable": "Target project directory cannot be inspected; choose a readable project directory before starting this saved Loop.",
    }
    return run_summaries.get(workdir_state, "Target project path cannot be used for this saved Loop.")


def _compose_workdir_unavailable_summary(workdir_state: str) -> str:
    if workdir_state == "required":
        return "Target project directory is required; choose a project directory before composing or running a Loop."
    if workdir_state == "missing":
        return "Target project directory does not exist yet; create it before composing or running a Loop."
    if workdir_state == "not_directory":
        return "Target project path exists but is not a directory; choose a project directory before composing or running a Loop."
    if workdir_state == "unavailable":
        return "Target project directory cannot be inspected; choose a readable project directory before composing or running a Loop."
    return "Target project path cannot be used for Loop compose."


def _alignment_workdir_unavailable_summary(workdir_state: str) -> str:
    if workdir_state == "required":
        return "Target project directory is required; choose a project directory before creating an Alignment session."
    if workdir_state == "missing":
        return "Target project directory does not exist yet; create it before creating an Alignment session."
    if workdir_state == "not_directory":
        return "Target project path exists but is not a directory; choose a project directory before creating an Alignment session."
    if workdir_state == "unavailable":
        return "Target project directory cannot be inspected; choose a readable project directory before creating an Alignment session."
    return "Target project path cannot be used for Alignment."


def _agent_workdir_unavailable_summary(workdir_state: str) -> str:
    if workdir_state == "required":
        return "Target project directory is required; choose a project directory before managing Agent entries."
    if workdir_state == "missing":
        return "Target project directory does not exist yet; create it before managing Agent entries."
    if workdir_state == "not_directory":
        return "Target project path exists but is not a directory; choose a project directory for Agent entries."
    if workdir_state == "unavailable":
        return "Target project directory cannot be inspected; choose a readable project directory before managing Agent entries."
    return "Target project path cannot be used for Agent entries."


class RoleExecutionError(LooporaError):
    def __init__(self, role: str, result: RecoveryResult) -> None:
        self.role = role
        self.result = result
        super().__init__(f"role={role} failed after {result.attempts} attempts")


class WorkspaceSafetyError(LooporaError):
    def __init__(self, *, role: str, deleted_paths: list[str], baseline_count: int, current_count: int) -> None:
        self.role = role
        self.deleted_paths = deleted_paths
        self.baseline_count = baseline_count
        self.current_count = current_count
        preview = ", ".join(deleted_paths[:5])
        super().__init__(
            "workspace safety guard blocked a destructive rewrite: "
            f"{len(deleted_paths)} of {baseline_count} original files disappeared"
            + (f" ({preview})" if preview else "")
        )


class StopRequestedError(LooporaError):
    """Raised when a user asked to stop a running loop."""


StopRequested = StopRequestedError


def normalize_completion_mode(value: str | None) -> str:
    mode = str(value or "gatekeeper").strip().lower() or "gatekeeper"
    if mode not in COMPLETION_MODES:
        raise LooporaError(f"unsupported completion mode: {value}")
    return mode
