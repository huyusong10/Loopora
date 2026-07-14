from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import threading

from loopora.service_types import LooporaError, LooporaWorkdirUnavailableError

PATH_PROBE_ERRORS = (OSError, RuntimeError, ValueError)
WORKDIR_SCOPE_ERROR = "workdir is outside the active isolated workspace"

_WORKDIR_SCOPE_LOCK = threading.RLock()
_ACTIVE_WORKDIR_SCOPES: dict[object, Path] = {}


@contextmanager
def restricted_workdir_scope(root: Path | str) -> Iterator[Path]:
    scope_root = _normalize_scope_root(root)
    token = object()
    with _WORKDIR_SCOPE_LOCK:
        _ACTIVE_WORKDIR_SCOPES[token] = scope_root
    try:
        yield scope_root
    finally:
        with _WORKDIR_SCOPE_LOCK:
            _ACTIVE_WORKDIR_SCOPES.pop(token, None)


def same_workdir_identity(left: object, right: object) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text or not right_text:
        return False
    if left_text == right_text:
        return True
    try:
        return Path(left_text).expanduser().resolve(strict=False) == Path(right_text).expanduser().resolve(strict=False)
    except PATH_PROBE_ERRORS:
        return False


def input_path_state(path: Path | str | None, *, label: str) -> dict[str, object]:
    if path is None or (isinstance(path, str) and not path.strip()):
        return {"status": "required", "path": "", "error": f"{label} is required"}
    try:
        raw_path = Path(path).expanduser()
        resolved = raw_path.resolve(strict=False)
        exists = resolved.exists()
        is_dir = resolved.is_dir() if exists else False
        is_file = resolved.is_file() if exists else False
    except PATH_PROBE_ERRORS as exc:
        safe_path = _unavailable_path_text(locals().get("resolved"), locals().get("raw_path"), exc)
        return {
            "status": "unavailable",
            "path": safe_path,
            "error": f"{label} could not be inspected",
        }
    if not exists:
        return {"status": "missing", "path": str(resolved)}
    if is_dir:
        return {"status": "directory", "path": str(resolved)}
    if is_file:
        return {"status": "file", "path": str(resolved)}
    return {"status": "other", "path": str(resolved)}


def _unavailable_path_text(resolved: object, raw_path: object, exc: Exception) -> str:
    if isinstance(exc, (RuntimeError, ValueError)):
        return ""
    safe_path = resolved or raw_path
    return str(safe_path or "")


def normalize_existing_workdir(workdir: Path | str | None) -> Path:
    state = workdir_path_state(workdir)
    if state["status"] == "required":
        raise LooporaError("workdir is required")
    if state["status"] == "unavailable":
        if state.get("error") == WORKDIR_SCOPE_ERROR:
            raise LooporaError("target project is outside the active isolated workspace")
        raise LooporaError("workdir could not be inspected")
    if state["status"] == "not_directory":
        raise LooporaError("workdir path is not a directory")
    if state["status"] != "ready":
        raise LooporaError("workdir does not exist")
    return Path(str(state["workdir"]))


def normalize_recoverable_workdir(workdir: Path | str | None, *, action: str) -> Path:
    state = workdir_path_state(workdir)
    if state["status"] == "ready":
        return Path(str(state["workdir"]))
    if state.get("error") == WORKDIR_SCOPE_ERROR:
        raise LooporaError("target project is outside the active isolated workspace")
    raise LooporaWorkdirUnavailableError(
        workdir=str(state.get("workdir") or ""),
        workdir_state=str(state.get("status") or "unavailable"),
        action=action,
    )


def workdir_path_state(workdir: Path | str | None) -> dict[str, object]:
    state = input_path_state(workdir, label="workdir")
    status = str(state["status"])
    workdir_state = {"status": _workdir_status_from_input_status(status), "workdir": str(state["path"])}
    if state["path"] and _outside_active_workdir_scopes(Path(str(state["path"]))):
        return {
            "status": "unavailable",
            "workdir": str(state["path"]),
            "error": WORKDIR_SCOPE_ERROR,
        }
    if status in {"required", "unavailable"}:
        workdir_state["error"] = str(state.get("error") or "workdir could not be inspected")
    return workdir_state


def _normalize_scope_root(root: Path | str) -> Path:
    state = input_path_state(root, label="isolated workspace")
    if state["status"] != "directory":
        raise LooporaError("isolated workspace must be an existing directory")
    return Path(str(state["path"]))


def _outside_active_workdir_scopes(candidate: Path) -> bool:
    with _WORKDIR_SCOPE_LOCK:
        roots = tuple(_ACTIVE_WORKDIR_SCOPES.values())
    if not roots:
        return False
    try:
        resolved = candidate.expanduser().resolve(strict=False)
    except PATH_PROBE_ERRORS:
        return True
    return any(not resolved.is_relative_to(root) for root in roots)


def spec_path_state(spec_path: Path | str | None) -> dict[str, object]:
    state = input_path_state(spec_path, label="spec path")
    status = str(state["status"])
    spec_state = {"status": _spec_status_from_input_status(status), "spec_path": str(state["path"])}
    if status in {"required", "unavailable"}:
        spec_state["error"] = str(state.get("error") or "spec path could not be inspected")
    return spec_state


def normalize_existing_spec_path(spec_path: Path | str | None) -> Path:
    state = spec_path_state(spec_path)
    status = str(state["status"])
    if status == "ready":
        return Path(str(state["spec_path"]))
    if status == "required":
        raise LooporaError("spec path is required")
    if status == "unavailable":
        raise LooporaError("spec path could not be inspected")
    if status == "not_file":
        raise LooporaError("spec path is not a file")
    raise LooporaError("spec does not exist")


def _spec_status_from_input_status(status: str) -> str:
    if status == "required":
        return "required"
    if status == "file":
        return "ready"
    if status in {"directory", "other"}:
        return "not_file"
    if status == "unavailable":
        return "unavailable"
    return "missing"


def _workdir_status_from_input_status(status: str) -> str:
    if status == "required":
        return "required"
    if status == "directory":
        return "ready"
    if status == "unavailable":
        return "unavailable"
    if status == "missing":
        return "missing"
    return "not_directory"
