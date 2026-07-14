from __future__ import annotations

from pathlib import Path, PureWindowsPath

from loopora.file_previews import preview_existing_path
from loopora.local_workdir_artifacts import state_dir_for_ready_workdir
from loopora.service_types import LooporaError
from loopora.workdir_inputs import workdir_path_state


class ServiceRunFileAccessMixin:
    def _file_root_base(self, run: dict, root: str) -> Path:
        if root == "workdir":
            state = workdir_path_state(run.get("workdir"))
            if state["status"] != "ready":
                raise LooporaError("run workdir is not available")
            return Path(str(state["workdir"]))
        if root == "loopora":
            base = state_dir_for_ready_workdir(run.get("workdir"))
            if base is None:
                raise LooporaError("run workdir is not available")
            return base
        raise LooporaError("invalid file root")

    def _resolve_file_path(self, run_id: str, root: str, relative_path: str) -> tuple[Path, Path]:
        run = self.get_run(run_id)
        base = self._file_root_base(run, root)
        requested_path = _normalize_requested_relative_path(relative_path)
        base_resolved = base.resolve()
        resolved = (base_resolved / requested_path).resolve()
        if not resolved.is_relative_to(base_resolved):
            raise LooporaError("requested path is outside the allowed root")
        if not resolved.exists():
            raise LooporaError("requested path does not exist")
        return base_resolved, resolved

    def preview_file(self, run_id: str, root: str, relative_path: str = "") -> dict:
        base, resolved = self._resolve_file_path(run_id, root, relative_path)
        return preview_existing_path(base=base, relative_path=relative_path, resolved=resolved)

    def download_file_path(self, run_id: str, root: str, relative_path: str = "") -> Path:
        _base, resolved = self._resolve_file_path(run_id, root, relative_path)
        if not resolved.is_file():
            raise LooporaError("path is not a file")
        try:
            with resolved.open("rb"):
                pass
        except OSError as exc:
            raise LooporaError("file could not be downloaded") from exc
        return resolved


def _normalize_requested_relative_path(relative_path: str) -> str:
    path_text = str(relative_path or "").strip()
    windows_path = PureWindowsPath(path_text)
    if Path(path_text).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise LooporaError("requested path must be relative")
    return path_text
